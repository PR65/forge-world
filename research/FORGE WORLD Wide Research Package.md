# FORGE WORLD Wide Research Package

**Prepared by:** Manus AI  
**Research date:** 22 August 2026  
**Scope:** Broad knowledge foundation for a future computational system that reasons from physical objectives to products, components, processes, factories, resources, time, cost, energy, logistics, dependencies, shocks, substitutions, and feasibility.  
**Important boundary:** This package does **not** build FORGE WORLD, implement software, or design its UI. It consolidates research inputs, evidence, source metadata, machine-readable structures, and unresolved questions.

> **Core conclusion:** A serious physical-industry planning system cannot be built as a static catalogue of products or companies. It must combine a capability graph, a material-and-process transformation graph, a facility and logistics layer, a qualification-and-know-how layer, and a stochastic flow model. The most dangerous planning error is to treat a nominally installed factory, an export record, a patent, or an in-ground reserve as equivalent to a qualified, scalable, resilient industrial capability.

## Research design and evidence discipline

The investigation was divided into the twelve streams specified in the supplied brief: IndiaBUILD; Swarajya industrial intelligence; global capability analogues; physical-economy data; industry decomposition; foundational industrial recursion; supplier qualification; industrial shocks; substitution; existing systems; the India one-million-humanoid benchmark; and a missing-dimensions challenge. A parallel discovery pass produced twelve stream notes. This report is the synthesis layer; the individual notes, source map, raw research index, and machine-readable appendices are supplied alongside it.

Every conclusion is classified using the following epistemic labels. **FACT** means the source explicitly reports or defines it. **DERIVED INTERPRETATION** means the conclusion follows from multiple facts or a transparent calculation. **MODEL/ESTIMATE** means a scenario assumption, forecast, or parameter requiring calibration. **UNCERTAIN CLAIM** means a reported claim whose primary evidence is incomplete, promotional, or not independently corroborated. **UNKNOWN** means that the public evidence is insufficient and the variable should remain unresolved rather than be invented.

| Label | Meaning in this package | Typical examples |
|---|---|---|
| FACT | Directly documented by an identified source | An OECD dataset maps cross-border production and trade flows; IndiaBUILD defines six capability statuses |
| DERIVED INTERPRETATION | Transparent synthesis or arithmetic from sourced inputs | Closing a foundational node can unlock several downstream capabilities; annual component demand equals units multiplied by components per unit |
| MODEL/ESTIMATE | Explicit assumption or forecast used for planning sensitivity | 50–200 assembly hubs under a stated throughput assumption; a 6–24 month qualification range |
| UNCERTAIN CLAIM | Plausible but not sufficiently corroborated | Exact commercial yield of Indian harmonic reducers; claimed AI reductions in mineral-exploration timelines |
| UNKNOWN | Not observable or not adequately measured publicly | Tier-4 inventories, tacit knowledge-transfer rates, true machine-tool self-replicability ratio |

## 1. Executive synthesis

### 1.1 The decisive discoveries

**First, capability is a layered relation, not a label.** IndiaBUILD’s public framework is unusually useful because it distinguishes sectors, capabilities, foundational capabilities, and builders. Its running example is a passenger jet resting on engines, avionics, and fatigue testing, with each foundation depending on deeper materials, machinery, and process nodes. The site also separates a builder’s own progress claim from an evidence-based assessment. These concepts are directly reusable, but FORGE WORLD must extend them with capacity, yield, quality, cost, lead time, energy, water, facilities, ownership, licensing, and logistics fields.[1] [2]

**Second, industrial capability has at least five different dimensions that must not be collapsed into one score.** A country may possess design knowledge but no production line; a factory may be installed but not qualified; a process may be qualified but not economically competitive; a product may be produced under a foreign licence rather than sovereign know-how; and an asset may be geographically present but constrained by power, water, input quality, or export controls. The data model should therefore expose a vector of states instead of a single maturity number.

**Third, the most valuable global analogues are complementary rather than substitutable.** Harvard’s Atlas is strong at trade-derived product-space and complexity structure, OECD ICIO at country-industry value-chain dependencies, UNIDO at manufacturing statistics, USGS and IEA at minerals and energy, Global Energy Monitor at geolocated power assets, NREL at mineral-system dynamics, DoD MRL at manufacturing maturity, and IndiaBUILD at human-readable capability/dependency curation.[5] [7] [8] [10] [11] [12] [16] [18]

**Fourth, the macro–micro integration gap is the central unsolved problem.** Macro datasets reveal country-product exports, value-added flows, and mineral concentration but rarely identify the exact factory, machine, recipe, yield, or customer qualification status. Enterprise digital twins can reschedule a plant or optimize inventory but usually lack the public macroeconomic, geopolitical, and cross-sector context required for national or continental planning. FORGE WORLD’s distinctive opportunity is the integration layer, not the reinvention of any individual dataset or optimization algorithm.[21] [22]

**Fifth, industrial time is endogenous.** Mines, refineries, fabs, furnaces, machine tools, and certified suppliers do not appear at the moment a model requests them. Permitting, grid connection, equipment procurement, commissioning, yield ramp, customer qualification, and tacit-knowledge transfer form a sequence of queues. A feasible plan is therefore a time-expanded network with state transitions, not a static bill of materials.

**Sixth, the physical bottleneck often sits midstream.** In-ground reserves do not equal usable supply. Separation, refining, high-purity conversion, alloying, magnet production, chemical precursors, and recycling can be more concentrated and more difficult to reproduce than mining. The Swarajya critical-minerals investigation makes this point vividly in the Indian context, but the general lesson applies globally: the relevant node is the required grade and process, not merely the element or ore deposit.[4] [15] [17]

**Seventh, substitution is a graph rewrite, not a free choice.** Replacing rare-earth permanent magnets with induction or synchronous-reluctance motors can reduce rare-earth dependence while increasing requirements for power electronics, control software, electrical steel, and possibly volume. Replacing NMC with LFP or sodium-ion changes mineral exposure but also changes energy density, pack size, hard-carbon or sodium-precursor requirements, and manufacturing qualification. Every substitution must carry its performance envelope, new dependencies, CapEx/OpEx shift, qualification state, and time to adoption.

**Eighth, shocks propagate through inventories, queues, and thresholds.** Maritime rerouting can occur in weeks, while a new semiconductor fab, chemical plant, or rare-earth refinery may require years. A small upstream shortage can become a large downstream production loss when inventory buffers are shorter than replenishment time, when alternative suppliers are unqualified, or when one material has no drop-in substitute. The event engine should model shock onset, inventory drawdown, rationing, order amplification, substitution, recovery, and permanent demand destruction as distinct phases.

**Ninth, the one-million-humanoid benchmark is principally a component-industrialization problem.** The arithmetic implied by the supplied component ranges is tens of millions of actuators, reducers, and motors per year—not one million final assemblies. The benchmark is also underspecified: “humanoid” may mean wheeled or bipedal, and “manufacture” may mean final assembly from imported kits or integrated domestic production. Under a stated 20–40 actuator, 30–50 reducer, and 20–30 motor range, the component system is a much larger industrial challenge than the headline unit count suggests.

**Tenth, some of the most important variables are currently unobservable.** Deep-tier inventories, true process yields, exact machine-tool capacity, tacit floor knowledge, supplier qualification failure rates, and customer-specific acceptance criteria are usually proprietary. FORGE WORLD should represent these as distributions, confidence intervals, scenario ranges, or explicit UNKNOWN states. It should never fill the gap with a precise-looking number.

### 1.2 Highest-priority recommendations

