# Translation protocol (English → Chinese)

This protocol governs the Claude-in-conversation translation step of the
pdf2md skill. The scripts produce a deterministic English document; the
translation quality is entirely this protocol's responsibility.

## Principles

1. **Fidelity over fluency.** This is a regulatory test guideline, not
   marketing copy. Translate what the text says; do not summarize, reorder,
   or "improve" the science. Sentence-by-sentence correspondence with the
   English source is the default; merge sentences only when Chinese
   grammar demands it, and never across a paragraph.
2. **Glossary first.** Read `toxicology-glossary.md` before starting. Any
   term present there uses exactly the glossary rendering — no synonyms,
   no paraphrases.
3. **First-occurrence bracketing.** On first occurrence in the body, render
   the Chinese term with the original abbreviation in parentheses:
   半抑制浓度（IC50）、光刺激因子（PIF）、平均光效应（MPE）. Afterwards use
   the bare Chinese term (or the bare abbreviation if that is the glossary
   form). In tables and figure alt-text, abbreviations may stay bare.

## Do not translate

- LaTeX math, inline `$...$` and display `$$...$$`: copy verbatim.
- Image paths and alt-text structure: `![图 N（第 P 页）](images/...)` —
  translate the alt label, never the path.
- YAML frontmatter keys; translate only human-readable values that are
  prose (title stays as 中文标题 + 原文括注 per the zh template).
- `<!-- page N -->` markers: keep the number exactly; you may append the
  Chinese word 页 inside a new comment if helpful, but never delete the
  original marker (it anchors source-page citations).
- Chemical names may keep the English form with a Chinese gloss on first
  use when no established Chinese name exists.
- Reference list entries in `{{REFERENCES}}`: keep author/title/journal
  fields as-is; translate only the section heading (参考文献).

## Procedure

1. Read the glossary. Skim the whole English file once to build a term
   frequency sense and pick first-occurrence points.
2. Create the output from `assets/template_zh.md`, filling frontmatter and
   the metadata table (六个占位符与英文版一致).
3. Translate section by section (heading-delimited). After each section,
   re-read your translation against the English before moving on. Work in
   2–4 sections per response when the document is long — never batch the
   whole document into one pass.
4. Headings: translate the heading text; keep the `##` level and the
   heading order exactly as the English file has them.
5. Numbers, units, and measurement values are copied, not localized
   (小数点保留原样;千分位跟随原文).

## Self-check checklist (run before declaring done)

- [ ] No English sentences remain in body text (abbreviations and
      do-not-translate items excepted).
- [ ] Every `$...$` / `$$...$$` span from the English file is present and
      byte-identical.
- [ ] Every `images/...` path appears the same number of times as in the
      English file.
- [ ] Every `<!-- page N -->` marker survives with the same N.
- [ ] Heading count and order match the English file.
- [ ] Glossary terms spot-check: PIF、MPE、IC50、NRU、受试化学物、阳性对照、
      接受标准 render exactly as the glossary specifies.
- [ ] First-occurrence bracketing applied once per term, not everywhere.
