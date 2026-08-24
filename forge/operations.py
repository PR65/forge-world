"""Operational industrial-intelligence projections over the FORGE world model.

This module deliberately does not introduce a second solver.  It converts the
existing evidence-linked graph and solver response into things a user can act on:

* a concise case brief;
* exact, structured evidence-resolution tasks;
* a make/buy/qualify execution plan;
* immutable architecture comparisons;
* a topology-derived cross-sector capability leverage ranking;
* causal shock deltas and paths; and
* a multi-year programme projection when a pack declares ``program_model``.

Every output carries an epistemic label.  A missing capacity observation remains
UNKNOWN and never becomes an inferred supplier or a zero-output fact.
"""
from __future__ import annotations

import copy
import math
from collections import defaultdict, deque
from dataclasses import dataclass, replace
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from .capacity import capacity_envelope
from .engine import DEFAULT_YEARS, ObjectiveSpecInput
from .epistemics import ResultClass
from .evidence import ProofGraph
from .explode import ExplosionResult, explode_variant
from .model import (
    CapabilityClaim,
    CapacitySegment,
    Entity,
    ForeignSupplySegment,
    Organization,
    Part,
    ProductionRecipe,
    Project,
    Qualification,
    Shock,
    World,
)
from .pack import KnowledgePack
from .registry import CanonicalRegistry
from .shocks import apply_shocks
from .solve import ScenarioOptions, SolveResult, solve_objective
from .substitutions import apply_substitution, validate_substitution


DEPENDENCY_RELATIONS = {
    "decomposes_into",
    "produced_via",
    "requires_input",
    "requires_equipment",
    "requires_tool",
    "requires_capability",
    "requires_qualification",
    "gated_by",
    "recurses_into",
    "supplied_by",
    "located_at",
}


def _years(deadline_year: int) -> List[int]:
    years = [year for year in DEFAULT_YEARS if year <= deadline_year]
    if deadline_year not in years:
        years.append(deadline_year)
    return sorted(set(years))


def _require_variant(pack: KnowledgePack, variant_id: str) -> None:
    if variant_id not in pack.variants or not pack.world.has(variant_id):
        raise KeyError(f"unknown product variant '{variant_id}'")


def _opts(obj: ObjectiveSpecInput) -> ScenarioOptions:
    return ScenarioOptions(
        funded_project_ids=set(obj.funded_projects),
        capacity_overrides=dict(obj.analyst_capacity_assumptions),
        cost_domestic=dict(obj.cost_domestic),
        cost_import=dict(obj.cost_import),
        geography=obj.geography,
        min_domestic_share=obj.min_dva,
        per_item_import_cap=dict(obj.per_item_import_cap),
        funded_pipeline="selected_only" if obj.funded_projects else "optimistic",
        foreign_supply_policy=obj.foreign_supply_policy,
    )


def _result_summary(result: SolveResult) -> Dict[str, Any]:
    return {
        "result_class": result.result_class.value,
        "blocking_unknowns": list(result.blocking_unknowns),
        "binding_summary": list(result.binding_summary),
        "required_relaxations": list(result.required_relaxations[:12]),
        "closure_candidates": list(result.closure_candidates[:12]),
        "max_shortfall_item": result.max_shortfall_item,
        "max_shortfall_year": result.max_shortfall_year,
    }


def _entity_name(world: World, entity_id: str) -> str:
    entity = world.entities.get(entity_id)
    return entity.name if entity is not None else entity_id.replace("_", " ").title()


def _entity_evidence_class(pack: KnowledgePack, entity: Optional[Entity]) -> str:
    if entity is None:
        return "UNKNOWN"
    classes = {
        pack.evidence[claim_id].epistemic_class.value
        for claim_id in getattr(entity, "evidence_ids", ()) or ()
        if claim_id in pack.evidence
    }
    if not classes:
        return "UNKNOWN"
    for candidate in (
        "CONFLICTED",
        "UNKNOWN",
        "SCENARIO",
        "ASSUMPTION",
        "ESTIMATED",
        "MODELLED",
        "DERIVED",
        "REPORTED",
        "MEASURED",
    ):
        if candidate in classes:
            return candidate
    return "UNKNOWN"


def _dependency_ancestors(
    world: World,
    start_ids: Iterable[str],
    *,
    roots: Optional[Set[str]] = None,
    max_depth: int = 12,
) -> Tuple[Set[str], List[List[str]]]:
    """Walk backwards from dependencies to the products that consume them."""

    root_ids = roots or {
        entity.id for entity in world.entities.values() if entity.kind == "product_variant"
    }
    reached: Set[str] = set()
    paths: List[List[str]] = []
    queue: deque[Tuple[str, List[str], int]] = deque(
        (start, [start], 0) for start in sorted(set(start_ids)) if world.has(start)
    )
    seen: Set[Tuple[str, str]] = set()
    while queue:
        current, path, depth = queue.popleft()
        if current in root_ids:
            reached.add(current)
            paths.append(path)
            continue
        if depth >= max_depth:
            continue
        for edge in sorted(world.in_edges(current), key=lambda row: (row.src, row.relation)):
            if edge.relation not in DEPENDENCY_RELATIONS:
                continue
            key = (edge.src, current)
            if key in seen:
                continue
            seen.add(key)
            queue.append((edge.src, path + [edge.src], depth + 1))
    paths.sort(key=lambda row: (len(row), row))
    return reached, paths[:20]


def _source_plan(entity: Optional[Entity], missing_variable: str) -> List[str]:
    kind = getattr(entity, "kind", "entity")
    if missing_variable == "qualified_effective_capacity":
        return [
            "facility-level audited output or production log for the exact specification",
            "customer or regulator qualification record tied to the facility and product",
            "nameplate, availability, utilization, yield, allocation, and validity-period evidence",
        ]
    if kind in {"equipment_class", "recipe"}:
        return [
            "machine builder technical specification and installed-base reference",
            "process capability study with tolerance, yield, and cycle-time evidence",
            "metrology or acceptance record traceable to the required specification",
        ]
    if kind == "qualification":
        return [
            "qualifier or regulator approval record",
            "standard edition and product/facility scope",
            "audit, test, non-conformance, and validity records",
        ]
    return [
        "primary supplier or facility disclosure scoped to the exact item",
        "independent customer, regulator, certification, or audited corroboration",
        "dated evidence for specification, geography, qualification, and usable quantity",
    ]


