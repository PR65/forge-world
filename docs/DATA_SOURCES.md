# DATA SOURCES

Provenance-first inventory of every external source used by FORGE WORLD V0.

## A. Supplied research corpus (seed evidence)

| Source | Used for | Access | License posture |
|---|---|---|---|
| IndiaBUILD public pages (indiabuild.wiki) | capability-ontology priors; maturity vocabulary; gap framing | Public web, observed 2026-08-22; **no public bulk/API endpoint found during inspection** | Referenced by URL only; no mirroring; reuse terms unconfirmed |
| Swarajya critical-minerals reporting | NdFeB import dependence (~54 kt FY24-25), China processing share, NCMM/recycling programme claims | Public articles | MEDIA-REPORTED class; flagged for primary corroboration; referenced not mirrored |
| Unitree G1/H1 product pages | HV-1 architecture anchor (23–43 joint motors, crossed-roller bearings); battery anchor 864 Wh | Public product pages | Manufacturer REPORTED specs; referenced |
| Figure 03 page + production-ramp disclosure | HV-2 energy/mass anchor (2.3 kWh, 61 kg); yield/ramp state-variable precedent (>80% EOL FPY company-reported) | Public pages | Company REPORTED; caveats preserved verbatim in evidence records |
| PIB releases (REPM scheme, Semicon 2.0, ACC PLI) | India project pipeline states: REPM 6,000 t/y @ bids stage; 12 semiconductor approvals; ACC PLI 40/50 GWh awarded | Public government releases | Public domain (GoI); REPORTED with dates + PRID URLs where cited in corpus |
| IEA critical-minerals analysis | processing concentration direction; mine lead-time context; substitution tradeoffs | Public report pages | CC BY 4.0 per IEA data products; referenced |
| McKinsey humanoid supply-chain article | component-envelope ESTIMATE ranges (20–40 actuators etc.) | Public article | Consultancy estimates — MODEL/ESTIMATE class only |
| DoD MRL deskbook / BCG aerospace supply-chain report | qualification-latency planning ranges (6–24 mo) | Public framework / commercial summary | Framework referenced; ranges are REPORTED planning ranges |
| IEEE Spectrum EV-motor article | SynRM/ferrite substitution tradeoff contract | Public article | Technical journalism; REPORTED |
| FORGE Wide Research corpus stream notes 06/11 | CNC/market concentration aggregates (FANUC/Siemens dominance; BLDC market value) | Supplied files | Internal corpus; commercial-aggregation ESTIMATES flagged |

## B. Live adapters

| Adapter | Endpoint | Terms | Status |
|---|---|---|---|
| World Bank Open Data v2 | `https://api.worldbank.org/v2/country/{ISO}/indicator/...` | CC BY 4.0 (World Bank Open Data) | **Working** (`GET /api/adapter/worldbank`, `forge adapter --country IND`). Fetches MVA/population/GDP series; wraps each observation as MEASURED EvidenceRecord with payload hash. No bulk mirroring. |

## C. Deliberately NOT integrated (and why)

| Source | Reason |
|---|---|
| ecoinvent LCI | Paid developer license required for software integration; enrichment-boundary only |
| Commercial shipment/multi-tier networks (Altana/Panjiva/etc.) | Contract restrictions; no redistribution rights |
| ISO/ASTM/IEEE standards text | Paywalled; identifiers cited, text never reproduced |
| IndiaBUILD bulk scrape | No public API found during inspection; redistribution terms unconfirmed |
| UN Comtrade bulk | Key registration + rate limits; adapter slot reserved (interface ready) — no fabricated trade numbers inserted meanwhile |

## D. Estimation methods recorded in-pack

1. `seg_india_structures` — robot casting-set capacity allocated as <0.01% of national
   automotive-grade casting base (order-of-magnitude prior). Class: ESTIMATED.
2. `seg_india_alu` — national primary-aluminium scale prior; robot demand negligible share.
   Class: ESTIMATED.
3. `dp_ndfeb_global` (250 kt/yr pool, 20% contestable) and `dp_soc_advanced` — order-of-
   magnitude pools from public industry reporting ranges. Class: ASSUMPTION basis noted.
4. Recipe cycle times / machine-hour coefficients — engineering planning assumptions
   (ASSUMPTION), surfaced in DVA assumption lists and VOI panels.
5. Currency conversions (INR→USD for scheme capex) use explicit scenario FX; never silent.

Every record above is also represented structurally in the packs' `sources:` and `evidence:`
sections with access dates and confidence dimensions — this file is the human map, the packs
are the machine truth.
