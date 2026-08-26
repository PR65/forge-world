"""Focused contracts for the deterministic Run 2 structural accounting."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.forge_india_v1_run2_quality_accounting import (
    DEFAULT_OUTPUT,
    SCHEMA_VERSION,
    build_quality_accounting,
)


def test_quality_artifact_covers_current_catalog_and_is_not_comparable() -> None:
    payload = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))

    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["record_counts"] == {
        "record_count": 14662,
        "direct_record_count": 12253,
        "reference_record_count": 2409,
        "direct_share": 0.835698,
        "reference_share": 0.164302,
    }
    assert set(payload["distributions"]["direct"]["domain_counts"]) == {
        *(f"{number:02d}" for number in range(1, 13)),
        "shared",
    }
    assert payload["integrity"]["ok"] is True
    assert payload["integrity"]["all_references_resolve"] is True
    india_build = payload["indiabuild_accounting"]
    assert india_build["row_level_export_available"] is False
    assert india_build["parity_status"] == "NOT_COMPARABLE"
    assert india_build["current_official_top_level_observation"]["mapped_capability_count"] == 7049


def test_quality_metrics_capture_name_family_graph_and_ladder_contracts() -> None:
    payload = build_quality_accounting()

    assert payload["canonical_names"]["direct"]["exact_duplicate_group_count"] == 0
    assert payload["families"]["direct"]["family_count"] == 1316
    assert payload["families"]["direct"]["multi_variant_family_count"] == 1235
    assert payload["families"]["direct"]["variant_consolidation_ratio"] > 1

    graph = payload["graph"]["direct"]
    assert graph["dead_end_count"] == 0
    assert graph["navigation_coverage_count"] == 12253
    assert graph["missing_unique_edge_count"] == 0
    assert graph["self_reference_count"] == 0

    ladder = payload["ladders"]["direct"]
    assert ladder["complete_count"] == 12253
    assert ladder["ordered_count"] == 12253
    assert ladder["allowed_action_violation_count"] == 0
    assert ladder["distinct_action_sequence_count"] > 1
    assert ladder["semantic_signature_count"] > 1
    assert ladder["low_semantic_diversity_defect"] is False
    assert ladder["action_diversity_defect_count"] == 0

    assert payload["profile_fixes"]["targeted_row_count"] == 180
    assert payload["profile_fixes"]["targeted_mismatch_count"] == 0
    assert payload["epistemic_corrections"]["source_direct_row_count"] == 12253
    assert payload["epistemic_corrections"]["derived_correction_count"] == 231


def test_quality_accounting_is_reproducible() -> None:
    first = build_quality_accounting()
    second = build_quality_accounting()
    assert first == second