def build_research_queue(
    pack: KnowledgePack,
    objective: ObjectiveSpecInput,
    solve_response: Mapping[str, Any],
    *,
    limit: int = 24,
) -> List[Dict[str, Any]]:
    """Turn decision-sensitive UNKNOWNs into executable evidence requests."""

    world = pack.world
    voi_rows = {
        str(row.get("item_id", row.get("unknown_id", ""))): row
        for row in solve_response.get("voi", ()) or ()
    }
    # Solver blocking_unknowns may contain human-readable aggregate messages.
    # Only world entity IDs become research targets; the per-item capacity rows
    # provide the authoritative structured fallback.
    blocking = [
        str(value)
        for value in solve_response.get("result", {}).get("blocking_unknowns", ()) or ()
        if world.has(str(value))
    ]
    for row in solve_response.get("capacity_envelopes", ()) or ():
        if row.get("epistemic") == "UNKNOWN" and row.get("item") not in blocking:
            blocking.append(str(row.get("item")))

    raw_tasks = pack.raw.get("research_tasks", ()) or ()
    execution_model = pack.raw.get("execution_model", {}) or {}
    if not raw_tasks and isinstance(execution_model, Mapping):
        raw_tasks = execution_model.get("research_tasks", ()) or ()
    explicit_by_target: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    if isinstance(raw_tasks, list):
        for row in raw_tasks:
            if isinstance(row, Mapping):
                explicit_by_target[str(row.get("target_entity_id", ""))].append(row)

    # Pack-authored tasks are explicit expert assertions of decision relevance,
    # including architecture alternatives and capital-equipment recursion that
    # may not appear as solver demand lines.  Keep all valid targets visible.
    active_explicit: List[str] = [
        target_id
        for target_id in explicit_by_target
        if target_id and world.has(target_id)
    ]
    blocking = active_explicit + [item_id for item_id in blocking if item_id not in active_explicit]

    output: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for rank, item_id in enumerate(blocking):
        if not item_id or item_id in seen:
            continue
        seen.add(item_id)
        entity = world.entities.get(item_id)
        name = _entity_name(world, item_id)
        spec = getattr(entity, "spec", "") if entity is not None else ""
        voi = voi_rows.get(item_id, {})
        sensitivity = voi.get("voi_score", voi.get("score", voi.get("priority_score")))
        explicit = explicit_by_target.get(item_id, [])
        if explicit:
            base = dict(explicit[0])
            question = str(base.get("question", "")).strip()
            missing_variable = str(base.get("missing_variable", "qualified_effective_capacity"))
            source_plan = list(base.get("suggested_source_types", ()) or ()) or _source_plan(
                entity, missing_variable
            )
            capture_fields = list(base.get("capture_fields", ()) or ())
            title = str(base.get("title", f"Resolve {name}"))
            task_id = str(base.get("id", f"research:{pack.pack_id}:{item_id}"))
            decision = str(base.get("decision", "Adjudicate the active production objective"))
            priority = str(base.get("priority", "high" if rank < 8 else "medium"))
        else:
            missing_variable = "qualified_effective_capacity"
            qualifier = f" for specification {spec}" if spec else " for the required specification"
            question = (
                f"Determine annual qualified effective capacity for {name}{qualifier} in "
                f"{objective.geography} by {objective.deadline_year}; report facility, nameplate, "
                "availability, utilization, yield, qualification fraction, customer allocation, "
                "validity period, and contradictory evidence separately."
            )
            source_plan = _source_plan(entity, missing_variable)
            capture_fields = [
                "facility_id",
                "item_and_specification",
                "nameplate_annual",
                "availability",
                "utilization",
                "yield_fraction",
                "qualification_fraction",
                "allocated_fraction",
                "valid_from",
                "valid_to",
                "source_url",
                "license",
            ]
            title = f"Resolve qualified supply for {name}"
            task_id = f"research:{pack.pack_id}:{item_id}"
            decision = (
                f"Whether {objective.annual_units:g}/year of {objective.variant_id} can be "
                f"adjudicated in {objective.geography}"
            )
            priority = "critical" if rank < 5 else "high" if rank < 12 else "medium"

        output.append(
            {
                "id": task_id,
                "title": title,
                "target_entity_id": item_id,
                "target_name": name,
                "missing_variable": missing_variable,
                "question": question,
                "decision": decision,
                "decision_sensitivity": sensitivity,
                "priority": priority,
                "source_plan": source_plan,
                "capture_fields": capture_fields,
                "workflow": [
                    "SOURCE_PLAN",
                    "CAPTURE_OBSERVATION",
                    "RECONCILE",
                    "HUMAN_APPROVAL",
                    "SCENARIO_OVERLAY",
                    "RE_RUN",
                ],
                "epistemic_class": "UNKNOWN",
                "persistent_world_mutation": False,
            }
        )
        if len(output) >= max(1, min(limit, 100)):
            break
    return output


def _capacity_posture(
    pack: KnowledgePack,
    item_id: str,
    objective: ObjectiveSpecInput,
) -> Tuple[str, str, Dict[str, Any]]:
    env = capacity_envelope(
        pack.world,
        item_id,
        objective.deadline_year,
        geography=objective.geography,
        funded_project_ids=(set(objective.funded_projects) or None),
    )
    if env.domestic.is_unknown():
        part = pack.world.entities.get(item_id)
        countries = list(getattr(part, "supplied_by_countries", ()) or ())
        posture = "BUY_OR_MAKE_RESEARCH_REQUIRED" if countries else "MAKE_BUY_UNRESOLVED"
        reason = "Qualified effective domestic capacity is UNKNOWN."
    elif (env.domestic.hi or 0.0) > 0:
        posture = "MAKE_CANDIDATE_EVIDENCED_CAPACITY"
        reason = "A domestic capacity envelope exists; specification and allocation still require checking."
    else:
        posture = "BUY_CANDIDATE_NO_DOMESTIC_CAPACITY_IN_MODEL"
        reason = "The current scoped model has an evidenced zero domestic envelope."
    return posture, reason, {
        "lo": env.domestic.lo,
        "hi": env.domestic.hi,
        "unknown": env.domestic.is_unknown(),
        "epistemic": env.epistemic,
        "unknown_reasons": list(env.unknown_reasons),
    }


