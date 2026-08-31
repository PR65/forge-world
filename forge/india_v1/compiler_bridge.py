"""Explicit India V1 ↔ quantitative-core adapter boundary.

Only physical edges carrying a non-UNKNOWN coefficient become core BOM edges.
All other architecture remains available to the capability/verification layers
without being fabricated into a quantitative ``World``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

from forge.capacity import CapacityEnvelope, capacity_envelope
from forge.evidence import ProofGraph
from forge.explode import ExplosionResult, explode_variant
from forge.model import (
    CapacitySegment,
    Entity,
    EquipmentClass,
    Part,
    ProcessStep,
    Qualification,
    ResourceClass,
    World,
)
from forge.solve import ScenarioOptions, SolveResult, solve_objective
from forge.units import Quantity, UnitError

from .objective_models import (
    ArchitectureNode,
    ArchitectureNodeKind,
    CoefficientState,
    ProductArchitecture,
)


_PHYSICAL = {
    ArchitectureNodeKind.PRODUCT_SYSTEM,
    ArchitectureNodeKind.PRODUCT_COMPONENT,
    ArchitectureNodeKind.MATERIAL,
}


@dataclass(frozen=True)
class CapacityObservation:
    node_id: str
    lo: float | None
    hi: float | None
    unit: str = "pcs"
    geography: str = "INDIA"
    epistemic_class: str = "ASSUMPTION"
    source_record_ids: tuple[str, ...] = ()
    note: str = ""

    def __post_init__(self) -> None:
        if (self.lo is None) != (self.hi is None):
            raise ValueError("capacity interval must provide both lo and hi or neither")
        if self.lo is not None and (self.lo < 0 or self.hi < self.lo):
            raise ValueError("capacity interval must satisfy 0 <= lo <= hi")


@dataclass
class BridgeResult:
    world: World
    proof_graph: ProofGraph
    explosion: ExplosionResult
    solve_result: SolveResult
    node_to_core: dict[str, str]
    unresolved_edges: list[dict]
    capacity_envelopes: dict[str, CapacityEnvelope]
    capacity_overrides: dict[str, tuple[float, float]]
    diagnostics: list[str] = field(default_factory=list)


def _core_id(node_id: str) -> str:
    return f"india_objective::{node_id}"


def _entity(node: ArchitectureNode, unit: str = "pcs") -> Entity:
    common = dict(
        id=_core_id(node.id),
        name=node.label,
        notes=(
            f"India V1 bridge; derivation={node.derivation_class.value}; "
            f"epistemic={node.epistemic_class}. {node.description}"
        ).strip(),
        evidence_ids=tuple(node.source_record_ids),
    )
    if node.kind in {ArchitectureNodeKind.PRODUCT_SYSTEM, ArchitectureNodeKind.PRODUCT_COMPONENT}:
        return Part(kind="part", part_class="subassembly" if node.kind is ArchitectureNodeKind.PRODUCT_SYSTEM else "component", **common)
    if node.kind is ArchitectureNodeKind.MATERIAL:
        return ResourceClass(kind="resource_class", category="material", unit=unit, **common)
    if node.kind in {ArchitectureNodeKind.MANUFACTURING_EQUIPMENT, ArchitectureNodeKind.METROLOGY}:
        return EquipmentClass(kind="equipment_class", **common)
    if node.kind is ArchitectureNodeKind.MANUFACTURING_PROCESS:
        return ProcessStep(kind="process_step", **common)
    if node.kind is ArchitectureNodeKind.QUALIFICATION:
        return Qualification(kind="qualification", item_id="", **common)
    return Entity(kind=node.kind.value.casefold(), **common)


def _typed_relation(kind: ArchitectureNodeKind) -> str:
    if kind is ArchitectureNodeKind.MATERIAL:
        return "requires_input"
    if kind in {ArchitectureNodeKind.MANUFACTURING_EQUIPMENT, ArchitectureNodeKind.METROLOGY}:
        return "requires_equipment"
    if kind is ArchitectureNodeKind.QUALIFICATION:
        return "requires_qualification"
    return "requires_capability"


def compile_architecture_to_core(
    architecture: ProductArchitecture,
    *,
    annual_quantity: float,
    target_year: int,
    geography: str = "INDIA",
    capacity_observations: Sequence[CapacityObservation] = (),
    import_eligibility: Mapping[str, float] | None = None,
) -> BridgeResult:
    """Translate supported structure, then run the existing core machinery."""

    if not architecture.nodes:
        raise ValueError("cannot bridge an unresolved architecture")
    if annual_quantity <= 0:
        raise ValueError("annual_quantity must be positive")

    world = World()
    proof = ProofGraph()
    node_map = {node.id: _core_id(node.id) for node in architecture.nodes}
    unit_by_node: dict[str, str] = {node.id: "pcs" for node in architecture.nodes}
    declared_units: dict[str, set[str]] = {}
    for edge in architecture.edges:
        coefficient = edge.coefficient
        if coefficient is None or coefficient.state is CoefficientState.UNKNOWN:
            continue
        if coefficient.unit:
            declared_units.setdefault(edge.destination_id, set()).add(coefficient.unit)
    for node_id, units in sorted(declared_units.items()):
        selected = sorted(units)[0]
        for unit in sorted(units)[1:]:
            try:
                Quantity(1.0, unit).to(selected)
            except (KeyError, UnitError) as exc:
                rendered = ", ".join(sorted(units))
                raise UnitError(
                    f"item '{node_id}' demanded in incompatible declared units ({rendered})"
                ) from exc
        unit_by_node[node_id] = selected

    for node in architecture.nodes:
        unit = unit_by_node[node.id]
        if node.kind in {ArchitectureNodeKind.PRODUCT_SYSTEM, ArchitectureNodeKind.PRODUCT_COMPONENT}:
            try:
                Quantity(1.0, unit).to("pcs")
            except (KeyError, UnitError) as exc:
                raise UnitError(
                    f"physical component '{node.id}' must be count-compatible, not '{unit}'"
                ) from exc

    for node in architecture.nodes:
        entity = _entity(node, unit_by_node.get(node.id, "pcs"))
        world.add(entity)
        proof.add_node(
            "parameter",
            f"Architecture node: {node.label}",
            node.to_dict(),
            tuple(node.source_record_ids),
            node_id=f"arch.{len(proof.nodes) + 1}",
        )

    root_core = node_map[architecture.product_record_id]
    # explode_variant accepts any entity as its objective root; identify this
    # bounded bridge root explicitly as the product variant.
    world.entities[root_core].kind = "product_variant"

    unresolved: list[dict] = []
    diagnostics: list[str] = []
    for edge in architecture.edges:
        src = node_map.get(edge.source_id)
        dst = node_map.get(edge.destination_id)
        node = architecture.node(edge.destination_id)
        if src is None or dst is None or node is None:
            diagnostics.append(f"Skipped edge with missing endpoint: {edge.source_id}->{edge.destination_id}")
            continue
        coefficient = edge.coefficient
        if node.kind in _PHYSICAL:
            if coefficient is None or coefficient.state is CoefficientState.UNKNOWN:
                unresolved.append(
                    {
                        "source_id": edge.source_id,
                        "destination_id": edge.destination_id,
                        "reason": "QUANTITY_UNKNOWN",
                        "source_record_ids": list(edge.source_record_ids),
                    }
                )
                continue
            world.link(
                src,
                "decomposes_into",
                dst,
                qty=Quantity(float(coefficient.value), coefficient.unit).to(unit_by_node[edge.destination_id]).value,
                unit=unit_by_node[edge.destination_id],
                coefficient_state=coefficient.state.value,
                source_record_ids=list(coefficient.source_record_ids),
            )
            if coefficient.state is CoefficientState.ASSUMPTION:
                proof.assumption(
                    f"Coefficient assumption: {edge.source_id} -> {edge.destination_id}",
                    coefficient.to_dict(),
                )
        else:
            relation = _typed_relation(node.kind)
            world.link(src, relation, dst, source_record_ids=list(edge.source_record_ids))

    overrides: dict[str, tuple[float, float]] = {}
    observations_by_core: dict[str, CapacityObservation] = {}
    for index, observation in enumerate(capacity_observations):
        core_id = node_map.get(observation.node_id)
        if core_id is None:
            diagnostics.append(f"Capacity observation target not in architecture: {observation.node_id}")
            continue
        observations_by_core[core_id] = observation
        if observation.lo is None:
            continue
        expected_unit = unit_by_node[observation.node_id]
        try:
            lo = Quantity(float(observation.lo), observation.unit).to(expected_unit).value
            hi = Quantity(float(observation.hi), observation.unit).to(expected_unit).value
        except (KeyError, UnitError) as exc:
            raise UnitError(
                f"capacity for '{observation.node_id}' uses incompatible unit "
                f"'{observation.unit}' (required '{expected_unit}')"
            ) from exc
        if lo == hi:
            world.add(
                CapacitySegment(
                    id=f"objective_capacity::{index}::{core_id}",
                    name=f"Declared capacity for {world.entities[core_id].name}",
                    kind="capacity_segment",
                    item_id=core_id,
                    geography=observation.geography,
                    nameplate_annual=Quantity(hi, expected_unit),
                    valid_from=target_year,
                    valid_to=target_year,
                    epistemic_class=observation.epistemic_class,
                    evidence_ids=observation.source_record_ids,
                    notes=observation.note,
                )
            )
        else:
            overrides[core_id] = (lo, hi)
        if observation.epistemic_class == "ASSUMPTION":
            proof.assumption(
                f"Capacity assumption: {world.entities[core_id].name}",
                {
                    "lo": observation.lo,
                    "hi": observation.hi,
                    "unit": observation.unit,
                    "note": observation.note,
                },
            )

    explosion = explode_variant(
        world,
        proof,
        root_core,
        annual_quantity,
        [target_year],
        geography=geography,
    )
    options = ScenarioOptions(
        geography=geography,
        capacity_overrides=overrides,
        import_eligibility=dict(import_eligibility or {}),
        foreign_supply_policy="strict",
        decision_year=target_year,
    )
    solved = solve_objective(world, proof, explosion, [target_year], options)
    envelopes = {
        item_id: capacity_envelope(world, item_id, target_year, geography=geography)
        for item_id in explosion.items()
    }
    return BridgeResult(
        world=world,
        proof_graph=proof,
        explosion=explosion,
        solve_result=solved,
        node_to_core=node_map,
        unresolved_edges=sorted(unresolved, key=lambda row: (row["source_id"], row["destination_id"])),
        capacity_envelopes=envelopes,
        capacity_overrides=overrides,
        diagnostics=sorted(set(diagnostics)),
    )


__all__ = ["CapacityObservation", "BridgeResult", "compile_architecture_to_core"]
