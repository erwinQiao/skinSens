# skinSens — skin sensitisation NAM toolchain

AI-assisted tooling for skin sensitisation safety assessment without animals:
an OECD test-guideline knowledge plugin for Claude Code, plus (in development)
defined-approach computation services.

## Install

```
/plugin marketplace add erwinQiao/skinSens
/plugin install oecd@skinSens
```

## Plugins

| Plugin | Install |
| --- | --- |
| **oecd** — OECD skin sensitisation guideline knowledge: `oecd497` skill (TG 497, 2 July 2026 defined approaches) + `oecd497` citation-first Q&A agent | `/plugin install oecd@skinSens` |

Upcoming skills in the same plugin: `oecd442c` / `oecd442d` / `oecd442e`
(in chemico / in vitro test methods).

## Attribution

Guideline-derived content is redistributed under CC BY 4.0 with attribution to
the OECD; software scaffolding is MIT. See
[plugins/OECD/ATTRIBUTION.md](plugins/OECD/ATTRIBUTION.md).
