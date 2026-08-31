from __future__ import annotations

import pytest

from forge.india_v1.compiler_bridge import CapacityObservation, compile_architecture_to_core
from forge.india_v1.objective_models import (
    ArchitectureEdge,
    ArchitectureNode,
    ArchitectureNodeKind,
    CoefficientState,
    DerivationClass,
    ProductArchitecture,
    QuantitativeCoefficient,
)
from forge.units import UnitError


def _node(node_id: str, kind: ArchitectureNodeKind = ArchitectureNodeKind.PRODUCT_COMPONENT) -> ArchitectureNode:
    return ArchitectureNode(
        id=node_id,
        label=node_id.title(),
        kind=kind,
        source_record_ids=(f"source:{node_id}",),
        derivation_class=DerivationClass.EXPLICIT,
    )


def _edge(source: str, destination: str, value: float | None, unit: str = "pcs") -> ArchitectureEdge:
    state = CoefficientState.UNKNOWN if value is None else CoefficientState.SUPPORTED
    return ArchitectureEdge(
        source_id=source,
        destination_id=destination,
        relation="contains_component",
        source_record_ids=(f"edge:{source}:{destination}",),
        derivation_class=DerivationClass.EXPLICIT,
        coefficient=QuantitativeCoefficient(
            value=value,
            unit=unit,
            state=state,
            source_record_ids=(f"coefficient:{source}:{destination}",),
        ),
    )


def _architecture(nodes: tuple[ArchitectureNode, ...], edges: tuple[ArchitectureEdge, ...]) -> ProductArchitecture:
    return ProductArchitecture(
        product_record_id="root",
        product_name="Root Product",
        family_key="test:root",
        nodes=nodes,
        edges=edges,
        coverage_class="EXACT_ARCHITECTURE",
    )


def _quantity(result, node_id: str) -> float:
    core_id = result.node_to_core[node_id]
    line = result.explosion.get(core_id)
    assert line is not None
    return line.gross_annual.value


def test_bridge_propagates_one_and_multiple_levels_through_core_explosion() -> None:
    architecture = _architecture(
        (_node("root", ArchitectureNodeKind.PRODUCT_SYSTEM), _node("a"), _node("b")),
        (_edge("root", "a", 2.0), _edge("a", "b", 3.0)),
    )

    result = compile_architecture_to_core(architecture, annual_quantity=100.0, target_year=2030)

    assert _quantity(result, "a") == 200.0
    assert _quantity(result, "b") == 600.0


def test_bridge_aggregates_shared_dependencies_once_per_incoming_path() -> None:
    architecture = _architecture(
        tuple(_node(node, ArchitectureNodeKind.PRODUCT_SYSTEM if node == "root" else ArchitectureNodeKind.PRODUCT_COMPONENT) for node in ("root", "a", "b", "shared")),
        (
            _edge("root", "a", 2.0),
            _edge("root", "b", 3.0),
            _edge("a", "shared", 5.0),
            _edge("b", "shared", 7.0),
        ),
    )

    result = compile_architecture_to_core(architecture, annual_quantity=10.0, target_year=2030)

    assert _quantity(result, "shared") == 310.0


def test_unknown_coefficient_is_preserved_and_never_defaulted_to_one() -> None:
    architecture = _architecture(
        (_node("root", ArchitectureNodeKind.PRODUCT_SYSTEM), _node("unknown")),
        (_edge("root", "unknown", None),),
    )

    result = compile_architecture_to_core(architecture, annual_quantity=100.0, target_year=2030)

    assert result.explosion.get(result.node_to_core["unknown"]) is None
    assert result.unresolved_edges == [
        {
            "destination_id": "unknown",
            "reason": "QUANTITY_UNKNOWN",
            "source_id": "root",
            "source_record_ids": ["edge:root:unknown"],
        }
    ]


def test_bridge_rejects_cycles_and_incompatible_units() -> None:
    cyclic = _architecture(
        (_node("root", ArchitectureNodeKind.PRODUCT_SYSTEM), _node("a")),
        (_edge("root", "a", 1.0), _edge("a", "root", 1.0)),
    )
    with pytest.raises(UnitError, match="cyclic BOM"):
        compile_architecture_to_core(cyclic, annual_quantity=1.0, target_year=2030)

    incompatible = _architecture(
        (
            _node("root", ArchitectureNodeKind.PRODUCT_SYSTEM),
            _node("a"),
            _node("b"),
            _node("material", ArchitectureNodeKind.MATERIAL),
        ),
        (
            _edge("root", "a", 1.0),
            _edge("root", "b", 1.0),
            _edge("a", "material", 2.0, "kg_product"),
            _edge("b", "material", 3.0, "pcs"),
        ),
    )
    with pytest.raises(UnitError, match="incompatible declared units"):
        compile_architecture_to_core(incompatible, annual_quantity=1.0, target_year=2030)


def test_capacity_known_interval_unknown_and_unit_validation() -> None:
    architecture = _architecture(
        (_node("root", ArchitectureNodeKind.PRODUCT_SYSTEM), _node("component")),
        (_edge("root", "component", 2.0),),
    )
    exact = compile_architecture_to_core(
        architecture,
        annual_quantity=100.0,
        target_year=2030,
        capacity_observations=(CapacityObservation("component", 80.0, 80.0),),
    )
    envelope = exact.capacity_envelopes[exact.node_to_core["component"]]
    assert (envelope.domestic.lo, envelope.domestic.hi) == (80.0, 80.0)

    interval = compile_architecture_to_core(
        architecture,
        annual_quantity=100.0,
        target_year=2030,
        capacity_observations=(CapacityObservation("component", 40.0, 60.0),),
    )
    assert interval.capacity_overrides[interval.node_to_core["component"]] == (40.0, 60.0)

    unknown = compile_architecture_to_core(architecture, annual_quantity=100.0, target_year=2030)
    assert unknown.capacity_envelopes[unknown.node_to_core["component"]].domestic.is_unknown()

    with pytest.raises(UnitError, match="incompatible unit"):
        compile_architecture_to_core(
            architecture,
            annual_quantity=100.0,
            target_year=2030,
            capacity_observations=(CapacityObservation("component", 40.0, 60.0, unit="kg_product"),),
        )


def test_bridge_is_deterministic() -> None:
    architecture = _architecture(
        (_node("root", ArchitectureNodeKind.PRODUCT_SYSTEM), _node("a")),
        (_edge("root", "a", 4.0),),
    )
    first = compile_architecture_to_core(architecture, annual_quantity=25.0, target_year=2030)
    second = compile_architecture_to_core(architecture, annual_quantity=25.0, target_year=2030)

    assert first.explosion.lines == second.explosion.lines
    assert first.unresolved_edges == second.unresolved_edges
    assert first.solve_result.result_class == second.solve_result.result_class
