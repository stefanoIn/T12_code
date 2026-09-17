"""
paper_renamer.py

Fully automatic PDF paper renamer for Windows.

Workflow:
    Downloads/*.pdf
        -> wait until download is complete
        -> try arXiv metadata
        -> try DOI/Crossref metadata
        -> try embedded PDF metadata
        -> rename as YEAR_FirstAuthor_ShortTitle.pdf
        -> move to DESTINATION

If metadata is too weak to rename safely, the PDF is moved unchanged to
DESTINATION/_NeedsReview so the script never silently invents metadata.
"""

from __future__ import annotations

import re
import shutil
import time
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote

import fitz  # PyMuPDF
import requests
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

DOWNLOADS = Path.home() / "Downloads"

# Option A: keep the papers in your local thesis folder.
DESTINATION = Path.home() / "Desktop" / "THESIS" / "Readings"

# Option B: uncomment and edit this line if you want the script to move papers
# directly into your Google Drive for Desktop folder.
# DESTINATION = Path(r"G:\My Drive\MSc Thesis - Stefano Infusini\01 - Literature")

NEEDS_REVIEW = DESTINATION / "_NeedsReview"

# Maximum number of words kept in the short title after common filler words
# have been removed.
MAX_TITLE_WORDS = 9

# Network timeout for metadata services.
REQUEST_TIMEOUT = 15

# A polite User-Agent is recommended by Crossref and useful for arXiv too.
HEADERS = {
    "User-Agent": (
        "StefanoPaperRenamer/1.0 "
        "(academic personal-use metadata client)"
    )
}


# ---------------------------------------------------------------------------
# TEXT / FILENAME HELPERS
# ---------------------------------------------------------------------------

WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

STOPWORDS = {
    "a", "an", "the", "on", "of", "for", "and", "or",
    "in", "to", "toward", "towards", "with", "from"
}

PHRASE_REPLACEMENTS = [
    (re.compile(r"\bgeospatial artificial intelligence\b", re.I), "GeoAI"),
    (re.compile(r"\bearth observation\b", re.I), "EO"),
    (re.compile(r"\bremote sensing\b", re.I), "Remote_Sensing"),
    (re.compile(r"\bfoundation models\b", re.I), "Foundation_Models"),
    (re.compile(r"\bfoundation model\b", re.I), "Foundation_Model"),
    (re.compile(r"\bdeep learning\b", re.I), "Deep_Learning"),
    (re.compile(r"\bmachine learning\b", re.I), "Machine_Learning"),
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


def short_title(title: str) -> str:
    title = " ".join(title.split())

    for pattern, replacement in PHRASE_REPLACEMENTS:
        title = pattern.sub(replacement, title)

    # Keep underscores that were introduced by phrase replacements.
    title = re.sub(r"[^\w\s-]", " ", title)
    title = re.sub(r"\s+", " ", title).strip()

    words = []
    for token in title.split():
        if token.lower() in STOPWORDS:
            continue
        words.append(token)
        if len(words) >= MAX_TITLE_WORDS:
            break

    result = "_".join(words)
    return sanitize_component(result)


def surname_from_name(name: str) -> str:
    name = re.sub(r"\s+", " ", name).strip()
    name = name.replace(",", " ")
    parts = [p for p in name.split() if p]

    if not parts:
        return "UnknownAuthor"

    # Remove common suffixes.
    while parts and parts[-1].rstrip(".").lower() in {"jr", "sr", "ii", "iii", "iv"}:
        parts.pop()

    return sanitize_component(parts[-1] if parts else "UnknownAuthor")


def unique_destination(folder: Path, filename: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / filename

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


# ---------------------------------------------------------------------------
# PDF EXTRACTION
# ---------------------------------------------------------------------------

def read_pdf_text(pdf_path: Path, pages: int = 2) -> str:
    doc = fitz.open(pdf_path)
    try:
        chunks = []
        for i in range(min(pages, len(doc))):
            chunks.append(doc[i].get_text("text"))
        return "\n".join(chunks)
    finally:
        doc.close()


def read_pdf_metadata(pdf_path: Path) -> dict:
    doc = fitz.open(pdf_path)
    try:
        return dict(doc.metadata or {})
    finally:
        doc.close()


def wait_until_file_is_stable(path: Path, checks: int = 3, delay: float = 2.0) -> bool:
    previous_size = -1
    stable_count = 0

    for _ in range(30):  # about one minute maximum
        try:
            size = path.stat().st_size
        except (FileNotFoundError, PermissionError):
            time.sleep(delay)
            continue

        if size > 0 and size == previous_size:
            stable_count += 1
            if stable_count >= checks:
                return True
        else:
            stable_count = 0

        previous_size = size
        time.sleep(delay)

    return False


# ---------------------------------------------------------------------------
# ARXIV
# ---------------------------------------------------------------------------

ARXIV_PATTERNS = [
    re.compile(r"\barXiv:(\d{4}\.\d{4,5})(?:v\d+)?\b", re.I),
    re.compile(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})(?:v\d+)?", re.I),
]


def find_arxiv_id(text: str) -> str | None:
    for pattern in ARXIV_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)
    return None


