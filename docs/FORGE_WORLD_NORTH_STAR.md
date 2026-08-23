# FORGE WORLD — NORTH STAR / SYSTEM CONSTITUTION

> **Status:** Canonical project source of truth
>
> **Purpose:** Preserve the full ambition, architecture, epistemic standards, product intent, and execution philosophy of FORGE WORLD so that future work by humans or agents does not drift into a narrower product than the one originally intended.
>
> **Rule:** If implementation convenience, a local feature request, or an agent's interpretation conflicts with this document, this document wins unless it is deliberately amended.

---

# 0. The shortest possible definition

**FORGE WORLD is a universal evidence-backed industrial intelligence, synthesis, design, execution, and learning system for physically meaningful futures.**

A user specifies something they want to exist — from a table, to 100 CNC machining centers, to one million humanoid robots, to 200 GW of nuclear generation, to 10,000 satellites per year, to a fleet of reusable launch vehicles — and FORGE works backward from that objective to determine:

1. whether the target is physically and industrially achievable;
2. what architectures could satisfy it;
3. what products, subsystems, components, materials, processes, machines, tools, facilities, capabilities, infrastructure, people, suppliers, energy, logistics, finance, policy, and time are required;
4. which of those capabilities exist today, where they exist, who controls them, and at what usable capacity and maturity;
5. what is missing, uncertain, fragile, concentrated, or blocked;
6. why the target can or cannot be achieved under the current model;
7. how the product or industrial architecture could be redesigned to improve buildability;
8. what should be built, bought, licensed, qualified, partnered for, substituted, trained, stockpiled, researched, or invented;
9. what sequence of actions closes the capability gap fastest, cheapest, most resiliently, or with the highest strategic option value;
10. what the user should actually do next if they decide to proceed.

Every consequential conclusion must be traceable to evidence, a transparent derivation, a declared model assumption, a scenario choice, or an explicit UNKNOWN.

FORGE must never become a confident LLM that guesses industrial feasibility.

---

# 1. The core question FORGE exists to answer

FORGE exists to answer a general class of question:

> **“What would it physically take to make this future real?”**

Examples include:

- Can humanity manufacture **1,000,000 humanoid robots per year by 2030**?
- Can India manufacture **1,000,000 humanoids/year with >=70% recursive domestic value addition and without Chinese permanent magnets**?
- Could Europe produce **5 million humanoids/year without Chinese rare-earth magnets**?
- Can India add **200 GW of nuclear generation capacity** by a target year?
- Can Africa manufacture **500 GW/year of solar equipment**?
- Can India manufacture **10,000 satellites/year**?
- What would it take for Earth to manufacture **100 reusable launch vehicles/year**?
- Can a company manufacture **100 CNC machining centers**?
- What would it take to manufacture **10,000 induction motors**?
- What would it take to manufacture **one high-quality table locally and economically**?
- What is the smallest set of investments required to remove a country's most dangerous industrial dependencies?
- Which industrial capabilities should be built now because they unlock the largest number of future industries?

The scale may range from:

`Earth -> continent -> country -> state/cluster -> company -> factory -> workshop`

The reasoning architecture should remain fundamentally the same.

---

# 2. FORGE is not a single-industry application

FORGE must not collapse into:

- a humanoid calculator;
- an India-only manufacturing dashboard;
- a static IndiaBUILD clone;
- a supply-chain visualization;
- a BOM explorer;
- a national industrial-policy dashboard;
- a procurement search engine;
- a generic LLM answering manufacturing questions;
- a spreadsheet with an optimization solver behind it;
- a collection of market reports;
- a company directory;
- a static database of industrial facts.

All of those may be useful layers, but none is the product.

The product is a **general engine for reasoning about the physical possibility, industrial architecture, transformation, and execution of manufactured futures.**

---

# 3. The five foundational questions

Every serious FORGE analysis should be able to answer these five questions.

## 3.1 CAN WE?

Can the stated objective be achieved under the modeled physical, industrial, temporal, economic, geopolitical, and policy constraints?

The answer class must be one of:

- `FEASIBLE`
- `CONDITIONALLY_FEASIBLE`
- `INFEASIBLE_UNDER_MODEL`
- `NOT_ADJUDICABLE`

The model must not force a binary yes/no when evidence is insufficient.

## 3.2 WHAT IS MISSING?

What exact capability, material, process, supplier, facility, machine, qualification, infrastructure, workforce, energy, logistics, policy, or evidence gap prevents closure?

FORGE must identify causal blockers, not generic risk factors.

## 3.3 HOW DO WE MAKE IT POSSIBLE?

What transformations can close the gap?

The core transformation vocabulary includes:

- BUILD
- BUY
- LICENSE
- JV / PARTNER
- ACQUIRE
- QUALIFY
- DEVELOP SUPPLIER
- R&D / INVENT
- REDESIGN
- SUBSTITUTE
- DIVERSIFY
- STOCKPILE
- RECYCLE
- TRAIN
- METROLOGY
- INFRASTRUCTURE
- POLICY
- RESEARCH

Each proposed transformation should carry, where evidence permits:

- cost;
- lead time;
- dependencies;
- capacity gained;
- quality/specification impact;
- qualification burden;
- maturity/risk;
- ownership/sovereignty implications;
- evidence;
- downside or new dependency created.

## 3.4 WHAT SHOULD WE INVESTIGATE NEXT?

FORGE must perform **value-of-information reasoning**.

If uncertainty prevents a decision, FORGE should rank which unknown is most worth resolving because it could materially change the answer.

This is not “show missing data.” It is:

> Which missing fact is decision-sensitive enough to justify further research, supplier contact, testing, site inspection, engineering analysis, or data purchase?

## 3.5 WHAT SHOULD WE BUILD NOW SO MANY FUTURES BECOME POSSIBLE?

FORGE must reason about **industrial option value**.

