# V0.1 — MATHEMATICAL ORACLE SPECIFICATIONS

Design rule: **an oracle is a test an incorrect implementation cannot satisfy while still
violating the intended semantics.** Every oracle below therefore specifies (i) a minimal
hand-solvable world, (ii) exact expected numbers derived by hand, (iii) *anti-cheat
assertions* that reject the known wrong implementations (item-localization DVA,
cumulative-accumulator explosion, flattened-line substitution, eligibility-as-supply,
scalar shortfall ranking, label-only proof graphs, count-hash ModelRuns), and (iv) the
invariant it certifies. Oracles must be written **before** correction code (they are the
acceptance gate), live in `tests/oracles/`, and use only public entry points
(`build_pack`, `explode_variant`, `capacity_envelope`, `solve_objective`,
`apply_substitution`, `apply_shocks`, `dva_fraction`, engine).

Conventions: all hand worlds built via `build_pack(raw)` with ASSUMPTION evidence so loader
gates pass; yields default 1.0 unless stated; `annual_units` chosen so every number is an
integer.

---

## A. Recursive aggregate DVA (oracle_dva.py)

**World.** Product P = 1×M per unit.
Recipe M (INDIA): inputs 1×R @ 10 USD + 1×S @ 10 USD; no steps.
Recipe R (INDIA): input 1×X imported (no domestic recipe) @ 20 USD landed.
Item S: pure domestic raw, no recipe, cost 10 USD domestic.
Processing values: `processing:M = 0` (declared, not defaulted), `processing:R = 0`.

**Hand calculation.**
Cost of R = its imported input X at landed cost = 20 (+0 processing declared) ⇒ R = 20.
Cost of M = R(20) + S(10) + 0 processing = 30 ex-works.
Imported embedded content of one P (all-domestic allocation) = R's chain = 20.
True recursive DVA = 1 − 20/30 = **1/3 ≈ 33.33%**.

**Assertions.**
1. `dva_fraction(...).fraction == pytest.approx(1/3, abs=1e-9)` when allocation is 100% domestic.
2. *Anti-localization*: solve with `min_dva=0.70`. The system must NOT claim feasibility by
   capping item imports; either it reports INFEASIBLE/CONDITIONAL for the DVA objective or the
   measured DVA ≥ 0.70. Assert `measured_dva >= min_dva − 1e-9 OR result_class in
   {INFEASIBLE_UNDER_MODEL, NOT_ADJUDICABLE}` — this fails V0 (which reports FEASIBLE-ish
   allocations at 15%-style DVA).
3. *Anti-fake-processing*: assert `assumptions_used == []` when processing values are declared;
   assert a missing processing value produces an explicit ASSUMPTION record **and** that
   flipping its value from 0→0.35 moves `fraction` — proving the denominator is honest about
   value added.

### A2. Unit-representation invariance inside DVA
Same world; express R's input as `[1000, "kg_product"]` instead of `[1, "t_product"]`
with price per kg scaled ×1000. DVA must be bit-identical (`==` on floats after canonical
parse, not approx): `dva(kg_repr) == dva(t_repr)`.
*Anti-cheat:* also assert total_cost_usd identical — catches implementations that convert via
float factor at the wrong point.

---

## B. Shared-input explosion linearity (oracle_explosion.py)

**World.** Exactly probe P2's: A→(2X), B→(3X); X→(4Y kg); PA/PB inert leaves;
variant V2 = A+B+PA+PB @ 100 units.

**Hand expectation.** explode(A)= {X:200}, explode(B)= {X:300}, joint X = 500;
Y = 4·(200+300) = 2000.

**Assertions.**
1. `explode(V2)["Y"].gross == 2000` exactly (V0 returns 2800 → fails).
2. Additivity property test over random DAGs (seeded, 20 worlds, depth ≤3, shared leaves):
   `explode(U∪W)[k] == explode(U)[k] + explode(W)[k]` for every k, within 1e-9 relative —
   linearity is the invariant; single fixtures are illustrations.
