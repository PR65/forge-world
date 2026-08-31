from __future__ import annotations

from types import SimpleNamespace

import pytest

from forge.india_v1.architecture import compile_product_architecture
from forge.india_v1.catalog import get_catalog
from forge.india_v1.objective import resolve_objective
from forge.india_v1.objective_models import ArchitectureNodeKind, DerivationClass


@pytest.fixture(scope="module")
def catalog():
    return get_catalog()


def test_structured_requirements_do_not_become_physical_subsystems(catalog) -> None:
    record = catalog.by_id["d03:product:hydrogen_electrolyzer:modular"]
    architecture = compile_product_architecture(record, catalog)
    physical = [
        node for node in architecture.nodes
        if node.id != architecture.product_record_id
        and node.kind in {ArchitectureNodeKind.PRODUCT_SYSTEM, ArchitectureNodeKind.PRODUCT_COMPONENT}
    ]
    assert physical == []
    assert architecture.coverage_class == "STRUCTURAL_REQUIREMENTS_ONLY"
    environment = [node.label.casefold() for node in architecture.nodes if node.kind is ArchitectureNodeKind.INDUSTRIAL_ENVIRONMENT]
    assert any("power" in label for label in environment)
    assert all("power" not in node.label.casefold() for node in physical)


def test_long_tail_record_keeps_process_material_and_capability_types(catalog) -> None:
    record = catalog.by_id["india-v1:11:textile-weaving-machine:air-jet-loom:cotton"]
    architecture = compile_product_architecture(record, catalog)
    kinds = {node.kind for node in architecture.nodes}
    assert ArchitectureNodeKind.MANUFACTURING_PROCESS in kinds
    assert ArchitectureNodeKind.MATERIAL in kinds
    assert ArchitectureNodeKind.MANUFACTURING_CAPABILITY in kinds
    assert ArchitectureNodeKind.INDUSTRIAL_ENVIRONMENT in kinds
    assert all(node.source_record_ids for node in architecture.nodes)
    assert all(edge.source_record_ids for edge in architecture.edges)


def test_family_level_confirmation_changes_provenance_not_status(catalog) -> None:
    record = catalog.by_id["d03:product:battery_energy_storage:modular"]
    exact = compile_product_architecture(record, catalog)
    family = compile_product_architecture(record, catalog, family_level=True)
    assert family.coverage_class == "FAMILY_LEVEL_ARCHITECTURE"
    assert {node.derivation_class for node in family.nodes} == {DerivationClass.FAMILY_LEVEL}
    assert [(node.id, node.status) for node in family.nodes] == [(node.id, node.status) for node in exact.nodes]


def test_recursive_physical_focus_is_bounded_and_cycle_safe() -> None:
    root = {
        "id": "root", "canonical_name": "Machine", "family_key": "machine", "kind": "PRODUCT",
        "status": "UNKNOWN", "status_epistemic_class": "UNKNOWN", "dependencies": {"systems": ["system"]},
    }
    system = {
        "id": "system", "canonical_name": "Motion system", "family_key": "motion", "kind": "PRODUCT",
        "category": "physical subsystem", "status": "UNKNOWN", "status_epistemic_class": "UNKNOWN",
        "dependencies": {"components": ["component"]},
    }
    component = {
        "id": "component", "canonical_name": "Ball screw", "family_key": "ball_screw", "kind": "PRODUCT",
        "category": "component", "status": "UNKNOWN", "status_epistemic_class": "UNKNOWN",
        "dependencies": {"systems": ["root"]},
    }
    catalog = SimpleNamespace(by_id={item["id"]: item for item in (root, system, component)})
    architecture = compile_product_architecture(root, catalog, max_depth=3)
    assert architecture.node("system").kind is ArchitectureNodeKind.PRODUCT_SYSTEM
    assert architecture.node("component").kind is ArchitectureNodeKind.PRODUCT_COMPONENT
    assert max(node.depth for node in architecture.nodes) == 2
    assert len({(edge.source_id, edge.destination_id, edge.relation) for edge in architecture.edges}) == len(architecture.edges)


def test_compilation_is_deterministic(catalog) -> None:
    record = catalog.by_id["product:05:servo-motor:heavy-induction-standalone"]
    first = compile_product_architecture(record, catalog).to_dict()
    second = compile_product_architecture(record, catalog).to_dict()
    assert first == second


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("air-jet loom", "STRONG"),
        ("lithium-ion pouch cell", "NEAREST"),
        ("satellite reaction wheel", "UNRESOLVED"),
        ("grain colour sorter", "UNRESOLVED"),
        ("hydraulic breaker", "UNRESOLVED"),
        ("vacuum pump", "UNRESOLVED"),
    ],
)
def test_data_driven_resolution_is_safe_on_long_tail(catalog, query: str, expected: str) -> None:
    assert resolve_objective(query, catalog)["resolution"]["classification"] == expected