A capability should not be valued only for one target product. A high-quality forging, precision grinding, metrology, power electronics, vacuum processing, machine-tool, specialty-chemicals, or qualification capability may unlock many downstream industries.

FORGE should eventually answer questions such as:

- Which 20 capabilities unlock the largest number of strategic industries?
- Which investment has the highest cross-sector industrial option value?
- Which missing foundational capability is currently blocking the most downstream products?
- Which capability gap is almost closed and therefore cheapest to unlock?

---

# 4. The product modes

FORGE should expose the same industrial world through several complementary modes.

## 4.1 FORGE ANALYZE

**Question:** Can this physical future happen?

Typical outputs:

- target interpretation;
- reference architectures;
- recursive requirements;
- current world-state comparison;
- capacity and qualification analysis;
- bottlenecks;
- dependencies;
- uncertainty;
- shocks;
- alternatives;
- feasibility class;
- causal proof.

Example:

> Can humanity manufacture 1,000,000 humanoids per year by 2030?

FORGE should analyze the global production system, component demand, motors, reducers, bearings, electronics, magnets, materials, machine tools, supplier capacity, industrial ramp, energy, logistics, and critical unknowns — not merely final assembly.

## 4.2 FORGE DESIGN

**Question:** What should we build, given industrial reality?

FORGE should co-design the product architecture and the industrial system.

Example:

> Design a humanoid optimized for Indian manufacturability.

If the original architecture depends on scarce NdFeB magnets or precision reducers that dominate closure time, FORGE may explore different motor topologies, reducer architectures, material choices, controller requirements, mechanical layouts, or specifications.

Substitution must be modeled as a graph rewrite, not as a free choice.

Every redesign must expose new dependencies, performance changes, qualification burden, cost, lead time, and risk.

## 4.3 FORGE EXECUTE

**Question:** We have decided to make it. Help us actually do it.

This turns FORGE from strategic analysis into an execution copilot.

For a target such as “manufacture 100 CNC machining centers,” FORGE should progressively help produce:

- architecture selection;
- product requirements;
- complete BOM;
- process plan / BOP;
- component specifications;
- tolerance and quality requirements;
- make/buy decisions;
- supplier shortlists;
- sourcing geography;
- RFQ-ready specifications;
- supplier qualification criteria;
- tooling requirements;
- factory equipment requirements;
- metrology requirements;
- workforce and skills;
- prototype plan;
- quality plan;
- test and acceptance plan;
- procurement sequence;
- production-ramp plan;
- project schedule;
- critical path;
- risks and unresolved engineering decisions;
- recommended next actions for today/this week/this phase.

FORGE EXECUTE must guide intelligently without pretending that expert engineering judgment, testing, certification, or vendor validation can always be replaced by software.

## 4.4 FORGE DISCOVER

**Question:** What should we become good at?

This is the inverse of product decomposition.

Instead of target -> capability, FORGE evaluates capability -> futures unlocked.

Examples:

- What should India build next?
- Which foundational capability has the highest downstream unlock value?
- Which missing technology is blocking multiple sectors?
- Where does India possess most prerequisites but lack one decisive node?
- What is the best use of a fixed industrial-investment budget?

## 4.5 FORGE LEARN

**Question:** Teach me the industrial system while I work through it.

FORGE should support progressive drill-down from intuitive explanation to expert technical depth.

Example:

`ball screw -> backlash -> preload -> C3 vs C5 -> grinding process -> grinder -> metrology -> supplier capability -> machine that builds the grinder`

The system should be useful to an intelligent non-specialist without flattening technical complexity.

A user should be able to repeatedly ask:

- Why is this needed?
- Why this specification?
- Why not a cheaper substitute?
- What physical principle matters here?
- What happens if this tolerance is relaxed?
- What machine makes this?
- How is it measured?
- Who can supply it?
- Where is it made?
- Can we make the machine that makes it?

---

# 5. The universal FORGE reasoning loop

The general pipeline should look like:

```text
PHYSICAL OBJECTIVE
    ↓
OBJECTIVE INTERPRETATION
quantity / quality / geography / time / autonomy / cost / constraints
    ↓
REFERENCE ARCHITECTURES
credible ways to satisfy the objective
    ↓
PRODUCT DECOMPOSITION
systems -> assemblies -> components -> materials
    ↓
PROCESS DECOMPOSITION
manufacturing / chemistry / assembly / testing / qualification
    ↓
CAPABILITY DECOMPOSITION
machines / tooling / metrology / know-how / skills / facilities
    ↓
PHYSICAL INPUTS
materials / minerals / energy / water / land / logistics / infrastructure
    ↓
WORLD STATE
who can do it, where, how much, at what maturity, with what evidence
    ↓
FEASIBILITY
what target is physically/industrially achievable
    ↓
BOTTLENECKS
what actually prevents closure
    ↓
TRANSFORMATION SYNTHESIS
build / buy / license / JV / qualify / redesign / substitute / invent / etc.
    ↓
TIME + COST + RISK
what sequence makes the target real
    ↓
EXECUTION
what should be done next
```

---

# 6. Objective interpretation must precede analysis

FORGE should not blindly accept underspecified objectives.

For example:

> “India builds 200 GW of nuclear.”

FORGE should distinguish:

- installed capacity vs annual generation;
- additional capacity vs total fleet;
- target year;
- capacity factor;
- reactor families allowed;
- imported reactor technology allowed or not;
- imported fuel allowed or not;
- domestic-value requirement;
- strategic-autonomy requirement;
- financing assumptions;
- grid constraints;
- site constraints;
- safety/regulatory regime.

The system should infer defaults only when defensible and make them visible.

---

# 7. Reference architectures, not one frozen BOM

A serious target may have multiple viable architectures.

FORGE should generate, ingest, or compare credible alternatives.

For nuclear, for example:

