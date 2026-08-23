# AGENTS.md — FORGE WORLD

This repository is FORGE WORLD.

Before making any architectural, mathematical, data-model, product, or research change, **read `docs/FORGE_WORLD_NORTH_STAR.md` in full**. It is the canonical project source of truth and exists specifically to prevent scope drift.

Also review the relevant material under `research/` and the V0.1 correctness/validation documents under `docs/` before touching the corresponding subsystem.

## Non-negotiable project identity

FORGE WORLD is a **universal evidence-backed industrial intelligence, synthesis, design, execution, discovery, and learning system for physically meaningful futures**.

It is not a humanoid calculator, India-only dashboard, static IndiaBUILD clone, BOM explorer, supply-chain visualization, procurement directory, or generic LLM wrapper.

The same underlying industrial world model should eventually support objectives ranging from a table or 100 CNC machining centers to one million humanoids, nuclear buildouts, satellites, and reusable launch vehicles.

The product modes are:

- **ANALYZE** — Can this physical future happen? What does it require and what blocks it?
- **DESIGN** — What product/industrial architecture should be chosen given real capabilities and constraints?
- **EXECUTE** — We decided to build it; guide the work from architecture/BOM/processes/suppliers through qualification and production.
- **DISCOVER** — What capabilities should be built because they unlock the most valuable future industrial options?
- **LEARN** — Explain any branch of the industrial system progressively from intuitive to expert depth.

## Hard epistemic rules

- UNKNOWN stays UNKNOWN.
- Eligibility is not supply.
- Factory existence is not qualified capability.
- Nameplate is not effective capacity.
- Trade is not production capability.
- Patent ownership is not production capability.
- Project announcement is not operating capacity.
- Mineral reserve is not usable industrial material.
- Substitution is a dependency-graph rewrite, not a free switch.
- Precision-looking numbers require evidence, transparent derivation, or explicit assumptions.
- Strong verdicts such as `INFEASIBLE_UNDER_MODEL` must only be used when the model semantics justify them.
- LLM plausibility may never silently override physics, data, or model contracts.

Use explicit epistemic classes such as:

`MEASURED / REPORTED / DERIVED / ESTIMATED / MODELLED / ASSUMPTION / SCENARIO / UNKNOWN / CONFLICTED`

## Industrial-model requirements

Treat capability as a vector including, where relevant:

- design/IP;
- process knowledge;
- tacit know-how;
- machinery;
- tooling;
- metrology;
- materials/precursors;
- workforce;
- qualification;
- quality;
- yield;
- utilization;
- maturity;
- supplier readiness;
- scalable throughput;
- sovereignty/ownership;
- resilience;
- time to ramp.

Geography is first-class. Facilities, companies, suppliers, mines, refineries, ports, logistics, power, utilities, industrial clusters, and geopolitical chokepoints should eventually be part of the same world model.

Industrial time is endogenous. Preserve distinct physical, evidence, and decision clocks.

## Canonical registry direction

A major architectural target is a shared canonical registry for:

- capabilities;
- companies/builders;
- facilities;
- products/components;
- processes;
- machines/equipment;
- materials/minerals;
- locations;
- evidence/source versions.

Knowledge discovered in one vertical must become reusable in others. Example: precision grinding learned while modeling CNCs should be available when analyzing bearings, reducers, robotics, aerospace, and machine tools.

IndiaBUILD-style capability/builder knowledge should be treated as a valuable baseline layer and extended with quantitative physical reasoning, capacity, process, facility, geography, time, uncertainty, sourcing, shocks, and transformation synthesis.

## Recursion policy

FORGE must be able to recurse from product -> component -> process -> machine -> tooling/metrology -> material -> upstream process -> facility/supplier, including machines that build machines.

Do not recurse infinitely. Use **lazy strategic recursion**: go deeper when a node is decision-sensitive, bottlenecked, strategically concentrated, high-cost, long-lead, high-uncertainty, hard to substitute, or important to sovereignty/feasibility.

## Current implementation state

V0.1 is the merged correctness foundation. It substantially improved the requirement-flow core, DVA semantics, unit safety, foreign-supply epistemics, temporal causality, transformations, proof/evidence graph, reproducibility, and mathematical oracles.

Treat V0.1 as the computational kernel, **not** as the completed FORGE vision.

Do not mistake the existence of modules such as planner/frontier/VOI/option-value/reverse-buildability for complete realization of the long-term feature.

## Existing research is part of the project memory

The `research/` directory contains foundational due-diligence work, including IndiaBUILD, Swarajya industrial intelligence, global capability analogues, physical-economy data, industry decomposition, foundational recursion, supplier qualification, industrial shocks, substitution, existing systems, the one-million-humanoid benchmark, and missing-dimensions analysis.

Use it. Do not assume every secondary claim is a hard model parameter; preserve evidence discipline and trace to primary sources where feasible.

## Development behavior

Prefer:

- deep correctness over feature-name breadth;
- reusable industrial abstractions over one-off vertical hacks;
- explicit assumptions over hidden defaults;
- evidence-linked state over prose claims;
- counterexamples and hand-derived oracles for mathematical semantics;
- coherent model contracts;
- small, reviewable commits;
- honest documentation of deferred depth.

Avoid:

- hardcoding flagship outcomes;
- tuning data to preserve an old headline;
- fake completeness;
- adding bureaucracy that does not materially improve truth or execution;
- shallow modules that exist only so a feature can be claimed;
- decorative evidence links that do not represent causal provenance.

## Long-term benchmark questions

Use these as recurring tests of whether the architecture remains general:

1. Can humanity manufacture 1,000,000 humanoids/year by 2030?
2. Can India manufacture 1,000,000 humanoids/year at >=70% recursive DVA without Chinese permanent magnets?
3. Help manufacture 100 high-quality CNC machining centers end-to-end.
4. What would it take for India to add 200 GW of nuclear generation by a target year?
5. What industrial system is required to produce 100 reusable launch vehicles/year?
6. Given the current world, what is the maximum achievable output and which intervention raises the ceiling most?
7. Which foundational capabilities have the highest cross-sector industrial option value?

## Final rule

The strongest FORGE output is not a polished paragraph or a numerical score.

It is an **auditable computational argument about industrial possibility, plus a credible path to change that possibility and help execute the result**.
