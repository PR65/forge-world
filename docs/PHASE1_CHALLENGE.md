# PHASE 1 — INDEPENDENT CHALLENGE OF THE SUPPLIED THESIS

Before freezing architecture, FORGE's build agent attacks the corpus and the mission brief.
Findings below changed design decisions; they are recorded in `DECISIONS.md` where so.

## 1. What is wrong or overclaimed in the supplied material

1. **"Capability graph" framing seduces toward catalog-building.** The dossier itself admits
   almost every feature exists somewhere (Altana, Interos, Kinaxis, Atlas, NREL). If V0 ships
   as a pretty graph over macro data, it is exactly the "impressive-looking interface on
   fabricated industrial data" the brief forbids. Countermeasure: the solver and its proof
   graph are the product; every visualization must be a view of computed state.
2. **The corpus has no decision-grade quantitative industrial dataset inside it.** It contains
   claims about capacities, but almost none that survive the evidence discipline it preaches
   (e.g., India's humanoid-grade reducer capacity is genuinely UNKNOWN). A system that hides
   this with synthetic numbers fails the mission. Countermeasure: UNKNOWN-first design;
   feasibility verdicts must be able to come out NOT ADJUDICABLE and the UI must make that
   a first-class, useful outcome.
3. **The "one million humanoids" arithmetic envelope is architecture-dependent guesswork**
   (20–40 actuators etc.). Using base=36M actuators/year as "the requirement" would fake
   precision. Countermeasure: multiple named reference architectures anchored to published
   products (Unitree G1-class, industrial 50–60 kg class, rare-earth-reduced variant), each a
   separate ProductVariant with its own BOM; ranges propagate, never collapse silently.
4. **LP/MILP worship is a trap when data is interval-valued.** A time-indexed MILP over
   UNKNOWN-capacity nodes produces authoritative-looking nonsense. Countermeasure: layered
   pipeline — typed explosion → per-node capacity envelopes (intervals) → allocation LP only
   over nodes with admissible numeric bounds → fixed-charge MILP for portfolio choice →
   explicit sensitivity/VOI on every parameter that was an assumption.
5. **"Domestic value addition" is not well-defined without an accounting convention.** Imported
   embedded inputs (magnets inside imported motors) break naive percentage math. The corpus
   flags this ("Does localization arithmetic preserve imported embedded inputs?") but no
   formula is given. Countermeasure: define DVA recursively over the recipe tree with an
   explicit boundary rule (see MODEL_CONTRACT §DVA) and test it.
6. **Shock multipliers in the corpus ("copper doubles ⇒ costs double") violate its own rule.**
   Shocks must edit constraints (eligibility, capacity, routes, prices of exogenous pools) and
   let recomputation propagate. Countermeasure: shocks are declarative constraint edits; the
   same solve() runs again; nothing downstream is hand-multiplied.
7. **Dates in the corpus are internally consistent (Aug 2026 "now") but unverifiable from here;
   some PIB/corporate items may drift.** Countermeasure: three clocks; every claim carries
   evidence date; packs pin evidence snapshots with access dates.

## 2. Hidden assumptions in the brief worth surfacing

- That a Python/JS web system can run a credible LP at interactive speed — true at our scale
  (hundreds of variables) if we keep the formulation tight (HiGHS via scipy).
- That "India" is the right default geography resolution — mostly yes (dossier argues state/
  site detail only where evidence exists); we keep country-level with a few evidenced sites.
- That LLMs are available at runtime — they are NOT guaranteed. Therefore FORGE Intelligence
  (NL parsing etc.) is designed as an optional adapter with a deterministic structured-objective
  path always available. No runtime behavior depends on an LLM.

## 3. What already exists elsewhere (and therefore must not be rebuilt badly)

Trade/product-space analytics (Atlas/OEC), MRIO (OECD/Eora), mineral trackers (USGS/IEA/GEM),
enterprise supply-chain twins (Kinaxis/anyLogistix/Pelico), risk networks (Altana/Interos).
FORGE V0 integrates ideas, copies epistemic discipline (Altana observed-vs-inferred), and
competes only on the inverse transformation problem + auditable proof.

## 4. Abstractions that fail across industries if copied naively

- A universal "capacity" scalar (fails: wafer starts ≠ packaged output ≠ qualified parts).
- One BOM per product (fails: G1 vs Figure 03 differ hugely).
- Graph centrality as option value (fails: ignores capacity/time/maturity/feasibility).
- Percentage-based resilience scores (the brief explicitly bans single sovereignty scores).
- Treating qualification as a boolean (it gates specific customer/spec pairs).

## 5. Where the ontology in the brief needs surgery

- The brief lists ~45 entity types. For V0 several collapse without loss:
  TechnologyRight/IP/License → one `TechnologyRight`; Skill/KnowledgeAsset → `Skill`;
  Tool/Fixture fold into `Equipment` with a class field; Inventory stays but as segment-level
  state, not node soup. We keep ~30 first-class types (implemented in `forge/model.py`).
- Edge vocabulary: implement the typed set from the brief plus `derived_from` for provenance;
  forbid bare `depends_on` in code (a lint test enforces allowed edge kinds).

## 6. What would make this system shallow (kill list)

Scripted outputs; hardcoded "reducers are missing"; invented factories; percentages without
denominators; UNKNOWN→0 conversions; one confidence number; LLM-authored coefficients;
announced-project capacity counted as operating; exports read as capability; patents read as
production. Each item has a corresponding automated test or runtime invariant.
