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
    catalog = get_catalog()
    assert payload["record_count"] == len(catalog.records)
    assert payload["direct_record_count"] == catalog.direct_record_count
    assert payload["reference_record_count"] == catalog.reference_record_count
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
    assert results[0]["domain_code"] == "05"
    assert any(row["domain_code"] == "05" and row["is_reference_only"] is False for row in results)
    assert any("5-axis" in row["canonical_name"].lower() for row in results)
    assert all(row["match_type"] for row in results)
    assert all(row["family_key"] for row in results)
    assert len({row["family_key"] for row in results}) == len(results)

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
    assert all("dependencies" not in item for item in payload["downstream"])


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


def test_india_search_alias_typo_related_and_variant_contracts():
    catalog = get_catalog()
    for query, expected_domain in (("magnetic resonance imaging", "07"), ("electrolyser", "03"), ("precision grindng", "12")):
        response = client.get("/api/india/search", params={"q": query, "limit": 5})
        assert response.status_code == 200
        results = response.json()["results"]
        assert results, query
        assert results[0]["domain_code"] == expected_domain
        assert results[0]["match_type"] in {"exact", "phrase", "all_tokens", "alias", "fuzzy", "related"}
        assert results[0]["matched_on"]

    grouped = client.get("/api/india/search", params={"q": "MRI", "limit": 10}).json()["results"]
    assert len({row["family_key"] for row in grouped}) == len(grouped)
    expanded = client.get("/api/india/search", params={"q": "MRI", "limit": 10, "include_variants": True}).json()["results"]
    assert len(expanded) >= len(grouped)

    shared_fallback = client.get("/api/india/search", params={"q": "robotic welding cell", "limit": 3}).json()["results"]
    assert shared_fallback
    assert shared_fallback[0]["domain_code"] == "05"
    assert shared_fallback[0]["match_type"] == "related"


def test_india_bootstrap_is_bounded_and_reuses_contracts():
    response = client.get("/api/india/bootstrap", params={"limit": 4})
    assert response.status_code == 200
    payload = response.json()
    assert payload["depth_profile"] == "V1_BROAD"
    assert len(payload["domains"]) == 12
    assert len(payload["discover"]["examples"]) <= 4


def test_india_launch_routes_and_public_documents_are_served():
    for route in ("/india", "/india/records/product%3A05%3Acnc-machining-center%3Aexample"):
        response = client.get(route)
        assert response.status_code == 200

    limitations = client.get("/docs/FORGE_INDIA_V1_KNOWN_LIMITATIONS.md")
    assert limitations.status_code == 200
    assert "UNKNOWN" in limitations.text and "valid" in limitations.text and "answer" in limitations.text

    assert client.get("/docs/FORGE_WORLD_NORTH_STAR.md").status_code == 404
