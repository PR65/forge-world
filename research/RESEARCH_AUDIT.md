# FORGE WORLD — RESEARCH AUDIT (Phase 0)

Audit date: 2026-08-22. Auditor: FORGE build agent.
Scope: every supplied artifact under `research/`. All artifacts were opened and read in full
(the 41-page PDF was text-extracted and read in full). SHA-256 hashes recorded below.

## Integrity actions performed

1. `FORGE_WORLD_Wide_Research_Appendices.zip` was unpacked **non-destructively** to a temp
   directory. Every entry was hashed and compared against the loose corpus files:
   - `forge_notes/01.md … 12.md` — byte-identical to loose `01.md … 12.md`.
   - Root observation/scope files — byte-identical to their loose counterparts.
   - **Unique content:** the ZIP contains `forge_notes/03.md`, which was MISSING from the
     loose corpus. A copy was restored to `research/03.md`. This is the only file whose
     canonical copy exists solely via the ZIP.
2. `forge_world_wide_research.json` and `forge_world_wide_research.csv` carry the same 12
   stream records (same input strings, same summaries, same signed Manus CDN note URLs).
   Treated as format duplicates; JSON is canonical for machine use.

## Artifact inventory

| # | Artifact | Type | Inspected | Duplicate status | Major contribution | Major caveats |
|---|----------|------|-----------|------------------|--------------------|---------------|
| 1 | `pasted_content.txt` | Mission brief (the wide-research prompt) | Yes, full | Canonical | Defines the 12 research streams; establishes evidence discipline expectations | It is an instruction artifact, not evidence |
| 2 | `forge_world_research_scope.md` | Scope manifest | Yes | Canonical | Stream list + required outputs + label taxonomy | Summary-level only |
| 3 | `FORGE WORLD Wide Research Package.md` | Synthesis report (~547 lines) | Yes, full | Canonical | Executive synthesis; IndiaBUILD/Swarajya findings; dataset matrix; capability-model design; humanoid benchmark arithmetic envelope incl. energy-arithmetic correction; substitution/shock/qualification dossiers; recommendations | Synthesis layer; numbers inherit upstream caveats; market-size figures are MODEL/ESTIMATE |
| 4 | `01.md` IndiaBUILD extraction | Stream note | Yes | Identical copy inside ZIP | 6-tier maturity taxonomy; builder ladder; claim-vs-assessment; engine pipeline; naked/capital-starved gaps; no public API found | Site-reported counts date-sensitive; dashboard % vs counts inconsistency preserved |
| 5 | `02.md` Swarajya mining | Stream note | Yes | Identical copy inside ZIP | Critical-minerals claims; NCMM ₹34,300 cr; purity paradox; UP/Gujarat semiconductor clusters; exploration lead-time parameterization | Media-reported; requires Ministry/Cabinet corroboration per its own ledger |
| 6 | `03.md` Global capability analogues | Stream note (recovered from ZIP) | Yes | Canonical (unique) | WIPO Navigator, Harvard Atlas, OECD TiVA/STAN, UNIDO CIP, WB Enterprise Surveys, EU CRM mapping, METI | All are proxies; none measures plant-level capability |
| 7 | `04.md` Physical-economy data | Stream note | Yes | Identical copy inside ZIP | Dataset matrix: USGS/Comtrade/UNIDO/ICIO/GEM/Pink Sheet/WIPO/I-TIP with licenses+limitations | Aggregates lag years; mirror-trade issues |
| 8 | `05.md` Industry decomposition | Stream note | Yes | Identical copy inside ZIP | BOM/BOP source landscape; LCI; customs; ontologies; standards; Q=B·P and g=A⁻¹f formalizations | Proprietary granularity wall; ecoinvent licensed |
| 9 | `06.md` Foundational recursion | Stream note | Yes | Identical copy inside ZIP | Machine-tool/bearing/metrology/lithography concentration; RDI concept; downstream unlocks | Market-share percentages are commercial MODEL/ESTIMATE |
| 10 | `07.md` Qualification & know-how | Stream note | Yes | Identical copy inside ZIP | Qualification latency 6–24 mo (aero), 6–18 mo (fab materials); Nadcap 6–12 mo; learning curves 71–85%; MRL framework | Planning ranges, not universal laws; tacit-knowledge transfer unquantified |
| 11 | `08.md` Shock case studies | Stream note | Yes | Identical copy inside ZIP | Ten shock cases with onset→propagation→substitution→recovery timing; vulnerability index form | Tier-N inventory opacity; thresholds unmodeled |
| 12 | `09.md` Technology substitution | Stream note | Yes | Identical copy inside ZIP | Eight substitution cases w/ tradeoffs & new dependencies; no universal rare-earth-free path | Several alternatives pilot-stage; secondary bottlenecks concentrated |
| 13 | `10.md` Existing systems | Stream note | Yes | Identical copy inside ZIP | Copy/Learn/Integrate/Avoid matrix across Altana/Interos/Kinaxis/anyLogistix/Harvard/NREL/NIST/AWS | Vendor claims; macro-micro gap confirmed as unsolved |
| 14 | `11.md` Humanoid benchmark | Stream note | Yes | Identical copy inside ZIP | Addverb Elixis-W baseline; component ranges 20–40 actuators / 30–50 reducers / 20–30 motors; energy claim | Energy claim corrected by synthesis package (see conflicts) |
| 15 | `12.md` Missing-dimensions challenge | Stream note | Yes | Identical copy inside ZIP | Ten-lens critique: refining bottleneck fallacy, yield non-linearity, bullwhip, grid lead time, O(N²) integration caveat | Critique only; no parameters |
| 16 | `FORGE WORLD Due-Diligence Dossier.pdf` | 41-page due-diligence review | Yes, full text extracted | Canonical | Strongest reformulation ("buildability compiler"); epistemic hierarchy (MEASURED…CONFLICTED); layered model; lazy recursion triggers; effective-capacity identity; project state machine; shock classes; V0 scope table; Unitree G1/H1, Figure 03 spec-derived bounding arithmetic; India program statuses (Semicon 2.0 ₹1,27,500 cr approved 15 Jul 2026; REPM scheme 6,000 t/y bids; ACC PLI 40/50 GWh awarded); prohibited shortcuts list | Company-reported figures (Figure yields etc.) are REPORTED not MEASURED; some PIB-sourced items need primary re-verification |
| 17 | `forge_verified_dataset_observations.md` | Direct browser observations (Atlas, OECD ICIO) | Yes | Identical copy inside ZIP | Verifies access/method descriptions of Atlas + ICIO pages | Observations ≠ validation of underlying data |
| 18 | `indiabuild_verified_observations.md` | Direct browser observations | Yes | Identical copy inside ZIP | Dated dashboard metrics incl. six maturity counts summing to 3,874 | Site-reported; internal ratio inconsistency preserved |
| 19 | `indiabuild_how_it_works_verified.md` | Direct browser observations | Yes | Identical copy inside ZIP | Four-layer ontology; six statuses; builder ladder; claim-vs-assessment | Conceptual only; no capacity data |
| 20 | `swarajya_verified_observations.md` | Direct browser observations | Yes | Identical copy inside ZIP | Exact article claims incl. 54,000 t NdFeB magnet imports 2024–25; Apr/Oct 2025 Chinese controls; recycling incentive | FACTS-about-the-article, not validation; normative framing noted |
| 21 | `forge_world_capability_schema.json` | Draft schema v0.1 | Yes | Canonical | Node types, edge types, dynamic variables, evidence labels, minimum provenance fields | Superseded where the dossier's stronger epistemic set applies |
| 22 | `forge_world_humanoid_benchmark.csv` | Machine-readable benchmark envelope | Yes | Canonical | Parameter rows low/base/high with units, status, derivation caveats | Explicitly MODEL/ESTIMATE rows must never be presented as measured |
| 23 | `forge_world_source_map.csv` | Source map S001–S042 | Yes | Canonical | Domain/source/access/license/limitation per source | Epistemic caution column is binding on us |
| 24 | `forge_world_wide_research.csv` | Raw stream index (CSV) | Yes | Format duplicate of JSON | Per-stream one-paragraph summaries + note URLs | Signed CDN URLs are ephemeral; do not rely on them |
| 25 | `forge_world_wide_research.json` | Raw stream index (JSON) | Yes | Canonical of the two | Same records, machine-readable | Same caveat |
| 26 | `FORGE_WORLD_Wide_Research_Appendices.zip` | Archive of above | Yes (unpacked, hashed) | Container duplicate except item 6 | Provenance container | Keep archived |

