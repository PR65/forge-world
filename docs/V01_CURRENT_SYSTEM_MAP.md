# V0.1 — CURRENT SYSTEM MAP (as-built, independently reconstructed)

**Status:** read-only reconstruction. No production code was modified for this document.
**Method:** every module read in full; claims below verified by execution probes
(`P1–P22`, see `V01_ADVERSARIAL_REVIEW.md`) and by the existing test suite (53 passing).
Where this map disagrees with `README.md` / `docs/VALIDATION_REPORT.md` /
`docs/FINAL_SELFCRITIQUE.md`, the code and its executed behavior are authoritative.

---

## 1. Repository inventory

| Layer | Files | Notes |
|---|---|---|
| Units / dimensions | `forge/units.py` (409 L) | Dimension-vector `Dim` over 11 base dims; 5 distinct tonne families; composite-unit parser; FX-gated currency `convert()`; `annual_scalar()` |
| Ontology | `forge/model.py` (479 L) | 25+ entity dataclasses; `ProjectState` machine; `CapacitySegment.effective_annual`; typed-edge `World` graph |
| Evidence | `forge/evidence.py` (192 L) | frozen `EvidenceRecord`, `Source`, `ProofGraph` DAG, `snapshot_hash` |
| Epistemics | `forge/epistemics.py` (57 L) | 9-class enum, `ResultClass`, `Confidence` |
| Pack loader | `forge/pack.py` (501 L) | YAML → World; validation (yields ∈ (0,1], factors ∈ [0,1], REPORTED/MEASURED need sources); substitution contract field gate |
| Explosion | `forge/explode.py` (245 L) | BOM leaves → per-part lines; recipe-input chain accumulator; mass-balance checker |
| Capacity | `forge/capacity.py` (274 L) | segment + project envelopes; state-credit commissioning model; import-eligibility averaging |
| Allocation LP | `forge/solve.py` (382 L) | HiGHS `linprog`, 3 vars/item (domestic/import/shortfall), shortfall penalty 1e6·max(demand,1) |
| DVA | `forge/dva.py` (154 L) | recursive input-cost import-share walk over domestic routes only |
| Substitution | `forge/substitutions.py` (198 L) | envelope-equivalence gate + flattened-line rewrite |
| Shocks | `forge/shocks.py` (169 L) | deep-copied world + cloned opts; 7 edit types |
| Planner | `forge/planner.py` (324 L) | candidate actions; exhaustive/greedy portfolio search re-verified through the solver |
| VOI | `forge/voi.py` (94 L) | pessimistic/optimistic override re-solves; rank-tuple flip detection |
| Frontier | `forge/frontier.py` (66 L) | sweep of θ ∈ {0, .5, .7, .85, .95} through full pipeline |
| Reverse / option value | `forge/optionvalue.py` (129 L) | volume-grid reverse query; `option_value_portfolio` (unused in flagship path) |
| Recursion | `forge/recursion.py` (84 L) | trigger rules + chain walk; **not called by engine/solver** (test-only) |
| ModelRun | `forge/run.py` (78 L) | hash of {pack_id/version, objective, scenario, pack summary(), solver version}; `finish()` never called |
| Orchestration | `forge/engine.py` (328 L) | flagship pipeline; response assembly |
| NLP | `forge/nlp.py` (172 L) | deterministic regex parsing → `ObjectiveSpecInput`; no LLM anywhere in solve path ✔ (C20 holds) |
| Adapters | `forge/adapters.py` (148 L) | World Bank fetch → `EvidenceRecord`s (not wired into solve) |
| API | `server/app.py` (188 L) | FastAPI; `/api/solve`, `/api/parse`, `/api/optionvalue` |
| CLI | `scripts/forge_cli.py` (117 L) | headless runs ("byte-reproducible" claim — see F21) |
| UI | `web/src/*` (~2,300 L TSX) | renders API JSON; not modified or audited in depth this pass |
| Packs | `packs/*.yaml` | humanoid_india v1.0.0 (flagship), battery_gwh_india, smallsat_india |
| Tests | `tests/*.py` | 53 tests, all passing (`py -3.12 -m pytest tests -q` → *53 passed*) |

Dead / orphaned code (grep-verified): `ProofGraph.evidence_node`
(zero call sites), `recursion.expand_recursion` (test-only),
`optionvalue.option_value_portfolio` (imported by engine, never invoked),
`ScenarioOptions.count_unproven_projects` (plumbed, never branched on),
`Project.commission_year_estimate` (written, effectively unread — P10),
`ProductionRecipe.requires_qualification` (loaded into the dataclass,
never consulted downstream).