| Priority | Recommendation | Why it matters |
|---|---|---|
| 1 | Define capability as a specification-bounded service with evidence, not as a product name | Prevents “factory exists” and “patent exists” from being mistaken for usable capability |
| 2 | Build a multi-layer graph: capability, BOM/process, facility, organization, policy, energy, logistics, and evidence | Connects products to factories, inputs, constraints, and actors |
| 3 | Add explicit readiness, qualification, yield, and ramp states | Captures the industrial-time gap between prototype, installed capacity, and dependable volume |
| 4 | Use public macro datasets as priors, not ground truth | Trade and input-output data are valuable but aggregated, lagged, and sometimes modeled |
| 5 | Treat substitutions as conditional alternatives with new dependency graphs | Avoids solving one chokepoint by silently creating another |
| 6 | Implement a time-expanded, stochastic throughput model | Makes power, inventory, downtime, yield, lead time, and recovery visible |
| 7 | Maintain claim-versus-assessment provenance and source snapshots | Reduces promotional bias and protects against changing web evidence |
| 8 | Start with a narrow, high-value vertical pilot while preserving a general ontology | A complete global graph is impossible initially; a traceable pilot can calibrate the model |

## 2. IndiaBUILD findings

### 2.1 What the public framework contributes

The IndiaBUILD homepage observed on 22 August 2026 displayed a living dashboard with 7,047 mapped capabilities, 1,544 still-red gaps, 1,835 builders, 96 schemes, and 101 investors. It displayed 3,874 assessed capabilities and 3,173 not yet assessed, and six maturity states: No capability, Emerging, Demonstrated, Producing (licensed), Producing (own tech), and Competitive.[1] These counts are **date-sensitive site observations**, not independent measurements of India’s entire industrial base.

The public “How the map is organised” page makes the conceptual model more explicit. It distinguishes approximately twenty-two hard-technology sectors; capability nodes can be final products or foundational building blocks; foundational nodes appear in dependency trees; and builders include companies, startups, laboratories, and government programmes. A separate builder ladder runs from Study through R&D, Prototype, Testing, Certification, and Limited production. This is a particularly important separation: capability maturity and builder activity are related but not identical.[2]

The engine page documents a five-step workflow: Research, Verify, Reconcile, Write, and Record. Research uses primary and authoritative sources; verification is described as an independent re-fetch and claim-support check; reconciliation addresses duplication and record identity; writing is performed from verified material; and recording maintains the resulting page and relationships.[3] FORGE WORLD should borrow this provenance discipline, while adding source snapshots, temporal validity, quantitative uncertainty, and machine-readable evidence objects.

| IndiaBUILD primitive | Direct value for FORGE WORLD | Necessary extension |
|---|---|---|
| Sector | Top-level navigation and priors for domain coverage | Support cross-sector capabilities and shared suppliers rather than forcing one sector per node |
| Capability | Human-readable object representing something a country wants to make | Add specification envelope, quantity, capacity, quality, unit, date, and geographical scope |
| Foundational capability | Exposes downstream unlocks and bottlenecks | Add material/process/facility/tool/resource node types and recursive closure analysis |
| Capability status | Common language for maturity | Split status into design, prototype, qualification, production, volume, competitiveness, and sovereignty dimensions |
| Builder | Identifies actors attempting a capability | Add facility, ownership, supplier tier, workforce, financing, and customer-qualification fields |
| Builder ladder | Tracks attempt progress | Add probabilities, elapsed time, failure modes, and evidence quality |
| Naked gap | Red node with no visible builder | Distinguish true absence from incomplete research or undisclosed activity |
| Capital-starved gap | Builders present but no mapped investor | Add public funding, internal CapEx, debt, grants, and unknown financing states |
| Tech tree | Shows prerequisites and unlocks | Permit cycles, alternatives, shared inputs, and strongly connected bootstrap components |
| Claim versus assessment | Anti-promotional control | Store both claims and evidence excerpts with source date and reviewer history |
| Changes feed | Temporal signal | Preserve immutable snapshots and quantify why a node moved |

### 2.2 Access, licensing, and reuse

During direct inspection, no public developer REST API or bulk JSON/CSV export endpoint was found. This should be stated as **“no public endpoint was found during inspection”**, not as an absolute claim that no private or undocumented interface exists. Public web pages and the public suggestion/ledger structure are observable; the terms governing bulk reuse, scraping frequency, derivative databases, and commercial redistribution require explicit confirmation before automated mirroring.[1] [3]

For FORGE WORLD, the safest integration path is a provenance-preserving reference layer that stores public URLs, page titles, access dates, extracted claims, and hashes or snapshots where legally permitted. It should not republish proprietary text or assume that public visibility implies permission for bulk commercial reuse. If a formal export or permission is later offered, the connector can be upgraded.

### 2.3 What should not be copied uncritically

IndiaBUILD is primarily a capability map and evidence-curated public intelligence layer. It is not visibly a full production-planning model. Its public metrics do not by themselves provide facility throughput, utilization, process yield, input coefficients, power constraints, working-capital requirements, or customer qualification. The site’s capability statuses are therefore best treated as one layer in a larger state vector.

A notable dashboard arithmetic issue should be preserved rather than hidden. The homepage showed six status counts summing to 3,874 assessed capabilities, but the displayed percentages do not appear to correspond cleanly to those counts. The counts and percentages should be treated as separate site-reported fields until the site’s denominator definition is clarified.

## 3. Swarajya industrial-intelligence findings

### 3.1 Value of the corpus

The relevant Swarajya corpus is useful as a discovery and framing layer rather than as a substitute for official statistics. The most valuable material concerns critical minerals, semiconductor policy, industrial clusters, rare-earth magnets, recycling, upstream chemical purity, and India’s effort to move from resource possession toward midstream and downstream capability. The investigated critical-minerals article reports that India is entirely dependent on foreign suppliers for at least ten critical minerals and imports 60–80% of other requirements; it also reports that China controls nearly 90% of global rare-earth processing.[4] These are **media-reported claims** that require primary corroboration before they become model parameters.

The same article reports the National Critical Mineral Mission as a ₹16,300 crore public expenditure component plus ₹18,000 crore of expected state-enterprise/private investment, approximately ₹34,300 crore in total between 2024 and 2031. It describes 1,200 exploration projects, processing parks, recycling support, KABIL overseas partnerships, and a ₹7,280 crore rare-earth permanent-magnet programme with 6,000 tonnes per year of planned capacity.[4] The article is especially useful because it identifies separate nodes that are often collapsed into “mineral security”: exploration, mining, separation, refining, high-purity conversion, magnet production, recycling, skilled labour, and overseas sourcing.

### 3.2 Claim → source → evidence → confidence ledger

| Claim from the corpus | Source | Evidence available in current pass | Confidence for Forge World use |
|---|---|---|---|
| India is importing most requirements for several critical minerals and 60–80% for others | Swarajya critical-minerals article; primary agencies named but not fully linked in article | Article-level reporting | **UNCERTAIN CLAIM** until Ministry of Mines/GSI/commerce tables are attached mineral by mineral |
| China controls nearly 90% of rare-earth processing | Swarajya article; IEA and other global analyses are relevant corroboration | Secondary report aligned with broad public consensus | **FACT at broad direction; numerical share requires date and scope definition** |
| NCMM total planned public/private commitment is approximately ₹34,300 crore | Swarajya article citing Cabinet/mission figures | Article reports ₹16,300 crore public plus ₹18,000 crore expected investment | **MEDIUM-HIGH**, verify against Cabinet and Ministry documents |
| Rare-earth magnet programme plans 6,000 tonnes/year | Swarajya article | Article reports programme size and capacity target | **MEDIUM**, verify official scheme notification and plant-level commitments |
| Indian bulk chemical processing does not imply electronic-grade capability | Swarajya reporting and industry examples | Strong engineering logic; public product-specific qualification evidence is limited | **DERIVED INTERPRETATION / MEDIUM** |
| AI can reduce mineral-exploration timelines by 60–70% | Swarajya interview/reporting | Reported company case claims; model and baseline are not public | **UNCERTAIN CLAIM**, not a general planning parameter |