## Contradictions and tensions noticed (preserved, not silently resolved)

| ID | Conflict | Disposition for FORGE |
|----|----------|----------------------|
| C1 | Note 11 states "1–2 GWh/day" fleet energy; Package §13.3 shows duty-cycle semantics unresolved and corrects to 4–32 GWh/day conditional range | Package correction adopted; energy figures remain MODEL/ESTIMATE with unresolved peak-vs-average semantics encoded explicitly |
| C2 | IndiaBUILD homepage maturity counts (sum 3,874) vs displayed percentages; "catalogue of 10,000" vs "7,047 mapped" | Store counts and percentages as separate site-reported fields; preserve catalogue-vs-mapped distinction |
| C3 | Note 11 marks India-1M feasibility "DERIVED INTERPRETATION (feasible given localization)"; Package §13.5 says public evidence insufficient under strict bipedal/integrated definitions | Treat as CONFLICTED; solver must derive its own verdict from model state, never import either prose conclusion |
| C4 | Note 02 assigns "High" confidence to China 90–95% processing share from media; verified-observations file demands primary corroboration | Evidence discipline wins: class REPORTED (media), flag for primary upgrade |
| C5 | Note 06 presents FANUC ~38.4% CNC revenue share as FACT(High); its own inventory says commercial aggregations vary | Downgrade to REPORTED/ESTIMATED (commercial aggregation) wherever used |
| C6 | Benchmark CSV actuator base = 36/robot while low=20/high=40 asymmetric around base | Preserve asymmetry; it reflects architecture variance, do not symmetrize |

