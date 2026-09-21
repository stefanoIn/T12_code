"""Check repository-local document links and Python/notebook syntax, offline.

Run from any directory. Use --strict to also fail on documented missing assets.
This is a static check, not a LaTeX build or a notebook execution.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
TEX_LINK = re.compile(
    r"\\(?:includegraphics\*?(?:\s*\[[^\]]*\])?|input|include|addbibresource|bibliography)"
    r"\s*\{([^{}]+)\}", re.DOTALL
)
MD_LINK = re.compile(r"!?\[[^\]\n]*\]\((<[^>]+>|[^)\s]+)\s*\)")


def exact_exists(path: Path) -> bool:
    """Check spelling as well as existence, even on Windows."""
    path = Path(os.path.abspath(path))
    if not path.exists():
        return False
    try:
        relative = path.relative_to(ROOT)
    except ValueError:
        return False
    current = ROOT
    for part in relative.parts:
        if part not in {child.name for child in current.iterdir()}:
            return False
        current = current / part
    return True


def missing_references() -> tuple[set[tuple[str, str]], int]:
    missing = set()
    checked = 0
    documents = [ROOT / 'README.md']
    for folder in ('reports', 'notes', 'docs'):
        documents.extend(p for p in (ROOT / folder).rglob('*')
                         if p.suffix in ('.tex', '.md'))
    for path in documents:
        if not path.exists():
            continue
        text = path.read_text(encoding='utf-8-sig')
        if path.suffix == '.tex':
            text = re.sub(r'(?<!\\)%[^\n]*', '', text)
            links = TEX_LINK.findall(text)
        else:
            text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
            links = MD_LINK.findall(text)
        for link in links:
            link = unquote(link.strip('<>'))
            if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', link) or link.startswith('#'):
                continue
            link = link.split('#', 1)[0]
            if not link:
                continue
            checked += 1
            target = path.parent / link
            candidates = [target]
            if not target.suffix:
                candidates += [target.with_suffix(s) for s in ('.tex', '.pdf', '.png', '.jpg', '.bib')]
            if not any(exact_exists(p) for p in candidates):
                missing.add((path.relative_to(ROOT).as_posix(), link))
    return missing, checked


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--strict', action='store_true')
    args = parser.parse_args()
    known = {(r['source'], r['target']) for r in json.loads(
        (ROOT / 'docs' / 'missing_assets.json').read_text(encoding='utf-8'))}
    missing, checked = missing_references()
    errors = []
    count = 0
    for path in sorted((ROOT / 'scripts').glob('*.py')):
        try:
            ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
        except SyntaxError as exc:
            errors.append(str(exc))
        count += 1
    for path in sorted((ROOT / 'notebooks').rglob('*.ipynb')):
        try:
            notebook = json.loads(path.read_text(encoding='utf-8-sig'))
            for index, cell in enumerate(notebook['cells']):
                if cell['cell_type'] == 'code':
                    ast.parse(''.join(cell['source']), filename=f'{path.name}:cell{index}')
            count += 1
        except (SyntaxError, ValueError, KeyError) as exc:
            errors.append(str(exc))
    for source, target in sorted(missing):
        label = 'KNOWN MISSING' if (source, target) in known else 'BROKEN'
        print(f'{label}: {source} -> {target}')
    for error in errors:
        print(f'ERROR: {error}')
    print(f'Checked {checked} local references and {count} Python/notebook files; '
          f'{len(missing - known)} new broken references; '
          f'{len(missing & known)} documented missing references.')
    return int(bool(errors or (missing if args.strict else missing - known)))


if __name__ == '__main__':
    raise SystemExit(main())
