# FORGE WORLD

**An evidence-backed industrial buildability compiler and transformation optimizer.**

> Specify a physical future. FORGE designs the industrial path to make it real.

FORGE takes a physical objective — e.g. *"India manufactures 1,000,000 humanoid robots
per year by 2030"* — and produces an **auditable computational argument about industrial
possibility**: what architectures could satisfy it, which components/materials/processes they
require, what qualified capacity exists today (with evidence), what is missing, what must be
built/bought/licensed/substituted/redesigned, how shocks propagate, which unknowns decide the
answer, and whether the target is feasible — conditionally, infeasibly, or not adjudicable.

## Quick start

Requirements: Python 3.12+, Node 18+ (frontend build only).

```powershell
# 1. Python deps (fastapi/uvicorn/pydantic/yaml/scipy/numpy/pytest)
pip install fastapi uvicorn pydantic pyyaml scipy numpy pytest

# 2. Run the test suite
python -m pytest tests -q

# 3. Headless flagship run (JSON)
python scripts/forge_cli.py run --pack humanoid_india --variant hv2_industrial --units 1000000 --min-dva 0.7

# 4. Serve the console
cd web; npm install; npm run build; cd ..
python -m uvicorn server.app:app --port 8000
# open http://127.0.0.1:8000
```

## What is real here (and what is not)

- **Real evidence:** every capacity number, project state, and architecture anchor in the
  knowledge packs traces to an immutable `EvidenceRecord` with source URL, access date,
  epistemic class (`MEASURED / REPORTED / ESTIMATED / ASSUMPTION / UNKNOWN / CONFLICTED`),
  and per-dimension confidence. Seed evidence comes from the supplied research corpus plus a
  live World Bank adapter (`/api/adapter/worldbank`).
- **Honest ignorance:** humanoid-grade reducer/encoder capacity in India is genuinely UNKNOWN
  in public data. FORGE refuses to fabricate it: those items become named binding gaps or
  blocking unknowns (`NOT_ADJUDICABLE`), with a value-of-information ranking telling you which
  audit would change the conclusion.
- **Computation, not scripts:** verdicts, gaps, plans, frontiers, and option values are outputs
  of a typed requirement-flow graph → effective-capacity → allocation-LP pipeline (HiGHS).
  No scenario outcomes are hardcoded; the shock engine edits constraints and re-solves.

## V0.1 correctness release (this branch)

V0.1 is a **correctness foundation**: the mathematics now means what it says.

- Requirement explosion is a linear, order-invariant flow graph — shared upstreams are
  counted exactly once (hand-derived oracles pin the numbers).
- `min_dva` means **aggregate recursive DVA** of the delivered mix, enforced by a
  certified loop with an exposed certificate — not per-item import caps.
- Shortfalls carry their physical units; cross-item rankings use a dimensionless
  normalized deficit. Import eligibility never creates supply: evidenced foreign
  capacity ceilings bound imports.
- Projects, qualifications, and plan actions obey the physical clock; scenario state
  survives every re-solve; displayed envelopes equal solved envelopes.
- Every consequential output traces to evidence nodes in a runtime proof DAG;
  `ModelRun` identity hashes the full world snapshot (deterministic).

See `docs/VALIDATION_REPORT_V2.md` for verified claims, modeled assumptions, and
deferred items. V0 history: see `docs/` (specification documents preserved).

## The five questions FORGE answers (V0 scope)

| Question | Where |
|---|---|
| Can we? | VERDICT mode + `/api/solve` result classes |
| What is missing? | Binding-gap tables, STRATA map, capacity envelopes |
| How do we make it possible? | Transformation portfolio (BUILD/FUND/QUALIFY/SUBSTITUTE) verified by re-solve |
| What should we investigate next? | Value-of-information panel (feasibility-flip detection) |
| What should we build for many futures? | Option-value report across domain objectives |

Plus: closure frontier (localization sweep), reverse buildability (max output under
constraints), shock lab (constraint-editing propagation), proof inspector (every number traces
to evidence).

## Repository layout

```
forge/        computational core (units, epistemics, ontology, solver, planner, VOI, …)
packs/        three schema-validated domain knowledge packs (YAML)
server/       FastAPI app serving API + built console
web/          React+TS console (source); web/dist is the built bundle
scripts/      CLI (headless runs, pack listing, live-data demo)
tests/        contract tests, pack benchmarks, mechanism backtests
docs/         MODEL_CONTRACT, ARCHITECTURE, DECISIONS, PHASE1_CHALLENGE,
              DATA_SOURCES, DATA_RIGHTS, VALIDATION_REPORT, PROJECT_STATUS
research/     supplied research corpus + RESEARCH_AUDIT.md
```

## Flagship acceptance path

1. Open the console → pack *humanoid_india*, variant *HV-2 industrial*.
2. Preset **Flagship baseline** → verdict is INFEASIBLE under ≥70% DVA with named precision-
   motion gaps; DVA panel shows achieved domestic share.
3. Preset **Imported-kit assembly** → CONDITIONALLY_FEASIBLE (assembly-only definition) with
   explicit conditions — the corpus's own distinction, computed.
4. Toggle the **REE export shock** → constraint edits propagate; substitution candidate gains
   rank in the verified plan.
5. FRONTIER shows the measured feasibility cliff between 0% and 50% localization; reverse
   query contrasts raw output vs owned output.
6. Click any gap → proof chain to source documents.

## License & data rights

Code: project-internal. Data: each claim carries its own license metadata — see
`docs/DATA_RIGHTS.md`. Restricted sources are referenced, never mirrored.
