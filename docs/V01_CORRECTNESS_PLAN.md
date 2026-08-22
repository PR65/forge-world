# V0.1 — CORRECTNESS PLAN

Priority scale: **P0** = any quantitative conclusion untrustworthy until fixed;
**P1** = conclusions conditionally trustworthy but wrong in stated scenarios;
**P2** = hygiene/latent. Dependency order is binding: an implementation agent executes
waves strictly in order; each wave's oracles (from `V01_MATHEMATICAL_ORACLES.md`) must pass
before the next wave begins. No wave may weaken an earlier wave's invariants.

---

## Wave 0 — Measurement substrate (no behavior change)

**W0.1 Typed flow core (redesign; replaces flat `RequirementLine` dict).**
New immutable `FlowGraph` per explosion: nodes = items with unit dims, edges =
(route, parent, child, qty_per_parent, yield_factor), plus derived aggregate views.
`ExplosionResult` becomes a compatibility wrapper exposing `.lines` read-only.
- Modules: new `forge/flows.py`; `explode.py` re-expressed over it.
- Invariants: additivity (oracle B), immutability under substitution (C1), depth honesty (B2).
- Preserve: yield math, proof-node emission per line, mass-balance checker (fix N7 dup).
- Migration: engine/adapters read via wrapper; no pack schema change.

**W0.2 Unit-safe scalars everywhere.**
`capacity_envelope` and LP vectors carry `(value, unit_dim)` pairs; merging heterogeneous
units raises `UnitError` (oracle J1). Shortfalls become per-unit-family structures;
`total_shortfall` replaced by `ShortfallVector` with explicit, labeled aggregations
(weighted only by declared weights).
- Modules: `capacity.py`, `solve.py`, `engine.py` reporting, `voi.py`, `frontier.py`,
  `optionvalue.py`.
- Invariants: H1-H6.

**W0.3 Honest ModelRun + FX closure.**
Hash = canonical serialization of full World (entities incl. numeric fields, edges) +
objective + scenario opts + solver version. Wire `finish()`. Close currency leak in
Quantity mul/div (raise on cross-currency canonical ops without fx context) (G3, H7).
- Modules: `run.py`, `pack.py(summary→snapshot)`, `units.py`, `engine.py`.

---

## Wave 1 — Explosion & substitution correctness (P0)

**W1.1 Incremental-flow recursion.**
Replace cumulative-accumulator expansion: each recipe edge expands from its own route's
incremental requirement; shared upstreams accumulate once. Oracle B/B2 gate.
- Modules: `explode.py` (over W0.1 core).
- Second-order check: flagship totals will DROP vs V0 numbers; VALIDATION_REPORT matrix
  must be regenerated, not trusted (docs drift N10 noted).

**W1.2 Architecture-level substitution.**
Substitution = {select alternative recipe for node X in FlowGraph} → rebuild graph →
re-aggregate lines. Original explosion deep-immutable (assert by snapshot). Removed
subtree = descendants reachable only through replaced node (C2/C3). Idempotence (C4).
changed_bom entries become graph edits with provenance nodes.
- Modules: `substitutions.py`, planner integration.
- Anti-regression: existing gate tests keep passing unchanged.

