# FORGE India Product V1 reconstruction

## Outcome

FORGE India now presents the existing industrial atlas as a focused product workbench rather than a graph/database dashboard. The public surface has three modes only: **ANALYZE**, **BUILD**, and **DISCOVER**. The underlying registry, evidence, solver, and Run 1/Run 2 data remain intact.

## Product behavior

- **ANALYZE** accepts a product or simple manufacturing objective, resolves it conservatively, states the current India position in one sentence, and presents a bounded product-to-system-to-requirement decomposition.
- **WHY** opens contextually from systems, requirements, or bottlenecks. It explains status, industrial importance, prerequisites, principal difficulty, a possible first action, and keeps evidence collapsed by default.
- **BUILD** turns the selected product's real dependency and status data into a product-specific staged localization path. It distinguishes feasible local work, initial sourcing/imports, integration and qualification, subsystem localization, deeper capability development, and conditional redesign.
- **DISCOVER** houses the 12-domain atlas, domain browsing, related capabilities, upstream dependencies, downstream uses, and unlocks. The domain rail no longer distracts from ANALYZE.
- Exact and strong matches can open directly. Nearest-family results require explicit user confirmation. Unresolved queries do not silently open an unrelated record.

## Architecture

- Added a deterministic objective parser/resolver and `/api/india/resolve` composition endpoint.
- The resolver returns the already-composed `BuildabilityViewModel`, preventing a second search from drifting to another product.
- Extended the presentation adapter so public surfaces receive normalized human labels, epistemic state, typed requirements, bottleneck reasons, localization actions, and graph relationships without exposing raw IDs or source-pack internals.
- Added a dedicated `product-v1` React layer with bounded decomposition, contextual WHY drawer, BUILD workflow, DISCOVER surface, responsive workbench shell, deep-link state, and stale-request cancellation.

## Historical UX adaptation

From the old industrial debugger, the reconstruction keeps disciplined objective state, a bounded semantic dependency plane, selection-to-WHY interaction, explicit UNKNOWN handling, and protection against stale async results. It deliberately retires permanent side rails, five unfinished modes, clocks, metric strips, and raw graph inspection.

## Product validation

The frozen lightweight probe contains 100 queries across 20 industrial groups:

- useful resolution: **87/100**
- safe resolution: **100/100**
- classifications: **16 exact, 19 strong, 52 nearest-family, 13 unresolved**
- analyzable results: **35**
- analyzable results with useful decomposition: **100%**
- bounded bottlenecks: **100%**
- localization path present: **100%**
- clean public payload: **100%**
- latency: **56.22 ms median**, **222.95 ms p95**, **2139.34 ms maximum**

Fifteen browser journeys covered CNC, MRI, freeze dryers, transformers, textile looms, pumps, industrial robots, heat exchangers, agriculture, packaging, medical equipment, chillers, ceramics, rail, and coating equipment. Twelve produced full analyses and three correctly stopped at explicit nearest-family confirmation. ANALYZE, WHY, BUILD, DISCOVER, deep-link behavior, and a 390x844 responsive viewport were exercised; no horizontal overflow was observed.

## Known weak query classes

The frozen probe leaves 13 precise subtypes unresolved: fruit pulping machines, grain color sorters, ultrasound scanners, plasma etching equipment, reflow ovens, fiber-optic transceivers, hydraulic breakers, ore sorting machines, automotive stamping presses, wheel-alignment machines, fuel-injection systems, shipboard desalination plants, and satellite reaction wheels. This is an honest product boundary: the UI offers families only when similarity is defensible and otherwise asks the user to search again.

The atlas remains a first-order industrial map. Many states are intentionally UNKNOWN; it does not prove suppliers, factory capacity, cost, schedule, or procurement feasibility. Some generated canonical names still exist below the presentation layer, while public labels remove common variant suffixes and implementation language.

## Screenshots

- [Before: Run 2 dashboard](images/forge-india-product-v1-before-1672x941.png)
- [After: ANALYZE](images/forge-india-product-v1-after-1672x941.png)
- [BUILD](images/forge-india-product-v1-build-1672x941.png)
- [DISCOVER](images/forge-india-product-v1-discover-1672x941.png)

## Automated checks

- Python: **254 passed, 1 skipped**
- Frontend: TypeScript and Vite production build passed
- Probe artifact: `docs/FORGE_INDIA_PRODUCT_V1_PROBES.json`