- PHWR-heavy expansion;
- mixed PHWR/LWR strategy;
- large reactor + SMR mix;
- closed-fuel-cycle variants;
- alternative site/geography portfolios.

For humanoids:

- different actuator topologies;
- magnet vs non-magnet motor families;
- direct drive vs reducer-heavy architectures;
- different battery chemistries;
- different sensor/control stacks.

For CNCs:

- VMC vs HMC vs turning center;
- 3-axis vs 5-axis;
- different spindle/tooling interfaces;
- direct-drive vs geared/belt spindle;
- linear guide vs box-way architecture;
- different controller/servo stacks.

FORGE should optimize across architectures, not merely optimize within one architecture.

---

# 8. Product decomposition

FORGE must recursively represent physical products at useful resolution.

A generic hierarchy may include:

- objective;
- product family;
- reference architecture;
- system;
- subsystem;
- assembly;
- component;
- part;
- material;
- precursor;
- mineral/feedstock.

The recursion must be dynamic.

A table may need shallow decomposition.

A CNC may require deeper decomposition into:

- structure;
- spindle;
- bearings;
- motors;
- ball screws;
- linear guides;
- servo drives;
- controller;
- ATC;
- lubrication;
- coolant;
- metrology;
- tooling;
- electrical cabinet;
- safety;
- calibration.

A nuclear fleet requires much deeper system decomposition across reactor island, turbine island, civil works, fuel cycle, grid, construction, qualification, and regulatory infrastructure.

---

# 9. Process decomposition / BOP

A BOM is insufficient.

FORGE must represent how things are produced.

Examples:

- casting;
- forging;
- heat treatment;
- machining;
- grinding;
- scraping;
- additive manufacturing;
- stamping;
- rolling;
- extrusion;
- coating;
- deposition;
- lithography;
- chemical synthesis;
- separation;
- refining;
- alloying;
- assembly;
- welding;
- brazing;
- inspection;
- calibration;
- burn-in;
- environmental testing;
- qualification.

Processes must carry:

- inputs;
- outputs;
- yields;
- scrap;
- cycle times;
- quality/specification envelope;
- required equipment;
- required tooling;
- metrology;
- energy/water/utilities;
- workforce/know-how;
- qualification status;
- maturity;
- location/facility context where relevant.

---

# 10. Machines-build-machines recursion

A defining FORGE capability is recursive industrial reasoning.

Example:

`CNC -> ball screw -> precision grinding -> ball-screw grinder -> machine-tool components -> bearings -> steel -> heat treatment -> metrology`

Or:

`nuclear pressure vessel -> large forging -> press / furnace / machining -> heavy machine tools -> precision components -> foundational materials`

FORGE should be able to ask:

> Can we make the machine that makes the component?

This recursion must be **lazy and strategic**, not infinite.

FORGE should recurse deeper when a node is:

- a bottleneck;
- strategically sensitive;
- highly concentrated geographically;
- high-cost;
- long-lead;
- high-uncertainty;
- critical to sovereignty;
- difficult to substitute;
- likely to determine feasibility.

Otherwise, branches can be collapsed.

This is **lazy strategic recursion**.

---

# 11. Capability is a vector, not a label

One of the most important research conclusions is:

> **Factory capacity != industrial capability.**

Capability must be represented as a multi-dimensional state.

Relevant dimensions include:

- product/specification envelope;
- design capability;
- IP / licensing status;
- process knowledge;
- tacit know-how;
- equipment availability;
- tooling;
- metrology;
- material/precursor access;
- workforce;
- qualification;
- quality consistency;
- yield;
- utilization;
- maturity;
- supplier readiness;
- current throughput;
- scalable throughput;
- competitiveness;
- ownership/sovereignty;
- resilience;
- time to ramp.

A country can possess design knowledge but no production line.

A facility can exist but be unqualified.

A process can be qualified but uneconomic.

A plant can have nameplate capacity but low effective capacity.

A capability can exist only under foreign license.

FORGE must preserve these distinctions.

---

# 12. Effective capacity

FORGE must distinguish nominal capacity from usable capacity.

A core conceptual form is:

`effective capacity = nameplate × availability × utilization × yield × qualification fraction`

Other factors may be required by domain.

The model must account for:

- downtime;
- maintenance;
- line balancing;
- bottleneck equipment;
- learning curves;
- scrap;
- yield ramp;
- supplier qualification;
- workforce ramp;
- customer acceptance;
- shared capacity / competing demand;
- product-mix effects.

---

# 13. The canonical Capability + Builder Registry

This is a foundational requirement.

IndiaBUILD-inspired knowledge should not live as disconnected research notes. FORGE needs a canonical registry with stable identity across sectors and objectives.

## 13.1 Capability registry

Every capability should have a stable identity and be reusable across analyses.

Example:

`ultra_precision_grinding`

may matter to:

- CNCs;
- harmonic reducers;
- bearings;
- aerospace;
- turbines;
- machine tools;
- robotics;
- defense.

If FORGE learns this capability once, the knowledge should propagate everywhere.

## 13.2 Builder / organization registry

Organizations should connect to:

- facilities;
- products;
- processes;
- capabilities;
- projects;
- maturity;
- ownership;
- suppliers;
- customers where public/usable;
- certifications;
- patents/licenses where relevant;
- capacity;
- evidence.

## 13.3 Facility registry

Facilities should carry:

- location;
- owner/operator;
- equipment;
- product/process scope;
- capacity;
- quality/specification envelope;
- qualification;
- ramp/maturity;
- utilities;
- logistics;
- evidence;
- operational status.

## 13.4 IndiaBUILD as baseline inspiration

The research corpus explicitly studied IndiaBUILD's useful primitives:

- sectors;
- capabilities;
- foundational capabilities;
- builders;
- builder maturity;
- capability maturity;
- dependency trees;
- capability gaps;
- claim vs evidence-based assessment.

