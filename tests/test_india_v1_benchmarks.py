"""Integrity tests for the deterministic India V1 benchmark runner."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

# ``scripts`` is intentionally a path-run directory rather than an installed
# package; import the benchmark runner the same way its CLI is executed.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from forge_india_v1_benchmark import (
    CHECK_NAMES,
    _load_config,
    run_benchmark,
)
from forge.india_v1.catalog import get_catalog


def _digest(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def test_benchmark_has_required_named_queries_and_random_unseen_products():
    config = _load_config()
    result, accounting = run_benchmark(config=config)
    required = list(config["required_named_queries"])
    assert [item["query"] for item in result["named_queries"]] == required
    assert result["atlas"]["source_api"] == "forge.india_v1.catalog.get_catalog"
    assert result["atlas"]["record_count"] == len(get_catalog().records)
    assert set(result["atlas"]["domain_counts_by_code"]) == {f"{index:02d}" for index in range(1, 13)}
    assert result["summary"]["tests_failed"] == 0
    assert all(item["passed"] for item in result["named_queries"] + result["random_product_samples"])
    assert len(result["random_product_samples"]) >= 12
    random_ids = [item["selection"]["record_id"] for item in result["random_product_samples"]]
    assert len(random_ids) == len(set(random_ids))
    assert all(item["selection"]["unseen_from_named_result_ids"] for item in result["random_product_samples"])
    assert all(item.get("record", {}).get("kind") == "PRODUCT" for item in result["random_product_samples"])
    assert accounting["count_level"]["indiabuild_public_observed_mapped_count"] == 7047
    assert accounting["count_level"]["indiabuild_public_catalogue_claim"] == 10000


def test_benchmark_check_contract_and_accounting_classes_are_machine_readable():
    result, accounting = run_benchmark(config=_load_config())
    assert result["schema_version"] == "india_v1.benchmark_results.v1"
    assert result["summary"]["tests_total"] == 15 + 12
    assert set(result["summary"]["check_counts"]) == set(CHECK_NAMES)
    assert set(accounting["reconciliation_classes"]) == {
        "MATCHED",
        "FORGE_DEEPER_EQUIVALENT",
        "UNRESOLVED",
        "MISSING",
        "INACCESSIBLE_OR_UNVERIFIABLE",
    }
    assert accounting["public_bulk_list_available"] is False
    assert accounting["sample_size"] == len(accounting["sampled_name_reconciliation"])
    assert sum(accounting["sample_class_counts"].values()) == accounting["sample_size"]
    for item in result["named_queries"] + result["random_product_samples"]:
        assert set(item["checks"]) == set(CHECK_NAMES)
        assert len(item["results"]) <= result["top_k"]
        record = item.get("record")
        assert record is not None
        assert record["dependency_count_displayed"] == min(record["dependency_count_raw"], 30)
        assert record["dependency_view"] == "V1_BROAD_DISPLAYED_SLICE"


def test_benchmark_run_is_byte_deterministic():
    first, first_accounting = run_benchmark(config=_load_config())
    second, second_accounting = run_benchmark(config=_load_config())
    assert _digest(first) == _digest(second)
    assert _digest(first_accounting) == _digest(second_accounting)
