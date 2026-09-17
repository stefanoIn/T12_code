"""
paper_renamer.py

Modes
-----
1) Watch Downloads continuously:
       python paper_renamer.py

2) Batch-rename every existing PDF in a folder, in place:
       python paper_renamer.py --folder "C:\path\to\folder"

3) Preview a batch run without changing files:
       python paper_renamer.py --folder "C:\path\to\folder" --dry-run

Naming:
    YEAR_FirstAuthor_ShortTitle.pdf

Metadata priority:
    arXiv -> DOI/Crossref -> embedded PDF metadata

Files for which metadata cannot be determined confidently are left unchanged
during batch mode and moved to _NeedsReview only in watch mode.
"""

from __future__ import annotations

import argparse
import re
import shutil
import time
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote

import pymupdf
import requests
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

DOWNLOADS = Path.home() / "Downloads"
DESTINATION = Path.home() / "Desktop" / "THESIS" / "Readings"
NEEDS_REVIEW = DESTINATION / "_NeedsReview"

MAX_TITLE_WORDS = 9
REQUEST_TIMEOUT = 15

HEADERS = {
    "User-Agent": (
        "StefanoPaperRenamer/2.0 "
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


def short_title(title: str) -> str:
    title = " ".join(title.split())

    for pattern, replacement in PHRASE_REPLACEMENTS:
        title = pattern.sub(replacement, title)

    title = re.sub(r"[^\w\s-]", " ", title)
    title = re.sub(r"\s+", " ", title).strip()

    words = []
    for token in title.split():
        if token.lower() in STOPWORDS:
            continue
        words.append(token)
        if len(words) >= MAX_TITLE_WORDS:
            break

    return sanitize_component("_".join(words))


def surname_from_name(name: str) -> str:
    name = re.sub(r"\s+", " ", name).strip()
    name = name.replace(",", " ")
    parts = [p for p in name.split() if p]

    if not parts:
        return "UnknownAuthor"

    while parts and parts[-1].rstrip(".").lower() in {"jr", "sr", "ii", "iii", "iv"}:
        parts.pop()

    return sanitize_component(parts[-1] if parts else "UnknownAuthor")


def unique_destination(folder: Path, filename: str, source: Path | None = None) -> Path:
    target = folder / filename

    # Renaming to the same current path is fine.
    if source is not None:
        try:
            if target.resolve() == source.resolve():
                return target
        except FileNotFoundError:
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


# ---------------------------------------------------------------------------
# PDF EXTRACTION
# ---------------------------------------------------------------------------

def read_pdf_text(pdf_path: Path, pages: int = 2) -> str:
    doc = pymupdf.open(pdf_path)
    try:
        chunks = []
        for i in range(min(pages, len(doc))):
            chunks.append(doc[i].get_text("text"))
        return "\n".join(chunks)
    finally:
        doc.close()


def read_pdf_metadata(pdf_path: Path) -> dict:
    doc = pymupdf.open(pdf_path)
    try:
        return dict(doc.metadata or {})
    finally:
        doc.close()


def wait_until_file_is_stable(path: Path, checks: int = 3, delay: float = 2.0) -> bool:
    previous_size = -1
    stable_count = 0

    for _ in range(30):
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
    return match.group(0).rstrip(".,;:)]}")


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

    bad_titles = {"untitled", "microsoft word", "document", "pdf"}
    if not title or title.lower() in bad_titles:
        return None
    if not author_field or not year:
        return None

    first_author = re.split(
        r";|\band\b",
        author_field,
        maxsplit=1,
        flags=re.I
    )[0].strip()

    if not first_author:
        return None

    return {
        "year": year,
        "author": surname_from_name(first_author),
        "title": title,
        "source": "PDF metadata",
    }


# ---------------------------------------------------------------------------
# METADATA + RENAMING
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


def rename_in_place(pdf_path: Path, dry_run: bool = False) -> tuple[bool, str]:
    try:
        metadata = metadata_for_pdf(pdf_path)
    except Exception as exc:
        return False, f"[ERROR] {pdf_path.name}: {exc}"

    if not metadata:
        return False, f"[SKIP] {pdf_path.name}: trustworthy metadata not found"

    filename = build_filename(metadata)
    target = unique_destination(pdf_path.parent, filename, source=pdf_path)

    if target == pdf_path:
        return True, f"[UNCHANGED] {pdf_path.name}"

    if dry_run:
        return True, f"[DRY RUN] {pdf_path.name} -> {target.name} ({metadata['source']})"

    pdf_path.rename(target)
    return True, f"[OK] {pdf_path.name} -> {target.name} ({metadata['source']})"


def batch_process_folder(folder: Path, dry_run: bool = False) -> None:
    folder = folder.expanduser().resolve()

    if not folder.exists():
        raise SystemExit(f"Folder does not exist: {folder}")
    if not folder.is_dir():
        raise SystemExit(f"Not a folder: {folder}")

    pdfs = sorted(folder.glob("*.pdf"))

    print(f"Batch mode: {folder}")
    print(f"PDFs found: {len(pdfs)}")
    if dry_run:
        print("DRY RUN: no files will be changed.")
    print()

    renamed = 0
    skipped = 0

    for pdf in pdfs:
        ok, message = rename_in_place(pdf, dry_run=dry_run)
        print(message)
        if ok:
            renamed += 1
        else:
            skipped += 1

    print()
    print(f"Finished. Processed: {len(pdfs)} | successful/unchanged: {renamed} | skipped: {skipped}")


# ---------------------------------------------------------------------------
# WATCH MODE
# ---------------------------------------------------------------------------

def move_to_review(pdf_path: Path) -> None:
    NEEDS_REVIEW.mkdir(parents=True, exist_ok=True)
    target = unique_destination(NEEDS_REVIEW, pdf_path.name)
    shutil.move(str(pdf_path), str(target))
    print(f"[REVIEW] {pdf_path.name} -> {target}")


def process_downloaded_pdf(pdf_path: Path) -> None:
    if pdf_path.suffix.lower() != ".pdf" or not pdf_path.exists():
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

    shutil.move(str(pdf_path), str(target))
    print(
        f"[OK] {pdf_path.name}\n"
        f"     -> {target.name}\n"
        f"     source: {metadata['source']}"
    )


class PDFHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            path = Path(event.src_path)
            if path.suffix.lower() == ".pdf":
                process_downloaded_pdf(path)

    def on_moved(self, event):
        if not event.is_directory:
            path = Path(event.dest_path)
            if path.suffix.lower() == ".pdf":
                process_downloaded_pdf(path)


def watch_downloads() -> None:
    DESTINATION.mkdir(parents=True, exist_ok=True)
    NEEDS_REVIEW.mkdir(parents=True, exist_ok=True)

    print("Automatic paper renamer is running.")
    print(f"Watching:  {DOWNLOADS}")
    print(f"Saving to: {DESTINATION}")
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


def parse_args():
    parser = argparse.ArgumentParser(
        description="Automatically rename academic PDFs from metadata."
    )
    parser.add_argument(
        "--folder",
        type=Path,
        help="Batch-rename all PDFs in this folder, in place."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview batch renames without changing files."
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.folder:
        batch_process_folder(args.folder, dry_run=args.dry_run)
    else:
        if args.dry_run:
            raise SystemExit("--dry-run requires --folder.")
        watch_downloads()


if __name__ == "__main__":
    main()
