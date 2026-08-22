# ADVERSARIAL REVIEW — PHASE 14

Internal red-team pass over the shipped V0, structured around the mission's own checklist
(§46). Each item: audited verdict, and fix where a defect was found.

## Findings and dispositions

| # | Attack | Verdict | Action |
|---|--------|---------|--------|
| 1 | Polished graph makes weak assumptions look like facts | **DEFECT FOUND** — envelope rows labeled all non-UNKNOWN capacity "evidenced", including ESTIMATED priors | FIXED: envelopes now carry `epistemic` (MEASURED/REPORTED/ESTIMATED/mixed/projects_only); UI renders distinct chips; ESTIMATED carries explanatory tooltip |
| 2 | Exports treated as production capability | PASS — no trade flow feeds capacity; trade appears only as confidence-bearing crosswalks | — |
| 3 | Patents treated as capability | PASS — patent-class crosswalk note states inventive-activity-only | — |
| 4 | Announced projects counted as operating | PASS — state machines + tests; ACC/REPM contribute only optimistic-edge capacity and flag CONDITIONAL | — |
| 5 | Generic motor manufacturing read as humanoid-grade | PASS — humanoid-grade motor/reducer/encoder capacity left UNKNOWN with capability claims separating claim-vs-assessment | — |
| 6 | Exact factory capacity inferred from national statistics | **PARTIAL** — two ESTIMATED segments are national-scale order-of-magnitude allocations | Mitigated: labeled ESTIMATED with method notes; surfaced as such in UI after fix #1 |
| 7 | Invented substitution | PASS — single substitution grounded in IEEE/IEA-sourced contract with envelope check | — |
| 8 | LLM sentence became solver coefficient | PASS — no LLM anywhere in the solve path | — |
| 9 | Product architecture vs category confusion | PASS — variants are first-class; no canonical BOM | — |
| 10 | Installed vs qualified capacity conflated | PASS — four separable factors; qualification boost only unlocks existing segments (tested) | — |
| 11 | Machine-tool dependencies ignored | PARTIAL-BY-EVIDENCE — recursion machinery implemented+tested; fleets UNKNOWN in pack so flagship doesn't trigger it | Documented in PROJECT_STATUS; VOI marks what to audit |
| 12 | Metrology ignored | PASS-LIGHT — metrology equipment class gates reducer route; capability vector dimension present | Future: deeper metrology capacity modeling |
| 13 | Customer qualification ignored | PASS — qualification objects gate; QUALIFY actions exist | — |
| 14 | Maintenance/spares ignored | KNOWN GAP — V0 scope; documented | Backlog |
| 15 | Competing demand ignored | PASS — demand pools with contestable fractions; shock-driven cuts tested | — |
| 16 | Commodity assumed fully contestable | PASS — contestable_fraction ≤ 0.25 everywhere | — |
| 17 | City-level detail fabricated | PASS — no invented coordinates; geography stays at evidence resolution | — |
| 18 | Conflicting evidence silently resolved | PASS-BY-ABSENCE — CONFLICTED is first-class and tested; packs currently contain no conflicted pairs | — |
| 19 | Unit mishandling | PASS — mechanical enforcement; ore/metal/oxide/alloy/product families separated | — |
| 20 | Hidden assumptions | PASS — DVA assumption lists, conditional reasons, scenario FX gating | — |
| 21 | Current vs 2030 states confused | PASS — three-clock fields on segments/projects | — |
| 22 | Single fake resilience score | PASS — frontier/Pareto presentation only | — |
| 23 | Impressive UI over shallow computation | PASS — every UI number originates in solver/emitter output; no scripted outcomes (verified by code review + tests) | — |

## Additional defects found & fixed during the pass

1. **Pipeline-mode incoherence:** funding any one project silently switched the world from
   "optimistic pipeline" to "selected-only", making before/after comparisons lie.
   → explicit `funded_pipeline` mode; reverse query aligned; option-value report uses an
   explicit strict baseline (`__baseline_none__`) for honest marginal relief measurement.
2. **Degenerate LP cost ties** produced all-import allocations (DVA exactly 0%) at min_dva=0.
   → imports now carry a landed-cost premium by default (explicit ASSUMPTION), breaking ties
   toward domestic supply where qualified capacity exists.
3. **Worst-year reporting** returned year 0 when no shortfalls existed → cosmetic fix.

## Residual risks (accepted, documented)

- ESTIMATED segments could still anchor over-confident narratives if screenshots circulate
  without chips — mitigated but inherent to any estimate.
- The magnet programme's 0% measured option-relief is correct under current architecture
  (motors imported wholesale embed the magnets) but may surprise policymakers; the
  explanation string says so explicitly.
- Equipment-hour constraints exist but lack fleet data to bind in production scenarios.
