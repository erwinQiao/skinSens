# skinSens — skin sensitisation NAM toolchain

AI-assisted tooling for skin sensitisation safety assessment without animals:
OECD test-guideline knowledge plugins for Claude Code, plus (in development)
defined-approach computation services.

## Install the marketplace

```
/plugin marketplace add erwinQiao/skinSens
```

## Plugins

| Plugin | Description |
| --- | --- |
| **oecd-tg497** | OECD TG 497 (2 July 2026) Defined Approaches on Skin Sensitisation — reviewed guideline knowledge skill + `oecd497` citation-first Q&A agent. `/plugin install oecd-tg497@skinSens` |

Upcoming: OECD TG 442C/D/E (in chemico / in vitro method) knowledge plugins.

## Attribution

Guideline-derived content is redistributed under CC BY 4.0 with attribution to
the OECD; software scaffolding is MIT. See
[plugins/oecd-tg497/ATTRIBUTION.md](plugins/oecd-tg497/ATTRIBUTION.md).
