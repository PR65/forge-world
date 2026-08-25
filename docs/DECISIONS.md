# FORGE WORLD — DECISIONS LEDGER

Append-only. Each decision: context, choice, consequences, alternatives rejected.

## D1 — Stack: Python core + FastAPI + React/TS console
- **Choice:** Python 3.12 for the computational core (numpy/scipy present; HiGHS LP/MILP via
  scipy.optimize); FastAPI server; Vite+React+TypeScript frontend with canvas-based custom
  visualization.
- **Why:** numeric engine quality (units, LP) dominates this product; JS has no comparable
  solver story. React gives the interaction depth the product brief demands.
- **Rejected:** pure-JS full-stack (weak LP); Jupyter-only (not a product); heavy graph DB
  (unnecessary at V0 scale).

## D2 — Evidence seed = corpus claims, live adapters for open data
- **Choice:** seed evidence graph from the supplied research corpus (each claim → its cited
  source URL, access date 2026-08-22, epistemic class per corpus discipline). Implement one
  live adapter (World Bank API, open terms) to demonstrate the ingest→normalize→promote
  pipeline against a real endpoint.
- **Why:** honest grounding without fabricating data; corpus explicitly licenses nothing for
  redistribution of third-party content beyond what we already hold as observations.
- **Rejected:** scraping IndiaBUILD (no public API found; reuse terms unconfirmed).

## D3 — UNKNOWN-first solver semantics
- **Choice:** parameters may be `UNKNOWN`. If an UNKNOWN is decision-critical and no estimation
  method is invoked, result is NOT_ADJUDICABLE naming the unknowns. Analysts may attach
  declared interval assumptions (ASSUMPTION class) which yield CONDITIONAL results + VOI.
- **Consequence:** flagship demo can honestly say "infeasible under model" or "cannot
  adjudicate" — and that is a feature.

## D4 — Reference architectures over canonical BOM
- **Choice:** three named humanoid variants: `HV-1` G1-class compact (23 joint motors,
  published Unitree spec anchor), `HV-2` industrial 50–60 kg class (30–40 powered joints,
  dexterous hands), `HV-3` rare-earth-reduced variant derived from HV-2 through a validated
  substitution contract (SynRM/ferrite-assisted actuation with power-electronics tradeoff).
- **Consequence:** component arithmetic differs per variant; ranges never averaged away.

## D5 — Solver pipeline layering
Explosion (typed) → capacity envelopes (intervals) → yearly allocation LP → portfolio MILP →
explanations. No global CGE, no agent-based model, no discrete-event simulation in V0.

## D6 — DVA convention fixed recursively (MODEL_CONTRACT C18)
Imported content valued at landed cost at boundary arrival; embedded imported content inside
imported assemblies remains imported. Tested with a two-level case.

## D7 — Ontology consolidation
~45 proposed entity types implemented as ~30 (TechnologyRight absorbs IP/License;
Equipment absorbs Machine/Tool/Fixture with class field; Skill absorbs KnowledgeAsset).
Rationale: V0 computation never needed finer split; pack schema keeps extension points.

## D8 — Frontend visual identity: "the forge instrument"
Dark iron surfaces, molten-orange accent reserved for binding constraints and heat (scarcity),
cold steel blues for capacity, amber for assumption/estimated, violet for UNKNOWN. Typography:
mono numerals, humanist sans labels. Custom canvas renderings (layered dependency strata,
capacity timelines, gantt-like transformation plan, Pareto frontier). No card walls, no tab
graveyard; single inspector panel pattern for proof lineage everywhere.

## D9 — Time grid: years 2026–2035, quarterly refinement only around deadlines
Annual resolution matches evidence resolution (C13); quarterly used only where qualification
windows demand it.

## D10 — Currency: USD for cross-pack comparability; INR converted where sources are INR
(₹ figures from corpus carry their own evidence records; conversions use explicit ASSUMPTION
rates recorded in scenario, never silent).

## D11 — Testing: contract tests per invariant (C1–C22), benchmark fixtures per pack,
backtests (2011 Tōhoku-style single-supplier outage; Red Sea reroute as corridor cost shock)
run through the same public API as the UI.

## D12 — The LLM adapter is optional and sandboxed
Structured objective parsing has a deterministic grammar path; an optional LLM adapter maps
free text → candidate structured objective which must pass validation before entering solve.
No LLM in the numerical path (C20). This session builds and tests the deterministic path.

