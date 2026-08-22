# FORGE WORLD — MODEL CONTRACT v1.0

Non-negotiable computational and epistemic invariants. Code that violates this contract is
defective regardless of output quality. Each invariant cites where it is mechanically enforced.

## C1 Evidence and model state are separate
Raw claims are immutable, versioned `EvidenceRecord`s (frozen after creation; corrections add a
new record with `supersedes`). Normalized model parameters are `DerivedValue`s produced by
declared transforms from evidence records. Enforced in `forge/evidence.py` (records are frozen
dataclasses; no mutation API) and by the proof graph.

## C2 Epistemic class is mandatory on every parameter
Exactly one of: `MEASURED REPORTED DERIVED ESTIMATED MODELLED ASSUMPTION SCENARIO UNKNOWN
CONFLICTED`. No silent conversion between classes. `UNKNOWN` never becomes 0; it either blocks
adjudication or enters explicitly as an interval under a declared estimation method.
Enforced in `forge/epistemics.py` + pack validation tests.

## C3 Units are mechanical
Every physical numeric value is a `Quantity(value, unit)`. The unit engine rejects dimensionally
invalid operations and non-convertible pairs (ore-tonne ≠ contained-metal-tonne ≠ magnet-tonne;
MW ≠ MWh; nameplate ≠ saleable). Enforced in `forge/units.py`; property tests cover conversions
and rejections.

## C4 Three clocks
`evidence_clock` (when observed/reported), `physical_clock` (when construction/production/ramp
occurs), `decision_clock` (deadline). Every capacity value carries both an effective period and an
evidence date. Enforced by required fields on `CapacitySegment` and `Project`.

## C5 Capability is a vector, not a flag
Capability = specification envelope + maturity vector (design ownership, process ownership,
tooling autonomy, capital-equipment dependence, precursor dependence, metrology/test, workforce,
qualification state, demonstrated scale). Human-facing labels are derived views only.
Enforced in `forge/model.py::Capability`.

## C6 Capacity is effective and temporal
`effective_capacity(t) = nameplate × availability × utilization × yield × qualification_fraction`,
all factors separately inspectable, all time-indexed. Ramp is a curve, not a step, unless
evidence says otherwise. Enforced in `forge/capacity.py`.

## C7 Projects use explicit state machines
States: concept → announced → engineering → permitting → approved → financed(FID) → procurement
→ construction → mechanical_completion → commissioning → process_qualification →
customer_qualification → ramping → mature → impaired → retired. Announced ≠ operating.
Capacity from a project counts only per its current state's contribution model.
Enforced in `forge/projects.py`.

## C8 Qualification gates production
Output is sellable/usable for the objective only through qualified routes; unqualified capacity
is visible but does not satisfy demand unless a QUALIFY action completes in time.
Enforced in the solver's constraint generation.

## C9 Substitution requires a validation contract
A `Substitution` must carry functional-compatibility envelope, performance deltas, changed BOM/
BOP, new equipment/skills/materials, maturity, transition time/cost, and evidence. LLM text can
propose candidates; candidates enter the solver ONLY as validated contracts.
Enforced in `forge/substitutions.py` (contract completeness validator).

## C10 Shocks modify constraints, never outputs directly
A shock edits capacity, yield, route availability/cost, supplier eligibility, demand pools,
input costs, financing, or project states. Propagation happens exclusively through re-solve.
Enforced in `forge/shocks.py` (shock objects have no "impact" field).

## C11 Lazy strategic recursion
Capital goods start as externally-supplied ResourceClasses. Recursion into their production is
triggered by materiality rules (import denial, concentration, lead time, shadow price, binding
constraint, policy). Stop when acquisition is reliable/non-binding/low decision value.
Enforced in `forge/recursion.py` with recorded triggers on every expanded node.

## C12 Classification crosswalks are confidence-bearing and many-to-many
HS/SITC/ISIC ↔ internal ontology mappings carry confidence and provenance; no silent conversion
of trade codes into engineering capabilities. Enforced in pack schema (`crosswalks:` section).

## C13 Model resolution cannot exceed evidence resolution
No city-level values derived from country-level priors; geographic fields degrade to coarser
levels rather than interpolate. Pack validator flags resolution escalation.

## C14 Model runs are reproducible
A `ModelRun` stores data snapshot hash, pack versions, objective, scenario, assumption set,
solver version+config, seed, timestamps, inputs, outputs, warnings, and the full proof graph.
Same inputs ⇒ byte-identical results (deterministic algorithms; stochastic parts seeded).
Enforced by reproducibility tests.

## C15 Important outputs create proof graphs
Every consequential number traces through derivation steps to evidence records and assumptions.
UI exposes the chain. Enforced in `forge/proof.py`; solver emits nodes for every computed claim.

## C16 Infeasibility must be explained
Result classes: `FEASIBLE`, `CONDITIONALLY_FEASIBLE`, `INFEASIBLE_UNDER_MODEL`,
`NOT_ADJUDICABLE`. Infeasible ⇒ binding constraints + minimal conflicting set where practical +
required relaxations + candidate closure actions. Not-adjudicable ⇒ list of blocking UNKNOWNs.
Enforced in `forge/solve.py`.

## C17 UNKNOWN / CONFLICTED are first-class
Blocking unknowns produce NOT_ADJUDICABLE or CONDITIONAL results with named unknowns.
Conflicting evidence remains represented as CONFLICTED unless a reconciliation rule (with its own
evidence) resolves it — and then the conflict history is preserved.

## C18 DVA (domestic value addition) accounting convention
DVA of a delivered unit = 1 − (imported content valued at landed cost) / (ex-works unit cost),
computed recursively over the recipe tree: imported raw materials/components count at first
arrival into the boundary; domestically produced subcomponents contribute their own recursive
domestic share. Imported embedded content inside imported assemblies stays imported.
All DVA claims expose the boundary and the recursion. Enforced in `forge/dva.py`.

## C19 Data rights follow the data
Every dataset/claim carries license metadata; restricted sources cannot contaminate exportable
core bundles. Enforced by pack schema + DATA_RIGHTS.md rules + a test asserting license presence.

## C20 LLMs are never numerical authorities
No code path assigns capacity/yield/cost/maturity/recipe coefficients from model-generated text
without promotion through evidence + validation. FORGE runs fully without any LLM present.
Enforced architecturally (no LLM in the solve path) + review.

## C21 No fabricated entities
Organizations, facilities, capacities not traceable to a source may exist only as explicit
ASSUMPTION/SCENARIO objects clearly labeled, never as observed reality. Pack validator requires
evidence links for MEASURED/REPORTED classes.

## C22 Physical conservation
Mass balances close across recipes within declared yields/scrap; inventory balances carry over
time; flow conservation holds in logistics; energy accounting separates power from energy.
Enforced by explosion/balance tests per knowledge pack.