FORGE should at minimum support these classes of knowledge and extend them substantially.

Important: the repository contains research and extracted understanding of IndiaBUILD, but FORGE must **not assume it already contains a perfectly complete, current mirror of every IndiaBUILD record**. A systematic ingestion/reconciliation process should eventually be used where legally and technically appropriate.

IndiaBUILD is a baseline/reference layer, not the ceiling.

FORGE must add quantitative physical reasoning, capacity, process, facility, geography, cost, time, uncertainty, shocks, substitution, execution, and synthesis.

---

# 14. Companies, suppliers, and sourcing

FORGE should eventually be able to answer:

- Who makes this component?
- Which companies can meet this specification?
- At which facilities?
- In which countries?
- At what approximate capacity?
- What is their maturity/qualification status?
- What inputs do they depend on?
- Who supplies them?
- What alternatives exist?
- What is the concentration risk?
- What evidence supports the claim?

For execution mode, FORGE should progress toward:

- supplier discovery;
- shortlist generation;
- make/buy analysis;
- RFQ preparation;
- specification packaging;
- qualification criteria;
- lead-time comparison;
- country-of-origin exposure;
- dependency analysis;
- sourcing alternatives.

A supplier directory alone is insufficient. Supplier relationships must connect to physical requirements and capability.

---

# 15. Geography is first-class

FORGE must be geospatial, not merely technological.

It should know where relevant entities are located:

- factories;
- mines;
- refineries;
- processing plants;
- ports;
- rail corridors;
- industrial clusters;
- warehouses;
- power plants;
- grids;
- water resources;
- research institutions;
- training centers;
- suppliers;
- customer clusters;
- strategic chokepoints.

The system should answer:

- Where is this made?
- Where is the critical input mined?
- Where is it refined?
- Where is the midstream process concentrated?
- Which ports/corridors connect the chain?
- Which cluster is best suited to manufacture the target?
- Which geographic node controls the architecture?

---

# 16. Minerals and material chains

A critical research conclusion is:

> **In-ground reserve != usable industrial supply.**

FORGE must distinguish:

`resource/reserve -> mining -> beneficiation -> separation -> refining -> purification -> precursor -> alloy/chemical -> component-grade material -> qualified production`

For rare-earth magnets, for example:

`humanoid -> actuator -> motor -> NdFeB magnet -> alloy/powder -> Nd/Pr oxide -> separation/refining -> mineral feedstock -> mine -> geography`

FORGE should identify where the real chokepoint lies, which may be midstream rather than mining.

The same logic applies to:

- battery materials;
- semiconductor-grade chemicals;
- nuclear fuel;
- aerospace alloys;
- specialty steels;
- catalysts;
- electronic-grade gases;
- optical materials.

---

# 17. Energy, water, land, infrastructure, and utilities

Industrial capability is constrained by infrastructure.

FORGE should model, when material to the objective:

- electricity quantity and quality;
- grid connection;
- firm power;
- fuel;
- water;
- process gases;
- waste handling;
- land;
- industrial zoning;
- transport;
- ports;
- storage;
- telecommunications;
- data centers / compute where relevant.

A facility that physically exists but cannot obtain required utilities is not usable capability.

---

# 18. Workforce, tacit knowledge, and qualification

Factories do not operate themselves.

FORGE should represent:

- engineers;
- operators;
- machinists;
- welders;
- metrology technicians;
- quality staff;
- process specialists;
- maintenance staff;
- certification bodies;
- customer qualification;
- regulatory qualification;
- training lead times;
- tacit knowledge transfer.

Some critical variables are inherently difficult to observe publicly. Those must remain uncertain rather than being filled with precise-looking numbers.

---

# 19. Industrial time is endogenous

Industrial systems cannot teleport into existence when the solver requests capacity.

FORGE must model physical sequences such as:

`decision -> financing -> permitting -> equipment procurement -> construction -> commissioning -> process qualification -> yield ramp -> customer qualification -> mature production`

Different assets have different clocks:

- mine;
- refinery;
- chemical plant;
- fab;
- forging facility;
- machine-tool line;
- supplier qualification;
- workforce training;
- reactor construction;
- grid connection.

## 19.1 The three clocks

FORGE must preserve three distinct clocks:

### Physical clock
When something can physically exist or operate.

### Evidence clock
What is known, and when it became known.

### Decision clock
When a commitment must be made to hit the target.

---

# 20. Demand competition

A target does not have exclusive access to the industrial world.

FORGE should model competing demand for:

- materials;
- skilled labor;
- machine tools;
- fabs;
- forgings;
- shipping;
- energy;
- capital;
- construction capacity;
- specialty chemicals;
- qualified suppliers.

A physically sufficient global capacity may still be unavailable to the target because it is already committed elsewhere.

---

# 21. Politics, geopolitics, regulation, and institutional risk

Industrial systems exist inside political reality.

FORGE should eventually model:

- wars;
- sanctions;
- export controls;
- trade restrictions;
- tariffs;
- embargoes;
- border closure;
- maritime disruption;
- shipping insurance constraints;
- diplomatic deterioration;
- nationalization/expropriation risk;
- capital controls;
- currency crises;
- financing shocks;
- policy reversal;
- subsidy withdrawal;
- regulatory change;
- permitting delay;
- labor unrest;
- civil instability;
- corruption/institutional friction;
- election/regime-policy changes where relevant.

These should propagate through the physical graph.

FORGE should prefer causal statements such as:

> “If export licensing from country X is interrupted for 18 months, these components lose supply; inventory lasts approximately N weeks under the stated assumption; these downstream factories become constrained; this alternative supplier requires qualification time Y.”

Not:

> “Country X has high geopolitical risk.”

---

# 22. Shocks, inventories, queues, and recovery

Shocks should propagate through:

