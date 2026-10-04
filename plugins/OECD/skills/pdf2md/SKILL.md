---
name: pdf2md
description: "Convert OECD test guideline PDFs into bilingual English/Chinese Markdown documents. Deterministic scripts extract text, tables and figures in reading order with stable ids and a manifest contract; translation follows a section-by-section protocol with a toxicology glossary."
---

# OECD PDF → bilingual Markdown translator

Use when the user provides an OECD (or similar scientific/regulatory) PDF and
wants bilingual `_en.md` / `_zh.md` output. Output is plain Markdown — light
YAML frontmatter, `$...$` math, `images/` folder — readable in Obsidian,
GitHub and pandoc with no build system required.

## Requirements

- `uv` (scripts carry inline PEP 723 dependencies; no venv setup needed).
  On slow networks first: `export UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple`
- `build_md.py` is pure standard library and also runs under plain `python3`.

## Workflow

Resolve paths relative to this skill directory. Steps 1 and 3–5 are yours
(Claude); only steps 2's two commands are scripted.

### 1. Read PDF page 1 for metadata

Open the PDF (Read tool supports PDFs; read page 1 only) and extract:
document title, TG number, OECD publication date. Do not guess these from
the filename — an ISBN like `9789264071162-en.pdf` is not the TG number.
If the PDF stem is an ISBN, name outputs `tg<NNN>_en.md` / `tg<NNN>_zh.md`
using the real TG number; otherwise keep the stem.

### 2. Extract and build

```bash
uv run scripts/extract.py --pdf <input.pdf> --out-dir <workdir>
uv run scripts/build_md.py --md <workdir>/<stem>_extracted.md \
    --manifest <workdir>/manifest.json \
    --out <workdir>/<stem>_en.md \
    --title "<title from page 1>" --doc-number "<NNN>" \
    --publication-date "<date from page 1>"
```

`extract.py` writes `<stem>_extracted.md`, `images/` and `manifest.json`
(stable page-anchored ids like `table_p4_1`; filtered entries carry
reasons). `build_md.py` resolves placeholders against the manifest and
fails hard on any id/file mismatch — if it errors, re-run `extract.py`,
never renumber by hand.

### 3. Review the English document

Read `<stem>_en.md`. Fix what heuristics cannot know: promote missed
mixed-case sub-headings, demote over-promoted lines, reflow hard-wrapped
lines into paragraphs, spot-check table screenshots against the source.
Keep `<!-- page N -->` markers — they anchor source-page citations.

### 4. Translate to Chinese

Follow `references/translation-protocol.md` (fidelity first, glossary
first, first-occurrence bracketing, do-not-translate list, self-check).
Read `references/toxicology-glossary.md` before starting. Build the output
from `assets/template_zh.md`, translating section-by-section from the
reviewed `_en.md`. 2–4 sections per response for long documents.

### 5. Verify

- `_en.md` and `_zh.md`: no `{{`, no `[TABLE:` / `[FIGURE:` left.
- Every `images/...` path in the md files exists on disk.
- `_zh.md`: math spans byte-identical to `_en.md`; page markers intact;
  glossary spot-check (PIF, MPE, IC50, 受试化学物, 阳性对照, 接受标准).
- Delete `<stem>_extracted.md` when done; keep `images/`, `manifest.json`
  and the two final documents.

## Limitations

- Tables spanning page breaks become one id/screenshot per page fragment.
- Vector or inline images without an xref get no placeholder (manifest
  logs them as filtered).
- ALL-CAPS heading detection misses mixed-case sub-headings — step 3
  catches them.
- Scanned PDFs without a text layer are out of scope.