3. Yield consistency: with X-route yield y, joint Y must equal 4·(gross_A_X/gross-up)…
   precisely: Y_gross = 4·(X_net_total)/y_X where X_net_total is additive. Assert against
   closed form.
4. *Anti-cheat*: construct a world where cumulative-accumulator recursion gives a *different*
   wrong answer than double-expansion (A,B share X AND X appears as a direct BOM leaf of B);
   assert the unique correct value. This distinguishes "fixed by dedup" from "fixed by
   incremental-flow recursion."

## B2. Depth/truncation honesty
Chain Z₁→Z₂→…→Z₁₂ (12 levels, each recipe consumes 1 of next). Explode product consuming Z₁.
Assert either full accumulation to Z₁₂ or an explicit `truncated_depths` report naming level;
silently stopping at 8 fails.

---

## C. Substitution immutability + dependency hygiene (oracle_substitution.py)

**World.** Variant V = 1×MotorA; MotorA recipe: NdFeB(1)+Cu(1); alt MotorB recipe:
ElSteel(1)+Cu(1); contract replaces MotorA with MotorB, envelope-covered, maturity=pilot.

**Hand expectation.** After substitution: lines == {MotorB:1, ElSteel:1, Cu:1};
NdFeB absent; MotorA absent.

**Assertions.**
1. Snapshot original explosion deep-equal before/after `apply_substitution`
   (compare every RequirementLine field of every item) — V0 FAILS today (steel line mutates).
   Also snapshot the *world* (entity/edge counts) — substitutions must not add entities as
   V0's changed_bom path does (`substitutions.py:185-187`).
2. Stale-dependency check: `"ndfeb_magnet" not in result.lines`.
3. Re-explosion equivalence: `explode(variant_with_substituted_architecture)` ==
   `result.lines` within tolerance — proves the rewrite is architecture-level, not patchwork.
4. Idempotence: applying twice equals applying once (no double-add of Cu).
5. Gate still rejects incomplete contracts (existing behavior preserved).

---

## D. Supply vs eligibility (oracle_supply.py)

**World.** Item W imported-only (no domestic recipe/segment), suppliers [ABC], foreign
capacity segment `geography: ABC, nameplate 10 pcs/yr`; demand 100.

**Hand expectation.** Feasible imports ≤ 10 ⇒ shortfall ≥ 90.

**Assertions.**
1. `imports_used ≤ 10 + tol` and `shortfall ≥ 90 − tol`.
   (V0 imports up to eligibility share of demand → fails.)
2. Two suppliers (6 + 5 capacity): imports ≤ 11 — sums independent sources, caps at evidence.
3. Eligibility zeroing: set import fraction ABC→0 ⇒ imports_used == 0 even though capacity
   exists — policy and physics are distinct levers.
4. *Anti-cheat*: demand 8 (< capacity): shortfall == 0 — proves cap binds only above supply,
   i.e., implementation didn't just hardcode min(demand, something_small).

---

## E. Aggregate DVA ≠ per-item localization (oracle_localization_vs_dva.py)

**World.** P = 9×D (domestic, 10 USD each, fully domestic chains) + 1×I (imported, 10 USD).
True DVA = 90%.

**Assertions.**
1. With `min_dva=0.70`: verdict must reflect PASS on the DVA dimension even though item I is
   100% imported — assert `measured_dva ≥ 0.69` and no closure candidate proposes
   "localize I" as mandatory.
2. Inverse trap (anti-regression to V0 semantics): with `min_dva=0.95`, same world must FAIL
   (true DVA 90% < 95%) even though **every item's import share ≤ 10% would pass a per-item
   cap reading**. V0's constraint passes this world at θ=0.95; correct semantics must fail it.
   This single assertion kills the localization-substitution permanently.
3. Mixed: P = 5×D@10 + 5×I@10 (50% true DVA): threshold sweep θ ∈ {0.4, 0.5, 0.6} flips
   verdict exactly between 0.5 and 0.6 — monotone, boundary-correct.

---

