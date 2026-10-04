#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pdfplumber>=0.11",
#     "pymupdf>=1.24",
#     "pillow>=10",
#     "numpy>=1.26",
# ]
# ///
"""Extract text, tables and figures from an OECD test guideline PDF in one pass.

Outputs (into --out-dir):
  <stem>_extracted.md  reading-order text with [TABLE: id] / [FIGURE: id] placeholders
  images/              table screenshots (300 dpi crops) and embedded figure PNGs
  manifest.json        the single source of truth linking placeholder ids to files

Design notes (why, not what):
  - IDs are page-anchored (table_p4_1) and NEVER renumbered, so a filtered
    table cannot shift the numbering of later ones. The old pipeline numbered
    placeholders and screenshots independently and silently desynced.
  - Text lines whose midpoint falls inside a table/figure bbox are skipped:
    that content is already captured as an image, and the old pipeline
    duplicated it (screenshot + flowing text).
  - Tables and figures are interleaved with text in true reading order by
    sorting everything on the page by vertical position.
  - The manifest is the contract consumed by build_md.py; unknown ids or
    missing image files are hard errors there, never silent renumbering.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pdfplumber
import pymupdf
from PIL import Image

# Decorative images (header logos etc.) repeat on many pages; a real figure
# appearing on more than this many pages has never been observed in OECD TGs.
DECORATIVE_XREF_PAGE_LIMIT = 3
# Below this size (points) an image is an inline glyph, not a figure.
MIN_FIGURE_WIDTH_PT = 50.0
MIN_FIGURE_HEIGHT_PT = 40.0
TABLE_RENDER_DPI = 300
# Vertical gap larger than this multiple of the line height starts a new
# paragraph, so the blank-line structure of the PDF survives extraction.
PARAGRAPH_GAP_FACTOR = 1.6


def is_solid_color(
    image: Image.Image,
    variance_threshold: float = 1.0,
    black_threshold: int = 15,
    use_edge_detection: bool = True,
) -> tuple[bool, str]:
    """Return (is_solid, reason) using layered checks.

    Layer 2 (content density) and layer 3 (gradient edges) exist because
    scientific charts on white backgrounds have very low ink coverage and
    would otherwise be mistaken for blank images by variance alone.
    """
    if image.mode != "RGB":
        image = image.convert("RGB")
    arr = np.array(image)

    variance = float(np.var(arr))
    if variance < variance_threshold:
        return True, f"Low variance ({variance:.4f} < {variance_threshold})"

    non_white_ratio = float(np.sum(arr < 230) / arr.size)
    if non_white_ratio > 0.05:
        return False, f"Valid content ({non_white_ratio * 100:.1f}% non-white)"

    if use_edge_detection:
        gray = np.mean(arr, axis=2).astype(np.uint8)
        grad_x = np.abs(
            gray[:-1, :-1].astype(np.int16) - gray[:-1, 1:].astype(np.int16)
        )
        grad_y = np.abs(
            gray[:-1, :-1].astype(np.int16) - gray[1:, :-1].astype(np.int16)
        )
        gradient = np.maximum(grad_x, grad_y)
        edge_ratio = float(np.sum(gradient > 15) / gradient.size)
        if edge_ratio > 0.01:
            return False, f"Has edges ({edge_ratio * 100:.1f}% edge pixels)"

    avg_pixel = float(np.mean(arr))
    if avg_pixel < black_threshold:
        return True, f"Solid black (avg={avg_pixel:.2f} < {black_threshold})"
    if avg_pixel > 245 and non_white_ratio < 0.02:
        return True, f"Solid white (avg={avg_pixel:.2f}, content={non_white_ratio * 100:.1f}%)"
    return False, f"Valid image (avg={avg_pixel:.1f}, content={non_white_ratio * 100:.1f}%)"


def safe_extract_lines(plumber_page: pdfplumber.page.Page) -> list[dict]:
    """extract_text_lines with a plain-text fallback for odd pages."""
    try:
        return plumber_page.extract_text_lines()
    except Exception as exc:  # noqa: BLE001 - degrade, keep going
        print(f"  ! extract_text_lines failed ({exc}); falling back to extract_text")
        raw = plumber_page.extract_text() or ""
        return [
            {"text": ln, "top": float(i), "bottom": float(i) + 1, "x0": 0, "x1": 0}
            for i, ln in enumerate(raw.splitlines())
        ]


def build_page_items(
    text_lines: list[dict],
    furniture: set[str],
    figure_entries: list[dict],
    table_entries: list[dict],
) -> list[dict]:
    """Interleave text lines, table and figure bboxes in reading order.

    Each item is {'kind': 'text'|'table'|'figure', 'top': float, ...}.
    Text lines inside a kept table/figure bbox are dropped here (their
    content ships as an image instead), as are running headers/footers
    (furniture) and bare page-number lines.
    """
    regions = [
        {"x0": e["bbox"][0], "top": e["bbox"][1], "x1": e["bbox"][2], "bottom": e["bbox"][3]}
        for e in table_entries + figure_entries
        if not e["filtered"]
    ]

    items: list[dict] = [
        {"kind": "table" if not e["filtered"] else None, "top": e["bbox"][1], "entry": e}
        for e in table_entries
    ] + [
        {"kind": "figure" if not e["filtered"] else None, "top": e["bbox"][1], "entry": e}
        for e in figure_entries
    ]

    for line in text_lines:
        text = line["text"].strip()
        # Running header/footer text repeats on many pages; a real sentence
        # never survives verbatim across 30% of a guideline.
        if text in furniture:
            continue
        # Bare 1-3 digit lines are page numbers in these PDFs.
        if re.fullmatch(r"\d{1,3}", text):
            continue
        mid_x = (line["x0"] + line["x1"]) / 2
        mid_y = (line["top"] + line["bottom"]) / 2
        inside = any(
            r["x0"] <= mid_x <= r["x1"] and r["top"] <= mid_y <= r["bottom"]
            for r in regions
        )
        if inside:
            continue
        items.append({"kind": "text", "top": line["top"], "line": line})

    items = [it for it in items if it["kind"] is not None]
    items.sort(key=lambda it: it["top"])
    return items


def extract_all(pdf_path: Path, out_dir: Path) -> dict:
    """Run the full extraction; write md, images/ and manifest.json."""
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    out_dir.mkdir(parents=True, exist_ok=True)
    images_dir = out_dir / "images"
    images_dir.mkdir(exist_ok=True)
    md_path = out_dir / f"{pdf_path.stem}_extracted.md"
    manifest_path = out_dir / "manifest.json"

    try:
        fitz_doc = pymupdf.open(pdf_path)
    except Exception as exc:  # noqa: BLE001 - report the real cause, then bail
        raise RuntimeError(f"Cannot open PDF with PyMuPDF: {pdf_path} ({exc})") from exc
    try:
        plumber_pdf = pdfplumber.open(pdf_path)
    except Exception as exc:  # noqa: BLE001
        fitz_doc.close()
        raise RuntimeError(f"Cannot open PDF with pdfplumber: {pdf_path} ({exc})") from exc

    # Count on how many pages each image xref appears -> decorative detection.
    xref_page_counts: dict[int, int] = {}
    for pno in range(len(fitz_doc)):
        for img in fitz_doc[pno].get_images(full=True):
            xref_page_counts[img[0]] = xref_page_counts.get(img[0], 0) + 1

    seen_unfiltered_xrefs: set[int] = set()
    tables_manifest: list[dict] = []
    figures_manifest: list[dict] = []
    md_parts: list[str] = []
    current_page = 0

    try:
        if len(fitz_doc) != len(plumber_pdf.pages):
            print(
                f"! page count mismatch: fitz={len(fitz_doc)} "
                f"pdfplumber={len(plumber_pdf.pages)}; using the smaller count"
            )
        n_pages = min(len(fitz_doc), len(plumber_pdf.pages))

        # First pass: cache text lines per page and detect running
        # headers/footers by cross-page repetition, so the second pass can
        # drop them deterministically instead of leaving ~2 noise lines per
        # page for the manual review pass.
        page_text_lines: dict[int, list[dict]] = {}
        text_page_counts: dict[str, int] = {}
        for page_index in range(n_pages):
            lines = safe_extract_lines(plumber_pdf.pages[page_index])
            page_text_lines[page_index] = lines
            for text in {ln["text"].strip() for ln in lines}:
                text_page_counts[text] = text_page_counts.get(text, 0) + 1
        furniture_threshold = max(5, int(0.3 * n_pages))
        furniture = {
            text
            for text, count in text_page_counts.items()
            if count >= furniture_threshold and 0 < len(text) <= 60
        }
        if furniture:
            print("Running header/footer lines suppressed:")
            for text in sorted(furniture):
                print(f"    {text!r} on {text_page_counts[text]} pages")

        for page_index in range(n_pages):
            page_num = page_index + 1
            current_page = page_num
            plumber_page = plumber_pdf.pages[page_index]
            md_parts.append(f"\n<!-- page {page_num} -->\n")

            # --- tables: stable ids, filter decided before placeholders ---
            table_entries: list[dict] = []
            try:
                detected = plumber_page.find_tables()
            except Exception as exc:  # noqa: BLE001
                print(f"  ! table detection failed on page {page_num}: {exc}")
                detected = []

            for ordinal, table in enumerate(detected, start=1):
                entry = {
                    "id": f"table_p{page_num}_{ordinal}",
                    "page": page_num,
                    "bbox": [round(v, 2) for v in table.bbox],
                    "filtered": False,
                    "reason": None,
                    "image": None,
                }
                try:
                    crop_img = plumber_page.crop(table.bbox).to_image(
                        resolution=TABLE_RENDER_DPI
                    ).original
                    solid, reason = is_solid_color(crop_img)
                    if solid:
                        entry["filtered"] = True
                        entry["reason"] = reason
                    else:
                        rel = f"images/{entry['id']}.png"
                        crop_img.save(images_dir / f"{entry['id']}.png", "PNG")
                        entry["image"] = rel
                except Exception as exc:  # noqa: BLE001
                    entry["filtered"] = True
                    entry["reason"] = f"Crop/render failed: {exc}"
                table_entries.append(entry)
            tables_manifest.extend(table_entries)

            # --- figures: page 1 skipped (cover), decorative/too-small/dup filtered ---
            figure_entries: list[dict] = []
            if page_num > 1:
                for info in fitz_doc[page_index].get_image_info(xrefs=True):
                    xref = info.get("xref", 0)
                    bbox = [round(v, 2) for v in info["bbox"]]
                    entry = {
                        "id": f"figure_p{page_num}_{len(figure_entries) + 1}",
                        "page": page_num,
                        "xref": xref,
                        "bbox": bbox,
                        "filtered": False,
                        "reason": None,
                        "image": None,
                    }
                    width = bbox[2] - bbox[0]
                    height = bbox[3] - bbox[1]
                    if xref == 0:
                        entry["filtered"] = True
                        entry["reason"] = "No xref (vector/inline image)"
                    elif xref_page_counts.get(xref, 0) > DECORATIVE_XREF_PAGE_LIMIT:
                        entry["filtered"] = True
                        entry["reason"] = (
                            f"Decorative: appears on {xref_page_counts[xref]} pages"
                        )
                    elif width < MIN_FIGURE_WIDTH_PT or height < MIN_FIGURE_HEIGHT_PT:
                        entry["filtered"] = True
                        entry["reason"] = f"Too small ({width:.0f}x{height:.0f} pt)"
                    elif xref in seen_unfiltered_xrefs:
                        entry["filtered"] = True
                        entry["reason"] = "Duplicate xref (first occurrence kept)"
                    else:
                        try:
                            base = fitz_doc.extract_image(xref)
                            pil_img = Image.open(io.BytesIO(base["image"]))
                            solid, reason = is_solid_color(pil_img)
                            if solid:
                                entry["filtered"] = True
                                entry["reason"] = reason
                            else:
                                rel = f"images/{entry['id']}.png"
                                if pil_img.mode != "RGB":
                                    pil_img = pil_img.convert("RGB")
                                pil_img.save(images_dir / f"{entry['id']}.png", "PNG")
                                entry["image"] = rel
                                seen_unfiltered_xrefs.add(xref)
                        except Exception as exc:  # noqa: BLE001
                            entry["filtered"] = True
                            entry["reason"] = f"Extraction failed: {exc}"
                    figure_entries.append(entry)
            figures_manifest.extend(figure_entries)

            # --- interleave text and placeholders in reading order ---
            items = build_page_items(
                page_text_lines[page_index], furniture, figure_entries, table_entries
            )
            prev_bottom: float | None = None
            prev_height: float | None = None
            for item in items:
                if item["kind"] == "text":
                    line = item["line"]
                    text = line["text"].strip()
                    if not text:
                        continue
                    if (
                        prev_bottom is not None
                        and prev_height is not None
                        and line["top"] - prev_bottom > PARAGRAPH_GAP_FACTOR * prev_height
                    ):
                        md_parts.append("\n")
                    md_parts.append(text + "\n")
                    prev_bottom = line["bottom"]
                    prev_height = max(line["bottom"] - line["top"], 1.0)
                else:
                    entry = item["entry"]
                    tag = "TABLE" if item["kind"] == "table" else "FIGURE"
                    md_parts.append(f"\n[{tag}: {entry['id']}]\n\n")
                    prev_bottom = None
    except Exception as exc:  # noqa: BLE001 - page number gives the debugging anchor
        raise RuntimeError(f"Extraction failed on page {current_page}: {exc}") from exc
    finally:
        fitz_doc.close()
        plumber_pdf.close()

    manifest = {
        "pdf": pdf_path.name,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "pages": n_pages,
        "tables": tables_manifest,
        "figures": figures_manifest,
    }

    try:
        md_path.write_text("".join(md_parts), encoding="utf-8")
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Cannot write outputs to {out_dir}: {exc}") from exc

    return {
        "md": md_path,
        "manifest": manifest_path,
        "manifest_data": manifest,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract text, tables and figures from an OECD TG PDF."
    )
    parser.add_argument("--pdf", required=True, help="Path to the source PDF")
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Output directory (default: the PDF's own directory)",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else pdf_path.parent

    print(f"PDF:        {pdf_path}")
    print(f"Output dir: {out_dir}")

    try:
        result = extract_all(pdf_path, out_dir)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    m = result["manifest_data"]
    kept_tables = [t for t in m["tables"] if not t["filtered"]]
    kept_figures = [f for f in m["figures"] if not f["filtered"]]
    print(f"\nDone: {m['pages']} pages")
    print(f"  Tables kept: {len(kept_tables)} / {len(m['tables'])}")
    print(f"  Figures kept: {len(kept_figures)} / {len(m['figures'])}")
    for t in m["tables"]:
        if t["filtered"]:
            print(f"    filtered {t['id']}: {t['reason']}")
    for f in m["figures"]:
        if f["filtered"]:
            print(f"    filtered {f['id']}: {f['reason']}")
    print(f"  Markdown:  {result['md']}")
    print(f"  Manifest:  {result['manifest']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
