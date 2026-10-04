# oecd

OECD skin-sensitisation test-guideline knowledge as a Claude Code plugin:
one reviewed knowledge skill per guideline, each with a dedicated Q&A agent.
Current release covers TG 497; 442C/D/E skills are in progress.

## What's inside

| Component | Description |
| --- | --- |
| `skills/oecd497` | Self-contained TG 497 knowledge pack: full guideline text (`references/paper.md`), navigation index, supplementary information, extracted figures (JPEG) and tables (CSV). Human-reviewed extraction with documented limitations. |
| `skills/pdf2md` | OECD TG PDF → bilingual English/Chinese Markdown. Deterministic extraction in reading order (text, 300-dpi table screenshots, figures) with page-anchored stable ids and a manifest contract, plus a section-by-section translation protocol with toxicology glossary. |
| `agents/oecd497` | TG 497 specialist subagent. Main sessions auto-delegate TG 497 / skin-sensitisation DA questions to it; it retrieves from the skill and answers with section/table/figure citations. Also advises on DA selection and result interpretation, clearly separating guideline text from interpretation. |

Upcoming skills in this plugin: `oecd442c` (DPRA/ADRA), `oecd442d`
(KeratinoSens/LuSens), `oecd442e` (h-CLAT/U-SENS/IL-8 Luc).

## Coverage

- **Part I — "2 out of 3" DA**: hazard identification; 24 permutations across 9
  information sources (ADRA/DPRA; KeratinoSens/LuSens/EpiSensA;
  GARDskin/h-CLAT/IL-8 Luc/U-SENS)
- **Part II — ITS DA**: UN GHS potency categorisation (1A/1B/NC) with
  *in silico* inputs (Derek Nexus, OECD QSAR Toolbox)
- **Part III — PoD DAs**: SARA-ICE (Bayesian ED01) and the regression-based DA
- Annex 1 prediction models, DA performance vs LLNA and human data,
  applicability domains, reporting requirements

## Usage

Ask any TG 497 question in a session — the oecd497 agent picks it up — or
invoke the skill directly (`/oecd:oecd497`).

> Applying a DA to your own data (running 2o3 scoring, computing a PoD) is
> reserved for the companion skinSens computation service (in development);
> the agent will retrieve and cite the rules but will not fabricate numerical
> outputs.

## Licence

Scaffolding: MIT. Guideline-derived content (`skills/oecd497/`): CC BY 4.0,
© OECD 2026 — see [ATTRIBUTION.md](ATTRIBUTION.md).
