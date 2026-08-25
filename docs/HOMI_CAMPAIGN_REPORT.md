# HOMI Reality Injection + World Model Expansion — Campaign Report

Date: 2026-08-25  
Branch: `codex/homi-reality-world-expansion`  
Baseline: `ece00c16f320c68d48b594b68917e5eff91ace1b`

## Outcome

The campaign moved FORGE WORLD from five authored objective packs plus a large
external research reservoir to a seven-pack canonical registry with a guarded
claim-staging layer, full corpus accounting, foundational materials, 44 shared
capability families, primary-source targeted reality closure, and frozen novel
objective composition.

The result is materially more general, but it is not a completed industrial
world model. It can compose and trace unfamiliar industrial architectures far
better than the baseline; it still cannot automatically construct a validated
quantitative BOM and facility-compatible qualified-capacity network for an
arbitrary objective. Every frozen novel objective therefore returns
`NOT_ADJUDICABLE`, explicitly meaning insufficient closure rather than
infeasibility.

## What changed

### Reality boundary

- Four layers are enforced: immutable raw vault, non-authoritative claims,
  reviewed canonical world state, and derived/scenario state.
- Staging IDs derive from corpus, path, artifact hash, locator, subject, and
  predicate rather than worker order.
- Identity, ontology/relation, geography, conflict, freshness, rights, and
  promotion states are separate.
- Trade, reserves, announcements, facility presence, supplier candidacy,
  nameplate, qualification, and available capacity have executable
  anti-laundering guards.
- Deterministic repair preserves original hashes, rationale, before/after row
  accounting, changed fields, repaired hashes, and validation outcome.

### Corpus and world expansion

- All 20 Manus corpora have bounded, hash-linked staging reports.
- The verified corpus numbering mismatch is preserved in
  `research/homi/corpus_map.json`; source content overrides expected numbering.
- The GLM materials pack was imported byte-identically from the approved source;
  the manual-test pack was not imported.
- Foundational materials add 137 entities and 138 edges covering materials,
  recipes, equipment, resources, organizations, facilities, projects,
  capability claims, qualifications, shocks, and substitutions.
- Targeted reality adds 28 entities and 14 evidence records for drives, motors,
  electronics, encoders, electrolyzer stacks, demonstration MEA fabrication,
  gas systems, compressors, heat transfer, metrology, bearings, grinders, and
  space electro-optics.
- Foundational packs without objective variants are excluded from objective
  solving, preventing ontology substrate from becoming an accidental product
  objective.

### Primary-source closure

The decision-gap ranking triggered 12 bounded research tasks. Fourteen selected
records completed the full path:

`source → deterministic snapshot → observation → reviewed evidence promotion → canonical mapping`

All 14 have declared rights posture and source lineage. Zero records became
effective qualified capacity. The promoted statements establish only their
actual scope: a reported line, facility, product/process family, demonstration,
or test scheme. Utilization, yield, qualification, allocation, compatibility,
and objective-grade throughput remain explicit unknowns.

Research stopped below the 20–30 task ceiling because the remaining ranked gaps
are Kenya-specific battery-pack integration evidence and field service; neither
has the cross-objective leverage of the completed work.

## Campaign accounting

| Measure | Result |
|---|---:|
| Research artifacts | 321 |
| Unique hashes | 315 |
| Duplicate artifacts | 12 |
| Raw ZIP packages | 20 |
| Raw ZIP entries byte-matched | 254 / 254 |
| Raw integrity failures | 0 |
| Structured validated artifacts | 101 |
| Inventoried context artifacts | 215 |
| Deterministically repaired artifacts | 30 |
| Malformed, unrepaired GLM staging YAMLs | 4 |
| Intentionally skipped manual-test pack | 1 |
| Manus corpora with bounded reports | 20 / 20 |
| Gate-0 claim candidates | 58 |
| Gate-0 conflicts | 3 |
| Gate-0 promotions | 0 |
| Targeted sources/snapshots/observations/promotions | 14 / 14 / 14 / 14 |
| Targeted effective-capacity promotions | 0 |
| Canonical packs | 7 |
| Registry nodes / edges / evidence | 924 / 1,412 / 131 |
| Canonical capability families | 44 |
| Families mapped across two or more packs | 20 |
| Facilities / capacity segments | 32 / 14 |

