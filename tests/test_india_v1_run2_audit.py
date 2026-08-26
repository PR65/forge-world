"""Contract tests for the frozen Run 2 search audit artifact."""
from __future__ import annotations

from pathlib import Path

from scripts.forge_india_v1_run2_audit import (
    DEFAULT_BATTERY,
    DEFAULT_OUTPUT,
    FAILURE_CATEGORIES,
    _load_battery,
    compare_metrics,
    run_audit,
)


def test_frozen_battery_has_founder_and_all_domain_coverage() -> None:
    battery, digest = _load_battery(DEFAULT_BATTERY)
    queries = [*(battery["founder_20"]), *(battery["unseen_queries"])]

    assert len(battery["founder_20"]) == 20
    assert len(battery["unseen_queries"]) == 72
    assert len(queries) == battery["coverage"]["total_queries"] == 92
    assert {row["domain"] for row in queries} == set(battery["coverage"]["domain_codes"])
    assert len({row["id"] for row in queries}) == len(queries)
    assert len(digest) == 64


def test_final_audit_is_deterministic_and_preserves_frozen_baseline() -> None:
    first_metrics, first_findings = run_audit(DEFAULT_BATTERY, phase="final")
    second_metrics, second_findings = run_audit(DEFAULT_BATTERY, phase="final")

    assert first_metrics == second_metrics
    assert first_findings == second_findings
    assert first_metrics["baseline_only"] is False
    assert first_metrics["fixes_applied"] is True
    assert first_metrics["query_set_frozen_before_baseline"] is True
    assert first_metrics["query_count"] == 92
    assert set(first_metrics["failure_counts"]) == set(FAILURE_CATEGORIES)
    baseline = __import__("json").loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    assert baseline["baseline_only"] is True
    assert baseline["fixes_applied"] is False
    assert baseline["battery_digest_sha256"] == first_metrics["battery_digest_sha256"]


def test_audit_records_requested_failure_taxonomy_and_family_signals() -> None:
    metrics, findings = run_audit(DEFAULT_BATTERY, phase="final")
    by_id = {row["id"]: row for row in findings["queries"]}

    # The final run must retain the complete taxonomy while exposing match
    # provenance and suppressing duplicate family pages.
    assert all("duplicate" not in row["failure_categories"] for row in by_id.values())
    assert by_id["f01"]["results"]
    assert all(result["family_key"] for result in by_id["f01"]["results"])
    assert all(result["match_type"] for result in by_id["f01"]["results"])
    assert any(result["match_type"] == "related" for result in by_id["f16"]["results"])
    assert metrics["failure_counts"]["broken_dependency"] == 0
    assert metrics["failure_counts"]["dead_end"] == 0


def test_findings_are_compact_enough_for_machine_review() -> None:
    _metrics, findings = run_audit(DEFAULT_BATTERY, phase="final")
    for row in findings["queries"]:
        assert set(row) >= {
            "id",
            "query",
            "results",
            "selected",
            "failure_categories",
            "failure_reasons",
        }
        assert len(row["results"]) <= row["top_k"]
        if row["selected"]:
            assert len(row["selected"]["gap_text"]) <= 500


def test_baseline_final_comparison_is_compact_and_digest_bound() -> None:
    import json

    baseline = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    final, _findings = run_audit(DEFAULT_BATTERY, phase="final")
    comparison = compare_metrics(baseline, final)
    assert comparison["query_count"] == 92
    assert comparison["battery_digest_sha256"] == baseline["battery_digest_sha256"]
    assert set(comparison["delta"]["failure_counts"]) == set(FAILURE_CATEGORIES)


def test_phase_c_retrieval_target_and_founder_domain_floor() -> None:
    metrics, _findings = run_audit(DEFAULT_BATTERY, phase="final")
    assert metrics["queries_with_relevant_result"] >= 85
    assert metrics["by_class"]["founder"]["search_miss_count"] <= 1
    assert metrics["by_class"]["founder"]["top1_expected_domain_count"] >= 19
    assert metrics["failure_counts"]["duplicate"] == 0
