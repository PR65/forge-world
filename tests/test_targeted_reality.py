from pathlib import Path

from forge.adapters import OfficialRecordCatalogAdapter
from forge.composition import compose_benchmark_set, load_objective_seeds
from forge.pack import load_pack
from forge.registry import load_registry
from scripts.homi_targeted_promote import build_ledger


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "data" / "ingestion" / "homi_targeted_observations.yaml"
PACK = ROOT / "packs" / "targeted_industrial_reality.yaml"


def test_targeted_catalog_runs_full_reviewed_promotion_path():
    results = OfficialRecordCatalogAdapter(CATALOG).load()
    assert len(results) == 14
    assert sum(len(result.observations) for result in results) == 14
    assert all(not result.source_snapshot.raw_payload_stored for result in results)
    assert all(result.source_snapshot.license != "UNSPECIFIED" for result in results)

    ledger = build_ledger()
    assert ledger["promotion_count"] == 14
    assert ledger["all_promotions_source_linked"] is True
    assert ledger["effective_capacity_promotion_count"] == 0
    assert all(row["mapped_registry_entity_ids"] for row in ledger["rows"])


def test_targeted_pack_is_foundational_and_capacity_safe():
    pack = load_pack(PACK)
    summary = pack.summary()
    assert summary["variants"] == []
    assert len(pack.evidence) == 14
    assert all(record.source_ids for record in pack.evidence.values())
    assert not any(entity.kind == "capacity_segment" for entity in pack.world.entities.values())
    claims = [
        entity for entity in pack.world.entities.values() if entity.kind == "capability_claim"
    ]
    assert len(claims) == 14
    assert all(claim.vector.get("qualified_effective_capacity") == "UNKNOWN" for claim in claims)


def test_targeted_mappings_enrich_existing_and_new_canonical_families():
    registry = load_registry()
    expected = {
        "cap:power-electronics",
        "cap:electric-motors",
        "cap:industrial-electronics",
        "cap:encoders-position-sensing",
        "cap:electrochemical-stacks",
        "cap:membrane-electrode-assemblies",
        "cap:industrial-gas-systems",
        "cap:industrial-compressors",
        "cap:heat-exchangers",
        "cap:metrology",
        "cap:precision-bearings",
        "cap:precision-grinding",
        "cap:space-optical-payloads",
    }
    for canonical_id in expected:
        node = registry.nodes[canonical_id]
        mapped = [registry.nodes[node_id] for node_id in node.metadata["mapped_entity_ids"]]
        assert any(
            candidate.pack_id == "targeted_industrial_reality"
            and candidate.evidence_ids
            and candidate.epistemic_class == "UNKNOWN"
            for candidate in mapped
        )


def test_targeted_closure_improves_composition_without_becoming_a_verdict():
    benchmark = load_objective_seeds(ROOT / "data" / "objectives" / "novel_objectives.yaml")
    composition = compose_benchmark_set(load_registry(), benchmark)
    assert composition["mean_composition_coverage"] == 0.96131
    assert composition["total_decision_critical_unknowns"] == 2
    assert all(
        objective["status"] == "COMPOSITION_DIAGNOSTIC_NOT_SOLVER_VERDICT"
        for objective in composition["objectives"]
    )
