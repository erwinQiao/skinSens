#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Build the final English Markdown document from extraction outputs.

Consumes <stem>_extracted.md + manifest.json (from extract.py) and a template,
resolving [TABLE: id] / [FIGURE: id] placeholders against the manifest.

Contract enforcement (why this is strict): the manifest is the single source
of truth. An unknown id, a filtered entry, or a missing image file is a hard
error — the old pipeline silently renumbered by count and produced image
references that pointed at the wrong tables.

Pure standard library on purpose: it must run anywhere without dependency
resolution, including `python3 scripts/build_md.py` without uv.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

from formulas import convert_line

DEFAULT_TEMPLATE = Path(__file__).parent.parent / "assets" / "template_en.md"

PLACEHOLDER_RE = re.compile(r"^\[(TABLE|FIGURE):\s*([A-Za-z0-9_]+)\]\s*$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
REFS_HEADING_RE = re.compile(r"^(?:#{1,6}\s+)?(literature|references)\s*$", re.IGNORECASE)

# Canonical OECD TG top-level sections. Mixed-case sub-headings are missed by
# design; the skill's review pass (Claude) re-levels them.
SECTION_NAMES = (
    "INTRODUCTION",
    "INITIAL CONSIDERATIONS",
    "PRINCIPLE OF THE TEST METHOD",
    "PRINCIPLE OF THE METHOD",
    "DESCRIPTION OF THE METHOD",
    "MATERIALS",
    "PREPARATION",
    "PROCEDURE",
    "TEST PROCEDURE",
    "ANALYSIS OF RESULTS",
    "METHOD PERFORMANCE",
    "INTERPRETATION OF RESULTS",
    "TEST REPORT",
    "DEFINITIONS",
    "ABBREVIATIONS",
    "ACCEPTANCE CRITERIA",
    "APPLICABILITY",
    "ANNEX",
)


def is_heading(text: str) -> bool:
    """ALL-CAPS short line, or a canonical OECD section name.

    Original case is preserved downstream — never .capitalize(): that is how
    'BALB/c 3T3' became 'Balb/c 3t3' in the old pipeline.
    """
    if not text or len(text) > 100:
        return False
    if text.isupper() and not text.endswith(".") and len(text.split()) <= 10:
        return True
    return text.upper().startswith(SECTION_NAMES)


def load_manifest(manifest_path: Path) -> dict[str, dict]:
    """Return id -> entry for unfiltered entries, validating the contract."""
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read manifest {manifest_path}: {exc}") from exc

    entries: dict[str, dict] = {}
    for kind in ("tables", "figures"):
        for entry in manifest.get(kind, []):
            eid = entry.get("id")
            if eid in entries:
                raise ValueError(f"Duplicate id in manifest: {eid}")
            entries[eid] = entry
            if entry.get("filtered"):
                continue
            image = entry.get("image")
            if not image:
                raise ValueError(f"Unfiltered entry {eid} has no image path")
            if not (manifest_path.parent / image).is_file():
                raise ValueError(
                    f"Image file for {eid} not found: {manifest_path.parent / image}"
                )
    return entries


def build(md_path: Path, manifest_path: Path, out_path: Path, template_path: Path,
          title: str, doc_number: str, publication_date: str) -> dict:
    entries = load_manifest(manifest_path)

    try:
        template = template_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Cannot read template {template_path}: {exc}") from exc

    try:
        lines = md_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"Cannot read markdown {md_path}: {exc}") from exc

    content_parts: list[str] = []
    refs_parts: list[str] = []
    in_refs = False
    table_display = 0
    figure_display = 0
    heading_count = 0

    for raw in lines:
        stripped = raw.strip()

        m = PLACEHOLDER_RE.match(stripped)
        if m:
            kind, eid = m.group(1), m.group(2)
            entry = entries.get(eid)
            if entry is None:
                raise ValueError(
                    f"Placeholder [{kind}: {eid}] has no manifest entry — "
                    f"re-run extract.py; never renumber manually"
                )
            if entry.get("filtered"):
                raise ValueError(
                    f"Placeholder [{kind}: {eid}] refers to a filtered entry "
                    f"({entry.get('reason')})"
                )
            bucket = refs_parts if in_refs else content_parts
            if kind == "TABLE":
                table_display += 1
                bucket.append(
                    f"![Table {table_display} (page {entry['page']})]({entry['image']})\n\n"
                )
            else:
                figure_display += 1
                bucket.append(
                    f"![Figure {figure_display} (page {entry['page']})]({entry['image']})\n\n"
                )
            continue

        if stripped.startswith("<!-- page"):
            (refs_parts if in_refs else content_parts).append(stripped + "\n\n")
            continue

        hm = HEADING_RE.match(stripped)
        if hm:
            level, text = "#" * min(len(hm.group(1)), 6), hm.group(2)
        elif is_heading(stripped):
            level, text = "##", stripped
        else:
            level, text = None, stripped

        if text and REFS_HEADING_RE.match(text):
            in_refs = True
            refs_parts.append("## References\n\n")
            continue

        if level:
            heading_count += 1
            (refs_parts if in_refs else content_parts).append(f"{level} {text}\n\n")
        elif stripped:
            (refs_parts if in_refs else content_parts).append(convert_line(stripped) + "\n")
        else:
            (refs_parts if in_refs else content_parts).append("\n")

    content = "".join(content_parts).strip()
    references = "".join(refs_parts).strip() or "See the reference list at the end of the source PDF."

    filled = template
    values = {
        "DOC_NUMBER": doc_number,
        "TITLE": title,
        "DATE": date.today().isoformat(),
        "PUBLICATION_DATE": publication_date or "n/a",
        "CONTENT": content,
        "REFERENCES": references,
    }
    for key, value in values.items():
        filled = filled.replace("{{" + key + "}}", str(value))

    if "{{" in filled:
        leftover = sorted(set(re.findall(r"\{\{(\w+)\}\}", filled)))
        raise ValueError(f"Template placeholders never filled: {leftover}")

    try:
        out_path.write_text(filled, encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Cannot write output {out_path}: {exc}") from exc

    return {
        "out": out_path,
        "headings": heading_count,
        "tables": table_display,
        "figures": figure_display,
        "reference_lines": len(refs_parts),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the English Markdown document from extraction outputs."
    )
    parser.add_argument("--md", required=True, help="Path to <stem>_extracted.md")
    parser.add_argument("--manifest", required=True, help="Path to manifest.json")
    parser.add_argument("--out", required=True, help="Path to the output .md file")
    parser.add_argument(
        "--template",
        default=None,
        help=f"Template path (default: {DEFAULT_TEMPLATE})",
    )
    parser.add_argument("--title", required=True, help="Document title from PDF page 1")
    parser.add_argument("--doc-number", required=True, help="OECD TG number, e.g. 442C")
    parser.add_argument(
        "--publication-date", default="", help="Original OECD publication date"
    )
    args = parser.parse_args()

    template_path = (
        Path(args.template).expanduser().resolve()
        if args.template
        else DEFAULT_TEMPLATE
    )

    try:
        result = build(
            md_path=Path(args.md).expanduser().resolve(),
            manifest_path=Path(args.manifest).expanduser().resolve(),
            out_path=Path(args.out).expanduser().resolve(),
            template_path=template_path,
            title=args.title,
            doc_number=args.doc_number,
            publication_date=args.publication_date,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("Done:")
    print(f"  Output:   {result['out']}")
    print(f"  Headings: {result['headings']}")
    print(f"  Tables:   {result['tables']}  Figures: {result['figures']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
