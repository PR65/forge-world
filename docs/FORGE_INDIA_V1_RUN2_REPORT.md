# FORGE India V1 — Run 2 Report

Run 2 turns the Run 1 breadth atlas into a launch-ready public V1 without adding supplier-directory, factory-capacity, procurement, detailed-specification, or finance scope.

## Shipped

- Reworked search around exact-match priority, industrial synonym families, acronyms, conservative typo tolerance, domain/category relevance, related-family fallback, and default family-level deduplication. Search responses now expose match type and matched fields.
- Consolidated 12,253 direct records into 1,316 navigable families while preserving every direct record and optional variant drill-down. Exact canonical-name collisions fell from 16 groups/32 rows to zero.
- Corrected 180 visibly wrong family/profile combinations across clinical equipment, laboratory incubators, and cold-chain systems.
- Added status- and dependency-aware six-stage making ladders. All 12,253 direct ladders are complete and ordered; they span 12 action sequences and 35 semantic signatures.
- Downgraded 231 unsupported `ASSUMPTION`-backed `STRONG`/`MISSING` labels to `UNKNOWN`, retaining the prior label in the status basis. No evidence claim was invented.
- Closed reverse related links so all 14,662 nodes are navigable. The graph has 1,962,040 unique resolved edges, zero unresolved edges, zero self-references, and zero dead ends.
- Rebuilt the public interaction layer around URL-backed universal search, domain browsing, deep-linked record pages, progressive dependency disclosure, explicit epistemic labels, resilient loading/error/empty states, and mobile accessibility.
- Added bounded API DTOs, a bootstrap endpoint, single-flight catalog construction, production SPA deep-link routes, and an explicit public documentation surface.

## Atlas accounting

The atlas remains **14,662 nodes: 12,253 direct records plus 2,409 honest `UNKNOWN` reference bridges**. Direct domain distribution is:

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
| 10 Infrastructure, Construction & Heavy Industrial Equipment | 1,080 |
| 11 Consumer, Textile, Packaging & General Manufacturing | 1,080 |
| 12 Foundational Industrial Capabilities | 1,080 |

There are also 81 direct shared-source records. Across the full graph, status counts are `AVAILABLE=660`, `PARTIAL=5,958`, `SCALE_LIMITED=3,336`, `IMPORT_DEPENDENT=1,909`, `UNKNOWN=2,741`, and `CONFLICTED=58`.

## Quality battery

The 92-query battery was frozen before fixes: 20 founder probes plus 72 unseen ordinary/obscure probes across all 12 domains.

- Relevant result: **72/92 → 91/92 (98.9%)**.
- Any result: **91/92 → 92/92**.
- Expected-domain top result: **61/92 → 79/92 (85.9%)**; all 20 founder probes rank the expected domain first.
- Search misses: **20 → 1**; duplicate-result flags: **88 → 0**; generic-decomposition flags: **31 → 0**; awkward-name flags: **30 → 16**.
- Unseen relevant-result rate: **71/72 (98.6%)**. The separate 20-query user abuse set resolves every query to an exact, phrase, all-token, or explicitly related nearest-family page.

These are deterministic lexical/product-quality checks, not evidence validation of every returned India status. The artifacts retain all remaining failure flags rather than converting them into a synthetic pass score.

## IndiaBUILD accounting

The current official top level observed on 2026-08-26 reports 7,049 mapped capabilities: 3,876 assessed and 3,173 unassessed. A verified public row-level export remains unavailable, so row parity is explicitly `NOT_COMPARABLE`; FORGE does not manufacture a parity percentage. The preserved ten-name reconciliation remains `MATCHED=2`, `FORGE_DEEPER_EQUIVALENT=4`, `UNRESOLVED=4`, `MISSING=0`, `INACCESSIBLE_OR_UNVERIFIABLE=0`.

## Frontend, performance, and validation

- Desktop QA: 1707×932. Mobile QA: 390×844. No horizontal overflow; key text contrast is 4.92–5.74:1; keyboard focus, modified-click navigation, history, direct URLs, 404, retry, and progressive disclosure were verified.
- Production build: 20 modules; 182.46 kB JavaScript and 66.18 kB CSS before gzip.
- Cold first search/catalog construction is approximately 15–20 seconds on the validation machine; warm search is approximately 21 ms median and 60 ms maximum across the final smoke set. Record and bootstrap responses are bounded.
- Full Python suite: **243 tests collected; 242 passed and 1 skipped**. All registry, scenario-pack, graph, API, benchmark, ladder, and epistemic integrity checks pass.
- `C:\GitHub\forge` was not touched; its unrelated pre-existing worktree changes remain unchanged.

## Known limitations and release assessment

No remaining defect found in the final gate blocks a V1 launch. The bounded post-launch checklist is: reduce one-time cold construction further; editorially improve the remaining awkward variant labels and shallow reference bridges; selectively validate high-connectivity statuses/gaps; and perform row-level IndiaBUILD reconciliation only if a lawful public export becomes available. Capacity, qualification, supplier/facility, detailed engineering, and execution depth remain later FORGE layers, not hidden V1 claims.

- Simplified FORGE India V1 maturity: **about 75% → about 95% (launch-ready V1)**.
- Full FORGE WORLD North Star maturity: **about 54% → about 57%**. Run 2 materially improves public discovery, epistemic communication, connectedness, and first-order actionability, but does not claim to close the deeper DESIGN, EXECUTE, capacity, time, or live-world-state gaps.

## Reproducible artifacts

- `data/india_v1/run2_search_battery.json`
- `research/india_v1/run2_baseline_metrics.json`
- `research/india_v1/run2_final_metrics.json`
- `research/india_v1/run2_baseline_vs_final.json`
- `research/india_v1/run2_abuse_probe_results.json`
- `research/india_v1/run2_quality_accounting.json`
- `scripts/forge_india_v1_run2_audit.py`
- `scripts/forge_india_v1_run2_quality_accounting.py`
- `docs/FORGE_INDIA_V1_KNOWN_LIMITATIONS.md`
