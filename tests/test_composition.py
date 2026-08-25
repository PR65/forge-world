from pathlib import Path

from forge.composition import compose_benchmark_set, load_objective_seeds, rank_decision_gaps
from forge.registry import load_registry
from fastapi.testclient import TestClient
from server.app import app


ROOT = Path(__file__).resolve().parents[1]


def test_novel_objectives_are_frozen_and_deterministic():
    benchmark = load_objective_seeds(ROOT / "data" / "objectives" / "novel_objectives.yaml")
    registry = load_registry()
    first = compose_benchmark_set(registry, benchmark)
    second = compose_benchmark_set(registry, benchmark)
    assert first == second
    assert first["objective_count"] == 6
    assert first["benchmark_hash"] == benchmark["benchmark_hash"]


def test_composition_metric_is_weighted_structural_reuse_not_feasibility():
    benchmark = load_objective_seeds(ROOT / "data" / "objectives" / "novel_objectives.yaml")
    composition = compose_benchmark_set(load_registry(), benchmark)
    heat_pumps = next(
        row for row in composition["objectives"] if row["objective_id"] == "india_heat_pumps_50k"
    )
    assert heat_pumps["composition_coverage"] == 1
    assert heat_pumps["status"] == "COMPOSITION_DIAGNOSTIC_NOT_SOLVER_VERDICT"
    assert "feasibility" in heat_pumps["coverage_not_claimed"]
    assert all(
        "supporting_evidence_classes" in requirement
        for requirement in heat_pumps["requirements"]
    )
    assert heat_pumps["architecture_seed_epistemic_class"] == "ASSUMPTION"


def test_missing_reality_becomes_ranked_structured_research_tasks():
    benchmark = load_objective_seeds(ROOT / "data" / "objectives" / "novel_objectives.yaml")
    composition = compose_benchmark_set(load_registry(), benchmark)
    gaps = rank_decision_gaps(composition)
    assert gaps["task_count"] > 0
    assert [row["rank"] for row in gaps["tasks"]] == list(range(1, gaps["task_count"] + 1))
    assert all(row["epistemic_class"] == "UNKNOWN" for row in gaps["tasks"])
    assert all(row["task_id"].startswith("research-task:") for row in gaps["tasks"])


def test_epistemic_closure_remains_disaggregated():
    benchmark = load_objective_seeds(ROOT / "data" / "objectives" / "novel_objectives.yaml")
    composition = compose_benchmark_set(load_registry(), benchmark)
    for objective in composition["objectives"]:
        closure = objective["epistemic_closure"]
        assert "world_record_class_counts" in closure
        assert "confidence" not in closure
        assert "decision_critical_unknowns" in closure


def test_reality_and_composition_api_expose_status_without_promoting_claims():
    client = TestClient(app)
    reality = client.get("/api/reality/status")
    assert reality.status_code == 200
    payload = reality.json()
    assert payload["gate0"]["status"] == "PASS"
    assert payload["staged_claims"] == 58
    assert payload["promotions"] == 0
    assert payload["conditioning"]["raw_integrity_failures"] == 0
    assert payload["targeted_closure"]["promotions"] == 14
    assert payload["targeted_closure"]["effective_capacity_promotions"] == 0

    claims = client.get("/api/reality/claims", params={"limit": 3})
    assert claims.status_code == 200
    assert len(claims.json()["claims"]) == 3
    assert claims.json()["authority"] == "NON_AUTHORITATIVE_STAGING"

    composition = client.get("/api/composition/novel")
    assert composition.status_code == 200
    result = composition.json()
    assert result["composition"]["objective_count"] == 6
    assert result["decision_gaps"]["task_count"] == 2