### 3.3 Industrial-intelligence method

The correct workflow for mining Swarajya or any editorial corpus is not “summarize the account.” It is to extract claims, identify the publication’s source and framing, follow linked government/company/academic sources, record the measured quantity and denominator, then assign confidence. X posts are discovery signals and may contain compressed or promotional language. A source hierarchy should rank statutes, official datasets, permits, company filings, technical papers, standards, and audited disclosures above commentary and social posts.

## 4. Global capability analogues

### 4.1 Complementary frameworks

The global landscape contains no single public system that fully maps “what a country can make” down to facilities, recipes, machine tools, and qualified suppliers. Instead, existing systems cover different slices of the problem.

| Framework | Strongest contribution | What it does not provide |
|---|---|---|
| WIPO Innovation Capabilities Navigator | Innovation ecosystem profiles using patents, trademarks, publications, and exports across economies | Direct plant capability, current yield, tacit know-how, and operational capacity |
| Harvard Atlas of Economic Complexity | Product-country trade network, product space, complexity, growth projections | Non-traded capabilities, facility status, design quality, and exact production processes |
| OECD ICIO/TiVA | Country-industry production, consumption, investment, trade, and value-added relationships | Fine-grained product BOMs, facility locations, and qualification status |
| UNIDO CIP/INDSTAT | Manufacturing performance, output, industrial structure, and statistical benchmarks | Hidden firms, informal activity, facility-level readiness, and detailed process graphs |
| World Bank Enterprise Surveys | Firm-level constraints such as infrastructure, finance, skills, and informality in surveyed economies | Full census, current production networks, and deep-tier supplier structure |
| EU RMIS/JRC | Critical and strategic material criticality and supply-risk mapping | Global facility-by-facility process yields and customer qualification |
| Japan METI and Korean industrial studies | Industrial competitiveness, supply-chain, and manufacturing-policy context | A universal machine-readable global capability graph |
| NREL LIBRA/RING-type models | Dynamic mineral, battery, recycling, and supply-chain scenario behavior | General product decomposition and shop-floor qualification |
| DoD MRL | A disciplined manufacturing-maturity vocabulary and assessment logic | Public country-wide industrial capacity and commercial market structure |
| GEM facility trackers | Geolocated assets, ownership, capacity, project status, and infrastructure pipeline | All industrial sectors and real-time production utilization |

WIPO’s Navigator is a useful innovation-capability proxy, while the Atlas provides a concrete trade-derived network. The Atlas page observed in this research states that it covers over 6,000 products across 250 countries and territories, offers bulk downloads and GraphQL API access, and publishes HS and SITC data with revisions and reporting lags.[5] [6] [7] OECD describes ICIO as mapping production, consumption, investment, and international goods/services trade by country and economic activity; its regular version covers 80 economies plus the rest of the world, with an extended version that splits China and Mexico for firm heterogeneity.[8]

The correct synthesis is a **capability evidence ensemble**: trade complexity provides a prior, manufacturing statistics provide macro scale, facilities provide physical presence, patents/publications provide knowledge proxies, standards and certifications provide readiness gates, and company/permit records provide current project status.

### 4.2 Why an ensemble is necessary

Trade data can show that a country exports a product without showing whether production is domestic, re-exported, contract-manufactured, or dependent on imported subassemblies. Patents can show inventive activity without showing reduction to practice. A facility database can show nameplate capacity without utilization or qualified yield. Input-output tables can show industry dependence but not which component or supplier will fail first. These are not minor caveats; they determine whether a plan is physically meaningful.

## 5. Physical-economy data and API matrix

### 5.1 Core dataset matrix

| Domain | Recommended source(s) | Main variables | Access and terms | Coverage/refresh | Primary limitation | Forge World role |
|---|---|---|---|---|---|---|
| Minerals | USGS NMIC, Mineral Commodity Summaries, World Production | Production, imports, prices, reserves/resources, supply risk, selected facilities | Public government releases; CSV/Excel and web data | Global, annual, commodity-level; some newer releases are geospatial | Country aggregates, voluntary reporting, limited real-time status | Material priors, supply concentration, resource-to-product pathways |
| Trade | UN Comtrade; Atlas; BACI/CEPII | Bilateral flows by product/partner, quantities/value where available, HS codes | UN API/web; Atlas downloads/GraphQL; BACI public download | Global, annual/monthly depending source | Mirror discrepancies, re-exports, classification changes, reporting lag | Import dependence, concentration, trade corridors, re-export detection |
| Manufacturing | UNIDO INDSTAT, IIP, manufacturing trade; national statistics | Output, value added, employment, establishments, industrial production | Public portal/API or downloads subject to terms | Country/industry, annual/monthly depending series | Formal-sector bias, classification breaks, missing small firms | Macro capacity priors and industrial benchmarking |
| Input-output | OECD ICIO/TiVA, EXIOBASE, WIOD, Eora | Industry-to-industry flows, value added, embodied trade/emissions | Downloads or database-specific terms | Multi-country, multi-industry, periodic revisions | Modeled/estimated, aggregated, several-year lag | Dependency matrices and scenario multipliers |
| Facilities | GEM trackers, national permit/asset databases, USGS facility releases | Coordinates, capacity, owners, status, start/retirement, technology | GEM downloadable datasets and wiki; licenses vary by tracker | Facility-level, rolling updates | Coverage thresholds, approximate coordinates, subjective status evidence | Physical asset graph, cluster mapping, project pipeline |
| Energy | IEA, EIA, national grid operators, GEM power trackers | Generation, fuels, demand, prices, grid, projects, capacity | EIA/public national data; IEA access varies; GEM public facility data | Annual to hourly depending source | Power quality, congestion, connection queues, and industrial contracts under-observed | Energy feasibility and co-location constraints |
| Logistics | UNCTAD, port authorities, AIS/commercial maritime data, World Bank transport data | Port calls, route times, canal traffic, freight, dwell, chokepoints | Public reports plus commercial datasets | Annual/quarterly/high-frequency depending source | Vessel arrivals are not cargo mass; proprietary inventory and freight data | Transit capacity, shock propagation, rerouting |
| Prices | World Bank Pink Sheet, IMF, EIA, FRED, metal exchanges | Commodity, energy, freight, currency, interest rates | Public downloads/APIs vary | Monthly/daily depending series | Spot benchmarks differ from contracts, grades, and local premia | Cost scenarios and substitution triggers |
| Technology/IP | WIPO IP Statistics, USPTO PatentsView, EPO Espacenet, publications | Patents, assignees, citations, R&D/publication signals | Public data portals/APIs with different terms | Long-run annual and bibliometric coverage | Filing does not prove manufacturing, quality, or adoption | Knowledge and ownership priors |
| Policy | WTO I-TIP, tariff databases, export-control/sanctions lists, national schemes | Tariffs, subsidies, local content, restrictions, notifications | Public portals; legal reuse varies | Policy-specific, often continuous | Notification gaps and legal scope complexity | Scenario constraints and policy-to-capability links |
| LCI/process | ecoinvent, USLCI/openLCA, process literature | Energy, material, emissions, transport, unit-process coefficients | ecoinvent commercial; USLCI/open route | Process-version dependent | Regional proxies, version lag, emerging-tech gaps | Mass/energy/environmental balance |

