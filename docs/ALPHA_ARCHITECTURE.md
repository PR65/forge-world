# FORGE WORLD Alpha Architecture

**Status:** implementation contract for the alpha campaign
**As-of:** 2026-08-24
**Authority:** subordinate to `FORGE_WORLD_NORTH_STAR.md` and `MODEL_CONTRACT.md`

## 1. Alpha claim

The alpha is one evidence-backed industrial workbench over one shared industrial world.
It is not five disconnected applications and it is not a visual wrapper around prose.

The shipped loop is:

```text
objective
  -> product architecture
  -> requirements / BOM / BOP
  -> capacity, qualification, geography, and evidence state
  -> auditable solve and WHY chain
  -> redesign or transformation candidate
  -> verified re-solve
  -> evidence and execution tasks
```

The V0.1 requirement-flow, capacity, DVA, temporal, proof, and reproducibility
contracts remain the computational authority. The alpha adds a canonical registry,
read/query surfaces, additional benchmark packs, and a unified workbench. It does not
weaken a V0.1 verdict or silently fill an UNKNOWN.

## 2. One world, two projections

FORGE uses two projections of the same checked-in knowledge:

1. **Solver projection.** A domain `KnowledgePack` produces an isolated typed `World`
   for a reproducible model run. Pack-local identifiers and solver semantics remain
   unchanged.
2. **Registry projection.** A versioned canonical read model indexes all packs,
   namespaces every pack-local identity, and binds equivalent industrial capabilities
   to stable cross-sector identifiers.

The registry is not a second numerical authority. A canonical binding says that two
pack nodes refer to or require the same reusable capability class. It does not imply
that a builder has that capability, that a facility is qualified, or that supply exists.

### 2.1 Canonical identity

- Pack entities are addressed as `pack:<pack_id>:<entity_id>`.
- Cross-sector capabilities use stable `cap:*` identifiers.
- Aliases are explicit registry records, never fuzzy overwrites.
- Conflicting observations coexist and remain `CONFLICTED` until reconciled.
- A missing observation stays `UNKNOWN`; absence is never converted to zero.

### 2.2 Persistence and versioning

The distributable alpha world state is repository-backed:

- YAML knowledge packs hold solver inputs and evidence records.
- The registry manifest holds canonical capability definitions, explicit bindings,
  aliases, and evidence tasks.
- Source and pack snapshots carry deterministic SHA-256 hashes.
- Registry snapshot identity is derived from normalized manifest, pack, source, and
  evidence state.

This establishes reproducible, diffable world versions without claiming a complete
live mirror of IndiaBUILD or any licensed source.

## 3. Evidence ingestion contract

Every adapter follows the same boundary:

```text
source reference
  -> immutable SourceSnapshot (hash, access time, license, storage posture)
  -> normalized Observation
  -> validation and reconciliation
  -> explicit promotion to EvidenceRecord
  -> entity / model parameter
  -> proof node
  -> output
```

Promotion is an explicit act. Fetching, parsing, or matching a source cannot mutate
solver state on its own. Raw third-party pages are not mirrored unless their rights
permit it; a content or metadata hash plus the minimal attributed claim is sufficient
for referenced sources. `MEASURED` and `REPORTED` observations require a real source.
Model mappings and engineering coefficients must remain `MODELLED` or `ASSUMPTION`.

## 4. Workbench contract

The primary surface is an industrial debugger with three persistent regions:

- **Case rail:** objective interpretation, active architecture, geography, deadline,
  DVA/autonomy constraint, scenario branch, funded projects, shocks, and assumptions.
- **World Plane:** a semantic two-dimensional dependency space with typed edges,
  epistemic state, year-local capacity state, bottleneck paths, and lazy recursion.
- **WHY inspector:** WHAT, WHY, HOW DO WE KNOW, WHAT IS UNKNOWN, WHAT WOULD CHANGE THE
  ANSWER, and the currently valid research/design/execution verbs.

The five modes are lenses over the same run, scenario, year, selection, and evidence
snapshot:

- **ANALYZE:** verdict, binding gaps, UNKNOWNs, causal path, shocks, and tradeoffs.
- **DESIGN:** architecture and substitution comparisons as dependency-graph rewrites.
- **EXECUTE:** verified transformations, project/qualification gates, and evidence work.
- **DISCOVER:** canonical capability-to-objective reuse and measured option value.
- **LEARN:** progressive explanation of the selected physical chain, down to evidence.

Existing V0.1 views become ANALYZE lenses rather than competing product modes.

### 4.1 Why the alpha is 2D

The current packs contain real dependency depth and time state, but little verified
facility geometry or route topology. A globe, free camera, factory fly-through, or
decorative particle network would imply spatial precision the model does not possess.
The alpha therefore uses accessible SVG/DOM geometry with a synchronized list/tree
fallback. A constrained 2.5D time/recursion layer may follow once it improves an actual
decision. Geographic 3D is gated on coordinate-backed facilities and corridors.

### 4.2 Scenario and decision discipline

- A baseline run is immutable.
- A scenario is a named delta and produces a new run/hash.
- A substitution rewrites dependencies and must pass its functional envelope.
- An approval may authorize research, procurement, testing, or an assumption; it may
  not turn UNKNOWN into supply.
- Rollback selects an earlier branch/snapshot rather than mutating history.
- Only operations supported by the backend are enabled.

## 5. The three clocks

The workbench keeps three clocks distinct:

| Clock | Alpha state |
|---|---|
| Physical | Modeled years, project windows, qualification, ramp, and plan timing |
| Evidence | Source publication/access dates, pack version, registry snapshot, run time |
| Decision | Explicit gate dates where modeled; otherwise `UNKNOWN — not modeled` |

The objective deadline is not silently reused as a decision deadline.

## 6. Benchmark boundaries

The alpha exercises four distinct physical regimes:

- one million humanoids/year at a recursive DVA target;
- 100 high-quality CNC machining centers/year;
- an annual manufacturing slice of a 200 GW nuclear buildout;
- existing battery and small-satellite contrast packs.

The nuclear benchmark is explicitly an annual production-flow representation. The
current solver does not yet claim to model cumulative installed generation, fleet
retirements, construction-site concurrency, or grid dispatch. Those limitations must
remain visible wherever the benchmark is shown.

## 7. Alpha acceptance gates

The milestone is accepted only when all of the following are observable:

1. The unchanged V0.1 suite still passes.
2. Registry snapshots are deterministic and pack identities cannot collide.
3. At least one canonical capability is demonstrably reused across multiple packs.
4. Every registry fact resolves to evidence, an explicit model mapping, or UNKNOWN.
5. World search and bounded graph slices are queryable through the API.
6. CNC and nuclear packs load, explode linearly, and preserve strict epistemics.
7. The five product modes preserve the same run/scenario/selection context.
8. A binding item can be followed through a real WHY/proof/evidence chain.
9. Keyboard and narrow-screen fallbacks expose the same essential information.
10. Production frontend build, Python tests, API smoke checks, and a browser walkthrough
    pass after an adversarial review-and-repair cycle.

## 8. Explicitly deferred depth

- Complete IndiaBUILD ingestion or mirroring.
- Facility-complete global geography and logistics routing.
- Cumulative nuclear fleet/grid modeling.
- Multi-user approvals, authentication, and external work-management integrations.
- General CAD geometry and photorealistic 3D.
- Automatic evidence promotion by an LLM.
- Claims of complete machine-builds-machine recursion in every benchmark.

These are deferred because the necessary data or model contracts are not yet present,
not because the long-term FORGE scope has narrowed.