Corpus-specific source, claim, entity, and relation counts use different
semantic units—rows, bounded samples, table members, or nested claims. They are
reported per corpus and are deliberately not added into a misleading global
claim total. The machine-readable accounting and every report hash are in
`research/homi/campaign_accounting.json`.

## Generalization results

Composition Coverage is weighted structural reuse only. It does not claim
feasibility, qualified supply, capacity closure, BOM completeness, or economics.

| Frozen objective | Structural coverage | Decision-critical composition gaps | Adjudication |
|---|---:|---:|---|
| India: 50,000 industrial heat pumps/year | 1.000 | 0 | NOT_ADJUDICABLE |
| India: multi-GW electrolyzer manufacturing | 1.000 | 0 | NOT_ADJUDICABLE |
| Kenya: 100,000 agricultural drones/year | 0.875 | 2 | NOT_ADJUDICABLE |
| Rare-earth-minimized industrial motor | 0.893 | 0 | NOT_ADJUDICABLE |
| India: 10,000 12U hyperspectral satellites/year | 1.000 | 0 | NOT_ADJUDICABLE |
| Shared CNC/robotics/aerospace/EV constraints | 1.000 | 0 | NOT_ADJUDICABLE |

Mean coverage moved from 0.795905 after foundational integration to 0.961310
after targeted closure. Decision-critical composition unknowns fell from 25 to
2, and ranked tasks from 16 to 2. This improvement comes from evidence-bearing
shared primitives, not from adding bespoke objective packs.

Each requirement now exposes canonical mappings, local entities, evidence IDs,
epistemic classes, source IDs, publisher, URL, and license. The heat-pump and
electrolyzer analyses are serious evidence-linked architecture compositions,
but remain `NOT_ADJUDICABLE` because quantitative BOMs, objective-grade
compatibility, qualified effective capacity, allocation, ramp, economics, and
complete physical/evidence clocks are absent.

## Acceptance assessment

| Criterion group | Result | Evidence |
|---|---|---|
| Raw integrity and reproducible conditioning | PASS | 254/254 archive matches; zero failures; deterministic repair reports |
| Source lineage and rights | PASS | 100% of 14 targeted promotions source-linked; unspecified corpus rights block bulk promotion |
| UNKNOWN/conflict preservation | PASS | Gate tests, corpus ledgers, capability-vector UNKNOWNs, conflict reconciliation |
| No proxy capacity laundering | PASS | No targeted capacity segment; all facility/nameplate factors remain separate |
| Solver/Alpha regression integrity | PASS | Full suite and pack validation pass |
| Reusable primitive expansion | PASS | 44 canonical families; 20 cross-pack; two foundational packs |
| Existing vertical enrichment without shadows | PASS | CNC, humanoid, nuclear, battery, and smallsat mappings reconcile to existing IDs |
| Novel-objective composition | PASS | Six frozen objectives; requirement/evidence/source traces; no bespoke objective packs |
| Material Composition Coverage improvement | PASS | 0.795905 → 0.961310 |
| Structured research backlog and bounded closure | PASS | 16 → 2 tasks after 12 bounded research tasks |
| Facility/geography improvement | PARTIAL | Ten-plus targeted facility scopes and 32 canonical facilities; many corpus coordinates remain staging |
| Capacity adjudicability | PARTIAL | Semantics are safer, but facility-specific effective qualified capacity remains sparse |
| Evidence-linked unfamiliar objective analysis | PASS | Heat pumps and electrolyzers compose reusable worlds and identify exact adjudication blockers |
| Verdict-to-source trace and honest insufficiency | PASS | Novel results return NOT_ADJUDICABLE and trace requirements to source URLs/licenses |

