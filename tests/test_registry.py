from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from forge.evidence import EvidenceRecord
from forge.epistemics import EpistemicClass
from forge.ingestion import Observation, SourceSnapshot, promote_observation
from forge.pack import load_pack
from forge.registry import build_registry, load_registry
from server.app import app


def test_registry_snapshot_is_deterministic():
    first = load_registry()
    second = load_registry()

    assert first.snapshot_id == second.snapshot_id
    assert first.content_hash == second.content_hash
    assert first.snapshots() == second.snapshots()
    assert [p.to_json() for p in first.snapshot.pack_snapshots] == [
        p.to_json() for p in second.snapshot.pack_snapshots
    ]


def test_pack_local_identity_is_namespaced_and_isolated():
    registry = load_registry()

    humanoid = registry.get_entity("pack:humanoid_india:metrology_cmm")
    smallsat = registry.get_entity("pack:smallsat_india:metrology_cmm")
    assert humanoid and smallsat
    assert humanoid["id"] != smallsat["id"]
    assert humanoid["pack_id"] == "humanoid_india"
    assert smallsat["pack_id"] == "smallsat_india"
    assert registry.get_entity("metrology_cmm") is None


def test_canonical_capability_is_reused_explicitly_across_packs():
    registry = load_registry()
    metrology = registry.get_entity("cap:metrology")
    assert metrology
    assert metrology["epistemic_class"] == "UNKNOWN"
    assert metrology["metadata"]["mapping_source"] == "ASSUMPTION"
    assert set(metrology["metadata"]["mapped_pack_ids"]) >= {"humanoid_india", "smallsat_india"}
    assert metrology["metadata"]["mapping_count"] == len(metrology["metadata"]["mapped_entity_ids"])
    mapped = [
        edge
        for edge in registry.edges
        if edge.target == "cap:metrology" and edge.relation == "requires_or_represents"
    ]
    assert {edge.metadata["pack_id"] for edge in mapped} >= {"humanoid_india", "smallsat_india"}


def test_unknown_status_is_not_converted_to_zero_or_supply():
    registry = load_registry()
    unknown_claim = registry.get_entity("pack:humanoid_india:cc_india_reducer_unknown")
    heavy_forging = registry.get_entity("cap:heavy-forging")
    assert unknown_claim and heavy_forging
    assert unknown_claim["epistemic_class"] == "UNKNOWN"
    assert unknown_claim["metadata"]["typed"]["vector"]["qualified_effective_capacity"] == "UNKNOWN"
    assert heavy_forging["epistemic_class"] == "UNKNOWN"
    assert heavy_forging["metadata"]["mapping_source"] == "ASSUMPTION"
    assert "capacity" not in heavy_forging["metadata"]


def test_pack_evidence_has_traceable_source_snapshot_without_page_mirroring():
    registry = load_registry()
    node = registry.get_entity("pack:humanoid_india:rec_joint_actuator_body")
    assert node and node["evidence_ids"]
    evidence = registry.evidence_for(node["evidence_ids"][0])
    assert evidence
    assert evidence["pack_id"] == "humanoid_india"
    assert evidence["source_snapshots"]
    assert "source_snapshots" not in evidence["value_text"]
    source = evidence["source_snapshots"][0]
    assert source["content_hash"]
    assert source["hash_scope"] == "reference_metadata"
    assert source["raw_payload_stored"] is False
    assert source["storage_posture"] == "reference_only"


def test_bounded_slice_and_search_are_deterministic():
    registry = load_registry()
    result = registry.slice(
        pack_id="humanoid_india", root="hv2_industrial", depth=8, limit=4
    )
    assert result["root"] == "pack:humanoid_india:hv2_industrial"
    assert len(result["nodes"]) <= 4
    assert result["truncated"] is True
    assert all("id" in node and "epistemic_class" in node for node in result["nodes"])

    search = registry.search("metrology", limit=20)
    assert search
    assert any(node["canonical_id"] == "cap:metrology" for node in search)
    assert registry.search("metrology", limit=20) == search

    default_slice = registry.slice(pack_id="humanoid_india", depth=0, limit=10)
    assert default_slice["root"].startswith("pack:humanoid_india:")
    assert default_slice["nodes"][0]["kind"] == "product_variant"


def test_source_snapshot_observation_promotion_is_explicit_and_immutable():
    source = SourceSnapshot(
        source_id="src:test",
        content_hash="abc123",
        access_date="2026-08-24",
        license="public",
    )
    observation = Observation(
        observation_id="obs:test",
        source_snapshot_id=source.snapshot_id,
        subject="cap:test",
        predicate="status",
        value_text="unresolved",
        epistemic_class=EpistemicClass.UNKNOWN,
    )
    record, promotion = promote_observation(
        observation, source, reviewer="test", rationale="unknown remains unknown"
    )
    assert record.epistemic_class == EpistemicClass.UNKNOWN
    assert record.source_ids == ("src:test",)
    assert promotion.observation_id == observation.observation_id
    assert promotion.rationale == "unknown remains unknown"
    try:
        source.content_hash = "changed"  # type: ignore[misc]
    except Exception:
        pass
    assert source.content_hash == "abc123"