**Wave exit:** G1+G2 green; flagship benchmark test rewritten against closed-form
incremental math (the old locked constants encode V0's bug).

---

## Wave 2 — Optimization reformulation (P0)

**W2.1 Dimensional LP.** Variables stay per-item; bounds/constraints computed from
unit-aware envelopes; demand basis unified (gross for capacity sizing, net reported
separately — N3 resolved by explicit naming: `demand_gross`, `demand_net`).
No cross-item unit arithmetic inside the objective except through declared cost weights
(USD/unit must state its unit denominator; default costs become explicit ASSUMPTION rows
per item family, not silent 1.0).

**W2.2 True DVA constraint (two-stage certified loop).**
Outer: given θ, solve LP; measure recursive DVA on delivered mix (F-corrected accounting);
if measured < θ, tighten per-item import caps via dual/price-guided iteration until
measured ≥ θ (report certificate: caps, iterations, achieved DVA) or declare
INFEASIBLE_WRT_DVA as a distinct reason. Later wave may fold content coefficients into a
single MILP/LP with import-content columns; two-stage is the minimal honest fix.
Oracle E2 boundary sweep is the acceptance test (V0 semantics fail it by construction).

**W2.3 Supply-side reality for imports.**
New optional `ForeignSupplySegment` (geography=country, nameplate) consumed by LP as an
import cap summed over eligible origins with evidenced share weights (fallback: concentration
or equal weights flagged ASSUMPTION). Eligibility multiplies availability; never creates
quantity (D1-D4). Unweighted averaging removed (F7).

**W2.4 Envelope interval logic fix.** lo=Σ(segments+operating projects pessimistic),
hi=lo+Σ(unproven optimistic); remove dead min() branch; stop forcing lo=0 on
mixed-provenance projects-only envelopes (J2); conflicted detection wired (K3).

**Wave exit:** G3 green; flagship verdict re-derived and recorded with full certificate.

---

## Wave 3 — Time, qualification, plans (P0/P1)

**W3.1 Action completion semantics.** Planner verification solves year-indexed action
activation: FUND ⇒ project scheduled by its own state machine; QUALIFY ⇒ boost available
only after latency window from decision date (F2); SUBSTITUTE ⇒ transition window gates
availability. `_sequence` becomes the single timing source feeding solves, not display.
Oracle F4 coherence check.

**W3.2 Qualification gating.** Recipe-level `requires_qualification` consulted: unqualified
⇒ route contributes to optimistic edge only + CONDITIONAL ledger entry naming qualification,
standard, window (F11). Remove instant `qualification_boost` bypass; keep boost API but it
must pass through time model.

**W3.3 Conditionality ledger.** Every optimistic-edge contributor emits a structured
condition record {project, state, commissioning window}; `count_unproven_projects=False`
removes their numeric contribution (K1/K2). commission_year_estimate either implemented as
a genuine floor/ceiling or deleted (F10 — recommend delete; state credit already encodes it).

**W3.4 Scenario-state integrity.** Option clones via `dataclasses.replace`-style full copy
including funded_pipeline (N4); competing_demand_cuts merge semantics (I1/I3);
demand_add merges; pool lookup honors growth_pa to solve year (N5).
Envelope display reads w_eff (J4).

**Wave exit:** G4+G6 green.

---

## Wave 4 — Epistemic wiring (P0 for trust, mechanical work)

**W4.1 Evidence-connected proof graphs.** Loader emits evidence nodes keyed by claim_id;
every parameter-consuming derivation links its parameter node to the evidence records of the
segment/project/recipe it came from (`evidence_ids` fields finally load-bearing).
Verdict output must reach ≥1 evidence node per consequential class (G1 assertions).
Disconnected roots become validation errors in debug mode.

**W4.2 Parameter provenance enforcement.** Numeric fields without evidence_ids are accepted
ONLY as epistemic_class ∈ {ESTIMATED, ASSUMPTION, MODELLED, SCENARIO} with a note; REPORTED/
MEASURED numerics require source-linked evidence ids at field level (extends C21 into
segments/projects/recipes). Envelope/DVA propagate class labels into gaps and response rows.

**Wave exit:** G5 green on all three packs.

---

## Wave 5 — Intelligence layer truthfulness (P1)

**W5.1 VOI.** HIGH ⇔ ResultClass flip; shortfall swing ⇒ MEDIUM; noise floor ⇒ LOW.
Counterfactual eval carries full scenario state (I4). Bounds derive from envelope
intervals where they exist, else declared priors (labeled).

**W5.2 Reverse buildability.** Replace dead-helper grid with bisection over volume using
monotonicity check first (feasibility monotone? assert; if not, report non-monotone and use
grid+refine). Grid points become seeds, not answers (L2).

**W5.3 Frontier.** Dominance-filtered Pareto set over (θ, earliest_full_year, capex estimate,
dependence index); capex from plan search at each θ (bounded); dependence from solved
import-value share. Points carry scenario id + run hash (L3).

**W5.4 Cross-pack option value.** Union-world evaluation: shared resources/projects matched
by id across packs; relief measured on joint infeasibility; within-pack numbers remain
available for comparison (L4).

**W5.5 Machine recursion integration.** Trigger rules evaluated post-solve on binding
equipment-hour constraints / concentration flags; expansion adds equipment production chains
to the requirement graph and re-solves once (bounded depth, recursion budget logged).
If packs still lack fleet data, result is an explicit RESEARCH closure candidate, not silence
(F25 honored without fabricating data).

**Wave exit:** G7 green.

---

## Wave 6 — Vocabulary breadth (P2, after core is sound)

Action kinds BUY/LICENSE/PARTNER/ACQUIRE/DEVELOP/INVENT/REDESIGN/DIVERSIFY/STOCKPILE/
RECYCLE/TRAIN mapped onto the same verified-effect machinery:
each kind declares its solver footprint (which constraint it edits, with what lead time).
Until a kind has semantics it must not appear in output vocabulary (honesty > breadth).
Stockpile introduces inventory state (defer unless evidence demands; C22 inventory clause).

---

## Priority table (defects → waves)

| Defects | Pri | Wave |
|---|---|---|
| F1, F3, F4+N1, F5+N2 | P0 | W0-W2 |
| F2 (DVA accounting), N3 | P0 | W0/W2 |
| F6, F7 | P0 | W2 |
| F8, F9, F10, F11, F12 | P0/P1 | W3 |
| F14, F15, F16+N4, F17 | P1 | W3/W5 |
| F18 | P1 | W2 (route selection exposed; oracle M) |
| F19, F20, F21 | P0(trust) | W0/W4 |
| F22, F23, F24, F25 | P1 | W5 |
| F26 | P2→P1 guard | W0 |
| N5-N10 | P1/P2 | W3/W0 |

## Preserved unchanged (explicit list)
units.py Dim/Quantity core + convert(); epistemics.py enums; evidence.py record/source
immutability; model.py entity schema (additive changes only); pack.py loader spine;
shocks.py clone-and-edit architecture (field-list bug only); planner search loop skeleton;
nlp.py; adapters.py; HiGHS invocation mechanics; web UI (reads response JSON; waves keep
response superset-compatible; UI updates deferred).

## Redesigned abstractions (with justification)
- `ExplosionResult` flat lines → FlowGraph (patching cannot express subtree removal or
  incremental flows; root cause of F3/F4/N1).
- Per-item localization constraint → certified DVA loop then single-program formulation
  (root cause of F1).
- Scalar shortfall → ShortfallVector (root cause of F5; every downstream consumer patched
  individually would drift again).
- `primary_recipe` global-preference → geography/route-policy parameterized selection
  (F18) — small function, outsized semantic leverage.
- ModelRun summary hash → world snapshot hash (F21; "reproducibility" claim currently false).

## Acceptance gates for V0.1 (all mandatory)
1. All oracle files A-M pass; suite green including legacy tests (updated constants only
   where old constants encoded defects — each such change listed in PR description).
2. Flagship re-run reproduces documented matrix WITH certificates: DVA constraint report,
   shortfall vector, conditionality ledger, proof lineage paths, run hash sensitivity demo.
3. Two independent runs same tree ⇒ byte-identical responses (hash-checked).
4. Pack edit probe (nameplate ×10⁻⁵) ⇒ different run hash AND different verdict inputs.
5. No response field presents a number without epistemic label reachable in ≤1 hop.
6. Docs regenerated from code (VALIDATION_REPORT v2); test-count claims match suite.
7. Adversarial re-probe script (this review's probes, updated) exits clean.

## Explicitly out of scope for V0.1
Inventory/WIP dynamics beyond stockpile stub; facility-level geography; price formation;
UI redesign; new domain packs. Ambition unchanged: auditable computational argument about
industrial possibility — now with mathematics that mean what they say.