## 2. The flagship solve as it actually executes

Objective (engine defaults): `hv2_industrial @ 1,000,000 units/yr`,
geography `INDIA`, years `[2026..2030]`, `min_dva = 0.70`.

### 2.1 Explosion (`explode.explode_variant`)

Phase A — BOM leaves: walk `decomposes_into` edges from the variant with edge-meta `qty`
multipliers; sum per-unit quantities per leaf; multiply by `annual_units`. Each leaf line is
grossed up by the **cumulative yield of its own primary recipe**
(`∏ step.yield_fraction·(1−scrap)`), i.e. gross = net/yf.

Phase B — recipe-input chains (`_expand_input_chains` → `_accumulate_inputs`): starting from
each leaf's *gross* quantity, walk the leaf's primary recipe inputs
(`need = iq.value · gross/output_qty`, then `need /= _yield_of(input)`), recursing to depth ≤ 8,
cycle-guarded by an ancestor tuple `seen`. Accumulate into `input_accumulator[item] += …`.

**Empirical shape (probe P2):** joint explosion of two products sharing upstream `X`→`Y` gives
X linear (500 = 200+300 ✔) but Y **overcounted**: 2800 vs true 2000 (+40%). Root cause:
`_accumulate_inputs` recurses with `res.input_accumulator[iname].value` — the *running cumulative
total* — as the demand base for that item's own recipe expansion, so shared items expand their
upstream multiple times. Linearity fails exactly when a shared intermediate has its own recipe.
In the real flagship this inflates steel/bearing/magnet-chain demand above BOM truth.
The locked test `test_humanoid_benchmark_multiplication` passes only because it checks the
*leaf+BOM-path* bearing term, which happens to be computed linearly, not the recipe-chain term.

### 2.2 Per-year capacity (`capacity.capacity_envelope`)

For each required item/year: collect `CapacitySegment`s matching item and geography
∈ {INDIA, GLOBAL} (none exist at GLOBAL today), effective value =
`nameplate × availability × utilization × yield × qualification_fraction` (boost ⇒
qualification_fraction := 1 instantly). Collect projects: operating states contribute
[pess, opt]; unproven states contribute **opt only** to the interval hi.
Interval assembly (`capacity.py:227-233`): `hi = Σ hi_vals`; `lo = Σ lo_vals` where `lo_vals`
receives segments and *operating* projects only — the intermediate `min(lo_vals)` expression
is **dead code**, overwritten by the `elif lo_vals: lo = sum(lo_vals)` branch whenever
anything exists. One real quirk remains: an envelope with zero segments but a mix of
operating and unproven projects forces `lo = 0`, discarding the operating projects' known
pessimistic output (conservative, but conflates "some projects unproven" with "none proven").
If nothing found ⇒ UNKNOWN (never zero-supply — C2 respected here).

Import eligibility: average `elig_map.get(country, 1.0)` over `supplied_by_countries`
(`capacity.py:241-245`). No foreign capacity object exists anywhere; imports face **no
quantity limit** (P13: encoder demand 137.7M, domestic unknown, imports fill all eligible
share).

### 2.3 Yearly allocation LP (`solve.solve_year`)

Variables per item k: `d_k` (domestic), `m_k` (imports), `s_k` (shortfall).

```
minimize   Σ cd_k·d_k + ci_k·m_k + 1e6·max(D_k,1)·s_k
s.t.       d_k + m_k + s_k = D_k                       (D_k = |annual_scalar(gross)|)
           0 ≤ d_k ≤ min(cap_hi_k, D_k)
           0 ≤ m_k ≤ D_k · elig_frac_k · (1 − min_domestic_share)
           0 ≤ s_k ≤ D_k
[optional equipment-hour rows: Σ h_e,k·d_k ≤ L_e]
```

Facts to record about this formulation:

- `cap_hi` is a **scalar float in canonical units** — pieces, tonnes, MWh summed across
  heterogeneous segments without conversion (P4: 100 pcs + 5 t ⇒ "105").
- The localization constraint is **per-item**: each item's imports ≤ 30% of that item's demand
  when `min_dva=0.70`. It is *not* an aggregate-DVA constraint. With `min_dva=0.70` the solved
  plan satisfies every per-item cap (max share exactly 0.30, probe P12) while measured
  aggregate recursive DVA ≈ 15.5% (engine run) / 0.16% under strict selected-only funding —
  i.e., the advertised constraint does not constrain what it advertises.