The UN Comtrade page describes detailed annual and monthly global trade statistics by product and trading partner, covering approximately 200 countries and more than 99% of merchandise trade, with API developer tools and premium bulk services.[9] USGS describes its NMIC as collecting domestic and international data on nonfuel minerals and provides releases that include world production, price, supply-risk, and selected facility information.[10] Global Energy Monitor’s Global Integrated Power Tracker is particularly valuable for the physical layer: the page observed in this research listed 200 country/areas, 22,296 GW of capacity, 182,400 facilities, and 8,000+ owners, with status, ownership, geolocation, and technology fields.[11]

### 5.2 Integration rules

The data layer should preserve the source-native unit, classification, and revision history. Do not merge HS trade codes directly into process or capability nodes without a concordance table and an explicit confidence field. Do not translate monetary input-output flows into tonnes without grade-, region-, and process-specific conversion coefficients. Do not interpret a facility’s nameplate capacity as output without an availability and utilization distribution.

A useful baseline identity is:

\[
\text{Output}_{k,t}=\text{NameplateCapacity}_{k,t}\times\text{Availability}_{k,t}\times\text{Utilization}_{k,t}\times\text{Yield}_{k,t}
\]

For a country-industry model, a supply-chain adjacency matrix can be estimated from ICIO/EXIOBASE and then constrained by physical mass, energy, water, facility, and logistics limits. The monetary matrix is a prior or accounting scaffold; it is not itself a physical bill of materials.

## 6. Industry decomposition: product → subsystem → component → process → material → machine/tool → resource

### 6.1 Evidence sources

The decomposition problem requires several source classes because no public source contains all levels. Engineering BOMs and MBOMs are generally proprietary. Commercial teardowns from TechInsights and Munro can reveal component geometry, packaging, die dimensions, and cost-to-feature estimates, but access is commercial and the results are snapshots.[26] Open repair and teardown guides such as iFixit are lower-cost and useful for part identity and disassembly structure, but they are weighted toward consumer products rather than aerospace or industrial systems.[27]

Life-cycle inventory databases such as ecoinvent and USLCI provide unit processes and material/energy/emissions coefficients. Standards from ISO, ASTM, IEEE, SAE, and sector regulators define tolerances, tests, and acceptance rules, although many detailed standards are paywalled and not graph-native. Patents and technical publications provide technology and process clues, but they can contain speculative or deliberately obfuscated information. Customs codes provide observable trade categories but are too coarse to be treated as engineering BOMs.

### 6.2 What is directly sourced versus inferred

| Relationship | Publicly sourceable? | Appropriate treatment |
|---|---|---|
| Product contains named subsystem | Often, from manuals, filings, teardowns, procurement specs | FACT if document-specific; version and configuration required |
| Component mass/material/part number | Sometimes; often proprietary | FACT when measured or specified; otherwise MODEL/ESTIMATE |
| Component requires process class | Usually inferable from engineering practice | DERIVED INTERPRETATION with cited standards or process literature |
| Process requires a machine class | Often inferable, but exact machine capability varies | Capability prerequisite with specification envelope |
| Exact machine-tool route and cycle time | Rarely public | MODEL/ESTIMATE or UNKNOWN |
| Material-to-grade conversion and yield | Partially available in LCI/literature | Use distributions by process, grade, and plant maturity |
| Tier-2/Tier-4 supplier identity | Sometimes in filings/customs; often hidden | Evidence graph with confidence and intermediary flags |
| Customer qualification status | Rarely public | UNKNOWN unless certification, approval, or contract evidence exists |

The correct graph is not a single tree. It is a multiplex network: products contain components; components are transformed by processes; processes consume materials and machine services; facilities host processes; organizations own or operate facilities; standards qualify processes; policies constrain flows; logistics nodes transport inputs; and substitution edges connect alternative designs with tradeoffs.

## 7. Foundational industrial recursion

### 7.1 The recursive stack

Industrial self-expansion depends on machine tools, controls, motion systems, metrology, thermal processing, materials, tooling, chemical processing, and energy infrastructure. The stream research identified high concentration in high-end CNC controls and drives, multi-axis machine tools, precision bearings, metrology, semiconductor lithography, deposition, etch, and inspection. Named leading firms in public market and company materials include FANUC, Siemens, Yamazaki Mazak, Okuma, Makino, DMG Mori, SKF, NSK, NTN, JTEKT, Schaeffler, Hexagon, Zeiss, Mitutoyo, Keyence, ASML, Applied Materials, Lam Research, and Tokyo Electron. The specific market-share percentages and market-size estimates in commercial reports should be treated as **MODEL/ESTIMATE**, not universal facts.

The important structural fact is more durable than any market forecast: precision manufacturing is a closed loop of machine, material, measurement, and control. High-speed spindles require specialized bearings and balance; bearings require high-quality steels and heat treatment; machine structures require vibration-damping castings and precision grinding; control systems require sensors, drives, software, and power electronics; and advanced process equipment relies on vacuum, chemistry, optics, metrology, and contamination control.

| Foundational node | Downstream unlocks | Typical hidden dependencies |
|---|---|---|
| CNC controls and drives | Machine tools, robots, automation, power systems | Semiconductors, firmware, sensors, motors, safety certification |
| Precision bearings and spindles | High-speed machining, robotics, turbines, compressors | Bearing steel, heat treatment, grinding, metrology, lubrication |
| Metrology and inspection | Yield, interchangeability, certification, closed-loop correction | Optics, sensors, calibration standards, software, skilled operators |
| Furnaces and thermal processing | Tooling, alloys, magnets, semiconductors, ceramics | Vacuum, temperature uniformity, atmosphere control, refractory materials |
| Tooling, dies, molds, grinding | Automotive, appliances, electronics, castings, mass production | Carbides, diamond, specialty steels, coatings, metrology |
| Semiconductor process equipment | Controls, power electronics, sensors, compute, advanced materials | Ultra-pure chemicals, gases, optics, vacuum, precision motion, software |
| Industrial robots and automation | High-volume assembly, welding, handling, inspection | Motors, reducers, encoders, controllers, safety, integration |

### 7.2 Recursion is not a simple DAG

The brief’s recursion statement—products require factories, factories require machinery, machinery requires other industries—is correct but incomplete. Many industrial systems form cycles or strongly connected components. A machine-tool producer may depend on earlier-generation machine tools, imported controls, bearings, and metrology; a metrology producer may depend on optics and electronics; optics depend on ultrapure materials and polishing; polishing equipment depends on precision machines. FORGE WORLD should therefore model bootstrap sets, strongly connected components, and minimum viable closure rather than assuming every dependency can be topologically sorted.

A useful variable is a **Recursive Depth Index**, but it should be accompanied by a **Bootstrap Closure Requirement**: the minimum set of mutually dependent capabilities, imported seed equipment, training, and standards needed to start a production loop. True self-replication is not a binary property; it is a spectrum from import-dependent assembly to progressively localized tool, material, control, and metrology closure.

## 8. Supplier qualification, industrial time, and tacit know-how

### 8.1 Installed capacity versus real capability

A component or factory becomes operationally valuable only when it can repeatedly deliver the required specification, volume, yield, reliability, documentation, and customer acceptance. Aerospace and defense use formal quality systems such as AS9100 and special-process accreditation such as Nadcap; the DoD Manufacturing Readiness Level framework provides a ten-level vocabulary for moving from basic manufacturing knowledge to stable, capable, full-rate production.[18] [19]

The parallel research notes identify six-to-twenty-four-month aerospace supplier qualification ranges, six-to-eighteen-month ranges for new semiconductor materials in some contexts, and two-to-three-year validation windows for some advanced packaging/OSAT pathways. These are useful **planning ranges**, not universal laws. Qualification duration depends on criticality, customer, sector, existing certifications, process novelty, test requirements, and whether an approved second source already exists.

