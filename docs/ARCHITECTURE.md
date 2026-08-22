# FORGE WORLD — ARCHITECTURE

## System shape

```
┌────────────────────────────────────────────────────────────────────┐
│ web/  React + TypeScript console (Vite build → static assets)      │
│   views: objective · architectures · requirements map · capacity   │
│   timeline · transformation plan · shock lab · uncertainty/VOI ·   │
│   closure frontier · option value · proof inspector                │
└──────────────▲─────────────────────────────────────────────────────┘
               │ JSON (REST, local)
┌──────────────┴───────────────┐   ┌───────────────────────────────┐
│ server/ FastAPI              │   │ scripts/ CLI (headless runs)  │
│  /api/objective  /api/solve  │──▶│ forge run --objective ...     │
│  /api/proof      /api/packs  │   └───────────────┬───────────────┘
└──────────────▲───────────────┘                   │
               │                                   ▼
┌──────────────┴──────────────────────────────────────────────────────┐
│ forge/  computational core (pure Python, no I/O at solve time)      │
│  units        dimensional analysis engine                           │
│  epistemics   epistemic classes, confidence dimensions              │
│  evidence     immutable EvidenceRecords, sources, provenance graph  │
│  model        typed ontology (~30 first-class entity types)         │
│  pack         knowledge-pack loading + validation                   │
│  explode      BOM/BOP explosion, gross requirements, mass balance   │
│  capacity     effective capacity, temporal segments                 │
│  projects     project state machines, ramp curves                   │
│  solve        feasibility engine: allocation LP (HiGHS), fixed-     │
│               charge MILP for portfolios, binding constraints       │
│  dva          recursive domestic-value-addition accounting          │
│  substitutions validated substitution contracts                    │
│  shocks       constraint-editing shock engine + re-solve            │
│  planner      closure actions → sequenced transformation plans      │
│  voi          value-of-information (feasibility-flip detection)     │
│  frontier     industrial closure frontier sweeps                    │
│  optionvalue  capability portfolio option-value scoring             │
│  recursion    lazy strategic machine recursion                      │
│  reverse      reverse-buildability max-output queries               │
│  proof        derivation DAG emitted by every computation           │
│  run          ModelRun reproducibility container                    │
└──────────────▲──────────────────────────────────────────────────────┘
               │ loads at startup (versioned snapshots)
┌──────────────┴──────────────────────────────────────────────────────┐
│ packs/  domain knowledge packs (YAML, schema-validated)             │
│  humanoid_india (flagship) · solar_pv · small_sat                  │
│ data/   evidence snapshots + fetched open data (World Bank etc.)    │
└─────────────────────────────────────────────────────────────────────┘
```

## Why this shape

- **Solver isolated from UI.** The core has zero web dependencies; the CLI can reproduce any
  API result byte-for-byte (ModelRun).
- **Knowledge packs are data, not code.** The universal ontology is exercised by three packs;
  pack-specific logic in the core is a contract violation.
- **LP where the abstraction is linear; explicit rules elsewhere.** Allocation of scarce
  qualified capacity across time with import eligibility is an LP (HiGHS via scipy).
  Portfolio choice over candidate projects is a small fixed-charge MILP. Everything else is
  deterministic typed computation — no method is used for spectacle.
- **Proof graph is a by-product, not a bolt-on.** Every solver/emitter call records derivation
  nodes; the UI's inspector renders the same DAG the tests assert on.
- **Frontend reads computed state only.** No numbers hardcoded in the UI layer.

## Data flow of a solve

1. Objective (structured or parsed) + scenario (shocks, constraints) selected.
2. Pack snapshot loaded (versioned); evidence records frozen.
3. Reference architecture chosen (user or auto-compare across variants).
4. Explosion computes annual component/material/process requirements incl. scrap/yield gross-up.
5. Lazy recursion expands binding capital-goods nodes when triggers fire.
6. Capacity engine assembles effective-capacity envelopes per node/year from facilities,
   capability claims, and project state machines under the scenario.
7. Feasibility engine solves allocation per year: domestic qualified production ≤ effective
   capacity; imports ≤ eligible supplier capacity × eligibility; deficits identified.
8. Result class assigned (FEASIBLE / CONDITIONALLY_FEASIBLE / INFEASIBLE_UNDER_MODEL /
   NOT_ADJUDICABLE) with binding constraints, minimal conflict sets, DVA accounting.
9. Planner synthesizes closure portfolios (BUILD/QUALIFY/LICENSE/SUBSTITUTE/REDESIGN/…),
   sequences them on the physical clock, and re-runs 7–8 to verify closure.
10. VOI, frontier, reverse, and option-value modules consume the same machinery.
11. ModelRun persisted with hash; proof graph serialized with every response.

## Performance posture

Graph sizes in V0 are hundreds of nodes — LPs solve in milliseconds; explosion is memoized;
the API caches solved ModelRuns by input hash; the frontend renders incrementally (canvas for
graphs/timelines), never mounting thousands of DOM nodes.

## Storage

File-based, versioned snapshots under `data/` (JSON). A database is unnecessary at V0 scale and
would add migration burden without benefit; `ModelRun` JSON artifacts provide reproducibility.
This is revisited if pack count grows by an order of magnitude (documented tradeoff).