## Claims requiring reverification before they may drive decisions

1. Humanoid architecture ranges (actuators/reducers/motors per unit) — MODEL/ESTIMATE only.
2. Qualification latency ranges (6–24 mo AS9100; 6–18 mo fab materials; Nadcap 6–12 mo).
3. NCMM ₹16,300 cr public + ₹18,000 cr expected private; ₹7,280 cr REPM scheme @6,000 t/y;
   54,000 t magnet imports FY2024–25 — verify against PIB/Ministry of Mines primaries.
4. Semicon approvals: 12 projects (1 silicon fab ~50k wsp, 1 compound-semi fab, 1 micro-LED/GaN,
   9 ATMP/OSAT) as of Jul 2026; Semicon 2.0 ₹1,27,500 cr — verify against PIB PRIDs cited in dossier.
5. ACC PLI: 50 GWh target, 40 GWh awarded to four beneficiaries by early 2026.
6. Figure 03 ramp/yield disclosures (>80% EOL first-pass yield, battery line 99.3%, 9,000+
   actuators/10+ SKUs, 1/day→1/hr <120 days) — company REPORTED.
7. Unitree G1 (35 kg, 23–43 joint motors, crossed-roller bearings), H1 (47 kg, 864 Wh),
   Figure 03 (61 kg, 2.3 kWh) specs — manufacturer-published REPORTED.
8. IEA >16-year average discovery-to-first-production for mines; wafer-fab cycle ~12 weeks.
9. Learning-curve progress ratios 71–85%; aerospace supplier defect leakage 30–50%.
10. USGS/Comtrade-style aggregates used anywhere in packs must be re-derived from fetched
    primary data or remain labeled ESTIMATED priors.

## Licensing/rights flags

- IndiaBUILD: no public bulk/API endpoint found during inspection; reuse terms unconfirmed →
  reference-layer only (URLs, dates, hashes), no mirroring. See DATA_RIGHTS.md.
- GEM CC BY (dossier says 4.0; source map says BY-NC for some trackers — conflict preserved;
  treat as attribution-required, non-commercial until verified per tracker).
- ecoinvent: paid; enrichment boundary only, never bundled.
- OSM ODbL share-alike implications; Atlas citation requirements; EPO OPS fair-use caps.
- Standards bodies (ISO/ASTM/IEEE): paywalled; cite identifiers, never reproduce text.

## Verdict feeding Phase 1

The corpus is strong on problem framing, ontology, epistemics, and failure modes of prior
attempts. It is deliberately weak on decision-grade quantitative industrial data — and says so
repeatedly. The correct build consequence: the system's value must come from computation over
honestly-labeled sparse evidence (including UNKNOWN/CONFLICTED as first-class), with real
source-linked claims from this corpus as the seed evidence graph, plus live open-data adapters
(World Bank API verified reachable 2026-08-22) where licensing permits.