def fetch_arxiv_metadata(arxiv_id: str) -> dict | None:
    url = f"https://export.arxiv.org/api/query?id_list={quote(arxiv_id)}"
    response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    root = ET.fromstring(response.text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entry = root.find("atom:entry", ns)

    if entry is None:
        return None

    title_node = entry.find("atom:title", ns)
    published_node = entry.find("atom:published", ns)
    author_node = entry.find("atom:author/atom:name", ns)

    if title_node is None or author_node is None or published_node is None:
        return None

    title = " ".join((title_node.text or "").split())
    author = " ".join((author_node.text or "").split())
    year_match = re.match(r"(\d{4})", published_node.text or "")

    if not title or not author or not year_match:
        return None

    return {
        "year": year_match.group(1),
        "author": surname_from_name(author),
        "title": title,
        "source": "arXiv",
    }


# ---------------------------------------------------------------------------
# DOI / CROSSREF
# ---------------------------------------------------------------------------

DOI_RE = re.compile(
    r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b",
    re.I,
)


def find_doi(text: str) -> str | None:
    match = DOI_RE.search(text)
    if not match:
        return None

    doi = match.group(0).rstrip(".,;:)]}")
    return doi


def crossref_year(message: dict) -> str | None:
    for key in ("published-print", "published-online", "issued", "created"):
        block = message.get(key)
        if not isinstance(block, dict):
            continue
        parts = block.get("date-parts")
        if parts and parts[0] and parts[0][0]:
            return str(parts[0][0])
    return None


def fetch_crossref_metadata(doi: str) -> dict | None:
    url = f"https://api.crossref.org/works/{quote(doi, safe='')}"
    response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    message = response.json().get("message", {})

    titles = message.get("title") or []
    authors = message.get("author") or []
    year = crossref_year(message)

    if not titles or not authors or not year:
        return None

    title = " ".join(str(titles[0]).split())
    first_author = authors[0].get("family")

    if not title or not first_author:
        return None

    return {
        "year": year,
        "author": sanitize_component(first_author),
        "title": title,
        "source": "Crossref",
    }


# ---------------------------------------------------------------------------
# EMBEDDED PDF METADATA FALLBACK
# ---------------------------------------------------------------------------

def year_from_pdf_metadata(meta: dict, text: str) -> str | None:
    for key in ("creationDate", "modDate"):
        value = meta.get(key) or ""
        match = re.search(r"(19|20)\d{2}", value)
        if match:
            return match.group(0)

    # Conservative fallback: look for common bibliographic/arXiv-style years
    # in the first two pages. Prefer recent plausible publication years.
    years = re.findall(r"\b(?:19|20)\d{2}\b", text)
    if years:
        plausible = [y for y in years if 1980 <= int(y) <= 2100]
        if plausible:
            return plausible[0]

    return None


def parse_embedded_metadata(meta: dict, text: str) -> dict | None:
    title = " ".join((meta.get("title") or "").split())
    author_field = " ".join((meta.get("author") or "").split())
    year = year_from_pdf_metadata(meta, text)

    # Reject obviously useless metadata.
    bad_titles = {"untitled", "microsoft word", "document", "pdf"}
    if not title or title.lower() in bad_titles:
        return None

    if not author_field or not year:
        return None

    # Many PDFs store multiple authors separated by semicolon.
    first_author = re.split(r";|\band\b", author_field, maxsplit=1, flags=re.I)[0].strip()
    if not first_author:
        return None

    return {
        "year": year,
        "author": surname_from_name(first_author),
        "title": title,
        "source": "PDF metadata",
    }


# ---------------------------------------------------------------------------
# MAIN PROCESSOR
# ---------------------------------------------------------------------------

def metadata_for_pdf(pdf_path: Path) -> dict | None:
    text = read_pdf_text(pdf_path, pages=2)

    arxiv_id = find_arxiv_id(text)
    if arxiv_id:
        try:
            metadata = fetch_arxiv_metadata(arxiv_id)
            if metadata:
                return metadata
        except Exception as exc:
            print(f"[WARN] arXiv lookup failed for {pdf_path.name}: {exc}")

    doi = find_doi(text)
    if doi:
        try:
            metadata = fetch_crossref_metadata(doi)
            if metadata:
                return metadata
        except Exception as exc:
            print(f"[WARN] Crossref lookup failed for {pdf_path.name}: {exc}")

    try:
        meta = read_pdf_metadata(pdf_path)
        metadata = parse_embedded_metadata(meta, text)
        if metadata:
            return metadata
    except Exception as exc:
        print(f"[WARN] PDF metadata fallback failed for {pdf_path.name}: {exc}")

    return None


def build_filename(metadata: dict) -> str:
    year = sanitize_component(str(metadata["year"]))
    author = sanitize_component(str(metadata["author"]))
    title = short_title(str(metadata["title"]))

    return f"{year}_{author}_{title}.pdf"


def move_to_review(pdf_path: Path) -> None:
    NEEDS_REVIEW.mkdir(parents=True, exist_ok=True)
    target = unique_destination(NEEDS_REVIEW, pdf_path.name)
    shutil.move(str(pdf_path), str(target))
    print(f"[REVIEW] {pdf_path.name} -> {target}")


def process_pdf(pdf_path: Path) -> None:
    if pdf_path.suffix.lower() != ".pdf":
        return

    if not pdf_path.exists():
        return

    print(f"[FOUND] {pdf_path}")

    if not wait_until_file_is_stable(pdf_path):
        print(f"[WARN] File never became stable: {pdf_path}")
        return

    try:
        metadata = metadata_for_pdf(pdf_path)
    except Exception as exc:
        print(f"[ERROR] Could not inspect {pdf_path.name}: {exc}")
        move_to_review(pdf_path)
        return

    if not metadata:
        print(f"[WARN] Not enough trustworthy metadata for {pdf_path.name}")
        move_to_review(pdf_path)
        return

    filename = build_filename(metadata)
    target = unique_destination(DESTINATION, filename)
    DESTINATION.mkdir(parents=True, exist_ok=True)

    try:
        shutil.move(str(pdf_path), str(target))
        print(
            f"[OK] {pdf_path.name}\n"
            f"     -> {target.name}\n"
            f"     source: {metadata['source']}"
        )
    except Exception as exc:
        print(f"[ERROR] Could not move {pdf_path.name}: {exc}")


# ---------------------------------------------------------------------------
# WATCHDOG
# ---------------------------------------------------------------------------

class PDFHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            path = Path(event.src_path)
            if path.suffix.lower() == ".pdf":
                process_pdf(path)

    def on_moved(self, event):
        if not event.is_directory:
            path = Path(event.dest_path)
            if path.suffix.lower() == ".pdf":
                process_pdf(path)


def main() -> None:
    DESTINATION.mkdir(parents=True, exist_ok=True)
    NEEDS_REVIEW.mkdir(parents=True, exist_ok=True)

    print("Automatic paper renamer is running.")
    print(f"Watching:   {DOWNLOADS}")
    print(f"Saving to:  {DESTINATION}")
    print("Press Ctrl+C to stop.\n")

    observer = Observer()
    observer.schedule(PDFHandler(), str(DOWNLOADS), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()


if __name__ == "__main__":
    main()