- Items whose capacity is UNKNOWN get `cap_hi = 0`; if eligible they are served by imports;
  otherwise they become blocking unknowns (NOT_ADJUDICABLE path exists and is tested).
- Costs default to `cd=1.0, ci=1.08` USD/unit for **every** item regardless of physical unit
  (kg vs pcs vs MWh conflated in one objective); `total_shortfall = Σ s_k` sums pieces +
  tonnes + MWh into one scalar used by planner/VOI/frontier/reverse ranking.

### 2.4 Result classification (`solve._classify`)

`NOT_ADJUDICABLE` if any item is capacity-UNKNOWN with no eligible import route across all
years; else `INFEASIBLE_UNDER_MODEL` if any year has positive total shortfall; else
`CONDITIONALLY_FEASIBLE` if conditional reasons exist (unknown-but-importable items,
analyst overrides, funded-unproven list nonempty **only when `count_unproven_projects=True`**,
which is the constant default and is never toggled — P9: funding REPM+ACC adds just one
generic conditional string via `funded_pipeline="selected_only"` semantics, not a per-project
conditionality ledger); else FEASIBLE.

### 2.5 DVA accounting (`dva.dva_fraction`)

Per explosion item, using solver allocations for decision year (defaults to max year):

- domestically-served fraction × recursive imported-content share from
  `_domestic_input_import_share` (walks **primary recipes flagged INDIA-applicable only**,
  depth ≤ 6, cycle-guarded); inputs without domestic route count fully imported at
  `cost_import.get(item, cost_domestic.get(item, 1.0))`;
- processing value added defaults to `35% × max(t_in, 0.5)` — an ASSUMPTION emitted to
  `assumptions_used`;
- imported-served fraction counts fully at landed cost;
- **shortfall share contributes zero to both numerator and denominator** — DVA is measured
  over delivered units only (P22);
- `fraction = 1 − imported_cost/total_cost`.

The recursion is dimension-blind: costs are plain floats; kg vs t vs pcs never enter
(P11). Changing a material shortage's representation between `1 t_product` and
`1000 kg_product` changes neither DVA nor LP behavior (values pass through `annual_scalar`),
but changing *which units a recipe mixes* silently changes cost weights.

### 2.6 Transformations (`planner`, `substitutions`, `shocks`)

Candidate actions: fund shortfalls' projects (capex from pack), apply validated substitution
contracts, generic QUALIFY ($20M, 1–2 yr, instant boost), generic RESEARCH ($5M).
Portfolio search enumerates combos ≤ 8 exhaustively (greedy above), re-verifying each
through the real solver — genuinely closed-loop, no scripted outcomes.

But: QUALIFY enters `qualification_boosts` immediately (P15: +13,340 units/yr unlocked at
2027 with zero latency despite `latency_months=[12,24]` status `not_started`); SUBSTITUTE
rewrites requirement lines immediately (no transition-month gating). FUND actions are
numeric **no-ops** inside plan verification: planner option clones drop `funded_pipeline`
(N4), so verification always re-runs optimistic-pipeline semantics in which every evidenced
project already contributes its optimistic edge whether funded or not — the portfolio
search therefore "improves" only via instant QUALIFY/SUBSTITUTE effects. Lead times appear
only in display timelines (`_sequence`). Net effect: **plan verification solves a world in
which actions complete instantly**, and funding decisions are not actually being evaluated.

Substitution mechanics (P3): `apply_substitution` copies the `lines` dict shallowly and then
**mutates the original `RequirementLine` objects in place** (net/gross `+=` on shared objects):
the "immutable original" claim is false — after applying the SynRM substitution, the original
explosion's `hq_electrical_steel` line grew from 780,197 to 1,528,331 units/yr. Additionally
the substituted result keeps the replaced part's stale upstream chain (ndfeb_magnet still
present after replacing bldc_servo_motor) because only the named line is popped, never its
recipe-derived descendants.

### 2.7 Scenario intelligence

Shocks: clone world+opts correctly, apply 7 edit types, report applied/rejected. Two state
losses verified: pre-existing `competing_demand_cuts` discarded (P14), and
`funded_pipeline` mode itself is not carried into the clone (shock clones rebuild opts field-by-field and omit `funded_pipeline`, reverting to `"optimistic"`).