def build_execution_plan(
    pack: KnowledgePack,
    objective: ObjectiveSpecInput,
    solve_response: Mapping[str, Any],
    research_queue: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Derive an execution workbench from real graph, recipe, and gate state."""

    world = pack.world
    explosion_rows = solve_response.get("explosion", {}).get("items", ()) or ()
    demand_by_item = {str(row["item"]): row for row in explosion_rows}
    make_buy: List[Dict[str, Any]] = []
    process_routes: List[Dict[str, Any]] = []
    qualifications: List[Dict[str, Any]] = []
    machinery: Dict[str, Dict[str, Any]] = {}

    recipes_by_output: Dict[str, List[ProductionRecipe]] = defaultdict(list)
    for entity in world.entities.values():
        if isinstance(entity, ProductionRecipe):
            recipes_by_output[entity.output_part].append(entity)

    qualification_by_item: Dict[str, List[Qualification]] = defaultdict(list)
    for entity in world.entities.values():
        if isinstance(entity, Qualification):
            qualification_by_item[entity.item_id].append(entity)

    for item_id, demand in sorted(
        demand_by_item.items(), key=lambda row: (-float(row[1].get("gross", 0.0)), row[0])
    ):
        entity = world.entities.get(item_id)
        if entity is None or entity.kind in {"recipe", "product_variant"}:
            continue
        posture, reason, envelope = _capacity_posture(pack, item_id, objective)
        supplier_countries = list(getattr(entity, "supplied_by_countries", ()) or ())
        linked_suppliers = [
            _entity_name(world, edge.dst)
            for edge in world.out_edges(item_id, "supplied_by")
            if world.has(edge.dst)
        ]
        claim_candidates = []
        for claim in world.entities.values():
            if not isinstance(claim, CapabilityClaim) or claim.capability_item != item_id:
                continue
            organization = world.entities.get(claim.org_id)
            facilities = [
                facility.id
                for facility in world.entities.values()
                if getattr(facility, "kind", "") == "facility"
                and (
                    getattr(facility, "owner_org", "") == claim.org_id
                    or getattr(facility, "operator_org", "") == claim.org_id
                )
            ]
            claim_candidates.append(
                {
                    "organization_id": claim.org_id,
                    "organization_name": getattr(organization, "name", claim.org_id),
                    "claim_id": claim.id,
                    "claim_vs_assessment": claim.claim_vs_assessment,
                    "capability_vector": claim.vector.to_json(),
                    "facility_ids": sorted(facilities),
                    "evidence_ids": list(claim.evidence_ids),
                    "epistemic_class": _entity_evidence_class(pack, claim),
                    "qualified_supply_asserted": False,
                }
            )
        make_buy.append(
            {
                "item_id": item_id,
                "name": entity.name,
                "specification": getattr(entity, "spec", ""),
                "demand_annual": demand.get("gross"),
                "unit": demand.get("unit"),
                "posture": posture,
                "reason": reason,
                "capacity_envelope": envelope,
                "candidate_supplier_countries": supplier_countries,
                "linked_supplier_candidates": linked_suppliers,
                "capability_claim_candidates": claim_candidates,
                "supplier_status": (
                    "CANDIDATES_NOT_QUALIFIED"
                    if supplier_countries or linked_suppliers or claim_candidates
                    else "UNKNOWN"
                ),
                "epistemic_class": _entity_evidence_class(pack, entity),
                "evidence_ids": list(getattr(entity, "evidence_ids", ()) or ()),
                "human_approval_required": True,
            }
        )

        for recipe in sorted(recipes_by_output.get(item_id, ()), key=lambda row: row.id):
            step_rows: List[Dict[str, Any]] = []
            for step in recipe.steps:
                equipment = sorted(set(step.equipment_classes))
                for equipment_id in equipment:
                    eq = world.entities.get(equipment_id)
                    machinery[equipment_id] = {
                        "equipment_id": equipment_id,
                        "name": _entity_name(world, equipment_id),
                        "domestically_producible": getattr(eq, "domestically_producible", None),
                        "dominant_supplier_countries": list(
                            getattr(eq, "dominant_supplier_countries", ()) or ()
                        ),
                        "epistemic_class": _entity_evidence_class(pack, eq),
                        "supports_items": sorted(
                            set(machinery.get(equipment_id, {}).get("supports_items", ()))
                            | {item_id}
                        ),
                    }
                step_rows.append(
                    {
                        "id": step.id,
                        "name": step.name,
                        "equipment_ids": equipment,
                        "resource_ids": list(step.resource_classes),
                        "cycle_time": str(step.cycle_time_per_unit) if step.cycle_time_per_unit else None,
                        "yield_fraction": step.yield_fraction,
                        "environment": step.environment,
                        "labor_skills": list(step.labor_skill),
                    }
                )
            process_routes.append(
                {
                    "item_id": item_id,
                    "recipe_id": recipe.id,
                    "route_name": recipe.name,
                    "route_type": recipe.route_type,
                    "maturity": recipe.maturity,
                    "steps": step_rows,
                    "required_qualification_ids": list(recipe.requires_qualification),
                    "evidence_ids": list(recipe.evidence_ids),
                    "epistemic_class": _entity_evidence_class(pack, recipe),
                }
            )

        for qualification in qualification_by_item.get(item_id, ()):
            qualifications.append(
                {
                    "qualification_id": qualification.id,
                    "item_id": item_id,
                    "name": qualification.name,
                    "qualifier": qualification.qualifier,
                    "standard_ref": qualification.standard_ref,
                    "status": qualification.status,
                    "latency_months": list(qualification.latency_months),
                    "evidence_ids": list(qualification.evidence_ids),
                    "epistemic_class": _entity_evidence_class(pack, qualification),
                    "human_approval_required": True,
                }
            )

    raw_execution = pack.raw.get("execution_model", {}) or {}
    explicit_packages = raw_execution.get("work_packages", ()) if isinstance(raw_execution, Mapping) else ()
    work_packages: List[Dict[str, Any]] = []
    if isinstance(explicit_packages, list):
        for row in explicit_packages:
            if isinstance(row, Mapping):
                work_packages.append(dict(row))

    if not work_packages:
        work_packages = [
            {
                "id": "wp_architecture_freeze",
                "name": "Freeze reference architecture and acceptance envelope",
                "phase": "DESIGN",
                "depends_on": [],
                "acceptance_criteria": [
                    "Variant and functional requirements approved by responsible engineers",
                    "Every decision-sensitive assumption is listed and owned",
                ],
                "epistemic_class": "MODELLED",
                "human_approval_required": True,
            },
            {
                "id": "wp_supply_resolution",
                "name": "Resolve make/buy and qualified supplier evidence",
                "phase": "SOURCE",
                "depends_on": ["wp_architecture_freeze"],
                "acceptance_criteria": [
                    "Facility, specification, effective capacity, allocation, and qualification are evidenced",
                    "Alternatives and country dependencies are recorded without equating eligibility to supply",
                ],
                "epistemic_class": "MODELLED",
                "human_approval_required": True,
            },
            {
                "id": "wp_process_qualification",
                "name": "Qualify manufacturing routes, tooling, metrology, and operators",
                "phase": "QUALIFY",
                "depends_on": ["wp_supply_resolution"],
                "acceptance_criteria": [
                    "Route-specific process capability and measurement-system analysis pass",
                    "Non-conformance, calibration, traceability, and change-control plans are approved",
                ],
                "epistemic_class": "MODELLED",
                "human_approval_required": True,
            },
            {
                "id": "wp_pilot",
                "name": "Build and accept pilot units before rate commitment",
                "phase": "PILOT",
                "depends_on": ["wp_process_qualification"],
                "acceptance_criteria": [
                    "Pilot units pass product acceptance and reliability testing",
                    "Observed yield and cycle time replace planning assumptions",
                ],
                "epistemic_class": "MODELLED",
                "human_approval_required": True,
            },
            {
                "id": "wp_rate_ramp",
                "name": "Ramp under controlled capacity and quality gates",
                "phase": "RAMP",
                "depends_on": ["wp_pilot"],
                "acceptance_criteria": [
                    "Effective capacity, allocation, yield, and field quality remain within approved control limits"
                ],
                "epistemic_class": "MODELLED",
                "human_approval_required": True,
            },
        ]

    critical_path = sorted(
        qualifications,
        key=lambda row: (-float(row["latency_months"][1]), row["qualification_id"]),
    )[:12]
    next_actions = [
        {
            "action": "RESEARCH_THIS",
            "task_id": row.get("id"),
            "title": row.get("title"),
            "why_now": row.get("decision"),
            "epistemic_class": "UNKNOWN",
            "human_approval_required": True,
        }
        for row in research_queue[:8]
    ]
    next_actions.extend(
        {
            "action": "QUALIFY",
            "qualification_id": row["qualification_id"],
            "title": f"Plan and confirm {row['name']}",
            "why_now": f"Current state: {row['status']}; planning latency {row['latency_months']}",
            "epistemic_class": row["epistemic_class"],
            "human_approval_required": True,
        }
        for row in critical_path[:4]
    )

    return {
        "objective": {
            "variant_id": objective.variant_id,
            "annual_units": objective.annual_units,
            "geography": objective.geography,
            "deadline_year": objective.deadline_year,
        },
        "make_buy": make_buy[:80],
        "process_routes": process_routes[:80],
        "machinery_requirements": sorted(machinery.values(), key=lambda row: row["equipment_id"]),
        "qualification_tasks": qualifications,
        "work_packages": work_packages,
        "critical_path_candidates": critical_path,
        "next_actions": next_actions,
        "recommendation_epistemic_class": "MODELLED",
        "approval_boundary": (
            "This is a model-derived execution structure, not an approved engineering, procurement, "
            "supplier-qualification, safety, or investment decision."
        ),
    }


def build_case_brief(
    pack: KnowledgePack,
    objective: ObjectiveSpecInput,
    solve_response: Mapping[str, Any],
    research_queue: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    result = solve_response.get("result", {})
    result_class = str(result.get("result_class", "NOT_ADJUDICABLE"))
    if result_class == ResultClass.FEASIBLE.value:
        conclusion = "The objective is feasible under the checked model and stated scenario."
    elif result_class == ResultClass.INFEASIBLE_UNDER_MODEL.value:
        conclusion = "The objective is infeasible under the checked model and stated constraints."
    elif result_class == ResultClass.CONDITIONALLY_FEASIBLE.value:
        conclusion = "The objective is conditionally feasible only if the listed conditions hold."
    else:
        conclusion = "The objective cannot yet be adjudicated because decision-critical evidence is missing."

    capacity_rows = list(solve_response.get("capacity_envelopes", ()) or ())
    demand = {
        str(row.get("item")): float(row.get("gross", 0.0))
        for row in solve_response.get("explosion", {}).get("items", ()) or ()
    }
    bottlenecks: List[Dict[str, Any]] = []
    blocking = set(result.get("blocking_unknowns", ()) or ())
    for row in capacity_rows:
        item_id = str(row.get("item", ""))
        deadline = (row.get("by_year", {}) or {}).get(str(objective.deadline_year), {})
        unknown = bool(deadline.get("unknown", row.get("epistemic") == "UNKNOWN"))
        if item_id not in blocking and not unknown:
            continue
        bottlenecks.append(
            {
                "item_id": item_id,
                "name": _entity_name(pack.world, item_id),
                "demand_annual": demand.get(item_id),
                "unit": row.get("unit"),
                "status": "UNKNOWN_CAPACITY" if unknown else "MODELED_SHORTFALL",
                "reasons": list(deadline.get("reasons", ())) or list(row.get("reasons", ())),
                "epistemic_class": "UNKNOWN" if unknown else str(row.get("epistemic", "MODELLED")),
            }
        )
    bottlenecks.sort(key=lambda row: (-float(row.get("demand_annual") or 0.0), row["item_id"]))

    alternatives = []
    for substitution_id, contract in sorted(pack.substitutions.items()):
        check = validate_substitution(pack.world, contract, variant_id=objective.variant_id)
        alternatives.append(
            {
                "id": substitution_id,
                "name": contract.get("name", substitution_id),
                "replaces_part": contract.get("replaces_part"),
                "maturity": contract.get("maturity"),
                "eligible_for_comparison": check.accepted,
                "reasons": check.reasons,
                "performance_delta": contract.get("performance_delta", {}),
                "epistemic_class": "MODELLED",
            }
        )

    critical_dependencies = sorted(
        (
            {
                "item_id": row.get("item"),
                "name": _entity_name(pack.world, str(row.get("item"))),
                "gross_annual": row.get("gross"),
                "unit": row.get("unit"),
                "depth": row.get("depth"),
                "recipe_id": row.get("recipe"),
                "epistemic_class": _entity_evidence_class(
                    pack, pack.world.entities.get(str(row.get("item")))
                ),
            }
            for row in solve_response.get("explosion", {}).get("items", ()) or ()
            if int(row.get("depth", 0)) > 0
        ),
        key=lambda row: (-float(row.get("gross_annual") or 0.0), row["item_id"]),
    )[:12]

    return {
        "target": {
            "pack_id": pack.pack_id,
            "variant_id": objective.variant_id,
            "annual_units": objective.annual_units,
            "geography": objective.geography,
            "deadline_year": objective.deadline_year,
            "minimum_dva": objective.min_dva,
        },
        "conclusion": conclusion,
        "result_class": result_class,
        "top_bottlenecks": bottlenecks[:8],
        "important_unknowns": list(research_queue[:8]),
        "architecture_alternatives": alternatives,
        "critical_dependencies": critical_dependencies,
        "conditions": list(result.get("conditional_reasons", ()) or ()),
        "required_relaxations": list(result.get("required_relaxations", ()) or ())[:8],
        "explore_actions": ["WHY", "FIND_A_PATH", "RESEARCH_THIS", "REDESIGN", "EXECUTE"],
    }


def compare_design(
    pack: KnowledgePack,
    objective: ObjectiveSpecInput,
    substitution_id: str,
    *,
    shock_ids: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Compare one validated graph rewrite against an immutable baseline."""

    _require_variant(pack, objective.variant_id)
    if substitution_id not in pack.substitutions:
        raise KeyError(f"unknown substitution '{substitution_id}'")
    contract = pack.substitutions[substitution_id]
    check = validate_substitution(pack.world, contract, variant_id=objective.variant_id)
    if not check.accepted:
        return {
            "substitution_id": substitution_id,
            "accepted": False,
            "reasons": check.reasons,
            "functional_envelope": check.envelope_report,
            "epistemic_class": "MODELLED",
        }

    years = _years(objective.deadline_year)
    pg_base = ProofGraph()
    pg_alt = ProofGraph()
    baseline_world = copy.deepcopy(pack.world)
    alternative_world = copy.deepcopy(pack.world)
    baseline_explosion = explode_variant(
        baseline_world, pg_base, objective.variant_id, objective.annual_units, years
    )
    alternative_seed = explode_variant(
        alternative_world, pg_alt, objective.variant_id, objective.annual_units, years
    )
    alternative_explosion = apply_substitution(
        alternative_world, pg_alt, alternative_seed, contract
    )

    base_opts = _opts(objective)
    alt_opts = _opts(objective)
    if shock_ids:
        baseline_world, base_opts, _ = apply_shocks(
            baseline_world, pg_base, list(shock_ids), base_opts
        )
        alternative_world, alt_opts, _ = apply_shocks(
            alternative_world, pg_alt, list(shock_ids), alt_opts
        )
    baseline_result = solve_objective(
        baseline_world, pg_base, baseline_explosion, years, base_opts
    )
    alternative_result = solve_objective(
        alternative_world, pg_alt, alternative_explosion, years, alt_opts
    )

    base_items = set(baseline_explosion.items())
    alt_items = set(alternative_explosion.items())
    changed: List[Dict[str, Any]] = []
    for item_id in sorted(base_items | alt_items):
        base_line = baseline_explosion.get(item_id)
        alt_line = alternative_explosion.get(item_id)
        base_value = base_line.gross_annual.value if base_line else 0.0
        alt_value = alt_line.gross_annual.value if alt_line else 0.0
        if math.isclose(base_value, alt_value, rel_tol=1e-12, abs_tol=1e-12):
            continue
        changed.append(
            {
                "item_id": item_id,
                "name": _entity_name(alternative_world, item_id),
                "baseline_gross_annual": base_value,
                "alternative_gross_annual": alt_value,
                "delta": alt_value - base_value,
                "unit": (
                    alt_line.gross_annual.unit
                    if alt_line
                    else base_line.gross_annual.unit if base_line else "pcs"
                ),
                "change": "ADDED" if item_id not in base_items else "REMOVED" if item_id not in alt_items else "RESIZED",
            }
        )

    return {
        "substitution_id": substitution_id,
        "name": contract.get("name", substitution_id),
        "accepted": True,
        "functional_envelope": check.envelope_report,
        "requirements_change": contract.get("performance_delta", {}),
        "transition_months": list(contract.get("transition_months", ())),
        "maturity": contract.get("maturity"),
        "graph_delta": {
            "added_dependencies": sorted(alt_items - base_items),
            "removed_dependencies": sorted(base_items - alt_items),
            "changed_demand": changed,
        },
        "baseline": _result_summary(baseline_result),
        "alternative": _result_summary(alternative_result),
        "binding_change": {
            "unknowns_added": sorted(
                set(alternative_result.blocking_unknowns) - set(baseline_result.blocking_unknowns)
            ),
            "unknowns_removed": sorted(
                set(baseline_result.blocking_unknowns) - set(alternative_result.blocking_unknowns)
            ),
        },
        "evidence_ids": list(contract.get("evidence_ids", ())),
        "epistemic_class": "MODELLED",
        "approval_boundary": "Graph rewrite passed the declared functional envelope; engineering approval is still required.",
    }


def capability_leverage(
    registry: CanonicalRegistry,
    *,
    limit: int = 50,
) -> Dict[str, Any]:
    """Rank canonical capabilities using transparent graph-topology proxies."""

    rows: List[Dict[str, Any]] = []
    total_packs = max(len(registry.packs), 1)
    nodes_by_id = registry.nodes
    edges = registry.edges

    incoming_by_target: Dict[str, List[Any]] = defaultdict(list)
    reverse_by_target: Dict[str, List[str]] = defaultdict(list)
    for edge in edges:
        incoming_by_target[edge.target].append(edge)
        if edge.relation in DEPENDENCY_RELATIONS:
            reverse_by_target[edge.target].append(edge.source)

    for capability in sorted(
        (node for node in nodes_by_id.values() if node.kind == "capability"),
        key=lambda node: node.id,
    ):
        mappings = [
            edge
            for edge in incoming_by_target.get(capability.id, ())
            if edge.relation in {
                "maps_to_canonical",
                "capability_reference",
                "requires_or_represents",
            }
        ]
        mapped_ids = {edge.source for edge in mappings}
        mapped_packs = {
            str(edge.metadata.get("pack_id"))
            for edge in mappings
            if edge.metadata.get("pack_id")
        }
        visited = set(mapped_ids)
        queue = deque((node_id, 0) for node_id in sorted(mapped_ids))
        product_roots: Set[str] = set()
        while queue:
            node_id, depth = queue.popleft()
            node = nodes_by_id.get(node_id)
            if node and node.kind == "product_variant":
                product_roots.add(node_id)
            if depth >= 12:
                continue
            for parent in reverse_by_target.get(node_id, ()):
                if parent in visited:
                    continue
                visited.add(parent)
                queue.append((parent, depth + 1))

        mapped_nodes = [nodes_by_id[node_id] for node_id in mapped_ids if node_id in nodes_by_id]
        unknown_mappings = sum(
            1 for node in mapped_nodes if node.epistemic_class in {"UNKNOWN", "CONFLICTED"}
        )
        evidence_gap_fraction = (
            unknown_mappings / len(mapped_nodes) if mapped_nodes else 1.0
        )
        task_count = sum(
            1
            for task in registry.evidence_tasks.values()
            if task.get("target_canonical_id") == capability.id
        )
        pack_coverage = len(mapped_packs) / total_packs
        objective_reach = len(product_roots)
        reverse_reach = max(len(visited) - len(mapped_ids), 0)
        # This is a topology proxy, not NPV or a causal intervention estimate.
        leverage_proxy = (
            0.40 * pack_coverage
            + 0.35 * (1.0 - math.exp(-objective_reach / 2.0))
            + 0.25 * (1.0 - math.exp(-reverse_reach / 12.0))
        )
        closure_readiness = max(0.0, 1.0 - evidence_gap_fraction)
        rows.append(
            {
                "capability_id": capability.id,
                "name": capability.name,
                "mapped_pack_ids": sorted(mapped_packs),
                "mapped_entity_count": len(mapped_ids),
                "downstream_objective_ids": sorted(product_roots),
                "downstream_unlock_count": objective_reach,
                "reverse_dependency_reach": reverse_reach,
                "cross_sector_reuse": len(mapped_packs),
                "evidence_gap_fraction": round(evidence_gap_fraction, 4),
                "closure_readiness_proxy": round(closure_readiness, 4),
                "open_research_task_count": task_count,
                "leverage_proxy": round(leverage_proxy, 6),
                "epistemic_class": capability.epistemic_class,
            }
        )

    rows.sort(
        key=lambda row: (
            -float(row["leverage_proxy"]),
            -int(row["cross_sector_reuse"]),
            row["capability_id"],
        )
    )
    return {
        "metric": "TOPOLOGICAL_CAPABILITY_LEVERAGE_PROXY",
        "formula": (
            "0.40*pack_coverage + 0.35*(1-exp(-downstream_objectives/2)) + "
            "0.25*(1-exp(-reverse_dependency_reach/12))"
        ),
        "not_claimed": [
            "economic option value",
            "intervention causality",
            "qualified supply",
            "investment return",
        ],
        "registry_snapshot_id": registry.snapshot_id,
        "capabilities": rows[: max(1, min(limit, 500))],
    }


def _shortfall_text(value: float) -> str:
    """Keep small binding deficits visible instead of rounding them to zero."""

    magnitude = abs(value)
    if magnitude >= 100:
        return f"{value:,.0f}"
    if magnitude >= 10:
        return f"{value:,.1f}".rstrip("0").rstrip(".")
    if magnitude >= 1:
        return f"{value:,.2f}".rstrip("0").rstrip(".")
    return f"{value:,.3g}"


def _binding_shortfalls(result: SolveResult) -> List[Dict[str, Any]]:
    """Aggregate physical shortfalls into a stable, ranked intervention list."""

    by_item: Dict[str, Dict[str, Any]] = {}
    for year, year_result in sorted(result.years.items()):
        for gap in year_result.shortfalls:
            candidate = {
                "item_id": gap.item_id,
                "first_binding_year": year,
                "peak_shortfall": float(gap.shortfall),
                "unit": gap.unit_family,
                "demand_at_peak": float(gap.demand),
                "domestic_used_at_peak": float(gap.domestic_used),
                "imports_used_at_peak": float(gap.imports_used),
                "service_deficit_share": float(gap.service_deficit_share),
                "epistemic_class": "UNKNOWN" if gap.unknown else "DERIVED",
            }
            current = by_item.get(gap.item_id)
            if current is None:
                by_item[gap.item_id] = candidate
                continue
            current["first_binding_year"] = min(
                int(current["first_binding_year"]), year
            )
            if float(candidate["service_deficit_share"]) > float(
                current["service_deficit_share"]
            ):
                candidate["first_binding_year"] = current["first_binding_year"]
                by_item[gap.item_id] = candidate

    rows = sorted(
        by_item.values(),
        key=lambda row: (
            -float(row["service_deficit_share"]),
            -float(row["peak_shortfall"]),
            str(row["item_id"]),
        ),
    )
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
        row["action"] = (
            "RESEARCH_QUALIFIED_EFFECTIVE_CAPACITY"
            if row["epistemic_class"] == "UNKNOWN"
            else "BUILD_OR_QUALIFY_CAPACITY"
        )
    return rows


def _capacity_pair(raw: Any, *, scenario_id: str, item_id: str) -> Tuple[float, float]:
    if not isinstance(raw, (list, tuple)) or len(raw) != 2:
        raise ValueError(
            f"reverse scenario '{scenario_id}' capacity assumption for '{item_id}' "
            "must be [lo, hi]"
        )
    lo, hi = float(raw[0]), float(raw[1])
    if lo < 0 or hi < lo:
        raise ValueError(
            f"reverse scenario '{scenario_id}' has invalid capacity range for "
            f"'{item_id}': [{lo}, {hi}]"
        )
    return lo, hi


def reverse_buildability_report(
    pack: KnowledgePack,
    objective: ObjectiveSpecInput,
    *,
    shock_ids: Optional[Sequence[str]] = None,
    max_iterations: int = 24,
    include_declared_scenarios: bool = True,
) -> Dict[str, Any]:
    """Find an evidence-bounded output ceiling without claiming a proof theorem."""

    _require_variant(pack, objective.variant_id)
    years = _years(objective.deadline_year)

    def finalize(report: Dict[str, Any]) -> Dict[str, Any]:
        if include_declared_scenarios:
            report["declared_scenarios"] = _declared_reverse_scenarios(
                pack,
                objective,
                shock_ids=shock_ids,
                max_iterations=max_iterations,
            )
        return report

    def evaluate(volume: int) -> Tuple[SolveResult, ExplosionResult]:
        pg = ProofGraph()
        explosion = explode_variant(pack.world, pg, objective.variant_id, float(volume), years)
        world = pack.world
        opts = _opts(objective)
        if shock_ids:
            world, opts, _ = apply_shocks(world, pg, list(shock_ids), opts)
        return solve_objective(world, pg, explosion, years, opts), explosion

    one_result, one_explosion = evaluate(1)
    if one_result.result_class == ResultClass.NOT_ADJUDICABLE:
        unknown_items = [
            item_id
            for item_id in one_explosion.items()
            if capacity_envelope(
                pack.world,
                item_id,
                objective.deadline_year,
                geography=objective.geography,
                funded_project_ids=(set(objective.funded_projects) or None),
            ).domestic.is_unknown()
        ]
        return finalize({
            "max_units_per_year": None,
            "epistemic_class": "UNKNOWN",
            "status": "NOT_ADJUDICABLE_AT_ONE_UNIT",
            "binding_constraints": list(one_result.blocking_unknowns),
            "interventions": [
                {
                    "item_id": item_id,
                    "action": "RESEARCH_QUALIFIED_EFFECTIVE_CAPACITY",
                    "reason": "The ceiling cannot be bounded until this input is evidenced.",
                }
                for item_id in unknown_items[:12]
            ],
            "algorithm": "bounded integer binary search after a one-unit adjudicability check",
            "proof_status": "HEURISTIC_SEARCH_NOT_A_MATHEMATICAL_PROOF",
        })

    target = max(int(math.ceil(objective.annual_units)), 1)
    target_result, _ = evaluate(target)
    if target_result.result_class in {ResultClass.FEASIBLE, ResultClass.CONDITIONALLY_FEASIBLE}:
        return finalize({
            "max_units_per_year": target,
            "search_upper_bound": target,
            "target_supported_within_search_bound": True,
            "class_at_max": target_result.result_class.value,
            "epistemic_class": "DERIVED",
            "binding_constraints": list(target_result.binding_summary),
            "interventions": list(target_result.closure_candidates[:12]),
            "algorithm": "bounded integer binary search",
            "proof_status": "SEARCH_BOUND_ONLY; CAPACITY MONOTONICITY ASSUMED",
        })

    lo, hi = 0, target
    last_ok: Optional[SolveResult] = None
    first_fail: SolveResult = target_result
    iterations = 0
    while lo + 1 < hi and iterations < max_iterations:
        mid = (lo + hi) // 2
        result, _ = evaluate(mid)
        iterations += 1
        if result.result_class in {ResultClass.FEASIBLE, ResultClass.CONDITIONALLY_FEASIBLE}:
            lo = mid
            last_ok = result
        else:
            hi = mid
            first_fail = result
    binding_shortfalls = _binding_shortfalls(first_fail)
    binding_constraints = list(
        first_fail.blocking_unknowns or first_fail.binding_summary
    )[:16]
    if not binding_constraints:
        binding_constraints = [
            f"{row['item_id']}@{row['first_binding_year']}: shortfall "
            f"{_shortfall_text(float(row['peak_shortfall']))} {row['unit']}/yr"
            for row in binding_shortfalls[:16]
        ]
    return finalize({
        "max_units_per_year": lo,
        "first_failing_units_per_year": hi,
        "search_upper_bound": target,
        "target_supported_within_search_bound": False,
        "class_at_max": last_ok.result_class.value if last_ok else one_result.result_class.value,
        "class_at_first_failure": first_fail.result_class.value,
        "epistemic_class": "DERIVED",
        "binding_constraints": binding_constraints,
        "binding_shortfalls": binding_shortfalls[:16],
        "ranked_interventions": binding_shortfalls[:12],
        "interventions": list(first_fail.closure_candidates[:12]),
        "iterations": iterations,
        "algorithm": "bounded integer binary search",
        "proof_status": "HEURISTIC SEARCH; CAPACITY MONOTONICITY ASSUMED",
    })


def _declared_reverse_scenarios(
    pack: KnowledgePack,
    objective: ObjectiveSpecInput,
    *,
    shock_ids: Optional[Sequence[str]],
    max_iterations: int,
) -> List[Dict[str, Any]]:
    """Evaluate pack-declared planning envelopes without mutating baseline truth.

    A declared scenario may close otherwise-UNKNOWN capacity cells only through
    an explicit item range or a named requirement-headroom policy. The complete
    generated assumption ledger is returned to the caller. This is deliberately
    separate from evidence and never upgrades the baseline reverse verdict.
    """

    declarations = list(pack.raw.get("reverse_buildability_scenarios", ()) or ())
    outputs: List[Dict[str, Any]] = []
    for declaration in declarations:
        scenario_id = str(declaration.get("id", "")).strip()
        if not scenario_id:
            raise ValueError("reverse buildability scenario requires an id")
        variant_id = str(declaration.get("variant_id", objective.variant_id))
        if variant_id != objective.variant_id:
            continue

        search_upper_bound = int(
            declaration.get("search_upper_bound", math.ceil(objective.annual_units))
        )
        if search_upper_bound < 1:
            raise ValueError(
                f"reverse scenario '{scenario_id}' search_upper_bound must be positive"
            )
        deadline_year = int(declaration.get("deadline_year", objective.deadline_year))
        geography = str(declaration.get("geography", objective.geography))
        years = _years(deadline_year)

        policy = dict(declaration.get("unresolved_capacity_policy", {}) or {})
        policy_type = str(policy.get("type", "NONE")).upper()
        basis_units = int(policy.get("basis_units_per_year", search_upper_bound))
        headroom = float(policy.get("multiplier", 1.0))
        if basis_units < 1 or headroom < 1.0:
            raise ValueError(
                f"reverse scenario '{scenario_id}' requires a positive basis and "
                "headroom multiplier >= 1"
            )

        proof = ProofGraph()
        basis_explosion = explode_variant(
            pack.world, proof, variant_id, float(basis_units), years
        )
        exploded_items = set(basis_explosion.items())
        assumptions: Dict[str, Tuple[float, float]] = {}
        assumption_ledger: List[Dict[str, Any]] = []

        for item_id, raw_assumption in dict(
            declaration.get("capacity_assumptions", {}) or {}
        ).items():
            item_id = str(item_id)
            if item_id not in exploded_items:
                raise ValueError(
                    f"reverse scenario '{scenario_id}' assumption '{item_id}' is not "
                    f"required by variant '{variant_id}'"
                )
            metadata = raw_assumption if isinstance(raw_assumption, Mapping) else {}
            raw_range = metadata.get("range") if metadata else raw_assumption
            lo, hi = _capacity_pair(
                raw_range, scenario_id=scenario_id, item_id=item_id
            )
            assumptions[item_id] = (lo, hi)
            line = basis_explosion.get(item_id)
            assumption_ledger.append(
                {
                    "item_id": item_id,
                    "range": [lo, hi],
                    "unit": str(
                        metadata.get(
                            "unit", line.gross_annual.unit if line else "UNKNOWN"
                        )
                    ),
                    "basis": "EXPLICIT_SCENARIO_RANGE",
                    "rationale": str(metadata.get("rationale", "")),
                    "epistemic_class": "ASSUMPTION",
                }
            )

        generated_items: List[str] = []
        if policy_type == "REQUIREMENT_HEADROOM":
            for item_id in sorted(exploded_items):
                if item_id in assumptions:
                    continue
                envelope = capacity_envelope(
                    pack.world,
                    item_id,
                    deadline_year,
                    geography=geography,
                    funded_project_ids=(set(objective.funded_projects) or None),
                )
                if not envelope.domestic.is_unknown():
                    continue
                line = basis_explosion.get(item_id)
                if line is None:
                    continue
                value = abs(float(line.gross_annual.value)) * headroom
                assumptions[item_id] = (value, value)
                generated_items.append(item_id)
                assumption_ledger.append(
                    {
                        "item_id": item_id,
                        "range": [value, value],
                        "unit": line.gross_annual.unit,
                        "basis": "REQUIREMENT_HEADROOM_POLICY",
                        "rationale": (
                            f"Assumed {headroom:g}x the modelled gross requirement "
                            f"at {basis_units:,} output units/year."
                        ),
                        "epistemic_class": "ASSUMPTION",
                    }
                )
        elif policy_type != "NONE":
            raise ValueError(
                f"reverse scenario '{scenario_id}' has unsupported unresolved "
                f"capacity policy '{policy_type}'"
            )

        per_item_import_cap = dict(objective.per_item_import_cap)
        import_policy = str(
            (declaration.get("import_policy", {}) or {}).get("type", "OBJECTIVE")
        ).upper()
        if import_policy == "DOMESTIC_ONLY":
            per_item_import_cap.update({item_id: 0.0 for item_id in exploded_items})
        elif import_policy != "OBJECTIVE":
            raise ValueError(
                f"reverse scenario '{scenario_id}' has unsupported import policy "
                f"'{import_policy}'"
            )

        base_spec = replace(
            objective,
            variant_id=variant_id,
            annual_units=float(search_upper_bound),
            geography=geography,
            deadline_year=deadline_year,
            min_dva=float(declaration.get("min_dva", objective.min_dva)),
            per_item_import_cap=per_item_import_cap,
            foreign_supply_policy=str(
                declaration.get("foreign_supply_policy", "strict")
            ),
        )
        conservative_assumptions = {
            item_id: (limits[0], limits[0]) for item_id, limits in assumptions.items()
        }
        optimistic_assumptions = {
            item_id: (limits[1], limits[1]) for item_id, limits in assumptions.items()
        }
        conservative = reverse_buildability_report(
            pack,
            replace(
                base_spec, analyst_capacity_assumptions=conservative_assumptions
            ),
            shock_ids=shock_ids,
            max_iterations=max_iterations,
            include_declared_scenarios=False,
        )
        optimistic = reverse_buildability_report(
            pack,
            replace(base_spec, analyst_capacity_assumptions=optimistic_assumptions),
            shock_ids=shock_ids,
            max_iterations=max_iterations,
            include_declared_scenarios=False,
        )

        low_ceiling = conservative.get("max_units_per_year")
        high_ceiling = optimistic.get("max_units_per_year")
        scenario_report = dict(optimistic)
        scenario_report.update(
            {
                "scenario_id": scenario_id,
                "title": str(declaration.get("title", scenario_id)),
                "description": str(declaration.get("description", "")),
                "variant_id": variant_id,
                "status": (
                    "SCENARIO_CEILING_DERIVED"
                    if low_ceiling is not None and high_ceiling is not None
                    else "SCENARIO_NOT_ADJUDICABLE"
                ),
                "epistemic_class": "SCENARIO",
                "calculation_epistemic_class": optimistic.get(
                    "epistemic_class", "UNKNOWN"
                ),
                "ceiling_range_units_per_year": [low_ceiling, high_ceiling],
                "conservative_edge": {
                    "max_units_per_year": low_ceiling,
                    "class_at_max": conservative.get("class_at_max"),
                    "binding_constraints": conservative.get(
                        "binding_constraints", []
                    ),
                    "binding_shortfalls": conservative.get(
                        "binding_shortfalls", []
                    ),
                    "ranked_interventions": conservative.get(
                        "ranked_interventions", []
                    ),
                },
                "optimistic_edge": {
                    "max_units_per_year": high_ceiling,
                    "class_at_max": optimistic.get("class_at_max"),
                    "binding_constraints": optimistic.get(
                        "binding_constraints", []
                    ),
                    "binding_shortfalls": optimistic.get(
                        "binding_shortfalls", []
                    ),
                    "ranked_interventions": optimistic.get(
                        "ranked_interventions", []
                    ),
                },
                "assumption_boundary": {
                    "persistent": False,
                    "baseline_world_mutated": False,
                    "capacity_policy": policy_type,
                    "basis_units_per_year": basis_units,
                    "headroom_multiplier": headroom,
                    "import_policy": import_policy,
                    "explicit_assumption_count": len(assumptions)
                    - len(generated_items),
                    "policy_generated_assumption_count": len(generated_items),
                    "assumptions": sorted(
                        assumption_ledger, key=lambda row: row["item_id"]
                    ),
                    "notes": list(declaration.get("assumption_notes", ()) or ()),
                },
                "not_claimed": [
                    "current evidenced production capacity",
                    "qualified supplier availability",
                    "mathematical proof of a global maximum",
                    "automatic permission to execute investments",
                ],
            }
        )
        outputs.append(scenario_report)
    return outputs


def shock_impact(
    pack: KnowledgePack,
    objective: ObjectiveSpecInput,
    shock_ids: Sequence[str],
) -> Dict[str, Any]:
    """Run baseline and shock worlds and expose real causal paths and deltas."""

    _require_variant(pack, objective.variant_id)
    years = _years(objective.deadline_year)
    pg_base = ProofGraph()
    pg_shock = ProofGraph()
    explosion_base = explode_variant(
        pack.world, pg_base, objective.variant_id, objective.annual_units, years
    )
    explosion_shock = explode_variant(
        pack.world, pg_shock, objective.variant_id, objective.annual_units, years
    )
    baseline = solve_objective(pack.world, pg_base, explosion_base, years, _opts(objective))
    shocked_world, shocked_opts, report = apply_shocks(
        pack.world, pg_shock, list(shock_ids), _opts(objective)
    )
    shocked = solve_objective(
        shocked_world, pg_shock, explosion_shock, years, shocked_opts
    )

    directly_affected: Set[str] = set()
    affected_origins: Set[str] = set()
    for shock_id in shock_ids:
        entity = pack.world.entities.get(shock_id)
        if not isinstance(entity, Shock):
            continue
        for edit in entity.edits:
            for key in ("item", "project_id", "equipment_class", "facility_id"):
                value = edit.get(key)
                if value and pack.world.has(str(value)):
                    directly_affected.add(str(value))
            origin = edit.get("origin", edit.get("country"))
            if origin:
                affected_origins.add(str(origin))
    if affected_origins:
        for entity in pack.world.entities.values():
            countries = set(getattr(entity, "supplied_by_countries", ()) or ())
            if countries & affected_origins:
                directly_affected.add(entity.id)
        for entity in pack.world.entities.values():
            if isinstance(entity, ForeignSupplySegment) and entity.origin_country in affected_origins:
                directly_affected.add(entity.item_id)

    roots, raw_paths = _dependency_ancestors(
        pack.world, directly_affected, roots={objective.variant_id}
    )
    causal_paths = [
        [
            {
                "entity_id": entity_id,
                "name": _entity_name(pack.world, entity_id),
                "kind": getattr(pack.world.entities.get(entity_id), "kind", "entity"),
            }
            for entity_id in path
        ]
        for path in raw_paths
    ]

    baseline_year = baseline.years.get(objective.deadline_year)
    shocked_year = shocked.years.get(objective.deadline_year)
    baseline_vector = (
        baseline_year.shortfall_vector.to_json() if baseline_year else {}
    )
    shocked_vector = shocked_year.shortfall_vector.to_json() if shocked_year else {}
    shortfall_units = sorted(set(baseline_vector) | set(shocked_vector))
    shortfall_delta_by_unit = {
        unit: round(
            float(shocked_vector.get(unit, 0.0))
            - float(baseline_vector.get(unit, 0.0)),
            3,
        )
        for unit in shortfall_units
    }
    normalized_deficit_delta = round(
        (shocked_year.normalized_deficit if shocked_year else 0.0)
        - (baseline_year.normalized_deficit if baseline_year else 0.0),
        6,
    )
    # Compatibility scalar is safe only when the entire physical vector is pcs.
    legacy_pcs_delta = (
        shortfall_delta_by_unit.get("pcs", 0.0)
        if set(shortfall_units) <= {"pcs"}
        else None
    )
    return {
        "shock_ids": list(shock_ids),
        "baseline": _result_summary(baseline),
        "shocked": _result_summary(shocked),
        "deadline_shortfall_vectors": {
            "baseline": baseline_vector,
            "shocked": shocked_vector,
        },
        "deadline_shortfall_delta_by_unit": shortfall_delta_by_unit,
        "deadline_normalized_deficit_delta": normalized_deficit_delta,
        "deadline_shortfall_delta": legacy_pcs_delta,
        "deadline_shortfall_delta_unit": (
            "pcs" if legacy_pcs_delta is not None else None
        ),
        "deadline_shortfall_delta_semantics": (
            "Legacy compatibility scalar; null for mixed physical unit families. "
            "Use deadline_shortfall_delta_by_unit or the dimensionless normalized delta."
        ),
        "directly_affected_entity_ids": sorted(directly_affected),
        "affected_origins": sorted(affected_origins),
        "objective_reached_by_causal_path": objective.variant_id in roots,
        "causal_paths": causal_paths,
        "applied_edits": report.applied_edits,
        "rejected_edits": report.rejected_edits,
        "inventory_posture": "UNKNOWN — inventories are not modeled unless explicitly represented",
        "epistemic_class": "DERIVED",
    }


def program_timeline(pack: KnowledgePack) -> Dict[str, Any]:
    """Project a declared fleet/program model without special-casing a vertical."""

    raw = pack.raw.get("program_model", {}) or {}
    if not isinstance(raw, Mapping) or not raw:
        projects = []
        for entity in pack.world.entities.values():
            if not isinstance(entity, Project):
                continue
            lo, hi = entity.years_to_commission
            projects.append(
                {
                    "id": entity.id,
                    "name": entity.name,
                    "start_year": entity.earliest_start_year,
                    "commission_earliest": entity.earliest_start_year + lo,
                    "commission_latest": entity.earliest_start_year + hi,
                    "state": entity.state.value,
                    "epistemic_class": _entity_evidence_class(pack, entity),
                    "evidence_ids": list(entity.evidence_ids),
                }
            )
        return {
            "available": bool(projects),
            "projection_type": "PROJECT_WINDOWS_ONLY",
            "projects": sorted(projects, key=lambda row: (row["start_year"], row["id"])),
            "annual_projection": [],
            "limitations": [
                "No structured program_model is declared; cumulative fleet output is not inferred."
            ],
        }

    objective = dict(raw.get("objective", {}) or {})
    tranches = list(raw.get("tranches", ()) or ())
    gates = list(raw.get("system_gates", ()) or ())
    start_year = int(objective.get("start_year", min((row.get("start_year", 2026) for row in tranches), default=2026)))
    target_year = int(objective.get("target_year", max((row.get("start_year", start_year) for row in tranches), default=start_year)))
    existing = float(objective.get("existing_capacity_gw", 0.0) or 0.0)
    annual: List[Dict[str, Any]] = []
    for year in range(start_year, target_year + 1):
        earliest_added = 0.0
        latest_added = 0.0
        units_earliest = 0
        units_latest = 0
        for row in tranches:
            if not isinstance(row, Mapping):
                continue
            units = int(row.get("units", 0) or 0)
            unit_gw = float(row.get("unit_capacity_gw", 0.0) or 0.0)
            construction = list(row.get("construction_years", (0.0, 0.0)) or (0.0, 0.0))
            commissioning = list(row.get("commissioning_years", (0.0, 0.0)) or (0.0, 0.0))
            if len(construction) != 2 or len(commissioning) != 2:
                continue
            tranche_start = float(row.get("start_year", start_year))
            earliest_year = tranche_start + float(construction[0]) + float(commissioning[0])
            latest_year = tranche_start + float(construction[1]) + float(commissioning[1])
            if earliest_year <= year:
                earliest_added += units * unit_gw
                units_earliest += units
            if latest_year <= year:
                latest_added += units * unit_gw
                units_latest += units
        annual.append(
            {
                "year": year,
                "commissioned_gw_optimistic": existing + earliest_added,
                "commissioned_gw_conservative": existing + latest_added,
                "commissioned_units_optimistic": units_earliest,
                "commissioned_units_conservative": units_latest,
                "epistemic_class": "SCENARIO",
            }
        )

    target_gw = objective.get("target_gw")
    last = annual[-1] if annual else {}
    return {
        "available": True,
        "projection_type": "DECLARED_TRANCHE_SCENARIO",
        "objective": objective,
        "tranches": tranches,
        "system_gates": gates,
        "annual_projection": annual,
        "target_gap_gw_optimistic": (
            float(target_gw) - float(last.get("commissioned_gw_optimistic", 0.0))
            if target_gw is not None
            else None
        ),
        "target_gap_gw_conservative": (
            float(target_gw) - float(last.get("commissioned_gw_conservative", 0.0))
            if target_gw is not None
            else None
        ),
        "epistemic_class": str(raw.get("epistemic_class", "SCENARIO")),
        "limitations": list(raw.get("limitations", ()) or ())
        + [
            "Tranche arithmetic does not prove site, finance, regulator, workforce, fuel-cycle, grid, or supply-chain feasibility.",
            "Optimistic/conservative dates are scenario windows, not probability bounds.",
        ],
    }