## F. Physical time (oracle_time.py)

**F1 project timing.** Project completing 2029 (state approved, start 2026, lead 3–3):
contribution(2028) == 0 exactly; contribution(2029) == ramp_fraction(0+)·design ≥ 0;
contribution(2031) > contribution(2029). Hand world mirrors pack REPM but deterministic.
Assert lo==hi==0 for pre-completion year — *both interval edges*, not just pessimistic.

**F2 qualification latency.** Segment qual_fraction=0.5 with Qualification(latency 18mo,
status not_started). QUALIFY action issued at t₀:
- verification solve for year t₀+1: NO increase (V0 increases instantly → fails);
- solve for t₀+2.5: full boost available;
- conditional ledger names the qualification and its window.

**F3 shock acceleration respects floors.** project_accelerate years=5 on a lead=(3,4.5)
project clamps at 0 but never negative contributions; impair zeroes both edges instantly
(impairment is itself an event, allowed immediate).

**F4 plan timeline ↔ solver coherence.** For the chosen plan, for every action kind:
the year-by-year shortfall trajectory implied by `_sequence` online dates matches the
trajectory of re-solves that enable actions only in their online years. (V0: mismatch —
verification solves assume instant completion.)

---

## G. Provenance chain completeness (oracle_provenance.py)

**G1 flagship lineage.** Run flagship; select the verdict output node. Assert:
1. ≥1 path verdict→…→evidence-kind node exists for each consequential number class:
   total_shortfall, dva.fraction, worst gap, plan capex.
2. Zero disconnected derived/output roots (V0 has 177 → fails).
3. Every numeric leaf node's detail carries either source_ids or an ASSUMPTION marker.
4. Walk check: for the binding-gap item, the chain visits its capacity envelope derivation,
   its requirement derivation, and ≥1 parameter node whose detail includes epistemic_class.

**G2 assumption accounting.** DVA assumptions_used list must equal exactly the set of
defaulted parameters actually consumed (V0 emits the 35% note but nothing forces equality).
Inject a deliberate `processing:X` override; assert it disappears from assumptions.

**G3 hash reproducibility (ModelRun).**
1. Identical runs ⇒ identical hashes (existing test keeps passing).
2. *Anti-count-hash*: change seg nameplate 4,000,000→40 t/yr ⇒ hash MUST change
   (P7b shows V0 identical → fails).
3. Change an unrelated entity's notes ⇒ hash MAY change (no false sharing assertion),
   but change nothing ⇒ stable across processes (subprocess determinism check).
4. `run.outputs` non-empty post-run (finish() wired) and contains result_class +
   worst_shortfall digest matching response.

---

## H. Dimensional normalization end-to-end (oracle_units_end_to_end.py)

**World.** Item K consumed 1 t/unit by product Q; segment supplies K.
Build two packs: representation A `[1,"t_product"]`, B `[1000,"kg_product"]` everywhere K
appears (recipe input + any mass fields).

**Run both through:** explosion, LP solve, VOI ranking over two unknowns, frontier,
reverse grid, option-value relief.

**Assertions.**
1. Per-item physical answers identical after canonicalization (kg values ×0.001 == t values).
2. Portfolio choice identical (same action ids in same order).
3. VOI decision_impact labels identical per item.
4. Worst-year identical.
5. Option-value scores identical to 1e-12.
6. *Anti-scalar-shortfall*: craft world where item₁ short 5 t_product and item₂ short 3 pcs;
   assert reported shortfall structure preserves units (either separate scalars per family
   or canonical Quantity list), and that multiplying all t-denominated masses ×1000 (pure
   re-unit) does NOT reorder `worst_year`/portfolio rankings. V0 fails: totals change 5000-fold.
7. Currency guard: `convert(EUR,USD)` raises without fx_rate **and** constructing
   `Quantity(1,"EUR") * Quantity(3,"pcs") / Quantity(3,"pcs")` either raises or returns EUR —
   returning USD silently fails (P8 leak closed at arithmetic level, not just convert()).

