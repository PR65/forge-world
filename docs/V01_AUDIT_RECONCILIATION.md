# V0.1 — AUDIT RECONCILIATION

Every external forensic finding independently re-derived from the implementation, then
classified. Verdicts are backed by file:line citations and, where marked **[P#]**, by an
executed probe (see `V01_ADVERSARIAL_REVIEW.md` for probe construction). Verdict scale:

- **CONFIRMED** — defect exists as described; demonstrated.
- **PARTIALLY CONFIRMED** — real effect exists; description over- or under-states it.
- **REJECTED** — the described defect does not exist; evidence given.
- **SUPERSEDED BY DEEPER DEFECT** — surface finding is subsumed by a more fundamental one.

---

## P0 findings

### F1 — `min_dva=0.70` does not enforce recursive aggregate DVA
**CONFIRMED.**
`solve.solve_year:203-204`: `bounds[n+k] = (0, demand_k · imp_frac_k · (1 − min_domestic_share))`
— a **per-item import cap**. Nothing in the LP references value, cost, or recursion.
Probe P12: at `min_dva=0.70`, every item satisfies its 30% import cap exactly
(max observed share = 0.300) while measured recursive DVA is 15.5% (engine run) and
0.16% under selected-only funding. The engine passes `min_domestic_share=obj.min_dva`
(`engine.py:156`) — a semantic substitution of *item localization* for *aggregate domestic
value addition*. This is precisely the failure mode FORBIDDEN_SHORTCUTS names ("redefine
DVA into item localization") — except V0 did it silently.
**Correction direction:** aggregate constraint `Σ imported_content_cost ≤ (1−θ)·Σ ex_works_cost`
inside the optimization (or an outer fixed-point that tightens per-item caps until measured
DVA meets θ, with the loop's certificate exposed). Oracle A/E must gate this.

### F2 — Recursive DVA mis-scales recursively manufactured inputs / double-counts content
**CONFIRMED with refinement.** `_domestic_input_import_share` (`dva.py:22-58`) walks each
recipe once **per unit of recipe output** (`scale = 1/output_qty`) and returns cost shares —
that part is structurally fine. The actual defects: (a) costs are unit-blind floats
(P11: `rec_X → (4.0, 4.0)` for "4 kg_product"), so a kg-priced input and a pcs-priced input
contribute identically-weighted "cost"; (b) processing value added is fabricated at
`35%·max(t_in, 0.5)` (`dva.py:49`, `dva.py:104-106`) whenever `processing:<item>` is absent —
which is always in shipped packs — making the denominator largely assumption-generated;
(c) when the solver imports an item, its embedded import content is counted again inside
`imp_unit` only if the pack priced it — default pricing means imported assemblies and their
inputs are both ~1.0, so embedded-import attribution is arbitrary. Not "fails to scale by
required quantity" in the walk itself; the deeper problem is that DVA has no dimensional or
price-provenance discipline at all.

### F3 — Requirement explosion double-counts shared upstream inputs
**CONFIRMED.** Probe P2: A→(2X), B→(3X), X→(4Y): joint explosion yields X=500 ✔ but Y=2800
vs true 2000 (+40%). Mechanism: `_accumulate_inputs` recurses using the **cumulative
accumulator value** as demand base (`explode.py:195,202`) instead of that route's incremental
requirement. Every additional consumer of X re-expands X's entire accumulated upstream.
In the flagship this silently inflates steel/magnet/bearing-chain demand.
The existing benchmark test locks only the linear BOM path, so tests stay green.

### F4 — Substitution mutates flattened result; old upstream survives
**CONFIRMED AND WORSE THAN DESCRIBED.** Two distinct defects:
(a) *Aliasing mutation*: `apply_substitution` copies the dict shallowly
(`substitutions.py:103`) then mutates shared `RequirementLine` objects in place
(`substitutions.py:146-147,168-170`). Probe P3: after applying SynRM substitution to a
10k-unit HV2 explosion, the **original** explosion's `hq_electrical_steel` line grew from
780,197 → 1,528,331 units/yr. The docstring's "Returns a NEW ExplosionResult (original
untouched)" is false; the external audit missed that the original object itself corrupts.
(b) *Stale dependency survival*: only the replaced line is popped; descendants generated for
it by recipe chains remain — `ndfeb_magnet` still present in the substituted result (P3).
Because explosion results are flat dicts without provenance edges, no correct deletion is
even expressible on this structure. **Superseded by a deeper architectural fact:** patching
flattened lines cannot satisfy oracle C; substitution must rewrite the architecture/recipe
selection and re-explode immutably.

### F5 — `total_shortfall` sums heterogeneous physical quantities
**CONFIRMED.** `solve.py:237` accumulates raw shortfall floats across items whose units are
pcs, t_product, MWh, kg_product… (P4 proves envelope scalars already conflate units upstream:
"100 pcs + 5 t = 105"). The single scalar drives worst-year selection
(`SolveResult.worst_year`), plan ranking keys (`planner.py:253,275`),
VOI swing thresholds (`voi.py:73`), reverse feasibility, frontier `earliest_full_year`,
and option-value relief fractions. All downstream orderings can change under a pure
kg↔t representation change of any pack quantity. Oracle H targets exactly this.

---

## P1 findings

### F6 — Import eligibility ⇒ demand-sized foreign supply, no absolute foreign capacity
**CONFIRMED.** No entity type carries foreign supply quantity. LP import bound is purely
`demand × eligibility-fraction` (`solve.py:204`). Probe P13: absolute_encoder demand
137.66M/yr served up to cap with zero supply-side evidence; soc_ai_chip likewise.
Eligibility is a policy variable being consumed as a physical capacity.

### F7 — Eligibility averaged across supplier countries without weights
**CONFIRMED.** `capacity.py:241-245`: mean of per-country fractions over
`supplied_by_countries`. Example: suppliers [CHN, JPN], CHN banned ⇒ elig=0.5 even if CHN
supplies ~95% of world volume (the NdFeB case — concentration_hhi=0.9 sits unused next to
the average). Weights exist implicitly nowhere; HHI fields never enter math.

### F8 — Announced/approved projects enter optimistic baseline without CONDITIONAL propagation
**PARTIALLY CONFIRMED.** The optimistic edge does include unproven projects
(`capacity.py:218-220`), and a generic conditional string is emitted when funded unproven
projects exist (`solve.py:301-306`). But: (a) the string fires only via
`collect_unproven_funded(w, opts.funded_project_ids)`, which is empty in optimistic-pipeline
mode because unfunded projects aren't in the set — so the *default flagship path* counts all
unproven projects in `hi` while naming none (P9: funding REPM+ACC yields exactly 1 generic
reason); (b) `assume_capacity_hi=True` default means INFEASIBLE verdicts lean on the
optimistic edge without any per-project conditionality ledger; (c) `conflicted` field of
CapacityEnvelope is initialized False and never set anywhere.
So "announced ≠ operating" holds at the interval level, but conditionality bookkeeping is
effectively decorative.

### F9 — `count_unproven_projects` has no effect on capacity logic
**CONFIRMED.** Parameter exists (`solve.py:73`), is cloned by shocks/planner, and gates only
the conditional-string emission (`solve.py:302`). Setting False removes a sentence; nothing
numeric changes. Grep shows no branch feeding `project_contribution_range`.

### F10 — `commission_year_estimate` has no effective influence
**CONFIRMED.** `capacity.py:75-76`:
`return int(max(start+remaining_optimistic, min(estimate, start+remaining_optimistic)))`.
Both branches collapse to `start+remaining_optimistic` for every estimate value. Probe P10:
estimates 2027 and 2045 both return 2028. Algebraically `max(A, min(E,A)) ≡ A ∀E`.

### F11 — Qualification requirements don't causally gate production
**CONFIRMED.** `ProductionRecipe.requires_qualification` loaded (`pack.py:174`) and never
read (grep). `Qualification.latency_months/status` never consulted by solver. The only
qualification lever is `qualification_boost` flipping segment factors to 1.0 instantly
(`capacity.py:187`; P15: +13,340 units/yr unlocked with zero latency despite
`latency_months=(12,24)` status not_started).

### F12 — Transformation lead times are display metadata
**CONFIRMED.** QUALIFY/SUBSTITUTE effects enter the verification solve immediately
(`planner.with_actions:216-219` adds boosts/subs before `evaluate`); transition_months appear
only in `_sequence` display rows and action JSON. A QUALIFY action with lead_time (1,2) yrs
raises 2026 capacity in the verified plan. FUND actions partially respect time only through
`project_contribution_range` scheduling — inconsistent with the other two kinds.

### F13 — Transformation vocabulary narrower than intended
**CONFIRMED.** Action kinds implemented: FUND_PROJECT, SUBSTITUTE, QUALIFY, RESEARCH (+ a
STOCKPILE literal allowed by a test assertion but produced by no code path). Missing vs
mandate: BUY/LICENSE/PARTNER/ACQUIRE/DEVELOP/INREDESIGN/DIVERSIFY/STOCKPILE/RECYCLE/TRAIN.
The ontology has placeholders (`Substitution.level`, `PolicyAction`) but no solver semantics.

### F14 — VOI labels same-class shortfall swings as "flips conclusion"
**CONFIRMED.** Rank tuple `(class_order, −shortfall)` (`voi.py:50-58`): any nonzero swing
changes the tuple ⇒ HIGH + "flips conclusion". Probe P5: flagship labels items HIGH with
"pessimistic=INFEASIBLE_UNDER_MODEL, optimistic=INFEASIBLE_UNDER_MODEL" — literally stating
no class flip. Additionally VOI counterfactual bounds come from `gross×1.5` guesses, not
from any evidence distribution; and (see F15) re-solves drop scenario state.

### F15 — VOI drops active scenario constraints during counterfactuals
**CONFIRMED.** Engine builds `eval_with` constructing a fresh `ScenarioOptions`
(`engine.py:198-206`) carrying only overrides/funding/capacity/geography/min_dva/boosts —
dropping `import_eligibility`, `cost_*` maps, equipment limits, competing-demand cuts, and
`funded_pipeline`. Under shock scenarios, VOI answers a different world than displayed.

### F16 — Shock application loses pre-existing scenario state
**CONFIRMED.** `shocks.apply_shocks:45-63` clones opts field-by-field and omits
`funded_pipeline`; `o2.competing_demand_cuts = dict(demand_cuts)` (`shocks.py:162`)
overwrites pre-existing cuts unconditionally. Probe P14: cuts `{battery_cell_liion: 1e9}`
→ `{}` after zero-edit shock application. (demand_add edits *should* merge onto existing cuts;
today they clobber.)

### F17 — Displayed envelopes built from original world under shocks
**CONFIRMED.** `_envelope_rows(self.w, …)` (`engine.py:282`) receives the base world, while
the solve uses `w_eff`. Probe P20: with `shk_atmp_fire` (project_impair), displayed
motor_driver_inverter hi@2030 stays 27,000,000 while the true shocked-world value is 0.
UI therefore contradicts the verdict it sits beside.

### F18 — Recipe selection prefers GLOBAL primary over INDIA-applicable secondary
**CONFIRMED.** `primary_recipe` sorts candidates into primaries-first, then prefers INDIA
*within that pool* (`explode.py:16-23`); an INDIA-flagged `route_type: secondary` route
(e.g., `rec_joint_actuator_india_candidate`) is unreachable while any primary exists.
Route_type conflates maturity/viability status with preference ordering; geography tiebreak
is inverted relative to the system's own purpose (domestic buildability).

### F19 — Proof graphs disconnected from evidence
**CONFIRMED.** Probe P6 (flagship response): 1,367 nodes — derived:1277, output:90,
**evidence:0**; 177 root nodes with no incoming edge; zero outputs reachable from any
evidence node. `ProofGraph.evidence_node()` has zero call sites. C15 ("important outputs
trace to evidence") is unimplemented in the solve path; packs' `evidence_ids` are validated
for existence but never wired to derivations.

### F20 — Model parameters lack mechanical provenance enforcement
**CONFIRMED.** Loader enforces sources only on EvidenceRecords (`pack.py:112-115`);
segments/projects/recipes accept numeric fields with `evidence_ids: []`
(seg_india_alu: 4 Mt/yr ESTIMATED, no evidence id — permitted by design note C13/C21 but
nothing forces the *label* to propagate into the solve or UI numerics; envelope epistemic
strings exist, DVA/LP consume bare floats). Documentation's "every important number traces
to evidence" is aspirational, not mechanical.

### F21 — ModelRun hash excludes industrial state; finish() unused; reproducibility overstated
**CONFIRMED.** `ModelRun.create` hashes `pk.summary()` — counts/kinds/name lists
(`pack.py:85-96`). Probe P7b: changing seg_india_alu nameplate 4,000,000 → 40 t/yr leaves
run hash **byte-identical** (`ac35932c…` before and after). `finish()` has no call site;
response `run.outputs` always empty. CLI banner claims "byte-reproducible".

### F22 — Reverse buildability is a tiny candidate grid, not optimization
**CONFIRMED.** Grid {250k, 500k, 750k, 1M} hardcoded at call sites (`engine.py:235,239`);
ascending scan, break at first infeasible; inner binary-search helper `ok()` dead code
(P16). Monotonicity of feasibility in volume is assumed, not established (shortfall penalty
scaling makes large-V classification path-dependent), so even grid answers can be wrong in
both directions.

### F23 — Closure frontier is a five-point localization sweep
**CONFIRMED.** θ ∈ {0,.5,.7,.85,.95} (`engine.py:233`); `capex_for`/`foreign_dep_for` left
None ⇒ min_capex_musd=null, dependence=1.0 constants. No Pareto semantics over
(cost,time,localization,dependence,resilience); points aren't even dominance-filtered.

### F24 — Option value within-pack only
**CONFIRMED with nuance.** `optionvalue.option_value_portfolio` scores investments per
objective via shortfall deltas, but the flagship engine never calls it; the API's
`/api/optionvalue` uses `optionreport.option_value_report`, which loops projects **per pack**
and sums per-objective relief where objectives are one-per-pack anyway — cross-pack synergy
(shared supplier/project across packs) is structurally impossible today because worlds are
separate objects and no entity is shared. Self-critique §52 already admits this; confirmed.

### F25 — Machine recursion not integrated into flagship solve
**CONFIRMED.** `expand_recursion` called only from tests; engine/solver never invoke it.
Equipment-hour constraints exist in the LP but no pack supplies fleet data, so the machinery
is dormant. The trigger rules (`strategic_materiality`) read fields that packs do populate
(dominant_supplier_countries) — integration would be meaningful, not decorative.

### F26 — Direct Quantity currency conversion bypasses FX guard
**PARTIALLY CONFIRMED.** `convert()` correctly demands fx_rate (P8 first half). But Quantity
arithmetic leaks currencies freely: EUR×pcs÷pcs → USD 10.0 silently (P8 second half)
because EUR/USD share dim USD with factor 1.0 (`units.py:126-128`) and mul/div operate on
canonical values. Any code path doing `q_cost * qty / qty` normalizes currency without the
guard. Impact today is latent (solve path doesn't multiply quantities this way), severity P2
now / P1 the moment multi-currency packs land. Also note INR registers at factor 1.0 — a
time bomb for anyone assuming real conversion.

---

## NEW defects found this pass (not in the external list)

### N1 (P0) — Substitution mutates the caller's original ExplosionResult
Described under F4(a); split out because the external audit asserted the original stays
immutable and only complained about stale deps. Any pipeline holding a baseline explosion
across a substitution gets silent corruption. Violates the explicit deliverable requirement
"Original ExplosionResult must remain immutable."

### N2 (P0) — Envelope/interval assembly mixes units and mishandles mixed project states
`capacity_envelope` sums raw canonical floats across segments+projects regardless of
unit family (P4), and a projects-only envelope with any unproven project forces `lo = 0`
even when operating projects contribute known pessimistic output (`capacity.py:229-231`;
the intermediate min() branch is dead code). Feeds F5 directly.

### N3 (P1) — Demand-side gross/net conflation in solve
LP demand uses `line.gross_annual` (`solve.py:134`) while DVA uses `net_annual`
(`dva.py:95`) and envelope rows display net as `demand_annual` (`engine.py:98`). Three
different demand notions for the same item in one response; shortfall shares computed
against gross inflate DVA's shortfall-share distortion (P22 sample: bearings shortfall_share
0.70 against a demand figure that includes yield inflation).

### N4 (P1) — `funded_pipeline` mode not preserved by shocks/planner clones
Field-by-field option clones (`shocks.py:45-63`, `planner.with_actions:193-209`) omit
`funded_pipeline`; any shocked or planned re-solve reverts to optimistic-pipeline semantics
even when the user pinned selected_only. Interacts with F8/F15.

### N5 (P1) — Competing-demand cut scales capacity, not demand; pool lookup ignores year & growth
`solve.py:157-167`: available pool = contestable fraction × baseline, then `cap_hi *= (pool−cut)/pool`
— i.e., rival demand reduces *supply*, though economically it should reduce *net availability*
identically only under full substitutability; more importantly the pool uses
`baseline_annual` with no growth_pa compounding to the solve year despite the field existing,
and cuts apply even when the item's binding side is imports.

### N6 (P1) — Planner FUND verification is a numeric no-op
`with_actions` adds ids to `funded_project_ids` but never sets `funded_pipeline="selected_only"`
and its clone drops the base mode anyway (N4); in optimistic mode adding an id changes
nothing (all evidenced projects already count optimistically), so FUND actions verify as
no-ops while appearing as portfolio content — funding decisions are never actually
evaluated by plan search. Mode-dependent, undisclosed, and it invalidates "every candidate
portfolio is re-verified" for the FUND kind specifically.

### N7 (P2) — `check_mass_balance` mutates `res.mass_balance_warnings` twice on failure paths
`explode.py:215-244` appends into `res.mass_balance_warnings` directly and also extends it
with the local list at the end — duplicate warnings possible; cosmetic but pollutes proof
labels. Also compares `total_in < out_mass·(1−tol)` only — surplus inputs (waste-heavy
routes) pass silently.

### N8 (P2) — Explosion depth caps are magic numbers (depth>8 recipes, >6 DVA) with no surfaced truncation flag
Deep-but-real chains silently stop accumulating; no warning node emitted. For industrial trees
(magnet→oxide→mine; ATMP→fab→wafer) 8 may bind; truncation is invisible in output.

### N9 (P2) — `annual_scalar` treats "mo"/"wk" rates uniformly via h-dimension exponent sign trick
Correct for rates, but any future quantity typed `t_product/h` (throughput) will be silently
annualized ×8760 wherever `annual_scalar` touches it; there is no dimension distinguishing
stocks from flows, which the three-clock contract (C4) implies. Design gap, not live bug.

### N10 (P2) — Test-count drift in docs (48 vs 52 vs 53)
VALIDATION_REPORT says 48, FINAL_SELFCRITIQUE says 52, actual suite = 53 passing. Symptom of
docs written at different times; reinforces "trust executable behavior" rule.

## Summary matrix

| # | External claim | Verdict | Primary evidence |
|---|---|---|---|
| 1 | min_dva ≠ aggregate DVA | CONFIRMED | solve.py:203-204; P12 |
| 2 | DVA scaling/double-count | CONFIRMED (refined) | dva.py:22-58; P11 |
| 3 | Explosion double-count | CONFIRMED | explode.py:195,202; P2 |
| 4 | Substitution mutation/stale | CONFIRMED+WORSE | substitutions.py:103,146; P3 |
| 5 | Heterogeneous shortfall sum | CONFIRMED | solve.py:237; P4 |
| 6 | Imports = demand-sized supply | CONFIRMED | solve.py:204; P13 |
| 7 | Unweighted country averaging | CONFIRMED | capacity.py:241-245 |
| 8 | Optimistic w/o conditional | PARTIALLY CONFIRMED | capacity.py:218; solve.py:301; P9 |
| 9 | count_unproven inert | CONFIRMED | grep; solve.py:302 |
| 10 | commission estimate inert | CONFIRMED | capacity.py:75-76; P10 |
| 11 | Qualification not gating | CONFIRMED | grep; capacity.py:187; P15 |
| 12 | Lead times display-only | CONFIRMED | planner.py:216-219 |
| 13 | Narrow vocabulary | CONFIRMED | planner.Action kinds |
| 14 | VOI false flips | CONFIRMED | voi.py:50-64; P5 |
| 15 | VOI drops constraints | CONFIRMED | engine.py:198-206 |
| 16 | Shock state loss | CONFIRMED | shocks.py:45-63,162; P14 |
| 17 | Envelopes ignore shocks | CONFIRMED | engine.py:282; P20 |
| 18 | GLOBAL primary preferred | CONFIRMED | explode.py:16-23 |
| 19 | Proof graph disconnected | CONFIRMED | P6 |
| 20 | Provenance not enforced | CONFIRMED | pack.py:112-115 |
| 21 | Hash ≠ state; finish() dead | CONFIRMED | run.py:38-47; P7b |
| 22 | Reverse grid | CONFIRMED | engine.py:235; P16 |
| 23 | Frontier sweep | CONFIRMED | frontier.py; engine.py:233 |
| 24 | Option value within-pack | CONFIRMED | optionreport.py |
| 25 | Recursion unintegrated | CONFIRMED | grep |
| 26 | FX bypass via arithmetic | PARTIALLY CONFIRMED | units.py:126-128; P8 |

Tally: 24 CONFIRMED, 2 PARTIALLY CONFIRMED, 0 REJECTED, plus 10 new defects (N1–N10).
