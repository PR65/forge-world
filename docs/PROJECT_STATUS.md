# PROJECT STATUS

**State: V0 complete and demonstrable.** Last updated 2026-08-22.

## What exists and works

- **Computational core (`forge/`)** — unit-safe quantities (dimensionally enforced,
  mass-family separated), immutable evidence + proof graphs, typed industrial ontology
  (~30 entity kinds, typed edges only), knowledge-pack loader with contract validation,
  BOM/BOP explosion with yield gross-up, effective-capacity envelopes (temporal, factor-
  separable), project state machines with ramp curves, allocation LP (HiGHS) with binding-
  constraint extraction, result classification incl. NOT_ADJUDICABLE, recursive DVA
  accounting, validated substitution contracts, constraint-editing shock engine,
  transformation planner verified by re-solve, value-of-information flip detection,
  closure-frontier sweep, reverse buildability, cross-objective option-value report,
  reproducible ModelRuns.
- **Three domain packs** — humanoid_india (flagship, 104 entities/18 evidence records),
  battery_gwh_india, smallsat_india. All schema-validated; UNKNOWN left UNKNOWN.
- **48 passing tests** including pack benchmarks and three mechanism backtests.
- **API server** — /api/packs, /api/solve, /api/packs/{id}, /api/optionvalue,
  /api/adapter/worldbank. Serves the built console.
- **Console UI** — five instrument modes (VERDICT / STRATA / TIME / STRESS LAB / FRONTIER)
  + persistent proof inspector. Canvas strata map, capacity-vs-demand timelines, plan gantt
  with lead-time windows, shock diffing, measured feasibility cliff, VOI ranking, option-value
  bars. Dark forge visual identity; no card walls; every view renders computed state.
- **Live data adapter** — World Bank open-data fetch wrapped as MEASURED observations.

## Flagship demo path

`README.md → "Flagship acceptance path"`. Headless equivalent:
`python scripts/forge_cli.py run --pack humanoid_india --variant hv2_industrial --units 1000000 --min-dva 0.7`

## Known limitations (honest list)

1. Capacity evidence is sparse where the world is opaque (reducers, encoders, robot-grade
   motors). The system says UNKNOWN instead of inventing numbers — by design.
2. Import supply is eligibility-fraction-limited, not vessel-level constrained; corridor
   capacities are cost/time proxies only in V0.
3. Competing demand uses contestable-pool priors (ASSUMPTION basis), not partial equilibrium.
4. Option value measures within-pack relief per evidenced investment; cross-pack synergy
   mapping (shared cells/machining across packs) is not yet wired into scoring.
5. Machine-hour recursion is implemented + tested on fixtures but the humanoid pack's
   equipment fleets are UNKNOWN (correctly) — so recursion triggers are exercised mainly in
   tests rather than the flagship run.
6. Frontend assumes local API; no auth/multi-user.
7. LLM adapter is an interface slot only — deterministic objective entry is the shipped path
   (C20 keeps LLMs out of the numeric authority role regardless).

## Next highest-leverage work

1. Comtrade/DGCI&S adapter to upgrade magnet-import REPORTED claims toward MEASURED.
2. Wire equipment-hour limits into flagship scenarios once fleet evidence lands (VOI already
   ranks what to collect).
3. Cross-pack capability sharing for true portfolio option value.
4. Quarterly time-grid refinement near qualification windows.