| Time mechanism | What it delays | Modeling treatment |
|---|---|---|
| Design verification | Release of a production-intent design | Gate before tooling and qualification |
| Tooling and equipment procurement | Physical line installation | Vendor lead-time distribution plus installation/commissioning |
| Process development | Stable cycle time and yield | Learning curve and experimentation state |
| Special-process accreditation | Use in regulated supply chains | Certification gate with audit/rework risk |
| First article and customer qualification | Revenue-grade supply | Customer-specific approval state |
| Yield ramp | Saleable output | Time-varying yield distribution, not a step function |
| Workforce learning | Repeatability and troubleshooting | Site/line-specific latent capability variable |
| Export-control and licensing review | Cross-border transfer and equipment access | Jurisdiction-specific legal latency |

A planning model should represent qualification latency as a distribution, not a single scalar. It should also distinguish **qualification of the process**, **qualification of the supplier**, **qualification of the part**, and **qualification of the customer’s use case**. A design can pass a material test while the supplier remains unable to produce stable volume; a supplier can be approved for one customer and unqualified for another.

### 8.2 Learning and yield

Learning curves are useful for labor and cycle-time reduction, but they do not eliminate stochasticity. Tool wear, calibration drift, rework, scrap, contamination, maintenance, incoming-material variance, and operator turnover can all reduce usable output. The package therefore recommends a throughput identity such as:

\[
\text{Throughput}_{i,t}=\min\left(\text{Capacity}_{i,t}\times\text{Yield}_{i,t},\ \text{AllocatedInputs}_{i,t},\ \frac{\text{PowerAvailable}_{i,t}}{\text{SpecificEnergy}_{i}}\right)\times(1-\text{StochasticDowntime}_{i,t})
\]

DoD MRL is valuable because it makes manufacturing risk visible, but it does not supply the yield curve or the customer’s exact acceptance distribution. NASA’s systems-engineering guidance is valuable for requirements, interfaces, verification, and validation; it should inform the integration layer, not be misread as evidence for a universal mathematical claim that interface complexity always follows a literal \(O(N^2)\) law.[20]

## 9. Industrial shock case studies

### 9.1 Common transmission pattern

Across oil shocks, earthquakes, pandemics, semiconductor shortages, canal blockages, maritime security crises, energy crises, and mineral restrictions, the same pattern recurs: a localized disruption consumes inventories, exposes a concentrated node, propagates through unqualified alternatives and order amplification, raises prices, triggers rationing or redesign, and eventually produces either recovery, structural substitution, or permanent demand destruction. UNCTAD’s analysis of the Red Sea crisis provides a current example of how canal disruption can alter route lengths and trade flows; it reported a sharp reduction in Suez traffic during the crisis period.[33]

| Case | First-order effect | Second-order effect | Substitution/recovery lesson | FORGE WORLD variable |
|---|---|---|---|---|
| 1970s oil shocks | Energy-price surge and supply uncertainty | Inflation, transport cost, industrial output pressure | Efficiency, fuel switching, strategic stocks, slower demand | Energy intensity and reserve days |
| 2011 Japan earthquake | Facility and grid disruption | Global auto/electronics shortages through specialized suppliers | Dual sourcing helps only if qualified and physically available | Geographic SPOF and qualification state |
| 2020–23 semiconductor shortage | Demand mismatch plus constrained fab/packaging capacity | Vehicle production delays, component redesign, allocation | Legacy-node redesign and allocation can outperform nominal capacity additions in short run | Lead-time, allocation, and redesign latency |
| Suez blockage | Six-day canal closure and vessel queues | Port congestion, schedule disruption, equipment imbalance | Rerouting trades time and fuel for continuity | Transit-time distribution and queue absorption |
| Red Sea disruption | Security-driven route avoidance | Longer voyages, higher fuel use, schedule and freight pressure | Route diversion and fleet redeployment are faster than new infrastructure | Route graph and dynamic shipping capacity |
| European gas crisis | Gas price and supply shock | Fertilizer, chemicals, steel, and glass curtailment | LNG, demand reduction, fuel switching, temporary shutdowns | Fuel substitution and restart time |
| Critical-mineral export controls | Licensing and shipment uncertainty | Refining and component anxiety in magnets, batteries, electronics | Recycling, alternative chemistries, new refining, stockpiling | Restriction state and substitution readiness |
| Copper tightness | Refined-material scarcity and treatment-charge pressure | Wiring, grid, motor, and construction cost pressure | Aluminum substitution, scrap, mine expansion | Grade-specific material substitution and mine latency |

### 9.2 Recovery time is asset-class dependent

A key model design principle is that “recovery” is not one event. A logistics route may be rerouted in weeks, a damaged plant repaired in months, a new supplier qualified in months to years, and a new mine, refinery, fab, or grid corridor built over several years. The event engine should output a recovery distribution with confidence bounds and distinguish temporary throughput loss from permanent capability erosion.

A practical vulnerability index can be defined as a diagnostic rather than a truth score:

\[
V_i=\frac{\text{SupplierConcentration}_i\times\text{RestrictionExposure}_i}{\text{SubstituteReadiness}_i\times\text{InventoryBufferDays}_i\times\text{GeographicRedundancy}_i}
\]

The factors must be normalized and sourced. The index should not be used without a sensitivity analysis because concentration, inventories, and substitution readiness are often measured with different uncertainty levels.

## 10. Technology substitution cases

| Bottleneck | Alternative | Tradeoffs | New dependencies |
|---|---|---|---|
| NdFeB magnets and heavy rare earths | Induction, synchronous-reluctance, or ferrite-based motor architectures | Lower power density or different torque/control behavior; packaging and inverter effects | Power electronics, control software, electrical steel, thermal design |
| Cobalt/nickel exposure in batteries | LFP | Lower energy density than high-nickel chemistries in many applications; supply-chain and pack-design effects | Phosphate/iron processing, cell qualification, pack volume |
| Lithium/graphite exposure in some applications | Sodium-ion | Lower energy density and immature commercial ecosystem in many use cases | Hard carbon, sodium precursors, cell and pack qualification |
| Copper in selected windings/conductors | Aluminum | Higher resistivity and larger cross-section; joining and corrosion challenges | Larger housings, joining technology, thermal management |
| Silicon limits in high-voltage/high-frequency power conversion | SiC/GaN | Higher material/process complexity and packaging demands | Crystal growth, epitaxy, specialized packaging, reliable supply |
| Coking coal and emissions in iron reduction | H-DRI | Large CapEx and continuous hydrogen/quality-pellet requirements | Green hydrogen, electrolysis, grid/renewable power, DR-grade ore |
| Hard tooling for low-volume complex parts | Additive manufacturing | Slower throughput, powder cost, post-processing, qualification | Metal powders, inert gas, inspection, heat treatment, design rules |
| Primary mineral extraction | Recycling/direct recycling | Collection, sorting, contamination, and reverse-logistics requirements | Disassembly automation, feedstock standards, recycling plants |

The substitution stream’s strongest general result is that there is no universal “critical-mineral-free” path. A substitution can lower geological exposure while increasing dependence on semiconductor control, high-purity electrical steel, specialized equipment, energy, volume, or qualification. Therefore, every substitution edge should carry a **conditional feasibility predicate**: acceptable performance envelope, available process route, qualified supplier, input availability, CapEx, energy, time, and customer acceptance.

## 11. Existing systems and what FORGE WORLD should copy, learn, integrate, and avoid

