"""Industrial Objective Compiler V0.

This module is an orchestration/translation layer.  Quantitative propagation,
capacity envelopes, and solve classification remain owned by the existing
FORGE core through :mod:`compiler_bridge`.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping

from forge.epistemics import ResultClass
from forge.units import Quantity, UnitError

from .architecture import compile_product_architecture
from .catalog import IndiaCatalog, get_catalog
from .compiler_bridge import CapacityObservation, compile_architecture_to_core
from .objective import (
    _candidate,
    _classification,
    _retrieval_query,
    _semantic_hits,
    parse_objective,
    resolve_objective,
)
from .objective_fixtures import ObjectiveFixture, fixture_for_family
from .objective_models import (
    ArchitectureEdge,
    ArchitectureNode,
    ArchitectureNodeKind,
    ClosureActionCategory,
    CoefficientState,
    DependencyState,
    DerivationClass,
    IndustrialObjective,
    IndustrialObjectiveCompilation,
    ProductArchitecture,
    QuantitativeCoefficient,
    QuantityState,
)


_PHYSICAL = {
    ArchitectureNodeKind.PRODUCT_SYSTEM,
    ArchitectureNodeKind.PRODUCT_COMPONENT,
    ArchitectureNodeKind.MATERIAL,
}


def objective_from_text(value: str) -> IndustrialObjective:
    parsed = parse_objective(value)
    period = {
        "PER_YEAR": "year",
        "PER_MONTH": "month",
        "PER_WEEK": "week",
        "PER_DAY": "day",
    }.get(parsed.cadence, "year")
    from .objective_models import ObjectiveConstraint

    constraints = tuple(
        ObjectiveConstraint(kind="text", value=item) for item in parsed.constraints
    )
    return IndustrialObjective(
        objective_type="manufacture",
        product=parsed.product_query,
        quantity=float(parsed.quantity or 1.0),
        output_unit=parsed.quantity_unit or "units",
        period=period,
        geography=parsed.geography or "INDIA",
        target_year=parsed.deadline_year or 2030,
        constraints=constraints,
    )


def _resolved_record(
    objective: IndustrialObjective,
    catalog: IndiaCatalog,
    public_resolution: Mapping[str, Any],
) -> tuple[Mapping[str, Any] | None, bool]:
    resolution = public_resolution["resolution"]
    classification = str(resolution.get("classification") or "UNRESOLVED")
    if classification == "UNRESOLVED":
        return None, False
    query = _retrieval_query(objective.product)
    raw = catalog.search_hits(query, limit=48, include_variants=False)
    hits = _semantic_hits(query, raw)
    if hits and _classification(hits[0]) == classification:
        return hits[0]["record"], classification == "NEAREST"

    public_candidate = resolution.get("selected") or resolution.get("nearest") or {}
    title = str(public_candidate.get("title") or "").strip()
    for hit in catalog.search_hits(title, limit=24, include_variants=False):
        candidate = _candidate(hit, catalog)
        if candidate["title"].casefold() == title.casefold():
            return hit["record"], classification == "NEAREST"
    return None, classification == "NEAREST"


def _apply_fixture(architecture: ProductArchitecture, fixture: ObjectiveFixture | None) -> ProductArchitecture:
    if fixture is None:
        return architecture
    nodes = {node.id: node for node in architecture.nodes}
    edges = {(edge.source_id, edge.destination_id, edge.relation): edge for edge in architecture.edges}

    def node_id(key: str) -> str:
        return architecture.product_record_id if key == "root" else f"fixture:{fixture.fixture_id}:{key}"

    for fixture_edge in fixture.edges:
        destination = node_id(fixture_edge.child)
        sources = fixture_edge.evidence_ids or (f"fixture:{fixture.fixture_id}",)
        if destination not in nodes:
            nodes[destination] = ArchitectureNode(
                id=destination,
                label=fixture_edge.child_label,
                kind=fixture_edge.child_kind,
                source_record_ids=tuple(sources),
                derivation_class=DerivationClass.MODELLED,
                status="UNKNOWN",
                epistemic_class=(
                    "UNKNOWN" if fixture_edge.state is CoefficientState.UNKNOWN else fixture_edge.state.value
                ),
                family_key=destination,
                description=fixture_edge.note,
                depth=1 if fixture_edge.parent == "root" else 2,
            )
        source = node_id(fixture_edge.parent)
        coefficient = QuantitativeCoefficient(
            value=fixture_edge.value,
            unit=fixture_edge.unit,
            state=fixture_edge.state,
            source_record_ids=tuple(sources),
            note=fixture_edge.note,
        )
        relation = "contains_component" if fixture_edge.child_kind is not ArchitectureNodeKind.MATERIAL else "requires_material"
        edge = ArchitectureEdge(
            source_id=source,
            destination_id=destination,
            relation=relation,
            source_record_ids=tuple(sources),
            derivation_class=DerivationClass.MODELLED,
            coefficient=coefficient,
        )
        edges[(edge.source_id, edge.destination_id, edge.relation)] = edge
    return replace(
        architecture,
        nodes=tuple(sorted(nodes.values(), key=lambda node: (node.depth, node.kind.value, node.label.casefold(), node.id))),
        edges=tuple(sorted(edges.values(), key=lambda edge: (edge.source_id, edge.relation, edge.destination_id))),
        diagnostics=tuple(sorted(set((*architecture.diagnostics, f"Applied deterministic fixture '{fixture.fixture_id}'; non-evidenced values remain ASSUMPTION.")))),
    )


def _dependency_state(node: ArchitectureNode, *, family_level: bool) -> DependencyState:
    if family_level:
        return DependencyState.UNKNOWN
    status = node.status.upper()
    if status in {"STRONG", "AVAILABLE"} and node.epistemic_class in {"MEASURED", "REPORTED", "DERIVED"}:
        return DependencyState.DOMESTIC
    if status in {"PARTIAL", "SCALE_LIMITED"}:
        return DependencyState.PARTIAL
    if status == "IMPORT_DEPENDENT":
        return DependencyState.IMPORT_DEPENDENT
    if status == "MISSING":
        return DependencyState.MISSING
    if status == "CONFLICTED":
        return DependencyState.CONSTRAINED
    return DependencyState.UNKNOWN


def _incoming_edges(architecture: ProductArchitecture, node_id: str) -> list[ArchitectureEdge]:
    return [edge for edge in architecture.edges if edge.destination_id == node_id]


def _path(architecture: ProductArchitecture, node_id: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    current = node_id
    seen: set[str] = set()
    while current != architecture.product_record_id and current not in seen:
        seen.add(current)
        incoming = sorted(_incoming_edges(architecture, current), key=lambda edge: (edge.source_id, edge.relation))
        if not incoming:
            break
        edge = incoming[0]
        result.append(
            {
                "source_id": edge.source_id,
                "destination_id": edge.destination_id,
                "coefficient": edge.coefficient.to_dict() if edge.coefficient else None,
            }
        )
        current = edge.source_id
    return list(reversed(result))


def compile_industrial_objective(
    objective: IndustrialObjective | str,
    *,
    catalog: IndiaCatalog | None = None,
    use_fixtures: bool = True,
) -> IndustrialObjectiveCompilation:
    """Compile one bounded manufacturing objective deterministically."""

    objective = objective_from_text(objective) if isinstance(objective, str) else objective
    try:
        annual_quantity = Quantity(objective.annual_quantity, objective.output_unit).to("pcs").value
    except (KeyError, UnitError) as exc:
        raise ValueError(
            f"V0 manufacturing objectives require a count-compatible output unit, not '{objective.output_unit}'"
        ) from exc
    catalog = catalog or get_catalog()
    resolution = resolve_objective(objective.product, catalog)
    record, family_level = _resolved_record(objective, catalog, resolution)
    confirmed_family = bool(family_level and objective.confirm_family)

    if record is None or (family_level and not objective.confirm_family):
        architecture = compile_product_architecture(record or "unresolved", catalog, family_level=family_level, requires_confirmation=family_level)
        diagnostics = [
            resolution["resolution"]["message"],
            "Family-level compilation requires explicit confirmation." if family_level else "No safe product/family resolution was available.",
        ]
        return IndustrialObjectiveCompilation(
            resolved_objective={**objective.to_dict(), "resolution": resolution["resolution"]},
            architecture=architecture,
            demand_ledger=(), capability_ledger=(), capacity_ledger=(), dependency_ledger=(), gap_ledger=(),
            bottlenecks=(), closure_actions=(), staged_plan=(), verification_frontier=(
                {"id": "verify:product_resolution", "question": f"Confirm the exact mapped product family for {objective.product}."},
            ),
            evidence_references=(), compiler_diagnostics=diagnostics,
            result_class=ResultClass.NOT_ADJUDICABLE.value,
        )

    architecture = compile_product_architecture(
        record,
        catalog,
        family_level=confirmed_family,
        requires_confirmation=False,
    )
    fixture = fixture_for_family(architecture.family_key) if use_fixtures else None
    architecture = _apply_fixture(architecture, fixture)
    capacities = tuple(
        CapacityObservation(
            node_id=f"fixture:{fixture.fixture_id}:{capacity.node}",
            lo=capacity.lo,
            hi=capacity.hi,
            unit=capacity.unit,
            geography=objective.geography,
            epistemic_class=capacity.epistemic_class,
            source_record_ids=capacity.evidence_ids or (f"fixture:{fixture.fixture_id}",),
            note=capacity.note,
        )
        for capacity in (fixture.capacities if fixture else ())
    )
    bridge = compile_architecture_to_core(
        architecture,
        annual_quantity=annual_quantity,
        target_year=objective.target_year,
        geography=objective.geography,
        capacity_observations=capacities,
    )

    reverse_map = {core_id: node_id for node_id, core_id in bridge.node_to_core.items()}
    demand: list[dict[str, Any]] = [
        {
            "node_id": architecture.product_record_id,
            "label": architecture.product_name,
            "quantity": annual_quantity,
            "unit": "pcs/year",
            "quantity_state": QuantityState.OBJECTIVE.value,
            "coefficient_state": None,
            "derivation_path": [],
            "source_record_ids": [architecture.product_record_id],
        }
    ]
    quantified_nodes: set[str] = set()
    for core_id in bridge.explosion.items():
        line = bridge.explosion.get(core_id)
        node_id = reverse_map.get(core_id)
        node = architecture.node(node_id or "")
        if line is None or node is None:
            continue
        quantified_nodes.add(node.id)
        incoming = _incoming_edges(architecture, node.id)
        coefficient_states = sorted({edge.coefficient.state.value for edge in incoming if edge.coefficient})
        demand.append(
            {
                "node_id": node.id,
                "label": node.label,
                "quantity": line.gross_annual.value,
                "net_quantity": line.net_annual.value,
                "unit": f"{line.gross_annual.unit}/year",
                "quantity_state": QuantityState.DERIVED.value,
                "coefficient_state": coefficient_states[0] if len(coefficient_states) == 1 else coefficient_states,
                "derivation_path": _path(architecture, node.id),
                "source_record_ids": sorted({source for edge in incoming for source in edge.source_record_ids}),
            }
        )
    for unresolved in bridge.unresolved_edges:
        node = architecture.node(unresolved["destination_id"])
        if node is None or node.id in quantified_nodes:
            continue
        demand.append(
            {
                "node_id": node.id,
                "label": node.label,
                "quantity": None,
                "unit": None,
                "quantity_state": QuantityState.UNKNOWN.value,
                "coefficient_state": CoefficientState.UNKNOWN.value,
                "derivation_path": _path(architecture, node.id),
                "source_record_ids": unresolved["source_record_ids"],
            }
        )
    demand.sort(key=lambda row: (0 if row["quantity_state"] == QuantityState.OBJECTIVE.value else 1, row["label"].casefold(), row["node_id"]))

    capability = [
        {
            "node_id": node.id,
            "label": node.label,
            "requirement_type": node.kind.value,
            "status": node.status,
            "epistemic_class": node.epistemic_class,
            "derivation_class": node.derivation_class.value,
            "source_record_ids": list(node.source_record_ids),
        }
        for node in architecture.nodes if node.kind not in _PHYSICAL
    ]
    capability.sort(key=lambda row: (row["requirement_type"], row["label"].casefold(), row["node_id"]))

    capacity_ledger: list[dict[str, Any]] = []
    gap_ledger: list[dict[str, Any]] = []
    demand_by_node = {row["node_id"]: row for row in demand}
    for node_id, row in sorted(demand_by_node.items()):
        if node_id == architecture.product_record_id:
            continue
        core_id = bridge.node_to_core.get(node_id)
        envelope = bridge.capacity_envelopes.get(core_id or "")
        override = bridge.capacity_overrides.get(core_id or "")
        if override:
            lo, hi = override
            epistemic = "ASSUMPTION"
        elif envelope and not envelope.domestic.is_unknown():
            lo, hi = envelope.domestic.lo, envelope.domestic.hi
            epistemic = envelope.epistemic
        else:
            lo = hi = None
            epistemic = "UNKNOWN"
        capacity_ledger.append(
            {
                "node_id": node_id,
                "label": row["label"],
                "geography": objective.geography,
                "capacity_lo": lo,
                "capacity_hi": hi,
                "unit": row.get("unit"),
                "state": "KNOWN" if lo is not None else "UNKNOWN",
                "epistemic_class": epistemic,
                "unknown_reasons": list(envelope.unknown_reasons) if envelope and lo is None else [],
            }
        )
        required = row.get("quantity")
        if required is not None and hi is not None:
            gap_lo = max(float(required) - float(hi), 0.0)
            gap_hi = max(float(required) - float(lo), 0.0)
            coverage_lo = min(float(lo) / float(required), 1.0) if required else 1.0
            coverage_hi = min(float(hi) / float(required), 1.0) if required else 1.0
        else:
            gap_lo = gap_hi = coverage_lo = coverage_hi = None
        gap_ledger.append(
            {
                "node_id": node_id,
                "label": row["label"],
                "required": required,
                "capacity_lo": lo,
                "capacity_hi": hi,
                "gap_lo": gap_lo,
                "gap_hi": gap_hi,
                "coverage_ratio_lo": coverage_lo,
                "coverage_ratio_hi": coverage_hi,
                "unit": row.get("unit"),
                "state": "CALCULATED" if gap_lo is not None else "UNKNOWN",
            }
        )

    dependency = []
    for node in architecture.nodes:
        if node.id == architecture.product_record_id:
            continue
        state = _dependency_state(node, family_level=confirmed_family)
        dependency.append(
            {
                "node_id": node.id,
                "label": node.label,
                "state": state.value,
                "epistemic_class": node.epistemic_class,
                "source_geographies": [],
                "constraint_effect": "UNRESOLVED" if objective.constraints and state is DependencyState.UNKNOWN else None,
                "source_record_ids": list(node.source_record_ids),
            }
        )
    dependency.sort(key=lambda row: (row["state"], row["label"].casefold(), row["node_id"]))

    bottlenecks: list[dict[str, Any]] = []
    for gap in gap_ledger:
        if gap["gap_lo"] is not None and gap["gap_hi"] and gap["gap_hi"] > 0:
            bottlenecks.append(
                {
                    "node_id": gap["node_id"], "label": gap["label"],
                    "reason": f"Objective demand exceeds declared domestic capacity; gap interval {gap['gap_lo']:g}-{gap['gap_hi']:g} {gap['unit']}.",
                    "criticality": 100.0 * (1.0 - float(gap["coverage_ratio_hi"] or 0.0)),
                    "trace": [gap["node_id"]],
                }
            )
    for dep in dependency:
        if dep["state"] in {DependencyState.MISSING.value, DependencyState.CONSTRAINED.value, DependencyState.IMPORT_DEPENDENT.value}:
            bottlenecks.append(
                {
                    "node_id": dep["node_id"], "label": dep["label"],
                    "reason": f"Objective path carries dependency state {dep['state']}.",
                    "criticality": 75.0 if dep["state"] != DependencyState.MISSING.value else 90.0,
                    "trace": [dep["node_id"]],
                }
            )
    bottlenecks = sorted(bottlenecks, key=lambda row: (-row["criticality"], row["label"].casefold(), row["node_id"]))

    actions: list[dict[str, Any]] = []
    verification: list[dict[str, Any]] = []
    for row in demand:
        if row["quantity_state"] == QuantityState.UNKNOWN.value:
            question = f"Verify units of {row['label']} required for the selected {architecture.product_name} architecture."
            verification.append({"id": f"verify:coefficient:{row['node_id']}", "target": row["node_id"], "question": question, "reason": "QUANTITY_COEFFICIENT_UNKNOWN"})
            actions.append({"id": f"action:verify:coefficient:{row['node_id']}", "category": ClosureActionCategory.VERIFY.value, "target": row["node_id"], "label": row["label"], "reason": question, "objective_demand": None, "capacity_state": "UNKNOWN", "dependency_state": "UNKNOWN", "prerequisites": [], "supporting_evidence": row["source_record_ids"], "unresolved_questions": [question]})
    for cap in capacity_ledger:
        if cap["state"] == "UNKNOWN":
            question = f"Verify current annual Indian production capacity for {cap['label']}."
            verification.append({"id": f"verify:capacity:{cap['node_id']}", "target": cap["node_id"], "question": question, "reason": "DOMESTIC_CAPACITY_UNKNOWN"})
            actions.append({"id": f"action:verify:capacity:{cap['node_id']}", "category": ClosureActionCategory.VERIFY.value, "target": cap["node_id"], "label": cap["label"], "reason": question, "objective_demand": demand_by_node[cap["node_id"]].get("quantity"), "capacity_state": "UNKNOWN", "dependency_state": next((dep["state"] for dep in dependency if dep["node_id"] == cap["node_id"]), "UNKNOWN"), "prerequisites": [], "supporting_evidence": [], "unresolved_questions": [question]})
    for gap in gap_ledger:
        if gap["gap_hi"] is not None and gap["gap_hi"] > 0:
            actions.append({"id": f"action:make:{gap['node_id']}", "category": ClosureActionCategory.MAKE.value, "target": gap["node_id"], "label": gap["label"], "reason": "Declared domestic capacity is below objective-derived demand.", "objective_demand": gap["required"], "capacity_state": "KNOWN", "dependency_state": next((dep["state"] for dep in dependency if dep["node_id"] == gap["node_id"]), "UNKNOWN"), "prerequisites": [f"action:verify:capacity:{gap['node_id']}"] if next((cap["epistemic_class"] for cap in capacity_ledger if cap["node_id"] == gap["node_id"]), "") == "ASSUMPTION" else [], "supporting_evidence": [], "unresolved_questions": []})
    for dep in dependency:
        category = {
            DependencyState.MISSING.value: ClosureActionCategory.DEVELOP,
            DependencyState.IMPORT_DEPENDENT.value: ClosureActionCategory.SOURCE,
            DependencyState.CONSTRAINED.value: ClosureActionCategory.LOCALIZE,
        }.get(dep["state"])
        if category:
            actions.append({"id": f"action:{category.value.casefold()}:{dep['node_id']}", "category": category.value, "target": dep["node_id"], "label": dep["label"], "reason": f"Dependency state is {dep['state']} on an objective-relevant path.", "objective_demand": demand_by_node.get(dep["node_id"], {}).get("quantity"), "capacity_state": next((cap["state"] for cap in capacity_ledger if cap["node_id"] == dep["node_id"]), "UNKNOWN"), "dependency_state": dep["state"], "prerequisites": [], "supporting_evidence": dep["source_record_ids"], "unresolved_questions": []})
    if len(demand) > 1:
        actions.append({"id": "action:integrate:product", "category": ClosureActionCategory.INTEGRATE.value, "target": architecture.product_record_id, "label": architecture.product_name, "reason": "Objective requires the quantified components to be integrated and qualified as a complete product.", "objective_demand": annual_quantity, "capacity_state": "UNKNOWN", "dependency_state": "UNKNOWN", "prerequisites": sorted(action["id"] for action in actions if action["category"] in {ClosureActionCategory.MAKE.value, ClosureActionCategory.DEVELOP.value, ClosureActionCategory.LOCALIZE.value}), "supporting_evidence": [architecture.product_record_id], "unresolved_questions": []})
    for index, constraint in enumerate(objective.constraints):
        unresolved_paths = [row for row in dependency if row["constraint_effect"] == "UNRESOLVED"]
        if not unresolved_paths:
            continue
        target = str(constraint.value)
        question = (
            f"Verify source-country exposure across unresolved {architecture.product_name} dependency paths "
            f"against constraint {constraint.kind}={target}."
        )
        verification_id = f"verify:constraint:{index}:{constraint.kind.casefold()}"
        verification.append(
            {
                "id": verification_id,
                "target": architecture.product_record_id,
                "question": question,
                "reason": "CONSTRAINT_EXPOSURE_UNKNOWN",
                "affected_node_ids": [row["node_id"] for row in unresolved_paths],
            }
        )
        actions.append(
            {
                "id": f"action:{verification_id}",
                "category": ClosureActionCategory.VERIFY.value,
                "target": architecture.product_record_id,
                "label": architecture.product_name,
                "reason": question,
                "objective_demand": annual_quantity,
                "capacity_state": "UNKNOWN",
                "dependency_state": "UNKNOWN",
                "prerequisites": [],
                "supporting_evidence": [],
                "unresolved_questions": [question],
            }
        )
    actions = sorted({action["id"]: action for action in actions}.values(), key=lambda row: (row["category"], row["label"].casefold(), row["id"]))
    verification = sorted({row["id"]: row for row in verification}.values(), key=lambda row: (row["reason"], row["question"], row["id"]))

    stages_spec = (
        ("FOUNDATION", {"VERIFY", "DEVELOP"}),
        ("CAPACITY_EXPANSION", {"MAKE"}),
        ("LOCALIZATION", {"SOURCE", "LOCALIZE", "JV"}),
        ("INTEGRATION", {"INTEGRATE"}),
        ("SCALE_VALIDATION", set()),
    )
    staged = []
    earlier: list[str] = []
    for stage, categories in stages_spec:
        stage_actions = [action["id"] for action in actions if action["category"] in categories]
        if stage == "SCALE_VALIDATION" and actions:
            stage_actions = []
        if stage_actions or stage == "SCALE_VALIDATION":
            staged.append({"stage": stage, "action_ids": stage_actions, "depends_on": list(earlier), "exit_evidence": (["Objective-specific throughput, yield, quality, and qualification are verified."] if stage == "SCALE_VALIDATION" else [])})
            earlier.extend(stage_actions)

    evidence_ids = sorted({source for node in architecture.nodes for source in node.source_record_ids} | {source for edge in architecture.edges for source in edge.source_record_ids})
    evidence = [
        {
            "id": source,
            "kind": "FIXTURE_ASSUMPTION" if source.startswith("fixture:") else "SOURCE_RECORD",
            "epistemic_class": "ASSUMPTION" if source.startswith("fixture:") else "REPORTED_OR_MAPPED",
        }
        for source in evidence_ids
    ]

    result_class = bridge.solve_result.result_class.value
    if bridge.unresolved_edges or verification or confirmed_family:
        result_class = ResultClass.NOT_ADJUDICABLE.value
    diagnostics = sorted(set((*architecture.diagnostics, *bridge.diagnostics, *bridge.solve_result.conditional_reasons)))
    return IndustrialObjectiveCompilation(
        resolved_objective={
            **objective.to_dict(),
            "record_id": architecture.product_record_id,
            "family_key": architecture.family_key,
            "family_level": confirmed_family,
            "resolution_classification": resolution["resolution"]["classification"],
        },
        architecture=architecture,
        demand_ledger=demand,
        capability_ledger=capability,
        capacity_ledger=capacity_ledger,
        dependency_ledger=dependency,
        gap_ledger=gap_ledger,
        bottlenecks=bottlenecks,
        closure_actions=actions,
        staged_plan=staged,
        verification_frontier=verification,
        evidence_references=evidence,
        compiler_diagnostics=diagnostics,
        result_class=result_class,
    )


__all__ = ["objective_from_text", "compile_industrial_objective"]
