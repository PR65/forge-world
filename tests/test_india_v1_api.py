"""Backend/API contract tests for the combined India V1 breadth catalog."""

from __future__ import annotations

import time

from fastapi.testclient import TestClient

from forge.india_v1.catalog import get_catalog
from server.app import app


client = TestClient(app)


def test_india_summary_has_all_domains_and_direct_distributions():
    response = client.get("/api/india/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["depth_profile"] == "V1_BROAD"
    assert payload["record_count"] == 14653
    assert payload["direct_record_count"] == 12253
    assert payload["owned_record_count"] == 12172
    assert payload["shared_source_record_count"] == 81
    assert payload["reference_record_count"] == 2400
    assert set(payload["domain_counts"]) == {f"{number:02d}" for number in range(1, 13)}
    assert sum(payload["domain_counts"].values()) == payload["owned_record_count"]
    assert sum(payload["direct_kind_counts"].values()) == payload["direct_record_count"]
    assert sum(payload["direct_status_counts"].values()) == payload["direct_record_count"]
    assert payload["integrity"]["all_references_resolve"] is True


def test_india_domains_are_frontend_navigable():
    response = client.get("/api/india/domains")
    assert response.status_code == 200
    domains = response.json()["domains"]
    assert [row["id"] for row in domains] == [f"{number:02d}" for number in range(1, 13)]
    assert all(row["description"] and row["record_count"] >= 800 for row in domains)


def test_india_search_aliases_and_filters_prefer_real_records():
    response = client.get("/api/india/search", params={"q": "5-axis CNC", "limit": 5})
    assert response.status_code == 200
    results = response.json()["results"]
    assert results
    assert all(row["domain_code"] == "05" for row in results)
    assert all(row["is_reference_only"] is False for row in results)
    assert any("5-axis" in row["canonical_name"].lower() for row in results)

    filtered = client.get(
        "/api/india/search",
        params={"q": "nuclear", "domain": "03", "kind": "CAPABILITY", "status": "UNKNOWN", "limit": 3},
    )
    assert filtered.status_code == 200
    assert all(row["domain_code"] == "03" and row["kind"] == "CAPABILITY" and row["status"] == "UNKNOWN" for row in filtered.json()["results"])

    for query in ("precision grinding", "semiconductor", "ball screw"):
        found = client.get("/api/india/search", params={"q": query, "limit": 3})
        assert found.status_code == 200
        assert found.json()["results"], query


def test_india_record_detail_exposes_navigable_contract_and_unknown_honesty():
    result = client.get("/api/india/search", params={"q": "nuclear waste", "limit": 1}).json()["results"][0]
    response = client.get(f"/api/india/records/{result['id']}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["depth_profile"] == "V1_BROAD"
    assert payload["explanation"] and payload["use"] and payload["status_basis"]
    assert set(payload["dependencies"]) == {"systems", "processes", "materials", "equipment", "capabilities"}
    assert all("id" in item and "canonical_name" in item for item in payload["dependencies"]["capabilities"])
    assert payload["unlocks"] == payload["downstream"]
    assert payload["links"]["upstream"] == payload["upstream"]
    assert len(payload["making_ladder"]) >= 5
    assert payload["status"] == "UNKNOWN"
    assert payload["status_basis"]


def test_india_graph_is_bounded_and_discover_is_deterministic():
    record_id = client.get("/api/india/search", params={"q": "satellite", "limit": 1}).json()["results"][0]["id"]
    response = client.get(f"/api/india/graph/{record_id}", params={"depth": 2, "limit": 12})
    assert response.status_code == 200
    graph = response.json()
    assert graph["depth_profile"] == "V1_BROAD"
    assert len(graph["nodes"]) <= 12
    assert all(node["depth"] <= 2 for node in graph["nodes"])
    assert all(edge["source"] != edge["target"] for edge in graph["edges"])

    first = client.get("/api/india/discover", params={"limit": 8})
    second = client.get("/api/india/discover", params={"limit": 8})
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert len(first.json()["examples"]) == 8


def test_high_reuse_foundation_record_links_are_bounded():
    response = client.get("/api/india/records/shared:capability:industrial_metrology")
    assert response.status_code == 200
    payload = response.json()
    assert payload["link_counts"]["downstream"] > 100
    assert payload["links_truncated"]["downstream"] is True
    assert len(payload["downstream"]) == 100
    assert len(payload["downstream_ids"]) == 100


def test_india_inputs_are_bounded_and_missing_records_are_404():
    assert client.get("/api/india/records/not-a-record").status_code == 404
    assert client.get("/api/india/search", params={"q": "x" * 201}).status_code == 422
    assert client.get("/api/india/search", params={"kind": "not-a-kind"}).status_code == 422
    assert client.get("/api/india/search", params={"domain": "99"}).status_code == 422
    assert client.get("/api/india/graph/not-a-record").status_code == 404
    assert client.get("/api/india/graph/not-a-record", params={"depth": 5}).status_code == 422


def test_catalog_cache_and_indexed_search_are_reused():
    first = get_catalog()
    assert get_catalog() is first
    start = time.perf_counter()
    results = first.search("semiconductor equipment", limit=25)
    elapsed = time.perf_counter() - start
    assert results
    assert elapsed < 0.5
