# FORGE India V1 — Run 1 Report

Date: 2026-08-25  
Branch: `codex/forge-india-buildability-v1`  
Depth profile: `V1_BROAD`

## Outcome

Run 1 turns the existing correctness kernel and HOMI research substrate into a broad public industrial atlas. A user can search or browse twelve domains, open a product or capability, understand its first-order purpose and requirements, see a broad India status with epistemic basis, inspect gaps and import notes, follow a making/localization ladder, and navigate upstream, downstream, and related records.

This is a breadth layer, not a supplier directory or a capacity census. It preserves the existing FORGE evidence and mathematical architecture while clearly separating broad V1 assumptions from evidenced claims.

## Universe and taxonomy

- **12,253 direct products/capabilities/processes/materials/equipment records**
- **2,400 explicit `UNKNOWN` reference bridges** used to close graph references
- **14,653 total searchable graph nodes**
- **39,818 unique search aliases**
- Direct kinds: 4,209 products; 4,886 equipment; 1,270 capabilities; 1,142 materials; 746 processes

| Domain | Direct records |
|---|---:|
| 01 Aerospace & Space | 928 |
| 02 Defense & Strategic Manufacturing | 928 |
| 03 Energy & Nuclear | 928 |
| 04 Electronics, Semiconductors & Computing | 928 |
| 05 Machines, Robotics & Industrial Automation | 900 |
| 06 Materials, Metals, Chemicals & Process Industries | 1,080 |
| 07 Medical, Scientific, Pharma & Biotech Equipment | 1,080 |
| 08 Food, Agriculture & Biological Production Systems | 1,080 |
| 09 Transport & Mobility | 1,080 |
| 10 Infrastructure, Construction & Heavy Equipment | 1,080 |
| 11 Consumer, Textile, Packaging & General Manufacturing | 1,080 |
| 12 Foundational Industrial Capabilities | 1,080 |

The 12 domain-owned sets contain 12,172 records; another 81 shared source foundations are direct reusable records.

## Connected graph

Direct records expose **371,461 dependency links**, plus 448,837 upstream, 201,322 downstream/unlock, and 40,904 related-record links. All references resolve. Product pages present a bounded, useful dependency slice while the API retains the broader graph for navigation.

Making ladders use the existing action vocabulary (`IMPORT`, `DEVELOP`, `LICENSE`, `JV`, `BUILD`, `SUBSTITUTE`, `REDESIGN`, `R&D`) and are generated structurally rather than as thousands of handwritten essays.

## India status layer

| Broad status | Direct records |
|---|---:|
| STRONG | 115 |
| AVAILABLE | 660 |
| PARTIAL | 5,958 |
| SCALE_LIMITED | 3,336 |
| IMPORT_DEPENDENT | 1,909 |
| MISSING | 116 |
| UNKNOWN | 101 |
| CONFLICTED | 58 |

Epistemic basis is explicit: 8,055 direct statuses are `ASSUMPTION`, 720 are `MODELLED`, 58 are `CONFLICTED`, and 3,420 are `UNKNOWN`. The status labels are therefore discovery priors, not proof of qualified supply, capacity, yield, or sovereignty. The 2,400 reference bridges are also `UNKNOWN` and are excluded from the direct distribution above.

## IndiaBUILD accounting

IndiaBUILD is used as a breadth and discovery benchmark, not cloned. Repository-verified public observations preserve **7,047 mapped capabilities** and a distinct **10,000 catalogue claim**. Because no public bulk row-level list was available, count parity is `NOT_COMPARABLE` and no fabricated full matching rate is reported.

The bounded ten-name reconciliation is: `MATCHED=2`, `FORGE_DEEPER_EQUIVALENT=4`, `UNRESOLVED=4`, `MISSING=0`, `INACCESSIBLE_OR_UNVERIFIABLE=0`. This sample is accounting evidence only, not a universe-wide coverage estimate.

## Benchmarks

The deterministic benchmark ran the 15 named founder queries and 12 unseen product samples selected after atlas construction with seed `20260825`. **27/27 passed** search, explanation/use, bounded dependency depth, India status/basis, gaps/imports, five-step-or-better ladder, and navigation checks.

Named coverage includes MRI, 5-axis CNC, freeze dryer, food dehydrator, industrial heat pump, electrolyzer, industrial motor, industrial robot, transformer, packaging machine, textile machine, centrifugal pump, agricultural drone, satellite, and semiconductor equipment. Random cases span aerospace, defense, electronics, energy, food/cold-chain, materials, transport, foundational capability, and general manufacturing records.

## Product and API

The old form/card default has been replaced by **FORGE INDIA — WHAT CAN INDIA BUILD?**: universal search, twelve-domain browse, discovery examples, readable record pages, grouped requirements, status and epistemic basis, gaps/imports, making ladder, dependency ribbon, unlocks, and related navigation. The layout is responsive and intentionally reads as an industrial field atlas rather than an admin dashboard, marketplace, or research paper.

The public read API adds summary, domains, bounded search/filtering, record detail, bounded graph traversal, and deterministic discovery endpoints. The combined catalog is cached once per process; cold construction is about 6–7 seconds and warm benchmark searches are approximately 0.3–30 ms.

## Validation

- Existing and new Python tests pass, with the pre-existing skip retained.
- All existing scenario packs validate.
- Atlas integrity, aliases, enums, graph references, broad product depth, ladders, API bounds, search filters, deterministic discovery, and benchmark reproducibility pass.
- Frontend production build passes.
- The separate `C:\GitHub\forge` repository was not touched.

## Remaining problems for Run 2

1. Validate high-value India statuses and gap claims with evidence; many Run 1 records are intentionally assumption- or unknown-based.
2. Improve taxonomy precision, alias reconciliation, variant grouping, and human editorial quality where deterministic expansion produced awkward or near-duplicate names.
3. Replace generic reference bridges with canonical reusable primitives and consolidate repeated directional links.
4. Add capacity, qualification, facility, supplier, yield, utilization, sovereignty, cost, and temporal depth only where decision-sensitive.
5. Deepen DESIGN and EXECUTE workflows; Run 1 primarily advances browse, ANALYZE orientation, DISCOVER, and LEARN.
6. Perform fuller IndiaBUILD row reconciliation if a licensed/public bulk source becomes available.

## Founder-level maturity assessment

- Simplified FORGE India V1: **about 38% before → about 75% after**. Breadth, connectedness, search, readable pages, and first-order making guidance now exist; evidence validation and execution depth remain.
- Full FORGE WORLD North Star: **47% before → about 54% after**. Run 1 materially improves universal registry breadth, reuse, discovery, and public usability, but does not materially close the hardest capacity, time, optimization, DESIGN, EXECUTE, or live-world-state gaps.

These are founder-level product judgments, not computed scientific metrics.

## Reproducible artifacts

- `data/india_v1/` — deterministic twelve-domain taxonomy and benchmark configuration
- `forge/india_v1/` — schema, generators, combined catalog, graph indexes, integrity rules
- `research/india_v1/benchmark_results.json` — named and unseen-query results
- `research/india_v1/indiabuild_accounting.json` — bounded machine-readable accounting
- `scripts/forge_india_v1_benchmark.py` — deterministic benchmark runner

