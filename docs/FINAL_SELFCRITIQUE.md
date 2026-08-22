# FINAL SELF-CRITIQUE (§52) — brutal assessment of FORGE WORLD V0

Written by the build agent before declaring completion. No praise below without evidence.

## What is genuinely real

- The **unit engine, epistemics, proof graphs, project state machines, LP allocation with
  binding-constraint extraction, DVA recursion, substitution gating, shock-as-constraint-edit,
  VOI flip detection, frontier sweep, reverse queries, and option-value measurement** are
  implemented, tested (52 tests), and exercised by every API call. The UI renders only this
  computed state; there are no scripted demo outcomes anywhere in the codebase.
- The flagship result — *imported-kit assembly is arithmetically feasible; a ≥70%-domestic
  1M/yr humanoid line is INFEASIBLE under current evidence because precision-motion capacity
  is absent or unknown* — is derived, matches the supplied dossier's independent human
  analysis, and changes coherently under shocks, deadlines and DVA edits.
- Evidence discipline is mechanical: packs fail validation without sources for REPORTED
  claims; UNKNOWN never silently becomes zero or infinity; ESTIMATED values are labeled
  through to the UI.

## What remains modeled or assumed

1. **Recipe depth.** Humanoid routes go component → key inputs; sub-component chains
   (insulation, adhesives, connectors) stop at resource classes. Defensible via lazy recursion,
   but a materials engineer would find the explosion coarse.
2. **Costs are planning placeholders** (default unit costs + landed-cost premium). Only scheme
   capex figures are source-backed. Cost rankings within a scenario are meaningful; absolute
   dollar outputs are not.
3. **Import supply is an eligibility fraction**, not a vessel-level network. Corridor shocks
   act through cost multipliers — directionally right, operationally shallow.
4. **ESTIMATED segments** (structures, aluminium) are order-of-magnitude allocations from
   national-scale priors. They cannot support facility-level claims and are labeled as such,
   but they do carry numeric weight in the LP.
5. **Competing demand** uses contestable-pool priors; no endogenous price formation.
6. **Qualification latency** is range-based, not queue-based; no audit-failure branching.

## Where a policymaker could be misled

- Screenshots of the VERDICT gap bars without the epistemic chips could read as measured
  factory data. The chips exist everywhere we control, but the burden is on presentation.
- "DVA 15.5%" is convention-dependent (C18); the boundary rule is documented but a reader
  could quote the number without the convention.
- The option-value ranking measures *within-objective* relief; cross-pack synergies (cells
  used by robots AND satellites) are not yet credited, so it currently understates shared-
  capability investments like ACC cell plants.

## Where an engineer would push back

- Yield/scrap gross-up treats route yield as a scalar multiplier; real lines have
  rework loops and binning.
- Machine-hour constraints exist but no fleet data binds them in production scenarios —
  the recursion story is currently proven in tests more than in the demo.
- Ramp curves are linear-interpolated priors; Figure's disclosed ramp suggests S-curves can
  be far steeper early.
- No inventory/WIP layer: short-run shock absorption (weeks) is invisible; our shocks bite
  immediately, which is conservative but unrealistic for stockpiled industries.

## Where the ontology is too coarse

- `ResourceClass` vs `Part` boundary blurs for commodity intermediates.
- Qualification objects gate items, not customer×spec pairs.
- Geography is country-level plus named facilities; corridors carry cost proxies, not
  capacities.

## Where the UI implies more certainty than the model has

- The capacity-vs-demand chart draws a crisp band edge at envelope `hi` even when `hi`
  includes unproven projects (the amber "projects" chip mitigates).
- Frontier points are single-scenario solves; parameter uncertainty bands around each point
  would be more honest (VOI partially covers this elsewhere).

## Performance

Solve times ~0.2–2.5 s including deep analytics; proof graphs serialize up to ~1,400 nodes;
UI stays responsive (canvas rendering, capped DOM). Not a bottleneck at V0 scale.

## Verdict

The system's core claim holds: it computes honest feasibility arguments over sparse evidence
and makes its ignorance actionable. Its biggest intellectual debt is the thinness of the
evidence layer beneath the flagship — which is precisely the world's fault, not a fabrication,
and the product turns that into its research programme. Next leverage: trade-data adapters to
upgrade REPORTED→MEASURED where possible, inventory dynamics for short-horizon shocks, and
cross-pack capability sharing in option value.