- inventories;
- work-in-progress;
- transportation;
- supplier qualification;
- queues;
- replacement lead times;
- substitution;
- rationing;
- recovery.

Useful shock phases include:

1. onset;
2. inventory drawdown;
3. rationing/reallocation;
4. substitution/alternate sourcing;
5. capacity response;
6. recovery;
7. permanent structural change if applicable.

Examples:

- remove China from supply;
- remove one major forging supplier;
- cut uranium imports 50%;
- shut a port;
- lose a semiconductor fab;
- impose export controls on a material;
- raise financing rates;
- restrict a technology license.

FORGE must re-solve the industrial world, not merely change a risk score.

---

# 23. Substitution and redesign

Substitution must be a graph rewrite.

Replacing one technology may create new requirements elsewhere.

Examples:

- rare-earth motors -> induction/synchronous reluctance;
- NMC -> LFP / sodium-ion;
- imported reducer -> different actuator topology;
- high-spec material -> relaxed specification with performance tradeoff.

Every substitution should carry:

- performance impact;
- new BOM/process dependencies;
- cost change;
- mass/volume change where relevant;
- energy impact;
- new equipment;
- qualification burden;
- time to adoption;
- evidence;
- uncertainty.

---

# 24. Product–industrial-system co-design

A major FORGE differentiator is simultaneous design of product and industrial architecture.

The question is not only:

> Can the current design be manufactured?

It is also:

> What design becomes easiest, fastest, cheapest, or most sovereign to manufacture using the capabilities available or realistically buildable?

FORGE should search across product architecture and industrial-system transformations together.

---

# 25. Reverse buildability

FORGE should answer the inverse question:

> Given the actual industrial system today, what is the maximum target we can sustain?

Examples:

- maximum humanoids/year;
- maximum nuclear GW/year;
- maximum satellites/year;
- maximum CNCs/year;
- maximum output without Chinese inputs;
- maximum output at >=70% recursive domestic value addition.

It should also answer:

> What single intervention increases this ceiling most?

---

# 26. Closure frontier / Pareto alternatives

There may be multiple ways to close an industrial gap.

FORGE should expose alternatives across dimensions such as:

- cost;
- time;
- domestic value addition;
- resilience;
- strategic autonomy;
- technical risk;
- execution risk;
- import dependence;
- option value.

The user should be able to understand tradeoffs rather than receiving one opaque recommendation.

---

# 27. Industrial option value

FORGE should eventually quantify the value of capabilities that unlock many objectives.

Example:

A heavy-forging capability created for nuclear may also support:

- turbines;
- petrochemical pressure vessels;
- naval systems;
- defense;
- heavy machine tools;
- energy equipment.

A precision-grinding or metrology capability created for CNCs may support:

- bearings;
- reducers;
- robotics;
- aerospace;
- semiconductor equipment;
- machine tools.

The canonical capability registry is a prerequisite for meaningful cross-objective option value.

---

# 28. Autonomous evidence hunting

FORGE should not merely consume a static database.

When a decision-sensitive unknown appears, the system should be able to initiate targeted research.

Example:

`harmonic reducer global qualified capacity = UNKNOWN`

Potential research loop:

`unknown -> identify decision-sensitive claim -> search primary sources -> filings -> factory announcements -> trade data -> official records -> technical papers -> supplier disclosures -> triangulate -> update confidence -> re-run`

If evidence remains insufficient, UNKNOWN remains UNKNOWN.

The research loop should be optimized for **decision relevance**, not maximum document collection.

---

# 29. Evidence hierarchy and provenance

Every consequential claim should preserve provenance.

A preferred source hierarchy is:

1. direct verified primary observations / machine-readable primary data;
2. authoritative government/regulatory/standards datasets;
3. official company filings and audited disclosures;
4. permits, certifications, tenders, customs/trade records, technical standards;
5. peer-reviewed or high-quality technical literature;
6. reputable industry databases/research;
7. credible secondary reporting;
8. company marketing / interviews / promotional claims;
9. social/discovery signals;
10. unsourced claims.

Secondary sources are useful for discovery but should not silently become hard model parameters.

The existing research corpus established a similar discipline and explicitly treated editorial sources such as Swarajya as discovery/framing that should be traced back to primary evidence where possible.

---

# 30. Epistemic classes

FORGE must never flatten certainty.

Every important observation/parameter should carry an epistemic class such as:

- MEASURED
- REPORTED
- DERIVED
- ESTIMATED
- MODELLED
- ASSUMPTION
- SCENARIO
- UNKNOWN
- CONFLICTED

Equivalent source-specific labels may be mapped into this canonical set.

Unknown is a valid result.

Conflicting evidence should remain visible rather than being averaged away without explanation.

---

# 31. Proof graph / industrial debugger

FORGE should behave like a compiler/debugger for industrial reality.

Example output:

```text
BUILD FAILED

Target:
1,000,000 humanoids/year by 2030

Primary blockers:
1. precision reducers
2. motor manufacturing
3. magnet dependency
4. precision bearings
5. metrology throughput
6. supplier qualification

Critical path:
reducer machine tools
 -> grinding capability
 -> metrology
 -> supplier qualification
 -> actuator production

Decision-sensitive unknowns: 7
```

The user should then be able to click:

- WHY?
- SHOW EVIDENCE
- SHOW DEPENDENCY CHAIN
- FIX IT
- REDESIGN
- REMOVE COUNTRY X
- ASSUME PROJECT Y SUCCEEDS
- WHAT SHOULD I RESEARCH NEXT?

Every consequential result should have a causal proof path through the model.

---

# 32. Dynamic resolution

FORGE should not use the same modeling depth for all objectives.

The system needs a resolution policy.

A table may require:

- wood;
- fasteners;
- cutting;
- joinery;
- finishing;
- labor;
- supplier;
- cost.

A CNC may require detailed spindle, bearing, ballscrew, guideway, motor, drive, controller, thermal, metrology, casting, grinding, and qualification analysis.