---

## I. Scenario-state preservation (oracle_scenario_state.py) — new

1. Pre-set `competing_demand_cuts={X:100}` then apply_shocks([]) → cuts preserved (P14 fails V0).
2. Set funded_pipeline="selected_only", funded={P}, apply_shocks([shk]) → shocked opts keep
   mode; solved allocations equal manual selected_only re-solve under shock edits.
3. Shock demand_add onto existing cut merges (cut_X' = cut_X + add) rather than replacing.
4. VOI under shocks: eval_with carries ALL active scenario fields — assert by flagging a
   sentinel (cost multiplier) that changes results if dropped (V0 drops → fails).

## J. Envelope integrity (oracle_envelope.py) — new

1. Unit homogeneity: segments in different unit families for one item raise / refuse merge —
   never produce scalar sum (P4 fails V0).
2. Interval logic: segments S (lo=hi=sᵢ) + unproven projects Pⱼ (opt oⱼ) + operating
   projects Oₖ (pess pₖ, opt oₖ): lo == Σsᵢ+Σpₖ, hi == Σsᵢ+Σoⱼ+Σoₖ. Projects-only envelope
   with mixed provenance must keep operating projects' pessimistic values in lo
   (V0 forces lo=0 there → fails; J2).
3. Epistemic propagation: ESTIMATED-only envelope surfaces epistemic="ESTIMATED" into solve
   gaps and UI rows; UNKNOWN stays UNKNOWN with reasons.
4. Display-vs-solve coherence: run engine with project_impair shock; assert displayed
   envelope for impaired item == shocked-world truth (P20 fails V0).

## K. Classification & conditionality ledger (oracle_conditionality.py) — new

1. Funding an ANNOUNCED project lists that project id in conditional_reasons with its
   commissioning window (V0: generic/no listing → fails).
2. `count_unproven_projects=False` removes optimistic-edge contribution numerically
   (not just prose): hi drops accordingly (V0 unchanged → fails).
3. CONFLICTED segments (two REPORTED capacities) yield conflicted=True envelope and a
   CONDITIONAL reason naming the conflict — first-class, not averaged away.

## L. Intelligence-layer semantics (oracle_intelligence.py) — new

1. VOI HIGH requires ResultClass flip; shortfall swing alone caps at MEDIUM (P5 fails V0).
2. Reverse buildability: monotone world (feasibility decreasing in volume) — grid answer must
   equal refined bisection answer within tolerance on a hand world where max feasible volume
   = 437,000 (between grid points) — grid-only implementations fail.
3. Frontier: two objectives (θ vs earliest_full_year) with dominance filtering — dominated
   points never returned; a hand world with known Pareto set {θ=0.5 early, θ=0.85 late}
   verifies.
4. Option value cross-pack: hand pack₂ shares supplier capacity with pack₁ via a common
   resource; investing must raise relief in BOTH objectives — within-pack implementations
   score 0 on the second (F24 fails V0).

## M. Recipe route selection (oracle_routes.py) — new

INDIA secondary route + GLOBAL primary coexist for actuator-class item; geography=INDIA solve
must prefer INDIA-applicable route for domestic-share purposes (or expose explicit
route-choice provenance); assert explosion's `via_recipe` reflects selection and DVA walk uses
the same recipe object (V0 splits these decisions across modules → can disagree).

---

### Oracle suite gates (must precede ANY corrective implementation)

| Gate | Oracles | Blocks |
|---|---|---|
| G0 | A2, H1-H7 | touching units/cost plumbing |
| G1 | B, B2 | explosion rewrite |
| G2 | C | substitution rewrite |
| G3 | D, E | LP/constraint reformulation |
| G4 | F | time/qualification/planner |
| G5 | G | proof/hash wiring |
| G6 | I, J, K | scenario/envelope/classification |
| G7 | L, M | intelligence layer |

Each oracle file states expected numeric constants inline (they are derived above, not
generated), so a separate implementation agent cannot tune code to observed output —
deviation from hand math fails loudly.