| Action | Existing pattern | FORGE WORLD implication |
|---|---|---|
| Copy | IndiaBUILD’s capability/foundation/builder layers and claim-versus-assessment split | Use auditable capability nodes, dependency edges, builder states, and public evidence |
| Copy | Atlas ECI/PCI and product-space network methods | Use trade-derived capability priors and adjacency, with explicit proxy caveats |
| Copy | OECD ICIO/TiVA input-output and value-added structure | Use country-industry flow matrices for macro constraints and embodied dependencies |
| Copy | DoD MRL readiness vocabulary | Use production maturity gates and manufacturing-risk reviews |
| Copy | GEM’s facility profiles, status definitions, and source-linked fact sheets | Use geospatial asset records with project-state and evidence fields |
| Learn | Enterprise digital twins and Pelico/Coupa/Relex-style rescheduling | Learn queue, allocation, inventory, and disruption-recovery algorithms without inheriting closed boundaries |
| Learn | NIST digital-twin economics | Require a cost/benefit and data-readiness case for every high-fidelity model |
| Integrate | AWS-style manufacturing digital-thread knowledge graphs | Connect BOMs, processes, suppliers, facilities, and logistics through semantic identifiers |
| Integrate | NREL mineral-system scenario models | Add dynamic extraction, refining, recycling, demand, and policy feedbacks |
| Avoid | A single black-box capability score | Preserve component scores, evidence, uncertainty, and reasons for status |
| Avoid | Static country rankings treated as feasibility | Use rankings as priors, not as production plans |
| Avoid | Product-only ontology | Represent processes, equipment, grades, standards, utilities, and people |
| Avoid | Reserve-only mineral planning | Model grade, refining, energy, water, permitting, and logistics |
| Avoid | A monolithic system that requires every dataset to be complete | Support partial graphs, missingness, scenario ranges, and confidence propagation |

Harvard, OECD, NREL, NIST, AWS, and GEM should be treated as components of a reference architecture rather than direct competitors. The landscape indicates that the hardest unsolved interface is between public macro models and proprietary factory reality.[7] [8] [16] [21] [22]

## 12. Capability model discoveries

### 12.1 A capability should be a service under a specification envelope

The primitive should not be “India makes humanoids.” It should be something such as: “A qualified Indian production system can deliver 250,000 bipedal humanoid joint actuators per year, at torque/precision/temperature/reliability specification X, with yield Y, using input grades Z, at facility set F, under standards S, with a verified customer-acceptance state.” This representation is harder to populate but far more useful for feasibility.

The attached JSON schema operationalizes this idea with node types for products, subsystems, components, materials, processes, machine tools, facilities, resources, standards, organizations, policies, logistics nodes, and energy nodes. It includes dynamic variables for inventory, concentration, qualification latency, ramp rate, learning, downtime, power, energy, permitting, restrictions, and recovery objectives.

### 12.2 Minimum graph layers

| Layer | Key nodes | Key edges | Key question |
|---|---|---|---|
| Capability | Product, subsystem, component, process | Depends-on, unlocks, substitutes-for | What must be possible? |
| Engineering | BOM, material grade, tolerance, process route | Contains, transforms, requires | How is it made? |
| Factory | Facility, line, machine, tool, utility | Located-at, operated-by, constrained-by | Where and at what rate? |
| Organization | Company, lab, state entity, supplier | Builds, owns, qualifies, finances | Who can do it and how far? |
| Evidence | Document, dataset, permit, filing, test | Supports, contradicts, supersedes | Why believe it? |
| Policy | Scheme, tariff, export control, standard | Funds, restricts, requires | What changes feasibility? |
| Physical flow | Mine, refinery, plant, port, rail, grid | Supplies, transports-through | Can inputs arrive? |
| Scenario | Shock, price, demand, rule change | Triggers, propagates, recovers | What happens if conditions change? |

### 12.3 Evidence and time versioning

Every edge needs an evidence object with publisher, URL, publication date, access date, claim or measurement, geography, temporal scope, license, and limitations. Sources should be versioned because facility status, company ownership, policy eligibility, and capability maturity change. The graph should distinguish three clocks: **physical clock** for construction and production; **evidence clock** for when the world was observed and reported; and **decision clock** for when a scenario must be achieved.

## 13. India producing one million humanoids per year by 2030

### 13.1 Benchmark definition problem

The target is a user-defined benchmark, not an established baseline. The public Indian evidence reviewed in this pass is concentrated in early commercial and research activity; Addverb’s public announcement provides a current Indian robotics signal, but a wheeled logistics platform should not automatically be counted as equivalent to a bipedal, general-purpose humanoid.[28] [29]

Before feasibility analysis, the scenario must specify:

| Definition choice | Possible interpretations | Why it changes the answer |
|---|---|---|
| Humanoid morphology | Wheeled torso; quasi-humanoid; bipedal industrial; general-purpose bipedal | Changes actuators, balance control, safety, energy, and qualification |
| Production meaning | Final assembly; local component integration; domestic BOM; sovereign end-to-end | Changes import dependence and industrial depth |
| Unit status | Built; tested; accepted; shipped; operating in the field | Changes required testing, service, and spare-parts capacity |
| Duty cycle | Warehouse shifts; intermittent service; continuous industrial use | Changes battery, thermal, charging, and grid requirements |
| Performance | Payload, speed, dexterity, terrain, safety, uptime | Changes mechanical and software architecture |
| Deadline | First units, stable run-rate, or annual average by end-2030 | Changes ramp schedule and qualification window |

### 13.2 Transparent arithmetic envelope

The stream research used a broad architecture range of 20–40 actuators, 30–50 reducers, and 20–30 BLDC motors per robot. These values are **MODEL/ESTIMATE**, not a universal humanoid standard. Multiplying by one million annual units gives the following component envelope.

| Component | Low case | Base case | High case | Status |
|---|---:|---:|---:|---|
| Final robots | 1,000,000/year | 1,000,000/year | 1,000,000/year | USER-DEFINED TARGET |
| Actuators | 20,000,000/year | 36,000,000/year | 40,000,000/year | DERIVED ARITHMETIC |
| Reducers | 30,000,000/year | 40,000,000/year | 50,000,000/year | DERIVED ARITHMETIC |
| BLDC motors | 20,000,000/year | 25,000,000/year | 30,000,000/year | DERIVED ARITHMETIC |
| Assembly hubs at 5–20k units/hub/year | 50 hubs | 100 hubs at 10k | 200 hubs | MODEL/ESTIMATE |

This table excludes spares, field replacements, scrap, rework, qualification lots, and reserve inventory. If a five-percent scrap/rework allowance were used, the required gross component production would increase by approximately 5.3% to deliver the stated saleable output; the actual rate depends on where scrap occurs and whether components can be reworked.

### 13.3 Energy arithmetic correction

The stream note reported 0.5–2 kW of robot power and one-to-two GWh of daily energy for one million units. That cannot be used without clarifying whether the power is **peak** or **average**. If 0.5–2 kW is interpreted as average electrical draw during 8–16 operating hours per day, the transparent arithmetic range is:

\[
1{,}000{,}000\times(0.5\text{ to }2\,\text{kW})\times(8\text{ to }16\,\text{h})=4\text{ to }32\,\text{GWh/day}
\]

That corresponds to approximately 1.46–11.68 TWh per year before charging losses, standby, HVAC, battery production, spares, and factory energy. If the 0.5–2 kW figure is peak rather than average, the range is not an energy forecast at all. Therefore the correct state is **MODEL/ESTIMATE with unresolved duty-cycle semantics**, not a single one-to-two-GWh claim.

### 13.4 Component and process bottlenecks

