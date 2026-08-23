# FORGE WORLD V0.1 — VALIDATION REPORT v2 (post-correctness)

> **RT4 review amendment (this branch, post independent review):** the four
> review findings were fixed and re-verified. Consequences for the numbers
> below: (a) the flagship's default run is now **NOT_ADJUDICABLE** under strict
> foreign-supply epistemics — 23 items delivered on imports whose absolute
> foreign capacity is UNKNOWN; with the explicit
> `foreign_supply_policy="unbounded_assumption"` the run is
> **CONDITIONALLY_FEASIBLE** with delivered-mix recursive DVA **90.6%**
> certified. The earlier "21.2% DVA / INFEASIBLE" row described the interim
> implementation, not tuned data; the honest current headline is the one in
> this note. (b) `min_dva` no longer applies any per-item cap; an
> unattainable θ yields `INFEASIBLE_WRT_DVA`, never manufactured shortage.
> (c) DVA proof nodes derive from allocation/basis/embedded/price/origin input
> nodes; `measure_dva` is a pure path (no monkey patching, no cross-run state).

All numbers below were produced by the V0.1 code on this worktree (2026-08-22,
Python 3.12.10). Reproduce via `python -m pytest tests/` and
`python scripts/forge_cli.py run …`. This report SUPERSEDES VALIDATION_REPORT.md;
its claims are scoped to what executable behavior now demonstrates.

## 1. Test suite

**93 passed + 1 skipped** (skip = fundable-project fixture absent in pack).
Includes 4 oracle modules that FAILED on the preserved V0 implementation, plus
`test_oracles_review.py` whose 5 finding-specific oracles were verified to fail
on the pre-review-fix implementation and pass after.

| Oracle module | Gates | V0 behavior killed |
|---|---|---|
| `test_oracles_flows.py` | G1/G2 | Y=2800 shared-input overcount (now exactly 2000); substitution mutating caller's result; stale NdFeB chains surviving; depth truncation silence; cycle RecursionError |
| `test_oracles_solve.py` | G3/A/D/E/J/H | per-item localization masquerading as DVA; eligibility-as-supply (imports ≤ evidenced foreign capacity); unit-representation sensitivity; heterogeneous shortfall sums |
| `test_oracles_time_state.py` | G4/G6 | instant qualification boosts; shock clones dropping pipeline mode/cuts; prose-only unproven flags |

Legacy suite retained; two expectations revised with documented justification
(`test_redesign_loop_improves_feasibility_under_constraint` — V0 passed only via
inflated explosion numbers; now asserts architectural invariants).

## 2. Flagship: HV-2 @ 1,000,000/yr, ≥70% DVA, INDIA, 2030

| Metric | V0 | V0.1 |
|---|---|---|
| Result class | INFEASIBLE_UNDER_MODEL | INFEASIBLE_UNDER_MODEL |
| 2030 pcs-family shortfall | 334.4M unit-eq (invalid mixed scalar) | 335.3M **pcs only**, families reported separately |
| Achieved DVA claim | "15.5%" against per-item caps | delivered-mix recursive DVA **21.2%**, certificate status `infeasible_delivery_shortfall` |
| Constraint semantics | per-item 30% import caps | certified aggregate-DVA loop (target not certifiable while delivery shortfall exists) |
| Proof graph | 1367 nodes, **0 evidence**, 177 disconnected roots, 0 outputs evidence-linked | all **87 outputs evidence-reachable**; scenario roots only; every substitution derives from its declared records |
| Run identity | hash of counts (invariant under 100,000× capacity change) | full canonicalized world+scenario snapshot hash; deterministic across runs |
| VOI | ~25× fake HIGH "flips conclusion: INFEASIBLE→INFEASIBLE" | HIGH iff real class flip; magnitude reported separately |
| Displayed envelopes under shocks | contradicted solver (27M shown vs true 0) | envelopes built from shocked effective world |

Top 2030 gaps (pcs family): crossed_roller_bearing ≈104M, absolute_encoder ≈96M,
bldc_servo_motor ≈40M — consistent with the pack's documented UNKNOWN precision-motion
capacity; the verdict remains derived, never encoded.

## 3. What is now IMPLEMENTED AND VERIFIED

- FlowGraph requirement core: linearity, order-invariance, cycle rejection, depth-honesty.
- Immutable architecture-level substitution with exact dependency swap + idempotence.
- Recursive product-basis DVA (embedded imports once), unit-invariant; raw-origin
  UNKNOWN handled by an explicit named ASSUMPTION share, never silently.
- Unit-safe deficits: ShortfallVector + normalized service deficit drive all rankings.
- Foreign supply ceilings (ForeignSupplySegment) bound imports; weighted eligibility
  (evidenced shares → concentration proxy → equal, each labeled).
- Temporal causality: pre-commissioning years are zero on BOTH envelope edges;
  qualification boosts honor latency windows.
- Scenario-state integrity through shocks/planner/VOI counterfactuals (full clone).
- Conditionality ledger naming unproven projects, states, commissioning windows;
  count_unproven_projects=False removes their contribution numerically.
- Evidence-connected proof graphs for every consequential output incl. plan search.
- ModelRun identity over full snapshots; finish() records outputs/warnings.

## 4. IMPLEMENTED WITH MODELED ASSUMPTIONS (labeled in-output)

- Planning costs default to declared/derived values; processing value added defaults
  to 35% of input cost where undeclared — every use is listed in `dva.assumptions`.
- Raw-material origin UNKNOWN defaults to `raw_material_import_share=0.0`
  (conservative domestic) unless a scenario declares otherwise.
- ESTIMATED capacity segments remain order-of-magnitude allocations (C13/C21 labels).

## 5. EXPERIMENTAL / DEFERRED (honestly labeled)

- Closure frontier = dominance-filtered sweep over five θ points (not continuous Pareto).
- Reverse buildability = monotone bisection seeded by grid; non-monotone worlds fall
  back to best sampled point.
- Machine recursion: trigger machinery present; flagship packs carry no equipment
  fleets to bind, so no recursion fires (absence surfaced, not claimed active).
- Cross-pack option value: API reports within-objective relief only; shared-capability
  credit deferred (requires cross-pack entity registry).
- Inventory/WIP, facility-level geography, price formation: out of V0.1 scope.

## 6. Determinism

Identical trees produce byte-identical run hashes (CI smoke asserts this). The hash
covers the full entity/edge snapshot, objective, scenario options, and solver version;
timestamps live outside the hashed payload.
