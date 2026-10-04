r"""
paper_renamer.py

Automatic academic-PDF renamer for Windows.

Default naming:
    YEAR_FirstAuthor_ShortTitle.pdf

Dataset-folder naming:
    YEAR_FirstAuthor_DatasetName.pdf

Examples:
    2023_Mai_Opportunities_Challenges_GeoAI_Foundation_Models.pdf
    2024_Kerner_FieldsOfTheWorld.pdf

USAGE
-----
Watch Downloads continuously:
    python runtime/scripts/paper_renamer.py

Batch-preview a folder:
    python runtime/scripts/paper_renamer.py --folder "research/literature/datasets" --dry-run

Apply batch rename:
    python runtime/scripts/paper_renamer.py --folder "research/literature/datasets"

Dataset mode is automatically enabled for a folder named "Datasets".
You can force it elsewhere with --dataset-mode.

Metadata strategy
-----------------
1. Extract a title candidate from embedded metadata / first-page layout.
2. If arXiv ID exists, query arXiv.
3. Extract ALL DOI candidates, query Crossref, and ACCEPT a DOI only if the
   Crossref title agrees with the PDF's title/arXiv title.
4. Search Crossref by title.
5. Search OpenAlex by title.
6. Fall back to good embedded PDF metadata.

The key safety rule is:
    NEVER trust a DOI merely because it appears in the PDF.
A PDF can contain cited DOIs, proceedings DOIs, dataset DOIs, etc.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import queue
import re
import shutil
import threading
import time
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import quote

import pymupdf
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


# =============================================================================
# DEFAULTS
# =============================================================================

DEFAULT_DOWNLOADS = Path.home() / "Downloads"
DEFAULT_DESTINATION = Path(__file__).resolve().parents[2] / "research" / "literature" / "papers"

MAX_TITLE_WORDS = 9
MAX_FILENAME_LENGTH = 180
REQUEST_TIMEOUT = 15
TITLE_MATCH_THRESHOLD = 0.82
STRICT_DOI_MATCH_THRESHOLD = 0.76

APP_NAME = "StefanoPaperRenamer"
APP_VERSION = "4.0"

LOGGER = logging.getLogger("paper_renamer")


# =============================================================================
# DATA
# =============================================================================

@dataclass(frozen=True)
class PaperMetadata:
    year: str
    author: str
    title: str
    source: str
    confidence: float = 1.0
    doi: str | None = None
    arxiv_id: str | None = None


# =============================================================================
# HTTP
# =============================================================================

def make_http_session() -> requests.Session:
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    session.headers.update(
        {
            "User-Agent": (
                f"{APP_NAME}/{APP_VERSION} "
                "(personal academic metadata client)"
            )
        }
    )
    return session


# =============================================================================
# TEXT / NAMES
# =============================================================================

WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

STOPWORDS = {
    "a", "an", "the", "on", "of", "for", "and", "or",
    "in", "to", "toward", "towards", "with", "from",
}

PHRASE_REPLACEMENTS = [
    (re.compile(r"\bearth observation foundation models?\b", re.I), "EOFMs"),
    (re.compile(r"\bgeospatial foundation models?\b", re.I), "GeoFMs"),
    (re.compile(r"\bgeospatial artificial intelligence\b", re.I), "GeoAI"),
    (re.compile(r"\bearth observation\b", re.I), "EO"),
    (re.compile(r"\bremote sensing\b", re.I), "Remote_Sensing"),
    (re.compile(r"\bfoundation models\b", re.I), "Foundation_Models"),
    (re.compile(r"\bfoundation model\b", re.I), "Foundation_Model"),
    (re.compile(r"\bdeep learning\b", re.I), "DL"),
    (re.compile(r"\bmachine learning\b", re.I), "ML"),
    (re.compile(r"\bstate of the art\b", re.I), "SOTA"),
]


def ascii_text(text: str) -> str:
    return (
        unicodedata.normalize("NFKD", text)
        .encode("ascii", "ignore")
        .decode("ascii")
    )


def sanitize_component(text: str) -> str:
    text = ascii_text(text)
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", text)
    text = re.sub(r"\s+", "_", text.strip())
    text = re.sub(r"_+", "_", text)
    text = text.strip(" ._")
    if text.upper() in WINDOWS_RESERVED:
        text = f"_{text}"
    return text or "Unknown"


def normalize_for_match(text: str) -> str:
    text = ascii_text(text).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def title_similarity(a: str, b: str) -> float:
    a_n = normalize_for_match(a)
    b_n = normalize_for_match(b)
    if not a_n or not b_n:
        return 0.0
    return SequenceMatcher(None, a_n, b_n).ratio()


def short_title(title: str, max_words: int = MAX_TITLE_WORDS) -> str:
    title = " ".join(title.split())
    for pattern, replacement in PHRASE_REPLACEMENTS:
        title = pattern.sub(replacement, title)

    title = re.sub(r"[^\w\s-]", " ", title)
    title = re.sub(r"\s+", " ", title).strip()

    words: list[str] = []
    for token in title.split():
        if token.lower() in STOPWORDS:
            continue
        words.append(token)
        if len(words) >= max_words:
            break

    return sanitize_component("_".join(words))


def surname_from_name(name: str) -> str:
    name = re.sub(r"\s+", " ", name).strip().replace(",", " ")
    parts = [p for p in name.split() if p]
    if not parts:
        return "UnknownAuthor"

    while parts and parts[-1].rstrip(".").lower() in {
        "jr", "sr", "ii", "iii", "iv"
    }:
        parts.pop()

    return sanitize_component(parts[-1] if parts else "UnknownAuthor")


def valid_year(value: object) -> str | None:
    if value is None:
        return None
    match = re.search(r"\b(19|20)\d{2}\b", str(value))
    if not match:
        return None

    year = int(match.group(0))
    if 1980 <= year <= datetime.now().year + 1:
        return str(year)
    return None


def trim_filename(filename: str, max_length: int = MAX_FILENAME_LENGTH) -> str:
    if len(filename) <= max_length:
        return filename
    suffix = ".pdf"
    stem = filename[:-4] if filename.lower().endswith(".pdf") else filename
    return stem[: max_length - len(suffix)].rstrip(" ._-") + suffix


def unique_destination(
    folder: Path,
    filename: str,
    source: Path | None = None,
) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / filename

    if source is not None:
        try:
            if source.resolve() == target.resolve():
                return target
        except OSError:
            pass

    if not target.exists():
        return target

    stem = target.stem
    suffix = target.suffix
    i = 2
    while True:
        candidate = folder / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


# =============================================================================
# PDF EXTRACTION
# =============================================================================

def read_pdf_text(pdf_path: Path, pages: int = 3) -> str:
    with pymupdf.open(pdf_path) as doc:
        return "\n".join(
            doc[i].get_text("text")
            for i in range(min(pages, len(doc)))
        )


def read_pdf_metadata(pdf_path: Path) -> dict[str, str]:
    with pymupdf.open(pdf_path) as doc:
        return dict(doc.metadata or {})


def infer_title_from_first_page(pdf_path: Path) -> str | None:
    """
    Infer likely title from large-font text near the top of page 1.
    Only used as a search/validation hint, never blindly as final metadata.
    """
    with pymupdf.open(pdf_path) as doc:
        if not doc:
            return None
        page = doc[0]
        page_height = page.rect.height
        data = page.get_text("dict")

    candidates: list[tuple[float, float, str]] = []

    for block in data.get("blocks", []):
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue

            text = " ".join(
                span.get("text", "").strip()
                for span in spans
                if span.get("text", "").strip()
            ).strip()

            if len(text) < 4:
                continue

            y0 = min(float(span["bbox"][1]) for span in spans)
            if y0 > page_height * 0.55:
                continue

            max_size = max(float(span.get("size", 0)) for span in spans)
            lowered = text.lower()
            if lowered.startswith(("arxiv:", "doi:", "abstract", "keywords")):
                continue

            candidates.append((max_size, y0, text))

    if not candidates:
        return None

    largest = max(size for size, _, _ in candidates)
    chosen = [
        item for item in candidates
        if item[0] >= largest * 0.80
    ]
    chosen.sort(key=lambda item: item[1])

    title = " ".join(item[2] for item in chosen[:4])
    title = " ".join(title.split()).strip()

    if 8 <= len(title) <= 350:
        return title
    return None


def wait_until_pdf_ready(
    path: Path,
    stable_checks: int = 3,
    delay: float = 1.5,
    max_attempts: int = 40,
) -> bool:
    previous_size = -1
    stable_count = 0

    for _ in range(max_attempts):
        try:
            size = path.stat().st_size
        except (FileNotFoundError, PermissionError):
            time.sleep(delay)
            continue

        if size > 0 and size == previous_size:
            stable_count += 1
        else:
            stable_count = 0

        previous_size = size

        if stable_count >= stable_checks:
            try:
                with pymupdf.open(path) as doc:
                    return len(doc) > 0
            except (pymupdf.FileDataError, RuntimeError, OSError):
                pass

        time.sleep(delay)

    return False


# =============================================================================
# IDENTIFIERS
# =============================================================================

ARXIV_PATTERNS = [
    re.compile(r"\barXiv:(\d{4}\.\d{4,5})(?:v\d+)?\b", re.I),
    re.compile(
        r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})(?:v\d+)?",
        re.I,
    ),
]

DOI_RE = re.compile(
    r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b",
    re.I,
)


def find_arxiv_id(text: str) -> str | None:
    for pattern in ARXIV_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)
    return None


def find_all_dois(text: str) -> list[str]:
    """Return unique DOI candidates in appearance order."""
    seen: set[str] = set()
    result: list[str] = []

    for match in DOI_RE.finditer(text):
        doi = match.group(0).rstrip(".,;:)]}").lower()
        if doi not in seen:
            seen.add(doi)
            result.append(doi)

    return result


# =============================================================================
# CROSSREF
# =============================================================================

def crossref_year(message: dict) -> str | None:
    for key in (
        "published-print",
        "published-online",
        "published",
        "issued",
        "created",
    ):
        block = message.get(key)
        if not isinstance(block, dict):
            continue

        parts = block.get("date-parts")
        if parts and parts[0] and parts[0][0]:
            year = valid_year(parts[0][0])
            if year:
                return year
    return None


def crossref_message_to_metadata(
    message: dict,
    source: str,
    confidence: float,
) -> PaperMetadata | None:
    titles = message.get("title") or []
    authors = message.get("author") or []
    year = crossref_year(message)

    if not titles or not authors or not year:
        return None

    title = " ".join(str(titles[0]).split())
    family = authors[0].get("family")

    if not title or not family:
        return None

    return PaperMetadata(
        year=year,
        author=sanitize_component(str(family)),
        title=title,
        source=source,
        confidence=confidence,
        doi=message.get("DOI"),
    )


def fetch_crossref_message(
    session: requests.Session,
    doi: str,
) -> dict | None:
    response = session.get(
        f"https://api.crossref.org/works/{quote(doi, safe='')}",
        timeout=REQUEST_TIMEOUT,
    )

    if response.status_code == 404:
        return None

    response.raise_for_status()
    return response.json().get("message", {})


def search_crossref_by_title(
    session: requests.Session,
    title: str,
) -> PaperMetadata | None:
    params = {
        "query.title": title,
        "rows": 5,
        "select": (
            "DOI,title,author,published-print,published-online,"
            "published,issued,created"
        ),
    }

    response = session.get(
        "https://api.crossref.org/works",
        params=params,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    items = response.json().get("message", {}).get("items", [])
    best: tuple[float, dict] | None = None

    for item in items:
        titles = item.get("title") or []
        if not titles:
            continue
        score = title_similarity(title, str(titles[0]))
        if best is None or score > best[0]:
            best = (score, item)

    if best is None or best[0] < TITLE_MATCH_THRESHOLD:
        return None

    return crossref_message_to_metadata(
        best[1],
        source=f"Crossref title match ({best[0]:.2f})",
        confidence=best[0],
    )


# =============================================================================
# ARXIV
# =============================================================================

def fetch_arxiv_metadata(
    session: requests.Session,
    arxiv_id: str,
) -> PaperMetadata | None:
    response = session.get(
        f"https://export.arxiv.org/api/query?id_list={quote(arxiv_id)}",
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    root = ET.fromstring(response.text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entry = root.find("atom:entry", ns)

    if entry is None:
        return None

    title_node = entry.find("atom:title", ns)
    published_node = entry.find("atom:published", ns)
    author_node = entry.find("atom:author/atom:name", ns)

    if title_node is None or published_node is None or author_node is None:
        return None

    title = " ".join((title_node.text or "").split())
    author = " ".join((author_node.text or "").split())
    year = valid_year(published_node.text or "")

    if not title or not author or not year:
        return None

    return PaperMetadata(
        year=year,
        author=surname_from_name(author),
        title=title,
        source="arXiv",
        confidence=0.98,
        arxiv_id=arxiv_id,
    )


# =============================================================================
# OPENALEX
# =============================================================================

def openalex_year(work: dict) -> str | None:
    return valid_year(work.get("publication_year"))


def openalex_to_metadata(
    work: dict,
    source: str,
    confidence: float,
) -> PaperMetadata | None:
    title = " ".join(str(work.get("title") or "").split())
    year = openalex_year(work)

    authorships = work.get("authorships") or []
    if not title or not year or not authorships:
        return None

    first_author = authorships[0].get("author") or {}
    display_name = first_author.get("display_name")
    if not display_name:
        return None

    doi_url = work.get("doi")
    doi = None
    if isinstance(doi_url, str):
        doi = re.sub(r"^https?://doi\.org/", "", doi_url, flags=re.I)

    return PaperMetadata(
        year=year,
        author=surname_from_name(display_name),
        title=title,
        source=source,
        confidence=confidence,
        doi=doi,
    )


def search_openalex_by_title(
    session: requests.Session,
    title: str,
) -> PaperMetadata | None:
    response = session.get(
        "https://api.openalex.org/works",
        params={
            "search": title,
            "per-page": 5,
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    results = response.json().get("results", [])
    best: tuple[float, dict] | None = None

    for work in results:
        work_title = str(work.get("title") or "")
        score = title_similarity(title, work_title)
        if best is None or score > best[0]:
            best = (score, work)

    if best is None or best[0] < TITLE_MATCH_THRESHOLD:
        return None

    return openalex_to_metadata(
        best[1],
        source=f"OpenAlex title match ({best[0]:.2f})",
        confidence=best[0],
    )


# =============================================================================
# EMBEDDED METADATA
# =============================================================================

BAD_METADATA_TITLES = {
    "untitled",
    "microsoft word",
    "document",
    "pdf",
    "article",
}


def parse_embedded_metadata(meta: dict[str, str]) -> PaperMetadata | None:
    title = " ".join((meta.get("title") or "").split())
    author_field = " ".join((meta.get("author") or "").split())

    if (
        not title
        or title.lower() in BAD_METADATA_TITLES
        or len(title) < 8
        or not author_field
    ):
        return None

    year = valid_year(meta.get("creationDate"))
    if not year:
        year = valid_year(meta.get("modDate"))
    if not year:
        return None

    first_author = re.split(
        r";|\band\b",
        author_field,
        maxsplit=1,
        flags=re.I,
    )[0].strip()

    if not first_author:
        return None

    return PaperMetadata(
        year=year,
        author=surname_from_name(first_author),
        title=title,
        source="embedded PDF metadata",
        confidence=0.62,
    )


# =============================================================================
# RESOLUTION
# =============================================================================

class MetadataResolver:
    def __init__(self, session: requests.Session):
        self.session = session

    def resolve(self, pdf_path: Path) -> PaperMetadata | None:
        text = read_pdf_text(pdf_path, pages=3)
        embedded = read_pdf_metadata(pdf_path)

        embedded_title = " ".join((embedded.get("title") or "").split())
        inferred_title = infer_title_from_first_page(pdf_path)

        title_hints: list[str] = []
        if (
            embedded_title
            and embedded_title.lower() not in BAD_METADATA_TITLES
            and len(embedded_title) >= 8
        ):
            title_hints.append(embedded_title)

        if inferred_title and inferred_title not in title_hints:
            title_hints.append(inferred_title)

        searchable_blob = "\n".join(
            [
                text,
                embedded.get("subject", ""),
                embedded.get("keywords", ""),
            ]
        )

        # ---------------------------------------------------------------------
        # 1) arXiv gives us a highly trustworthy title anchor if present.
        # ---------------------------------------------------------------------
        arxiv_metadata = None
        arxiv_id = find_arxiv_id(searchable_blob)
        if arxiv_id:
            try:
                arxiv_metadata = fetch_arxiv_metadata(
                    self.session,
                    arxiv_id,
                )
            except (requests.RequestException, ET.ParseError) as exc:
                LOGGER.warning(
                    "[WARN] arXiv lookup failed for %s: %s",
                    pdf_path.name,
                    exc,
                )

        if arxiv_metadata:
            title_hints.insert(0, arxiv_metadata.title)

        # ---------------------------------------------------------------------
        # 2) DOI candidates. Crucially, Crossref result title must match the
        #    PDF title/arXiv title before a DOI is trusted.
        # ---------------------------------------------------------------------
        for doi in find_all_dois(searchable_blob):
            try:
                message = fetch_crossref_message(self.session, doi)
            except requests.RequestException as exc:
                LOGGER.warning(
                    "[WARN] Crossref DOI lookup failed for %s (%s): %s",
                    pdf_path.name,
                    doi,
                    exc,
                )
                continue

            if not message:
                continue

            crossref_titles = message.get("title") or []
            if not crossref_titles:
                continue

            crossref_title = str(crossref_titles[0])

            scores = [
                title_similarity(hint, crossref_title)
                for hint in title_hints
                if hint
            ]

            # Without any PDF title hint, do not trust an arbitrary DOI.
            if not scores:
                continue

            score = max(scores)
            if score < STRICT_DOI_MATCH_THRESHOLD:
                LOGGER.debug(
                    "Rejected DOI %s for %s: title similarity %.2f",
                    doi,
                    pdf_path.name,
                    score,
                )
                continue

            result = crossref_message_to_metadata(
                message,
                source=f"Crossref DOI validated ({score:.2f})",
                confidence=score,
            )
            if result:
                return result

        # ---------------------------------------------------------------------
        # 3) arXiv is safer than a weak title-search result.
        # ---------------------------------------------------------------------
        if arxiv_metadata:
            return arxiv_metadata

        # ---------------------------------------------------------------------
        # 4) Search bibliographic services by title.
        # ---------------------------------------------------------------------
        for hint in title_hints:
            try:
                result = search_crossref_by_title(self.session, hint)
                if result:
                    return result
            except requests.RequestException as exc:
                LOGGER.warning(
                    "[WARN] Crossref title search failed for %s: %s",
                    pdf_path.name,
                    exc,
                )

        for hint in title_hints:
            try:
                result = search_openalex_by_title(self.session, hint)
                if result:
                    return result
            except requests.RequestException as exc:
                LOGGER.warning(
                    "[WARN] OpenAlex search failed for %s: %s",
                    pdf_path.name,
                    exc,
                )

        # ---------------------------------------------------------------------
        # 5) Last resort: embedded metadata.
        # ---------------------------------------------------------------------
        return parse_embedded_metadata(embedded)


# =============================================================================
# DATASET MODE
# =============================================================================

GENERIC_DATASET_STEM_WORDS = {
    "paper", "article", "dataset", "datasets",
    "towards", "toward", "creation",
    "large", "scale", "high", "resolution",
}


def clean_existing_dataset_label(pdf_path: Path) -> str | None:
    """
    Use clean existing stems as dataset names:
        MADOS.pdf              -> MADOS
        DynamicEarthNet.pdf    -> DynamicEarthNet
        SEN12MS-CR-TS.pdf      -> SEN12MS-CR-TS
        FieldsOfTheWorld.pdf   -> FieldsOfTheWorld

    Reject long/generic filenames and already-normalized bibliography names.
    """
    stem = pdf_path.stem.strip()

    if re.match(r"^\d{4}_[^_]+_", stem):
        return None

    if not (2 <= len(stem) <= 50):
        return None

    if re.match(r"^\d{4,}", stem):
        return None

    tokens = [
        token.lower()
        for token in re.split(r"[_\-\s]+", stem)
        if token
    ]

    if not tokens or len(tokens) > 6:
        return None

    generic_hits = sum(
        token in GENERIC_DATASET_STEM_WORDS
        for token in tokens
    )
    if generic_hits >= 2:
        return None

    return sanitize_component(stem)


def build_filename(
    metadata: PaperMetadata,
    dataset_label: str | None = None,
) -> str:
    descriptor = (
        sanitize_component(dataset_label)
        if dataset_label
        else short_title(metadata.title)
    )

    filename = (
        f"{sanitize_component(metadata.year)}_"
        f"{sanitize_component(metadata.author)}_"
        f"{descriptor}.pdf"
    )
    return trim_filename(filename)


# =============================================================================
# DUPLICATE CHECK
# =============================================================================

def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


# =============================================================================
# FILE PROCESSING
# =============================================================================

def rename_in_place(
    pdf_path: Path,
    resolver: MetadataResolver,
    dry_run: bool,
    dataset_mode: bool,
) -> tuple[bool, str]:
    try:
        metadata = resolver.resolve(pdf_path)
    except (pymupdf.FileDataError, RuntimeError, OSError) as exc:
        return False, f"[ERROR] {pdf_path.name}: cannot read PDF ({exc})"

    if not metadata:
        return False, f"[SKIP] {pdf_path.name}: trustworthy metadata not found"

    dataset_label = (
        clean_existing_dataset_label(pdf_path)
        if dataset_mode
        else None
    )

    target_name = build_filename(
        metadata,
        dataset_label=dataset_label,
    )

    target = unique_destination(
        pdf_path.parent,
        target_name,
        source=pdf_path,
    )

    if target == pdf_path:
        return True, f"[UNCHANGED] {pdf_path.name}"

    details = f"{metadata.source}; confidence={metadata.confidence:.2f}"

    if dry_run:
        return (
            True,
            f"[DRY RUN] {pdf_path.name} -> {target.name} [{details}]",
        )

    try:
        pdf_path.rename(target)
    except OSError as exc:
        return False, f"[ERROR] {pdf_path.name}: rename failed ({exc})"

    return True, f"[OK] {pdf_path.name} -> {target.name} [{details}]"


def iter_pdfs(folder: Path, recursive: bool) -> list[Path]:
    iterator = folder.rglob("*.pdf") if recursive else folder.glob("*.pdf")
    excluded = {"_NeedsReview", "_Duplicates"}
    return sorted(
        [
            path
            for path in iterator
            if not any(part in excluded for part in path.parts)
        ],
        key=lambda path: path.name.lower(),
    )


def batch_process_folder(
    folder: Path,
    resolver: MetadataResolver,
    dry_run: bool,
    recursive: bool,
    dataset_mode: bool,
) -> int:
    folder = folder.expanduser().resolve()

    if not folder.exists() or not folder.is_dir():
        LOGGER.error("Invalid folder: %s", folder)
        return 2

    pdfs = iter_pdfs(folder, recursive)

    LOGGER.info("Batch folder: %s", folder)
    LOGGER.info("PDFs found: %d", len(pdfs))
    LOGGER.info("Dataset mode: %s", "ON" if dataset_mode else "OFF")
    if dry_run:
        LOGGER.info("DRY RUN: no files will be changed.")
    LOGGER.info("")

    good = 0
    skipped = 0

    for pdf in pdfs:
        ok, message = rename_in_place(
            pdf,
            resolver,
            dry_run=dry_run,
            dataset_mode=dataset_mode,
        )
        LOGGER.info(message)
        if ok:
            good += 1
        else:
            skipped += 1

    LOGGER.info("")
    LOGGER.info(
        "Finished. Processed=%d successful/unchanged=%d skipped=%d",
        len(pdfs),
        good,
        skipped,
    )

    return 0 if skipped == 0 else 1


def move_to_review(pdf_path: Path, review_folder: Path) -> None:
    review_folder.mkdir(parents=True, exist_ok=True)
    target = unique_destination(review_folder, pdf_path.name)
    try:
        shutil.move(str(pdf_path), str(target))
        LOGGER.info("[REVIEW] %s -> %s", pdf_path.name, target)
    except OSError as exc:
        LOGGER.error(
            "Could not move %s to review folder: %s",
            pdf_path.name,
            exc,
        )


def process_downloaded_pdf(
    pdf_path: Path,
    resolver: MetadataResolver,
    destination: Path,
    dataset_mode: bool,
) -> None:
    if pdf_path.suffix.lower() != ".pdf" or not pdf_path.exists():
        return

    LOGGER.info("[FOUND] %s", pdf_path)

    if not wait_until_pdf_ready(pdf_path):
        LOGGER.warning("[WARN] PDF never became ready: %s", pdf_path)
        return

    try:
        metadata = resolver.resolve(pdf_path)
    except (pymupdf.FileDataError, RuntimeError, OSError) as exc:
        LOGGER.error("[ERROR] Could not inspect %s: %s", pdf_path.name, exc)
        move_to_review(pdf_path, destination / "_NeedsReview")
        return

    if not metadata:
        LOGGER.warning(
            "[WARN] Not enough trustworthy metadata for %s",
            pdf_path.name,
        )
        move_to_review(pdf_path, destination / "_NeedsReview")
        return

    dataset_label = (
        clean_existing_dataset_label(pdf_path)
        if dataset_mode
        else None
    )

    target_name = build_filename(
        metadata,
        dataset_label=dataset_label,
    )

    target = unique_destination(destination, target_name)
    destination.mkdir(parents=True, exist_ok=True)

    try:
        shutil.move(str(pdf_path), str(target))
    except OSError as exc:
        LOGGER.error("[ERROR] Could not move %s: %s", pdf_path.name, exc)
        return

    LOGGER.info(
        "[OK] %s -> %s [%s; confidence=%.2f]",
        pdf_path.name,
        target.name,
        metadata.source,
        metadata.confidence,
    )


# =============================================================================
# WATCH MODE
# =============================================================================

class PDFHandler(FileSystemEventHandler):
    def __init__(self, work_queue: queue.Queue[Path]):
        super().__init__()
        self.work_queue = work_queue
        self._recent: dict[str, float] = {}
        self._lock = threading.Lock()

    def _enqueue(self, path: Path) -> None:
        if path.suffix.lower() != ".pdf":
            return

        key = str(path).lower()
        now = time.monotonic()

        with self._lock:
            last = self._recent.get(key, 0.0)
            if now - last < 3.0:
                return

            self._recent[key] = now

            stale = [
                item
                for item, timestamp in self._recent.items()
                if now - timestamp > 300
            ]
            for item in stale:
                self._recent.pop(item, None)

        self.work_queue.put(path)

    def on_created(self, event):
        if not event.is_directory:
            self._enqueue(Path(event.src_path))

    def on_moved(self, event):
        if not event.is_directory:
            self._enqueue(Path(event.dest_path))


def watch_worker(
    work_queue: queue.Queue[Path],
    stop_event: threading.Event,
    resolver: MetadataResolver,
    destination: Path,
    dataset_mode: bool,
) -> None:
    while not stop_event.is_set() or not work_queue.empty():
        try:
            path = work_queue.get(timeout=0.5)
        except queue.Empty:
            continue

        try:
            process_downloaded_pdf(
                path,
                resolver,
                destination=destination,
                dataset_mode=dataset_mode,
            )
        except Exception:
            LOGGER.exception("Unexpected error processing %s", path)
        finally:
            work_queue.task_done()


def watch_folder(
    source: Path,
    destination: Path,
    resolver: MetadataResolver,
    dataset_mode: bool,
) -> int:
    source = source.expanduser().resolve()
    destination = destination.expanduser().resolve()

    if not source.exists() or not source.is_dir():
        LOGGER.error("Watch folder does not exist: %s", source)
        return 2

    destination.mkdir(parents=True, exist_ok=True)
    (destination / "_NeedsReview").mkdir(parents=True, exist_ok=True)

    LOGGER.info("Automatic paper renamer is running.")
    LOGGER.info("Watching:  %s", source)
    LOGGER.info("Saving to: %s", destination)
    LOGGER.info("Press Ctrl+C to stop.")

    work_queue: queue.Queue[Path] = queue.Queue()
    stop_event = threading.Event()

    worker = threading.Thread(
        target=watch_worker,
        args=(
            work_queue,
            stop_event,
            resolver,
            destination,
            dataset_mode,
        ),
        daemon=True,
        name="paper-renamer-worker",
    )
    worker.start()

    observer = Observer()
    observer.schedule(
        PDFHandler(work_queue),
        str(source),
        recursive=False,
    )
    observer.start()

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        LOGGER.info("Stopping...")
    finally:
        observer.stop()
        observer.join()
        stop_event.set()
        worker.join(timeout=10)

    return 0


# =============================================================================
# CLI
# =============================================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Automatically rename academic PDFs with bibliographic metadata."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--folder",
        type=Path,
        help="Batch-rename PDFs already in this folder.",
    )
    parser.add_argument(
        "--watch",
        type=Path,
        default=DEFAULT_DOWNLOADS,
        help="Folder watched when --folder is omitted.",
    )
    parser.add_argument(
        "--destination",
        type=Path,
        default=DEFAULT_DESTINATION,
        help="Destination for watch mode.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview batch changes without modifying files.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Include subfolders in batch mode.",
    )
    parser.add_argument(
        "--dataset-mode",
        action="store_true",
        help=(
            "Prefer a clean existing filename as dataset name "
            "(MADOS.pdf -> YEAR_Author_MADOS.pdf)."
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show diagnostic details including rejected DOI matches.",
    )

    return parser


def configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(message)s",
    )
    if not verbose:
        logging.getLogger("urllib3").setLevel(logging.WARNING)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.verbose)

    if args.dry_run and args.folder is None:
        parser.error("--dry-run requires --folder.")

    dataset_mode = args.dataset_mode
    if args.folder is not None and args.folder.name.lower() == "datasets":
        dataset_mode = True

    session = make_http_session()
    resolver = MetadataResolver(session)

    try:
        if args.folder is not None:
            return batch_process_folder(
                args.folder,
                resolver,
                dry_run=args.dry_run,
                recursive=args.recursive,
                dataset_mode=dataset_mode,
            )

        return watch_folder(
            args.watch,
            args.destination,
            resolver,
            dataset_mode=dataset_mode,
        )
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