| Subsystem | Likely requirement at 1M units/year | Indian baseline from current public evidence | Main unknown or bottleneck |
|---|---|---|---|
| Actuation | Tens of millions of integrated motor/drive/reducer/encoder assemblies | India has automotive, motor, gear, and CNC capabilities, but the benchmark-specific precision scale is not demonstrated publicly | Stable high-volume reducer yield and life testing |
| Reducers | 30–50 million units/year under the stream’s architecture range | Precision gear and gearbox capability exists in adjacent industries | Harmonic/cycloidal performance, backlash, fatigue, and qualification at scale |
| Motors | 20–30 million BLDC motors/year | Broad motor and automotive supplier base | Magnet, electrical steel, winding automation, thermal, and controller integration |
| Encoders and sensors | One or more high-quality sensors per joint plus vision/IMU/tactile systems | Electronics and sensor activity exists; exact high-volume humanoid stack unclear | Calibration, reliability, supply, and imported sensor dependence |
| Compute | Edge AI/control hardware and real-time safety systems | India has software and electronics design strengths | Advanced chips, packaging, power, firmware, safety certification, and supply assurance |
| Batteries/BMS | Large cell/pack throughput and charging/swapping infrastructure | Battery and EV ecosystem is expanding | Cell chemistry choice, pack safety, thermal life, power electronics, and materials |
| Structures | Castings, forgings, machined links, composites, fasteners | Strong adjacent automotive/aerospace suppliers | Lightweight fatigue-qualified parts and cycle-time/yield at volume |
| Test and certification | Joint, whole-body, EMC, functional safety, cyber, human-interaction testing | Standards can be adopted, but national pathway is not yet a demonstrated volume capability | Customer acceptance and shared-workspace safety qualification |
| Factory utilities | Clean power, compressed air, cooling, machining, electronics assembly, test | Industrial clusters provide partial infrastructure | Grid quality, transformers, water, maintenance, and supplier synchrony |

The most likely near-term choke points are not the existence of software talent or final assembly space. They are high-volume precision motion, reducer yield, magnets/electrical steel, encoders and drives, component qualification, power electronics, test throughput, and the synchronized expansion of tier-2 and tier-3 suppliers. Claims that India is already capable of one-million-unit bipedal production should remain **DERIVED INTERPRETATION or UNCERTAIN CLAIM** until factory, supplier, yield, and customer-acceptance evidence is available.

### 13.5 Feasibility framing

A responsible answer is conditional. One million units could be arithmetically assembled by a large network of modular lines under an imported-kit definition, but that would not demonstrate sovereign industrial capability. Under a bipedal, high-reliability, integrated-domestic-BOM definition, the public evidence reviewed here is insufficient to establish feasibility by 2030. The decisive next research step is a bottoms-up reference architecture with target specifications, a measured or quoted BOM, process routes, supplier capacities, and qualification schedules.

## 14. Unexpected findings and missing dimensions

### 14.1 Purity is a hidden capability ladder

“Chemical production” is not one capability. Commodity-grade, industrial-grade, electronic-grade, ultra-pure, and process-qualified material are separate nodes with different equipment, contamination control, analytics, packaging, and customer qualification. This purity ladder should be represented explicitly for chemicals, gases, metals, powders, wafers, magnets, battery materials, and specialty alloys.

### 14.2 Quality is an output multiplier

Nameplate capacity multiplied by availability is still insufficient. A line with 50% yield at a demanding specification may deliver less usable output than a smaller line with 95% yield. FORGE WORLD should propagate yield uncertainty downstream and treat rework, scrap, test failures, and warranty reserves as physical resource requirements.

### 14.3 Infrastructure is a synchronized system

Factories are coupled to power quality, transformers, water, wastewater, roads, ports, skilled labour, housing, fire protection, environmental permits, and financing. A site with land and a building may still lack the utility service or qualified suppliers needed for operation. GEM’s facility-level approach is useful for asset presence, but a full industrial plan must add utility and process-specific constraints.[11]

### 14.4 The “human layer” is not optional

Operators, maintenance technicians, process engineers, quality engineers, auditors, and customer application engineers are part of capability. Codified drawings and recipes transfer more easily than tacit troubleshooting and organizational routines. The workforce variable should include skill categories, training lead times, retention, shift coverage, and site-specific learning—not simply headcount.

### 14.5 Industrial policy changes graphs, not just prices

Subsidies, local-content rules, export controls, tariffs, standards, procurement preferences, and financing guarantees can create or destroy edges in the industrial graph. A policy engine should model eligibility, timing, conditionality, and enforcement rather than only adding a percentage subsidy to CapEx.

### 14.6 Evidence itself has a supply chain

Source availability is uneven. Public company announcements overrepresent successes; failed plants and cancelled projects are less visible. Trade data arrive with reporting lag; facility databases use status definitions; standards may be paywalled; and commercial supply-chain datasets are inaccessible. FORGE WORLD needs an evidence-quality model that estimates observation bias and records negative evidence, not only positive records.

## 15. Recommendations for improving FORGE WORLD

### 15.1 Separate five questions that are often conflated

For every capability, ask separately: **Can it be designed? Can it be physically produced? Can it be produced at the required volume? Can it meet quality and customer qualification? Can it be supplied resiliently under shocks?** These correspond to different evidence and different bottlenecks.

### 15.2 Use a layered state vector

A recommended minimum state vector is:

\[
S=(D,P,Q,V,C,R,E,L,I,T,O)
\]

where \(D\) is design maturity, \(P\) production process maturity, \(Q\) qualification, \(V\) usable volume, \(C\) competitiveness, \(R\) resilience, \(E\) energy/resource feasibility, \(L\) legal/IP status, \(I\) input security, \(T\) tacit-knowledge/workforce readiness, and \(O\) evidence quality. A single headline score can be generated for communication, but the underlying vector must remain visible.

### 15.3 Make graph edges typed and conditional

“Depends on” is too broad. Use requires, consumes, transforms, qualifies, supplies, transports-through, constrains, finances, substitutes-for, and unlocks. Each edge should carry quantity, grade/specification, geography, time, capacity, confidence, and alternatives. Some edges are hard constraints; others are probabilistic or price-sensitive.

### 15.4 Add bootstrap and import-seed scenarios

Industrial sovereignty rarely begins from zero. A country may import lithography equipment, machine tools, or process chemicals while building domestic capability around operation, maintenance, integration, and eventual substitution. The scenario engine should distinguish import seed, licensed production, joint development, domestic redesign, and sovereign closure.

### 15.5 Treat data gaps as model objects

A missing value should be represented as an explicit missingness type: not measured, not public, not applicable, contradictory, stale, or legally restricted. The system should produce “decision sensitivity to unknown” reports so that users can see which unmeasured variable controls feasibility.

### 15.6 Build around calibration events

Use historical shocks and completed industrial projects as calibration cases. For each event, reconstruct inventories, propagation, substitution, recovery, and price transmission. For each factory, reconstruct announcement, permitting, equipment arrival, commissioning, qualification, ramp, and output. The model earns credibility by explaining known histories before forecasting unknown futures.

## 16. Risks, missing data, and things that cannot currently be modeled reliably

