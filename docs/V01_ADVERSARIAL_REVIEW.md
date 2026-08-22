# V0.1 — ADVERSARIAL REVIEW (second-pass falsification record)

Reviewer stance: every first-pass conclusion treated as suspect; each finding re-derived
from code, then attacked with the smallest executable counterexample that could disprove it.
Probes ran against the exact worktree (`worktree-new-v0.1-correctness`, clean at
`c384a14`), Python 3.12.10, 2026-08-22. No production file was modified; probes live in
system temp (`%TEMP%\forge_v01_probes\`), reproducible verbatim.

---

## 1. Falsification attempts and outcomes

### F1 (min_dva semantics) — attack: "maybe DVA is enforced elsewhere"
Searched for any aggregate value constraint: engine passes `min_dva` only into
`ScenarioOptions.min_domestic_share`; solver uses it solely in `bounds[n+k]`
(solve.py:203-204); no post-solve check compares measured DVA to θ anywhere.
Counter-attempt: maybe per-item caps *imply* high DVA? Disproved by construction:
P12 shows all caps satisfied at exactly 0.30 import share while measured DVA = 15.5%
(optimistic funding) / 0.16% (selected-only). The gap is structural: item-level physical
quantity shares ≠ value-weighted recursive content shares. **Finding stands.**
Second-order consequence of fixing it (logged in plan W2.2): flagship verdict class may
change from INFEASIBLE_UNDER_MODEL (shortfall-driven) to DVA-infeasible with different
closure candidates — UI copy must not hardcode "shortfall" framing.

### F3 (explosion overcount) — attack: "maybe probe world is unrepresentative"
Tried worlds where V0 gives correct answers: linear chains (no shared upstream) — correct;
shared leaves without recipes — correct. The defect requires shared intermediate WITH a
recipe, which the flagship has (bearings/steel/magnets feed multiple consumers).
Independent confirmation without probes: `test_humanoid_benchmark_multiplication` computes
its expected bearing gross via closed-form BOM-path math and passes — while P2's
recipe-path world fails linearity — proving the two paths diverge and only one is tested.
**Stands.** Correction invariant is additivity (B), not a patched constant.

### F4/N1 (substitution) — attack: "maybe mutation is benign because callers re-explode"
Callers do NOT re-explode: planner reuses `explosion_builder` output then mutates via
`apply_substitution` per combo; engine holds `ex` across plan/VOI/frontier stages
(engine.py:160-237) — any future substitution-in-engine path would corrupt baselines.
Even as-is, P3 demonstrates same-object mutation observable from outside the call.
Also attempted to falsify "stale ndfeb survives": checked whether `_accumulate_inputs`
re-run would remove it — it isn't re-run at all after substitution. **Both parts stand;
mutation part upgraded to standalone N1 (external audit's immutability claim was wrong).**

### F5+N2 (heterogeneous scalars) — attack: "maybe packs never mix units"
Flagship explosion mixes pcs items (actuators), kg_product inputs (steel), t_product
capacities (alu 4Mt), MWh project (ACC 40 GWh/yr) — all entering one LP and one scalar.
P4's minimal mix proves silent confluence ("105"). Attempted defense: does annual_scalar
normalize? It normalizes time-denominators only; unit families remain distinct dims that
the envelope/LP ignore. **Stands.**

### F6/F7 (imports) — attack: "maybe demand pools cap imports"
DemandPool objects exist but enter solve only via competing_demand_cuts when cuts are
explicitly provided; baseline solves apply none (grep: no automatic pool consumption).
P13 confirms unbounded-by-evidence imports. Averaging attack (F7): tried to find weights —
`elig_map.get(c, 1.0)` mean over countries, no volume data consulted; HHI fields present
in pack (ndfeb 0.9) and unread. **Stands.**

### F8-F12 (projects/time/qualification) — attack: "tests already cover announced≠operating"
They cover interval edges, which do behave. The residual claims were about *conditionality
accounting* and *estimate influence*: P9 (funding both projects yields exactly one generic
conditional string), P10 (estimate algebra collapses ∀E: max(A,min(E,A))≡A — proof by
identity, no probe needed but executed anyway), F9 grep (parameter never branched on),
F11 grep + P15 (instant boost vs latency_months), F12 (with_actions adds boosts/subs
before evaluate; _sequence display-only). **All stand.**

### F14/F15 (VOI) — attack: "maybe HIGH labels are rare"
P5: on the flagship's real unknown set, EVERY sampled task reads HIGH with text asserting
a flip between two identical class names — self-refuting output. Rank-tuple inspection
makes it definitional, not incidental. Constraint-drop (F15): read eval_with literal —
seven ScenarioOptions fields absent. **Stand.**

### F16/F17/N4 (scenario state) — attacks: "clone list is long, maybe I misread"
Diffed clone field list against ScenarioOptions fields mechanically (dataclass fields vs
constructor kwargs in shocks.py/planner.py): funded_pipeline absent in both clones;
competing_demand_cuts overwritten post-loop (shocks.py:162) even for zero edits (P14).
Display-vs-solve divergence (P20): baseline==impaired displayed hi (27,000,000) while
true shocked-world value is 0 — the strongest single demonstration in the set, since the
UI would show capacity exactly where the model asserts none. **Stand.**

### F19/F20 (proof/provenance) — attack: "evidence nodes maybe added by server layer"
Counted kinds directly in engine response JSON (what UI consumes): evidence=0.
Loader validates evidence existence but nothing constructs graph nodes from records —
`evidence_node()` zero call sites. **Stands.**

### F21 (hash) — attack: "maybe summary includes content somewhere"
Read summary(): counts, kinds histogram, sorted id lists. P7b executes the decisive
experiment: 100,000× capacity change ⇒ identical hash. Reproducibility claim inverted:
V0 hashes are insensitive to the very numbers they claim to pin. **Stands.**
(First probe batch's P7 compared full-summary vs skeleton hashes — unequal, correctly —
that comparison alone would NOT have proven insensitivity; the numeric-edit variant was
required. Recorded to keep the falsification chain honest.)

### F22-F25 (intelligence layer) — source inspection suffices except reverse (dead ok() count
via inspect.getsource, P16) and option-report structure (per-pack loop, no cross-pack
object sharing exists architecturally — worlds are distinct; ids don't match across packs
by design today). **Stand.**

### F26 (FX) — attack: "convert() guard may suffice"
convert() raises correctly (P8); leak is in Quantity arithmetic canonicalization
(EUR factor 1.0 == USD factor 1.0). Latent today (no multi-currency solve path), hence
PARTIAL + P2-with-guard in plan W0.3 rather than P0.

## 2. Where the external audit was WRONG or incomplete

1. F4's "Original ExplosionResult must remain immutable" is violated more deeply than
   audited: the original object mutates through shared RequirementLine references (N1).
2. Audit missed N2 (unit-blind envelope summation + projects-only lo=0 quirk with a dead
   min() branch) entirely — affects every multi-source item in the flagship.
3. Audit missed N3 (gross/net demand split across solver vs DVA vs UI rows).
4. Audit missed N4 (funded_pipeline dropped by clones) though it flagged adjacent state loss.
5. Audit's F8 partially overstated: generic conditional emission DOES exist; the defect is
   its emptiness on the default path, not total absence.
6. Repo self-docs understate their own suite (48→52→53 drift) — external audits relying on
   docs would inherit stale counts; another reason probes > prose.

## 3. Interactions requiring joint correction (why waves, not patches)

- **F3+F4:** substitution correctness is undefined until explosion has subtree structure;
  patching deletion onto flat lines re-creates staleness bugs. → W1 must land together.
- **F1+F2+F5:** an honest DVA constraint needs dimensional cost weights (F2) and cannot be
  evaluated against a heterogeneous scalar shortfall (F5). Fixing F1 alone produces a
  constraint measured against noise. → W0 before W2.
- **F12+F15+N4:** VOI and plans are only trustworthy after scenario-state cloning is total;
  otherwise corrections measure the wrong counterfactuals. → W3 precedes W5.
- **F17+F19:** displaying w_eff envelopes without evidence-linked derivations just moves
  the trust hole; wire both in one pass. → W4 pairs J4 with G-gates.
- **F9+F10+F11:** three dead knobs suggest a pattern — parameters validated at load,
  ignored at solve. Any NEW parameter added by this plan must ship with its solver
  consumption test in the same commit (process rule adopted).

## 4. Abstractions reviewed for replacement vs repair

| Abstraction | Verdict | Reasoning |
|---|---|---|
| Dim/Quantity | REPAIR-only (currency op guard) | Core algebra sound; tested; foundational |
| Flat ExplosionResult | REPLACE (FlowGraph) | Cannot express incremental flows/subtree ops |
| primary_recipe() | REWRITE (policy param) | 8 lines; wrong preference order; central |
| Envelope Interval | REPAIR (unit-aware pair + fixed lo/hi logic) | Concept right, assembly wrong |
| Per-item localization bound | REPLACE (certified DVA loop → later unified program) | Wrong semantics irreparable locally |
| Scalar shortfall | REPLACE (vector) | Consumers all need families |
| ProofGraph | KEEP (mechanism) — WIRE (usage) | Machinery sound, unused where it matters |
| ModelRun.create hashing | REPAIR (payload swap) + finish() wiring | Structure fine |
| Shock clone-and-edit | KEEP (fix field lists) | Architecture honored C10 |
| Planner verify-through-solve | KEEP | Right idea; feed it corrected solver+time |
| VOI rank tuple | REPAIR (flip definition) | Small, surgical |
| Reverse grid scan | REPLACE (bisection + monotonicity cert) | Dead helper betrays abandoned intent |
| Frontier sweep | EXTEND to Pareto filter + cost column | Sweep core reusable |

Nothing sound was rewritten; nothing broken was preserved for familiarity's sake.

## 5. Residual risks / open questions for the implementation agent

1. Flagship headline numbers WILL move (explosion fix lowers demand; supply fixes raise
   feasible imports' honesty; DVA constraint tightens verdicts). Do not tune packs to
   preserve old headlines; regenerate validation matrix (plan gate 2/6).
2. Two-stage DVA loop termination: cap-tightening is monotone; require iteration ceiling +
   certificate export; if non-convergent on real packs, escalate to unified formulation
   rather than loosening θ.
3. Cross-pack option value needs an id-alignment convention across packs (shared resource
   ids like lithium_carbonate already overlap informally) — define registry before W5.4.
4. ForeignSupplySegment is new ontology surface: keep additive to model.py; packs unchanged
   until evidence exists (no invented capacities — C21).
5. Legacy tests encode several defective constants (benchmark bearing gross includes
   recipe-chain inflation? — verified it does NOT for bearings, but encoder ≥ inequality
   and redesign-loop acceptance magnitudes will shift; update with justification notes).

## 6. Exhaustion statement

All 26 external findings re-derived (24 confirmed, 2 partial, 0 rejected); 10 new defects
documented with minimal demonstrations; every proposed correction mapped to wave, oracle
gate, invariant, and second-order consequence; abstractions individually adjudicated.
Remaining uncertainty is evidential (pack thinness), not mechanical — which is FORGE's
honest research programme, not a correctness debt.
