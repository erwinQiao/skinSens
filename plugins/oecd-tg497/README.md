# oecd-tg497

OECD TG 497 — Defined Approaches on Skin Sensitisation (adopted 2 July 2026)
as a Claude Code plugin: a reviewed knowledge skill plus a dedicated Q&A agent.

## What's inside

| Component | Description |
| --- | --- |
| `skills/tg497` | Self-contained knowledge pack: full guideline text (`references/paper.md`), navigation index, supplementary information, extracted figures (JPEG) and tables (CSV). Human-reviewed extraction with documented limitations. |
| `agents/oecd497` | TG 497 specialist subagent. Main sessions auto-delegate TG 497 / skin-sensitisation DA questions to it; it retrieves from the skill and answers with section/table/figure citations. Also advises on DA selection and result interpretation, clearly separating guideline text from interpretation. |

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
invoke the skill directly (`/tg497` via `oecd-tg497:tg497`).

> Applying a DA to your own data (running 2o3 scoring, computing a PoD) is
> reserved for the companion skinSens computation service (in development);
> the agent will retrieve and cite the rules but will not fabricate numerical
> outputs.

## Licence

Scaffolding: MIT. Guideline-derived content (`skills/tg497/`): CC BY 4.0,
© OECD 2026 — see [ATTRIBUTION.md](ATTRIBUTION.md).
