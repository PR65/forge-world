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