| Risk or gap | Why it matters | Current status |
|---|---|---|
| Deep-tier supplier and inventory opacity | Determines true resilience and shock absorption | UNKNOWN / proprietary |
| Exact process yield and defect distributions | Controls usable output and cost | UNKNOWN outside selected public case studies |
| Tacit knowledge and workforce transfer | Determines ramp and troubleshooting | UNCERTAIN; no general quantitative law |
| Plant status versus actual production | Avoids false capacity | Partially observable; requires facility and company evidence |
| Re-export and contract manufacturing | Distorts country capability inference | Persistent trade-data limitation |
| High-purity and grade-specific materials | Commodity production may not satisfy advanced use | Under-measured; should be separate capability nodes |
| Customer qualification and standards | Production may not translate into saleable output | Usually customer-specific and proprietary |
| Policy and export-control tail risk | Can create discontinuous graph changes | Scenario-based; probabilities difficult to calibrate |
| Grid quality and connection queues | Nameplate power does not equal usable industrial power | Requires regional and site-level data |
| Ecological and water constraints | Can block factories even with energy/material supply | Incomplete cross-dataset integration |
| Informal and military-industrial production | Formal statistics omit important capacity | UNKNOWN or proxy-only |
| Commercial market-size reports | Definitions and shares vary by publisher | Use only as low-to-medium confidence estimates |
| IndiaBUILD API/licensing | Automated reuse may not be permitted or supported | No public endpoint found during inspection; verify terms |
| Humanoid benchmark semantics | Different robot definitions produce different BOMs | UNKNOWN until scenario is specified |

## 17. Deliverables and machine-readable appendices

This package includes the following supporting files:

| File | Purpose |
|---|---|
| `forge_world_source_map.csv` | Curated 42-record source map with domain, source type, access, coverage, limitations, and Forge use |
| `forge_world_humanoid_benchmark.csv` | Arithmetic envelope and scenario assumptions for the one-million-humanoid benchmark |
| `forge_world_capability_schema.json` | Draft node, edge, evidence, and dynamic-variable schema |
| `forge_world_wide_research.csv` / `.json` | Raw index of the twelve parallel stream summaries and returned research notes |
| `forge_notes/01.md` through `12.md` | Detailed stream research notes, including source inventories and follow-up leads |
| `indiabuild_verified_observations.md` | Direct homepage and engine-page observations |
| `indiabuild_how_it_works_verified.md` | Direct organizational and maturity-model observations |
| `swarajya_verified_observations.md` | Direct article observations and evidence-status cautions |
| `forge_verified_dataset_observations.md` | Direct Harvard Atlas and OECD ICIO observations |

## 18. Final assessment

The broad research supports FORGE WORLD as a consequential research direction, but it also changes the problem definition. The project is not primarily an encyclopedia, a company directory, a supply-chain dashboard, or a country ranking. It is an evidence-aware, time-dependent, uncertainty-bearing model of **capability formation and constrained physical flow**.

The system’s strongest differentiator would be the ability to answer not only “what is required?” but also: “what exact specification is required; which process makes it; which machine, material, facility, utility, workforce, standard, and license enable that process; which actors can currently do it; what is qualified versus merely announced; what quantity can be delivered at what yield; how long does the ramp take; which inputs are concentrated; what happens under a shock; and which substitution paths are physically and institutionally admissible?”

The correct next step is not immediate autonomous coding. It is a calibrated reference-case study—ideally one product with a manageable but deep industrial stack—where every edge is sourced or explicitly inferred, every unknown is visible, and the model is tested against a historical shock and a completed production ramp. The one-million-humanoid benchmark should remain a stress test for the ontology and scenario engine, not a conclusion that India can or cannot achieve the target based on public headlines alone.

# References

[1]: https://indiabuild.wiki/ "IndiaBUILD public homepage"
[2]: https://indiabuild.wiki/how-it-works "IndiaBUILD: How the map is organised"
[3]: https://indiabuild.wiki/engine "The IndiaBUILD Engine"
[4]: https://swarajyamag.com/economy/how-india-is-confronting-its-vulnerability-in-critical-mineral-supply-chains "Swarajya: How India Is Confronting Its Vulnerability In Critical Mineral Supply Chains"
[5]: https://www.wipo.int/innovation-capabilities-navigator "WIPO Innovation Capabilities Navigator"
[6]: https://www.wipo.int/en/web/economics/w/news/2026/ipo-launches-innovation-capabilities-navigator-to-support-evidence-based-innovation-policy "WIPO Navigator launch release"
[7]: https://atlas.hks.harvard.edu/data-downloads/ "Harvard Atlas data downloads and methodology"
[8]: https://www.oecd.org/en/data/datasets/inter-country-input-output-tables.html "OECD Inter-Country Input-Output tables"
[9]: https://comtrade.un.org/ "UN Comtrade database"
[10]: https://www.usgs.gov/centers/national-minerals-information-center/data "USGS National Minerals Information Center data"
[11]: https://globalenergymonitor.org/projects/global-integrated-power-tracker "Global Energy Monitor Global Integrated Power Tracker"
[12]: https://stat.unido.org/data/table "UNIDO Statistics Portal databases"
[13]: https://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=37 "CEPII BACI bilateral trade database"
[14]: https://www.ip-stats.wipo.int/ "WIPO IP Statistics Data Center"
[15]: https://www.iea.org/reports/the-role-of-critical-minerals-in-clean-energy-transitions "IEA: The Role of Critical Minerals in Clean Energy Transitions"
[16]: https://www.nrel.gov/critical-minerals/supply-chain-market-analysis "NREL critical-minerals supply-chain analysis"
[17]: https://rmis.jrc.ec.europa.eu/critical-and-strategic-materials "European Commission JRC Raw Materials Information System"
[18]: https://dodmrl.com/ "DoD Manufacturing Readiness Levels"
[19]: https://www.p-r-i.org/nadcap/getting-started "Performance Review Institute Nadcap accreditation guidance"
[20]: https://www.nasa.gov/reference/systems-engineering-handbook/ "NASA Systems Engineering Handbook"
[21]: https://www.nist.gov/publications/economics-digital-twins-costs-benefits-and-economic-decision-making "NIST: Economics of Digital Twins"
[22]: https://aws.amazon.com/blogs/industries/building-a-manufacturing-digital-thread-using-graph-and-generative-ai-on-aws/ "AWS: Manufacturing digital thread using graph and generative AI"
[23]: https://oec.world/en/ "Observatory of Economic Complexity"
[24]: https://ecoinvent.org/ "ecoinvent life-cycle inventory database"
[25]: https://nexus.openlca.org/database/USLCI "USLCI database via openLCA Nexus"
[26]: https://www.techinsights.com/blog/beyond-cost-estimates-why-teardown-analysis-your-cost-optimization-advantage "TechInsights teardown analysis"
[27]: https://www.ifixit.com/ "iFixit repair and teardown guides"
[28]: https://addverb.com/press-release/addverb-thrusts-india-into-humanoid-race/ "Addverb public robotics announcement"
[29]: https://www.mckinsey.com/industries/industrials/our-insights/turning-humanoid-supply-chain-constraints-into-billion-dollar-wins "McKinsey: Humanoid supply-chain constraints"
[30]: https://spectrum.ieee.org/ev-motor "IEEE Spectrum: EV motors without rare earths"
[31]: https://www.mpie.de/4554568/direct_reduction_with_hydrogen "Max Planck Institute: Hydrogen direct reduction research"
[32]: https://www.nature.com/articles/s44296-025-00083-7 "Nature: Lithium-ion battery recycling perspective"
[33]: https://unctad.org/news/red-sea-black-sea-and-panama-canal-unctad-raises-alarm-global-trade-disruptions "UNCTAD: Red Sea, Black Sea and Panama Canal disruptions"
[34]: https://unctad.org/news/critical-minerals-are-reshaping-global-trade-demand-surges "UNCTAD: Critical minerals and global trade"
[35]: https://i-tip.wto.org/ "WTO Integrated Trade Intelligence Portal"
[36]: https://www.eia.gov/ "U.S. Energy Information Administration"
[37]: https://www.worldbank.org/ "World Bank data and commodities resources"