## Founder-level maturity assessment

These are judgment estimates, not engineering KPIs. The overall estimate does
not reach the aspirational 50–55% range because capacity reality, automated BOM
synthesis, DESIGN optimization, and execution-grade workflows remain shallow.

| Dimension | Start | End | Evidence for movement | Next major level requires |
|---|---:|---:|---|---|
| Truth/solver integrity | 78% | 81% | New features remain outside solver unless model-ready; full oracles regress cleanly | More product/facility compatibility and capacity oracles |
| Evidence architecture | 50% | 73% | Claim gate, rights, snapshots, observations, promotions, conflicts, freshness | Automated source refresh, supersession, and reviewer workflow |
| Industrial primitive coverage | 40% | 60% | Materials, processes, equipment, metrology, qualification, and 44 families | Deeper controlled process cards, tooling, utilities, and tacit knowledge |
| Facility/geography coverage | 22% | 39% | Corpus facility atlas plus primary-source facility scopes | Canonical coordinates, ownership histories, corridors, utilities, and site identity resolution |
| Capacity realism | 34% | 43% | Stronger anti-laundering and explicit nameplate state | Measured output, utilization, yield, qualification, allocation, and time series |
| Cross-sector reuse | 38% | 64% | 20 multi-pack families and six novel compositions | Qualification-aware family/subtype lattice and more cross-sector process reuse |
| Generalization | 28% | 58% | Frozen objectives compose at 0.961 structural coverage | Automatic validated BOM/process/facility networks and solver handoff |
| DESIGN capability | 27% | 39% | Architecture seeds and substitution boundaries | Multi-architecture generation, physics constraints, trade studies, qualification effects |
| EXECUTE capability | 18% | 25% | Better supplier/project/qualification semantics | Work packages, sourcing events, readiness gates, schedules, change control |
| DISCOVER capability | 30% | 51% | Decision-gap ranking and cross-objective leverage | Causal intervention value, cost/time/option models, portfolio optimization |
| Research automation | 20% | 49% | Deterministic corpus conditioning and targeted promotion pipeline | Continuous connectors, primary-source crawling, diffing, and bounded review queues |
| Freshness/update readiness | 18% | 35% | Freshness states and snapshots exist | Scheduled refresh, source monitoring, supersession, stale-impact propagation |
| UX/product usability | 30% | 37% | Evidence, reality, ingestion, composition, and gap APIs exposed | Analyst review UI, trace explorer, scenario comparison, decision workflow |
| Overall long-term vision | 36% | 47% | Reusable evidence-backed substrate and honest unfamiliar-objective analysis | Capacity-dense world state, automatic physical synthesis, DESIGN/EXECUTE depth, live freshness |

## Verification

- Python: 212 tests collected; 211 passed and 1 intentionally skipped.
- Registry: seven packs load successfully; foundational packs remain non-objectives.
- Frontend: TypeScript and Vite production build pass.
- Raw corpus: 20 archives, 254 entries, 254 byte matches, zero failures.
- Targeted promotion: 14/14 source-linked; zero effective-capacity promotions.

## Material blockers retained

1. Facility-specific realized output, utilization, yield, qualification, and
   allocable capacity are sparse across most industrial families.
2. Corpus licenses and original-source snapshots remain unspecified for most
   Manus claims, correctly blocking bulk canonical promotion.
3. Geography needs canonical facility identity, coordinates, ownership history,
   utility/corridor links, and chokepoint state.
4. Novel objectives have architecture seeds but not automatically validated
   quantitative BOMs, process recipes, or facility-compatible capacity graphs.
5. Supplier qualification needs product/customer/date-specific approval and
   available allocation rather than manufacturer identity.
6. Continuous freshness, supersession, and conflict review are not yet an
   operational service.

The campaign therefore stops with a stronger and more honest FORGE WORLD: it
can assemble much more of an unfamiliar industrial future, show the supporting
world evidence, and identify exactly why a defensible feasibility verdict is
still unavailable.