A nuclear program requires architecture, fuel cycle, heavy engineering, grid, construction, regulation, finance, workforce, materials, and site pipelines.

FORGE should recurse where answer sensitivity is high and collapse where it is not.

---

# 33. FORGE LEARN: bite-sized expert guidance

A user may want to execute something they do not yet deeply understand.

FORGE should be capable of teaching without oversimplifying.

For example:

`ball screw`

Beginner explanation:

> Converts rotary motion into precise low-friction linear motion.

Then progressive questions:

- Why not ordinary threaded rod?
- What is backlash?
- What does preload do?
- What is C3 vs C5?
- Rolled vs ground?
- What manufacturing process produces C3?
- What grinder is needed?
- What metrology certifies it?
- Which firms can supply it?
- Can that grinder be manufactured domestically?

This is a core product behavior, not a documentation afterthought.

---

# 34. FORGE EXECUTE: end-to-end operationalization

When the user decides to build, FORGE should progressively transform the industrial model into executable work.

For a real manufacturing project, useful artifacts may include:

- product requirements document;
- engineering specification tree;
- BOM;
- BOP/process route;
- make/buy matrix;
- supplier shortlist;
- supplier qualification matrix;
- RFQ package;
- prototype build plan;
- test plan;
- inspection plan;
- quality plan;
- tooling list;
- machine/equipment list;
- facility layout assumptions;
- capex plan;
- staffing plan;
- procurement schedule;
- project critical path;
- qualification schedule;
- production-ramp plan;
- risk register tied to causal dependencies;
- decision log;
- next-actions list.

The system should not produce meaningless bureaucracy. Every generated artifact should exist because it materially helps execution.

---

# 35. Benchmarking

FORGE should identify real-world benchmarks and understand **why** they worked.

For a major industrial objective, benchmark dimensions may include:

- production/build rate;
- standardization;
- supplier ecosystem;
- construction time;
- capital model;
- workforce;
- regulatory environment;
- local-content strategy;
- technology architecture;
- facility scale;
- qualification systems;
- bottleneck resolution;
- logistics;
- learning curves.

FORGE must not copy a historical benchmark as proof that another geography can reproduce it.

It should extract causal conditions and compare them to the target context.

---

# 36. Nuclear example — intended depth

Question:

> Can India add 200 GW of nuclear generation by a target year?

FORGE should decompose across:

## Reactor architecture

- PHWR / LWR / SMR / breeder / other architecture choices;
- reactor vessels / calandria / pressure tubes;
- pumps;
- steam generators;
- heat exchangers;
- valves;
- piping;
- control systems;
- safety systems;
- containment;
- instrumentation;
- qualification.

## Turbine island

- turbine forgings;
- generators;
- condensers;
- feedwater systems;
- bearings;
- electrical systems;
- heavy machining.

## Civil / construction

- nuclear-grade concrete;
- structural steel;
- heavy lifting;
- specialized welding;
- modularization;
- NDT;
- construction workforce;
- site pipeline.

## Fuel cycle

- uranium mining;
- milling;
- conversion;
- enrichment where applicable;
- fuel fabrication;
- zirconium/cladding;
- heavy water where relevant;
- spent-fuel handling;
- reprocessing where relevant;
- waste systems.

## Industrial recursion

Example:

`pressure vessel -> nuclear-grade large forging -> ingot/steel chemistry -> vacuum degassing -> forging press -> heat treatment -> machining -> welding -> NDT -> supplier qualification`

The model should compare required throughput against actual qualified capability and identify bottlenecks.

---

# 37. Humanoid example — intended depth

Question:

> Can humanity manufacture one million humanoids/year by 2030?

FORGE should not stop at final assembly.

It should resolve:

- humanoid definition / architecture;
- actuators per robot;
- motors;
- reducers;
- bearings;
- encoders;
- controllers;
- power electronics;
- batteries;
- sensors;
- computing;
- structures;
- wiring;
- thermal systems;
- final assembly;
- test;
- software-dependent physical requirements where relevant;
- materials;
- machine tools;
- metrology;
- supplier capacity;
- geographic concentration;
- industrial ramp.

If the target implies tens of millions of actuators/reducers/motors, FORGE should surface that explicitly.

The model must compare global capacity, geography, competing demand, projects, qualification, and time — not assume scale-up is automatic.

---

# 38. CNC example — intended depth

Question:

> We want to manufacture 100 CNC machining centers.

FORGE should guide architecture choice and decompose into:

- bed / column / saddle / table;
- castings;
- stress relief;
- rough/finish machining;
- scraping/grinding;
- spindle cartridge;
- spindle motor;
- spindle bearings;
- drawbar;
- cooling;
- ball screws;
- linear guides;
- couplings;
- servos;
- drives;
- encoders;
- CNC controller;
- PLC / I/O;
- ATC / magazine;
- tool holders;
- lubrication;
- hydraulics;
- pneumatics;
- coolant;
- chip evacuation;
- electrical cabinet;
- safety;
- probes/scales;
- calibration;
- acceptance testing.

Then it should recurse into critical nodes such as ball screws, spindle bearings, castings, grinding, heat treatment, control systems, and metrology.

FORGE should be able to answer not only “what part?” but “why this specification?” and “what industrial capability is required to make it?”

---

# 39. Company and industrial-memory behavior

FORGE's industrial knowledge should accumulate.

If FORGE discovers that company A operates facility B with process capability C at specification D, that knowledge should become reusable in future objectives.

The system should not repeatedly rediscover the same world from scratch.

A canonical entity system should reconcile:

- company aliases;
- facility identities;
- capability identities;
- product identities;
- process identities;
- material identities;
- location identities;
- source/evidence versions.

---

# 40. The industrial knowledge engine

The long-term data pipeline should resemble:

```text
sources / APIs / filings / datasets / websites / papers / reports
    ↓
raw immutable snapshots
    ↓
hash + timestamp + licensing/access metadata
    ↓
parsing / normalization
    ↓
entity resolution
    ↓
EvidenceRecords
    ↓
canonical capability / builder / facility / material / process registry
    ↓
versioned industrial world state
    ↓
solver / synthesis / research / execution
    ↓
proof graph / interactive product
```

Trade data is useful evidence, but:

> trade flow != capability.

Patent ownership is evidence, but:

> patent != qualified production capability.

Factory announcement is evidence, but:

> announced project != operating qualified capacity.

Mineral reserve is evidence, but:

> reserve != usable industrial material.

---

# 41. IndiaBUILD, Swarajya, and the existing research corpus

The repository's `research/` directory preserves the foundational due-diligence work, including:

- the twelve research streams;
- FORGE WORLD Due-Diligence Dossier;
- FORGE WORLD Wide Research Package;
- capability/schema/source material;
- IndiaBUILD analysis;
- Swarajya industrial-intelligence analysis;
- global capability analogues;
- physical-economy datasets;
- industry decomposition;
- foundational industrial recursion;
- supplier qualification;
- shocks;
- substitution;
- existing-system review;
- one-million-humanoid benchmark;
- missing-dimensions challenge.

This corpus is not historical clutter. It is part of the intellectual foundation of FORGE.

Future agents should use it as source material, while applying source hierarchy and verifying claims before turning them into hard model parameters.

The research corpus currently influences architecture more deeply than it is operationally ingested. A major future objective is to turn this research foundation into live industrial memory.

---

# 42. Core anti-bullshit rules

These are non-negotiable.

## 42.1 UNKNOWN stays UNKNOWN

Do not invent capacity, price, yield, supplier maturity, or project success simply to make the model run.

## 42.2 Eligibility is not supply

A country being theoretically import-eligible does not imply enough physical foreign supply exists.

## 42.3 Factory existence is not capability

A building or line does not prove qualified, scalable, high-yield production.

## 42.4 Nameplate is not effective capacity

Use usable qualified output, not promotional nameplate numbers where possible.

## 42.5 Trade is not production capability

Exports/imports are signals, not direct proof of local industrial capability.

## 42.6 Project announcement is not production

Model project state and ramp time explicitly.

## 42.7 Reserve is not usable supply

Model the entire processing chain.

## 42.8 Substitution is not free

Every substitution creates new physical requirements.

## 42.9 Precision-looking numbers require evidence or explicit assumptions

Never create fake confidence through excessive numeric specificity.

## 42.10 “Infeasible” must mean what the model can actually prove

Do not use strong verdict labels when the model only failed to find a solution or lacks evidence.

## 42.11 The LLM does not get to override physics

Language-model plausibility is never a substitute for the industrial model.

---

# 43. Model contracts

The system should preserve several hard conceptual invariants.

- Requirement propagation must be dimensionally correct and order-invariant.
- Shared upstream dependencies must not be double-counted.
- Physical quantities from incompatible unit families must not be summed into meaningless scalars.
- Recursive domestic value addition must measure aggregate delivered value, not per-item localization.
- Supply and eligibility must remain distinct.
- Qualification must causally gate usable capacity.
- Projects and transformation actions must obey lead time.
- Scenario clones must preserve all relevant state.
- Shocks must alter the solved world, not only presentation state.
- Reproducibility hashes must cover actual solver-relevant state.
- Consequential outputs should be traceable through proof/evidence lineage.
- Transformations must not mutate baseline worlds accidentally.

---

# 44. Current implementation state — V0.1

V0.1 is a **correctness foundation**, not the final FORGE product.

The merged V0.1 work established or substantially improved:

- typed requirement FlowGraph;
- shared-input linearity;
- recursive DVA semantics;
- unit-safe shortfall representation;
- foreign-supply epistemic handling;
- temporal causality;
- scenario-state correctness;
- substitution immutability;
- project/qualification handling;
- shock consistency;
- proof/evidence graph wiring;
- run-state reproducibility;
- strengthened mathematical oracles;
- CI and validation discipline.

The current code should be treated as the **computational kernel** on which the much larger industrial knowledge and synthesis system will be built.

Do not mistake the existence of modules named “frontier,” “VOI,” “planner,” “option value,” or similar for complete realization of the long-term vision. Some are currently prototypes/foundations and require deeper implementation as the industrial world model becomes richer.

---

# 45. Major capabilities still to build deeply

The largest missing work includes:

- canonical cross-sector capability registry;
- builder/company/facility registry;
- large-scale evidence ingestion;
- entity resolution;
- real industrial capacity datasets;
- suppliers and qualified supply relationships;
- equipment-fleet modeling;
- tooling and metrology depth;
- mineral/midstream chains;
- geospatial industrial graph;
- logistics networks;
- utilities/infrastructure;
- inventories;
- workforce and tacit-knowledge modeling;
- richer process/routing models;
- economic/capex models;
- serious transformation optimization;
- cross-objective industrial option value;
- machine-builds-machine recursion backed by evidence;
- product–industrial-system co-design;
- autonomous research/evidence hunting;
- richer uncertainty/robust optimization;
- production-grade persistence/caching/jobs;
- end-to-end EXECUTE workflows;
- exceptional interactive product UX;
- empirical/historical validation.

---

# 46. Product experience / “12/10” standard

FORGE should not feel like a conventional dashboard.

A user should feel like they are entering and interrogating an industrial world.

The product should make causal structure legible.

A user should be able to:

- enter a physical objective;
- inspect alternative architectures;
- navigate the requirement graph;
- drill from product to material to machine to supplier to mine;
- inspect geography;
- inspect evidence;
- inspect uncertainty;
- change assumptions;
- remove countries/suppliers;
- inject shocks;
- fund projects;
- add transformations;
- redesign architecture;
- compare scenarios;
- inspect critical path;
- ask WHY;
- ask FIX IT;
- ask WHAT SHOULD I DO NEXT;
- ask WHAT SHOULD I LEARN;
- ask WHAT SHOULD I RESEARCH;
- export execution artifacts.

Visual polish matters, but **technical legibility and truthfulness matter more than decorative complexity**.

The interface should make a deep industrial model understandable without making it look simplistic.

---

# 47. A recommended mental model: compiler + debugger + world model

FORGE can be thought of as three things at once:

## 47.1 Compiler

Compile a desired physical future into the required industrial system.

## 47.2 Debugger

Explain exactly why the current world fails to satisfy the target.

## 47.3 World model

Maintain a versioned representation of industrial reality — capabilities, facilities, suppliers, materials, geography, projects, evidence, time, and risk — against which objectives can be evaluated.

This mental model is useful because it prevents FORGE from drifting toward static reporting.

---

# 48. Design philosophy for future development

## 48.1 Build depth, not feature-name breadth

A 100-line module named `option_value.py` is not equivalent to real cross-sector option-value reasoning.

Prefer fewer deeply correct capabilities over shallow named modules.

## 48.2 Reuse abstractions where physics allows

A general capability/flow/evidence model should support many industries.

Do not hard-code each industry as a separate application unless domain physics requires a specialized extension.

## 48.3 Domain packs should provide data/ontology, not fake intelligence

The engine should remain general while packs provide domain-specific architectures, processes, sources, and constraints.

## 48.4 Use mature numerical/software libraries

Implementing the engine in relatively few lines is acceptable when robust third-party solvers, numerical libraries, web frameworks, databases, and visualization systems provide the lower-level machinery.

Line count is not a quality target.

## 48.5 But do not confuse abstraction with omission

If a concept exists only as a thin placeholder, document that honestly.

---

# 49. Acceptance benchmarks for the long-term system

The following should be treated as recurring flagship benchmarks.

## Benchmark A — Humanoids

> Can humanity manufacture 1,000,000 humanoids/year by 2030?

Must analyze full component industrialization and global constraints.

## Benchmark B — India humanoids under strategic constraint

> Can India manufacture 1,000,000 humanoids/year at >=70% recursive DVA without Chinese permanent magnets?

Must test substitution, domestic capability, machine-tool recursion, supplier qualification, and time.

## Benchmark C — CNC execution

> Help us manufacture 100 high-quality CNC machining centers.

Must test ANALYZE + DESIGN + EXECUTE + LEARN, including detailed engineering decomposition, suppliers, processes, tooling, metrology, and machine recursion.

## Benchmark D — Nuclear

> What would it take for India to add 200 GW of nuclear generation by a target year?

Must test infrastructure, fuel cycle, heavy engineering, workforce, regulation, projects, geography, and long industrial clocks.

## Benchmark E — Reusable launch vehicles

> What industrial system is required to produce 100 reusable launch vehicles/year?

Must test aerospace materials, propulsion, precision manufacturing, supplier depth, test infrastructure, and production-rate scaling.

## Benchmark F — Reverse buildability

> Given the actual current world state, what is the maximum achievable output and what intervention increases it most?

## Benchmark G — Discover / option value

> Which industrial capability investments unlock the largest portfolio of future strategic industries?

---

# 50. What “complete enough” means

FORGE does not need to know literally every industrial fact on Earth before it becomes useful.

A useful path is:

1. a correct general computational kernel;
2. one or more deeply modeled verticals;
3. canonical cross-sector capability identity;
4. evidence-backed industrial state;
5. dynamic research to resolve unknowns;
6. increasingly broad coverage.

The system should be designed to expand without changing its fundamental epistemic discipline.

---

# 51. What future agents must never forget

If you are a future coding/research agent working on FORGE WORLD, remember:

- The ambition is universal industrial reasoning, not one use case.
- IndiaBUILD is a useful baseline/inspiration layer, not the product ceiling.
- Companies, builders, facilities, suppliers, mines, refineries, ports, logistics, and geography are first-class.
- Political/geopolitical/regulatory instability is part of the industrial world.
- A product objective must recurse into processes, machines, metrology, materials, and capabilities where decision-sensitive.
- FORGE must support analysis, design, execution, discovery, and learning.
- The system must be able to tell the user WHY.
- The system must be able to tell the user WHAT IS UNKNOWN.
- The system must be able to identify what evidence would resolve that uncertainty.
- The system must eventually help the user actually execute a manufacturing plan.
- The system must reason about alternative architectures and product–industrial co-design.
- The system must understand machines that build machines.
- The system must reason across geography and time.
- The system must not use fake precision.
- The system must not let an LLM hallucination silently become model truth.
- The strongest output is an **auditable computational argument about industrial possibility**.

---

# 52. Final North Star

**FORGE WORLD should let a user specify almost any physically meaningful manufactured future at any useful scale — from a table, to a CNC, to a million humanoids, to nuclear fleets, satellites, or reusable rockets — and then research, understand, decompose, benchmark, model, explain, redesign, synthesize, stress-test, and execute the industrial system required to make that future real.**

It should know what must exist, what exists today, who can do it, where it is done, where the materials come from, where the mines/refineries/factories/ports are, what the effective capacity is, what is missing, what is uncertain, what political or geographic risks matter, why a target succeeds or fails, what alternative architectures exist, what transformations close the gap, which capabilities are worth building for many futures, and what the user should do next.

The user should be able to move seamlessly between:

**ANALYZE -> DESIGN -> EXECUTE -> DISCOVER -> LEARN**

without leaving the same underlying industrial world model.

The intended end state is not a report generator.

It is a **living industrial intelligence and synthesis system** — a compiler, debugger, design environment, research engine, and execution copilot for the physical economy.

That is FORGE WORLD.
