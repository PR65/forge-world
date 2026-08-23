# Alpha benchmark verified observations

**Observed:** 2026-08-24
**Scope:** primary-source checks for the CNC and nuclear alpha benchmarks

These observations are source anchors, not automatic solver parameters. Each numerical
or categorical use still requires an evidence record with the correct scope and
epistemic class.

## Nuclear buildout

### Policy objective is 100 GWe, not the FORGE 200 GW scenario

The Press Information Bureau's 4 December 2025 parliamentary answer describes the
Nuclear Energy Mission for Viksit Bharat as targeting 100 GWe of nuclear generation
capacity by 2047. It describes a two-pronged strategy: indigenous 700 MWe PHWRs and
large imported reactors, alongside small reactors including a roughly 200 MWe Bharat
Small Modular Reactor and a 55 MWe design. It states that a roadmap was prepared by the
Department of Atomic Energy, Ministry of Power, and Central Electricity Authority.

Source: https://www.pib.gov.in/PressReleasePage.aspx?PRID=2198951

The 12 August 2026 PIB parliamentary answer repeats the 100 GWe by 2047 objective and
the target of at least five indigenous SMRs by 2033. It describes the SMR designs as
being under design and development.

Source: https://www.pib.gov.in/PressReleasePage.aspx?PRID=2298208

**FORGE use:** the campaign's 200 GW case is a `SCENARIO`, not a reported government
target. A design under development is not operating capacity.

### Approved PHWR fleet is a project pipeline, not available supply

NPCIL's official overview states that the Government of India approved and financially
sanctioned ten 700 MW PHWR units in fleet mode at Kaiga, Gorakhpur, Chutka, and Mahi
Banswara.

Source: https://npcil.nic.in/content/328_1_AboutNPCIL.aspx

**FORGE use:** this supports project existence and programme architecture. It does not
establish commissioning dates, annual component throughput, effective capacity, yield,
or qualification fractions.

### Specific equipment capability exists; its annual envelope remains unknown

BHEL's official product page reports capability to manufacture nuclear steam generators
and reactor headers to ASME Section III NB Class 1 requirements, and nuclear steam
turbines and generators up to 700 MWe. The page also lists several nuclear heat
exchanger and balance-of-plant product classes.

Source: https://bhel.com/product-services

A BHEL release dated 9 July 2021 reports an NPCIL fleet-mode order for 12 steam
generators and refers to an order for 32 reactor-header assemblies for 700 MWe PHWRs.

Source: https://tenders.bhel.com/bhel-bags-order-nuclear-steam-generators-npcil-against-stiff-competition

**FORGE use:** these sources support `REPORTED` product/manufacturing activity at a
specified equipment class. Neither source establishes current qualified annual
throughput, utilization, yield, availability, or the capacity needed for a 200 GW
programme. Those fields remain `UNKNOWN` unless separately evidenced.

### Nuclear manufacture is gated by explicit QA regimes

The Atomic Energy Regulatory Board's codes-and-guides catalogue lists quality-assurance
requirements for nuclear power plants, including guides covering manufacture of items,
site construction, commissioning, and operation.

Source: https://aerb.gov.in/english/publications/codes-guides

**FORGE use:** nuclear equipment and site work require explicit qualification/QA gates.
The existence of a general fabrication process or factory cannot silently satisfy a
nuclear-grade manufacturing requirement.

## CNC machining centers

### Public programmes demonstrate activity, not 100-machine qualified capacity

The Ministry of Heavy Industries describes its Capital Goods Scheme Phase I as having
supported machine-tool technology development, including a turn-mill centre and a
four-guideway CNC lathe, plus the integrated Machine Tools Park at Tumakuru and a common
test/certification centre.

Source: https://heavyindustries.gov.in/en/scheme-enhancement-competitiveness-indian-capital-goods-sector-phase-i

The Ministry's approved-projects page lists an IIT Madras machine-tools and production-
technology centre of excellence with industry partners including Jyoti CNC, Micromatic
Grinding Technologies, and Ace Designers.

Source: https://heavyindustries.gov.in/en/projects-approved-under-scheme

**FORGE use:** these are `REPORTED` programme, development, and builder-activity signals.
They do not prove that any participant can deliver 100 machines per year at the alpha
benchmark's accuracy, reliability, localization, or customer-qualification envelope.

### Critical component recursion is officially recognized

The Ministry's machine-tool strategic plan identifies anti-friction linear guideways,
ball screws, precision spindle and ball-screw support bearings, CNC controls, and
spindle/axis servo motors with controllers as critical machine-tool components needing
domestic manufacturing development.

Source: https://www.heavyindustries.gov.in/sites/default/files/2023-07/Strategic_Plan_dhi.pdf

**FORGE use:** this supports the benchmark's component-recursion structure. Because the
document is old and does not establish current status, present-day capability and
throughput remain `UNKNOWN` unless newer evidence supports them.

## Epistemic decisions

- Policy target != modeled scenario.
- Project approval != commissioned capacity.
- Product-class manufacturing != benchmark-qualified capability.
- Order quantity != annual effective throughput.
- Builder participation != builder capability assessment.
- A historical gap statement is not proof that the gap still exists.
- QA catalogue existence establishes a gate, not that a supplier has passed it.
