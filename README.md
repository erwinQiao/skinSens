# skinSens — skin sensitisation NAM toolchain

AI-assisted tooling for skin sensitisation safety assessment without animals:
an OECD test-guideline knowledge plugin for Claude Code, plus (in development)
defined-approach computation services.

## Install

```
/plugin marketplace add erwinQiao/skinSens
/plugin install oecd@skinSens
```

## Skills

| Skill | Description |
| --- | --- |
| `oecd497` | TG 497 (2 July 2026) defined-approach knowledge pack; citation-first Q&A through the `oecd497` agent. |
| `pdf2md` | OECD TG PDF → bilingual EN/ZH Markdown; terminology-precise translation through the `oecdTranslate` agent. |

Upcoming skills: `oecd442c` / `oecd442d` / `oecd442e`
(in chemico / in vitro test methods).

## Attribution

Guideline-derived content is redistributed under CC BY 4.0 with attribution to
the OECD; software scaffolding is MIT. See
[plugins/OECD/ATTRIBUTION.md](plugins/OECD/ATTRIBUTION.md).