## D13 — Current operating scope: FORGE India first, global dependency layer retained
- **Context:** FORGE WORLD's universal country/region/humanity ambition is directionally valid,
  but attempting to populate every country's full industrial reality now would spread evidence,
  compute, entity resolution, facility/capacity research, and product effort too thinly. The
  project needs one geography deep enough to become genuinely useful and publicly releasable.
- **Choice:** India becomes the current canonical target geography for buildability questions.
  The default product question is **"Can India build this?"** FORGE must decompose the complete
  objective, then classify every decision-relevant requirement against India's evidenced
  capability, scale, specification, qualification, capacity and dependency state. The complete
  operating vision is recorded in `docs/FORGE_INDIA_OPERATING_VISION.md`.
- **Global-data consequence:** no useful global research is discarded. Foreign organizations,
  facilities, technologies, materials, minerals, machine tools, semiconductor ecosystems,
  logistics routes, export controls, sanctions, commodity exposures and supplier alternatives
  remain modeled whenever they affect India's sourcing, localization, substitution or
  resilience. The near-term model is therefore a **deep India core + selective global
  dependency/sourcing/risk layer**, not an isolated India model.
- **Product consequence:** presentation remains objective-first and progressively disclosed.
  Normal users see buildability, domestic/partial/import/missing/UNKNOWN composition,
  bottlenecks, localization paths and major dependencies; experts can drill through complete
  system/component/process/machine/material/metrology/qualification/evidence chains.
- **Localization consequence:** a missing domestic requirement does not imply "import it".
  FORGE must consider direct localization, source diversification, licensing/technology
  transfer, material/component/process substitution, adjacent Indian capabilities, full
  architecture redesign, temporary import while localizing, and indigenous alternative routes;
  alternatives are graph rewrites followed by re-solve.
- **Coverage consequence:** IndiaBUILD is treated as a minimum public breadth benchmark, not as
  canonical truth or as FORGE's ontology. FORGE should account for that capability universe and
  materially exceed it through deeper engineering decomposition, evidence, capacity,
  qualification, geography, alternatives, shocks and execution reasoning.
- **Retained North Star:** FORGE WORLD remains the long-term product identity and eventual global
  ambition. Country-by-country global buildability expansion is deferred until FORGE India is
  strong enough to serve as the proven country-model architecture.
- **Rejected:** deleting global research; replacing FORGE with a flat India capability wiki;
  reducing the solver to an IndiaBUILD clone; or continuing broad country-by-country data
  expansion before the India-first system is mature.

## D14 — Hard-recall refinement: full industrial transformation action space
- **Context:** the first India operating draft correctly preserved build/import/license/
  substitute/redesign logic but under-specified several important FORGE WORLD ideas, especially
  JV/acquisition, explicit supplier-development/qualification pathways, finance/policy enablers,
  recursive machine-builds-machine closure, project state/ramp, purity/yield, inventory buffers,
  competing demand, and value-of-information prioritization.
- **Choice:** `docs/FORGE_INDIA_OPERATING_VISION_CANONICAL.md` is the current canonical execution
  vision for the India-first phase. It preserves the prior India draft for history and does not
  modify `docs/FORGE_WORLD_NORTH_STAR.md`.
- **Transformation consequence:** missing capability is solved over a full action space including
  BUY/IMPORT, diversify/stockpile, QUALIFY, supplier development, LICENSE/technology transfer,
  JV/co-development, ACQUIRE, greenfield/brownfield build, seed-equipment bootstrap, FUND/
  procurement/offtake/policy enablement, SUBSTITUTE/RECYCLE, REDESIGN, indigenous R&D and
  targeted RESEARCH. Each path changes the industrial graph and must be re-solved.
- **Industrial-depth consequence:** usable output must distinguish grade/purity, uptime, yield,
  specification acceptance, qualification and allocatable capacity; projects progress through
  funded/construction/commission/ramp/qualification states; machine/tool dependencies can recurse
  into bootstrap sets; shared resources face competing demand; shocks propagate through buffers,
  qualification delays and recovery paths.
- **Optimization consequence:** FORGE may compare fastest, cheapest, most sovereign, most
  resilient, most qualification-certain and highest-option-value paths rather than pretending
  one plan is universally best.
- **Non-goal:** these additions must remain decision-relevant. FORGE does not become a generic
  bureaucracy, ESG scorecard, finance simulator or global encyclopedia; finance, policy and
  legal/ethical sourcing rules enter only when they materially change physical buildability,
  eligibility, timing or resilience.
