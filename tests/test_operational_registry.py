from pathlib import Path

from forge.adapters import OfficialRecordCatalogAdapter
from forge.operations import capability_leverage
from forge.registry import load_registry


ROOT = Path(__file__).resolve().parent.parent


def test_canonical_registry_covers_cross_sector_operational_capabilities():
    registry = load_registry()
    capabilities = [node for node in registry.nodes.values() if node.kind == "capability"]

    assert len(capabilities) >= 30
    required = {
        "cap:precision-motion-components",
        "cap:precision-bearings",
        "cap:precision-reducers",
        "cap:rare-earth-separation",
        "cap:nuclear-pressure-boundary",
        "cap:nuclear-fuel-cycle",
    }
    assert required <= {node.id for node in capabilities}
    assert not {
        node.id: node.metadata["unresolved_mappings"]
        for node in capabilities
        if node.metadata.get("unresolved_mappings")
    }
    assert all(node.epistemic_class == "UNKNOWN" for node in capabilities)


def test_discover_ranking_is_computed_from_registry_topology():
    registry = load_registry()
    result = capability_leverage(registry, limit=100)
    rows = {row["capability_id"]: row for row in result["capabilities"]}

    assert result["metric"] == "TOPOLOGICAL_CAPABILITY_LEVERAGE_PROXY"
    assert "economic option value" in result["not_claimed"]
    assert rows["cap:precision-bearings"]["cross_sector_reuse"] >= 2
    assert rows["cap:precision-bearings"]["mapped_entity_count"] >= 6
    assert rows["cap:nuclear-pressure-boundary"]["open_research_task_count"] >= 1


def test_builder_registry_preserves_candidate_not_qualified_boundary():
    registry = load_registry()
    bhel = registry.get_entity("builder:bhel")
    mapped = registry.get_entity("pack:nuclear_buildout_india:org_bhel")

    assert bhel and mapped
    assert bhel["epistemic_class"] == "UNKNOWN"
    assert "cap:steam-generators" in bhel["metadata"]["capability_ids"]
    assert "builder:bhel" in mapped["metadata"]["builder_ids"]
    assert "capacity" not in bhel["metadata"]


def test_checked_in_official_observations_bind_to_real_registry_subjects():
    registry = load_registry()
    results = OfficialRecordCatalogAdapter(
        ROOT / "data" / "ingestion" / "official_observations.yaml"
    ).load()

    missing = {
        observation.subject
        for result in results
        for observation in result.observations
        if registry.get_entity(observation.subject) is None
    }
    assert not missing