VOI: per unknown item, re-solve at cap=(lo,lo) and (hi,hi); HIGH iff rank tuple differs.
Because rank includes `−shortfall`, any shortfall swing flips the tuple **within the same
ResultClass**, so the flagship labels ~all 25 unknowns HIGH with text
“flips conclusion: pessimistic=INFEASIBLE_UNDER_MODEL, optimistic=INFEASIBLE_UNDER_MODEL”
(P5) — self-contradictory output.

Frontier: five-point sweep of θ; each point a full re-solve with `min_domestic_share=θ`;
cost/dependence columns left None/1.0 by the engine (no capex_for passed).

Reverse: grid {250k, 500k, 750k, 1M} ascending, first feasible volume wins; inner binary-search
helper `ok()` defined and never called (P16). Not an optimizer.

ModelRun: `create()` hashes pack_id/version + objective dict + scenario dict +
`pk.summary()` (counts and name lists only) + solver version. Probe P7b: editing a numeric
capacity from 4,000,000 t/yr to 40 t/yr leaves the run hash **byte-identical**. `finish()`
is never called, so outputs/warnings fields stay empty in the response's `run` block.

Proof graph: 1,367 nodes in the flagship response, **zero evidence-kind nodes**;
177 disconnected roots of kind derived/output; no output node is reachable from any evidence
node (P6). Numbers carry derivation labels but not source lineage.

### 2.8 Flagship numbers produced on this exact tree (2026-08-22)

```
result_class          INFEASIBLE_UNDER_MODEL
2030 total_shortfall  334,396,038 (unit-eq.; mixed pcs/t/MWh scalar)
2026 total_shortfall  573,680,186
achieved DVA          15.52%
top 2030 gaps         crossed_roller_bearing 104.5M; absolute_encoder 96.4M;
                      bldc_servo_motor 40.3M; harmonic_reducer 35.0M;
                      actuator_rotary_body 24.8M; micro_actuator_hand 10.9M;
                      dram_chip 6.2M; motor_driver_inverter 3.8M (demand 44.0M)
```

These match the repo's VALIDATION_REPORT matrix closely enough to confirm the same
executable behavior; the interpretation attached to them there is not always warranted
(see reconciliation doc).

## 3. What is genuinely sound (preserve unchanged)

1. **Unit/dimension engine core** — Dim algebra, family-separated tonnes, prefix handling,
   power-vs-energy, `annual_scalar` semantics, explicit-FX `convert()` (the bypass is in
   Quantity arithmetic, not `convert`).
2. **Epistemic class system + ResultClass vocabulary** — enums, confidence validation,
   REPORTED-needs-source enforcement in the loader.
3. **Frozen EvidenceRecord / Source immutability** and supersedes design.
4. **UNKNOWN ≠ supply discipline inside the LP** — unknown-capacity items never receive
   phantom domestic supply (tested; verified).
5. **Project state machine vocabulary and ramp interpolation** — `ramp_fraction`,
   state-credit table, impairment zeroing are individually correct primitives.
6. **Shock-as-constraint-edit architecture** (deep copy + re-solve; C10 honored structurally).
7. **Portfolio search re-verification loop** — plans are checked through the real solver;
   the defect is what the solver is told, not that outcomes are scripted.
8. **Pack loader validation spine** — yields/factors ranges, duplicate-id rejection,
   substitution field gate, crosswalk confidence fields.
9. **Deterministic NLP parse layer** — inspectable, never authoritative.
10. **HiGHS LP mechanics** — the solver itself, marginal extraction, tolerance logic.

## 4. Data-flow diagram (actual)

```
YAML ──load_pack──▶ World(+Evidence,Source) ──▶ explode_variant ──▶ ExplosionResult(lines)
                                                                     │
                    ┌────────────────────────────────────────────────┘
                    ▼
        for year: capacity_envelope(item,year) ──▶ cap_hi scalars ─┐
                                                                   ▼
                                              solve_year LP (HiGHS) ──▶ YearResult
                                                                   │
             classify ◀── totals/scalars ──────────────────────────┘
                │
   dva_fraction(walks recipes w/ allocations) ─▶ DVABreakdown
   candidate_actions ─▶ PlanEngine.search_portfolio ─▶ TransformationPlan
   voi(value_of_information) / closure_frontier(sweep) / reverse_buildability(grid)
   ModelRun.create(hash of summary) ; ProofGraph(labels only, no evidence nodes)
                │
                ▼
        response JSON ─▶ FastAPI ─▶ React console
```

Every arrow above is exercised by the probes; none is inferred from documentation alone.