def test_registry_records_are_recursively_immutable():
    registry = load_registry()
    node = registry.nodes["pack:humanoid_india:rec_joint_actuator_body"]

    with pytest.raises(TypeError):
        node.metadata["typed"]["name"] = "mutated"  # type: ignore[index]
    with pytest.raises(TypeError):
        node.metadata["typed"]["evidence_ids"][0] = "mutated"  # type: ignore[index]


def test_reported_promotion_requires_identified_licensed_source():
    source = SourceSnapshot(source_id="", content_hash="abc123", license="UNSPECIFIED")
    observation = Observation(
        observation_id="obs:reported",
        source_snapshot_id=source.snapshot_id,
        subject="cap:test",
        predicate="status",
        value_text="available",
        epistemic_class=EpistemicClass.REPORTED,
    )
    with pytest.raises(ValueError, match="source id"):
        promote_observation(observation, source)

    source = SourceSnapshot(source_id="src:test", content_hash="abc123", license="UNSPECIFIED")
    observation = Observation(
        observation_id="obs:reported",
        source_snapshot_id=source.snapshot_id,
        subject="cap:test",
        predicate="status",
        value_text="available",
        epistemic_class=EpistemicClass.REPORTED,
    )
    with pytest.raises(ValueError, match="source license"):
        promote_observation(observation, source)


def test_superseded_claim_does_not_create_false_conflict():
    root = Path(__file__).resolve().parents[1]
    pack = load_pack(str(root / "packs" / "humanoid_india.yaml"))
    pack.evidence["ev_registry_old"] = EvidenceRecord(
        claim_id="ev_registry_old",
        subject="joint actuator body",
        predicate="status",
        epistemic_class=EpistemicClass.REPORTED,
        value_text="old status",
    )
    pack.evidence["ev_registry_new"] = EvidenceRecord(
        claim_id="ev_registry_new",
        subject="joint actuator body",
        predicate="status",
        epistemic_class=EpistemicClass.REPORTED,
        value_text="corrected status",
        supersedes="ev_registry_old",
    )
    pack.world.entities["rec_joint_actuator_body"].evidence_ids = (
        "ev_registry_old",
        "ev_registry_new",
    )

    registry = build_registry([pack], {})
    node = registry.get_entity("pack:humanoid_india:rec_joint_actuator_body")
    assert node
    assert node["epistemic_class"] == "REPORTED"
    assert node["metadata"]["superseded_evidence_ids"] == [
        "pack:humanoid_india:evidence:ev_registry_old"
    ]
    assert "conflicting_evidence_ids" not in node["metadata"]


def test_world_api_surfaces_registry_contract():
    client = TestClient(app)

    summary = client.get("/api/world/summary")
    assert summary.status_code == 200
    assert summary.json()["pack_count"] >= 3

    search = client.get("/api/world/search", params={"q": "metrology", "limit": 5})
    assert search.status_code == 200
    assert search.json()["results"]

    entity = client.get("/api/world/entities/cap:metrology")
    assert entity.status_code == 200
    assert set(
        ("id", "name", "kind", "pack_id", "canonical_id", "epistemic_class", "evidence_ids", "metadata")
    ).issubset(entity.json())

    bounded = client.get(
        "/api/world/slice",
        params={"pack_id": "humanoid_india", "root": "hv2_industrial", "depth": 6, "limit": 3},
    )
    assert bounded.status_code == 200
    assert set(bounded.json()) == {"nodes", "edges", "root", "truncated"}
    assert len(bounded.json()["nodes"]) <= 3

    capabilities = client.get("/api/world/capabilities")
    assert capabilities.status_code == 200
    assert any(row["id"] == "cap:battery-cell" for row in capabilities.json()["capabilities"])

    builders = client.get("/api/world/builders")
    assert builders.status_code == 200
    assert builders.json()["builders"]

    evidence_id = "pack:humanoid_india:evidence:ev_humanoid_envelope"
    evidence = client.get(f"/api/world/evidence/{evidence_id}")
    assert evidence.status_code == 200
    assert evidence.json()["evidence_id"] == evidence_id

    tasks = client.get("/api/world/evidence-tasks")
    assert tasks.status_code == 200
    assert tasks.json()["evidence_tasks"]

    snapshots = client.get("/api/world/snapshots")
    assert snapshots.status_code == 200
    assert snapshots.json()["registry"]["hash"] == summary.json()["hash"]
