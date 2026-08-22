# VALIDATION REPORT

All numbers below were produced by the shipped code (run 2026-08-22) and are reproducible via
`python scripts/forge_cli.py run …` or the pytest suite. `validation_runs.json` holds raw output.

## 1. Contract test suite

`python -m pytest tests -q` → **48 passed**. Coverage by MODEL_CONTRACT invariant:

| Invariant | Tests |
|---|---|
| C1 evidence immutability | frozen dataclass mutation raises |
| C2 epistemic classes / UNKNOWN≠0 | unknown capacity never becomes supply; UNKNOWN flags propagate to gaps |
| C3 units | mass-family separation, prefix conversions, power/energy separation, composite units, FX-rate gating |
| C4 clocks | capacity segments carry validity windows; project states carry dates |
| C6 effective capacity identity | nameplate×avail×util×yield×qual verified numerically |
| C7 project state machines | announced ≠ operating; ramp is piecewise-linear not step; impairment zeroes |
| C8 qualification gating | qualification boost only unlocks existing segments |
| C9 substitution contracts | missing envelope/maturity rejected; validated contract rewrites requirements |
| C10 shocks edit constraints | eligibility shock reduces solved imports (not hand-multiplied); applied-edit ledger exposed |
| C15 proof graphs | every explosion line emits derivation nodes; lineage walk verified |
| C16 result classes | all four classes reachable and tested |
| C17 NOT_ADJUDICABLE | unknown + blocked-import item produces refusal with named unknowns |
| C21 no fabricated entities | REPORTED/MEASURED without source fails pack validation |
| C30-style determinism | ModelRun input hash stable across identical inputs |

## 2. Benchmark fixtures

**HV-2 @ 1,000,000 units/yr** (`tests/test_core.py::test_humanoid_benchmark_multiplication`):
- body actuators: exactly 30,000,000 net/yr (30 × 1M)
- hand micro-actuators: exactly 14,000,000 net/yr
- crossed-roller bearings gross = [64M + 60M/yield(actuator-route)] / yield(bearing route) —
  verified to machine precision against the closed-form expression.
- encoders ≥ 60M/yr. No silent supply creation anywhere in the chain.

## 3. Mechanism backtests (directional)

| Backtest | Expectation | Result |
|---|---|---|
| Tōhoku-2011 style single-origin outage (JPN MCU) | banning the concentrated origin creates shortfall at the SPOF item | PASS — shortfall concentrates on `auto_ecu` |
| Red Sea style corridor cost shock (+35% landed import cost) | import value rises ≥1.2× under same quantities | PASS |
| 2020–23 style chip allocation crunch (−50% TWN/KR eligibility @95% DVA) | shortfall appears on compute items | PASS — soc/edge_compute shortfalls present |
| Ramp behavior vs Figure-style disclosure | fast early ramp then plateau, never a step | PASS |

## 4. Flagship scenario matrix (humanoid_india, HV-2 @ 1M/yr)

| Scenario | Verdict | 2030 shortfall (unit-eq.) | Achieved DVA | Verified plan outcome |
|---|---|---|---|---|
| ≥70% DVA baseline | INFEASIBLE_UNDER_MODEL | 334.4M | 15.5% | INFEASIBLE (residual gap) |
| 0% DVA (imported-kit assembly) | CONDITIONALLY_FEASIBLE | 0 | 8.2% | CONDITIONAL (unknown-capacity imports) |
| ≥95% DVA | INFEASIBLE_UNDER_MODEL | 463.5M | 22.7% | INFEASIBLE |
| REE export −80% shock @70% | INFEASIBLE_UNDER_MODEL | 371.7M | 12.8% | INFEASIBLE; substitution action ranked up |
| Deadline pulled to 2028 @70% | INFEASIBLE_UNDER_MODEL | 361.4M | 11.9% | INFEASIBLE |

Reading: the corpus's conditional conclusion ("arithmetically assemblable from kits;
not demonstrably sovereign-capable by 2030") falls out of the model rather than being
encoded. The binding gaps are precision motion components — reducers, robot-grade bearings,
encoders, servo motors — precisely where the dossier documents evidence gaps.

## 5. Domain packs 2 & 3

- **battery_gwh_india @500k packs/yr, ≥60% DVA:** INFEASIBLE until ACC PLI projects ramp
  (cells short 2026–27, close ~2028), residual ~1.12M unit-eq from BMS/busbar/graphite.
  Graphite-control shock widens residual → 1.21M. Chemistry substitution (NMC→LFP) removes
  Ni/Co exposure through a validated contract.
- **smallsat_india @50 sats/yr, ≥60% DVA:** INFEASIBLE on space-PV cells, screened cells,
  reaction wheels — HiRel regime behaves qualitatively differently from volume regimes,
  exercising the same ontology.

## 6. Numerical sanity checks (§37 of mission)

- Units: ore ≠ metal ≠ oxide ≠ alloy ≠ product tonnes (mechanically enforced).
- Power ≠ energy; per-year rates normalized via explicit `annual_scalar` (tested ×8760 semantics).
- Component counts double-checked: BOM leaf counts + recipe-input chains sum correctly
  (bearings case exercises both paths simultaneously).
- Yield/scrap gross-up verified against closed-form multi-step expressions.
- Nameplate vs qualified: every segment exposes its four factors separately in API rows.
- Announced projects contribute zero until commissioning window opens (2026 floor does not
  apply to already-operating assets).

## 7. Reproducibility

ModelRun hashes pack snapshot summary + objective + scenario + solver version. Identical
inputs reproduce identical outputs (LP is deterministic; no stochastic elements in V0 paths).
`run_id` in the top bar matches CLI runs given equal configuration.
