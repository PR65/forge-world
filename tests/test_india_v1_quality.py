"""Focused contracts for the deterministic India V1 quality layer."""

from __future__ import annotations

import sys
from pathlib import Path

# The repository root is not guaranteed to be on ``sys.path`` when pytest is
# launched through the desktop environment rather than ``python -m pytest``.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data.india_v1 import domains_05_08, domains_09_12
from forge.india_v1.quality import (
    ALLOWED_ACTIONS,
    build_making_ladder,
    correct_epistemic_status,
    display_name,
    family_key,
    variant_label,
)


def _rows(pack: object) -> list[dict[str, object]]:
    return [
        row
        for records in getattr(pack, "DOMAIN_RECORDS").values()
        for row in records
    ]


def test_identity_helpers_cover_all_three_record_id_schemes() -> None:
    assert family_key("d01:product:machine-tool:prototype") == "d01:product:machine-tool"
    assert family_key("product:05:3-axis-cnc-vmc:compact-series") == "product:05:3-axis-cnc-vmc"
    assert family_key("india-v1:09:tractor:battery-electric:agriculture") == "india-v1:09:tractor:battery-electric"

    assert variant_label("d01:product:machine-tool:prototype") == "prototype"
    assert variant_label("product:05:3-axis-cnc-vmc:compact-series") == "compact · series"
    assert variant_label("india-v1:09:tractor:battery-electric:agriculture") == "battery electric · agriculture"

    product_name = display_name(
        {
            "id": "product:05:pump:compact-automated",
            "canonical_name": "Pump (compact, automated)",
            "variant": {"labels": ["compact configuration", "automated control"]},
        }
    )
    assert "(" not in product_name
    assert "compact configuration" in product_name

    atlas_name = display_name(
        {
            "id": "india-v1:09:tractor:battery-electric:agriculture",
            "canonical_name": "Battery Electric Tractor — Agriculture",
            "variant_axes": {"architecture": "battery-electric", "operating_context": "agriculture"},
        }
    )
    assert atlas_name.startswith("Tractor —")
    assert "Battery Electric Tractor — Agriculture" not in atlas_name


def test_display_name_is_idempotent_for_already_variant_qualified_rows() -> None:
    product = {
        "id": "product:08:cold-storage-system:chilled-cold-room-closed-loop",
        "canonical_name": "Industrial cold-storage system — chilled-temperature zone · cold-room configuration · closed-loop thermal monitoring",
    }
    assert display_name(product) == product["canonical_name"]

    infrastructure = {
        "id": "india-v1:10:industrial-compressor:centrifugal:construction-site",
        "canonical_name": "Infrastructure Industrial compressor — centrifugal · construction site",
    }
    rendered = display_name(infrastructure)
    assert rendered == infrastructure["canonical_name"]
    assert "Infrastructure Infrastructure" not in rendered


def test_targeted_profile_cleanup_preserves_breadth_and_removes_collisions() -> None:
    rows_05_08 = _rows(domains_05_08)
    target_profiles = {
        "patient-monitor": "clinical",
        "infusion-pump": "clinical",
        "dialysis-machine": "clinical",
        "lab-incubator": "lab",
        "cold-storage-system": "cold_chain",
    }
    for archetype_id, profile in target_profiles.items():
        target_rows = [row for row in rows_05_08 if row["archetype_id"] == archetype_id]
        assert len(target_rows) == 36
        assert {row["profile"] for row in target_rows} == {profile}
        assert all("(" not in str(row["canonical_name"]) for row in target_rows)

    rows_09_12 = [
        row
        for domain_id, records in domains_09_12.DOMAIN_RECORDS.items()
        if domain_id.startswith(("10_", "12_"))
        for row in records
    ]
    assert len(rows_09_12) == 2_160
    assert len({row["canonical_name"] for row in rows_09_12}) == len(rows_09_12)
    assert any(str(row["canonical_name"]).startswith("Infrastructure ") for row in rows_09_12)
    assert any(str(row["canonical_name"]).startswith("Foundational ") for row in rows_09_12)


def test_status_correction_is_non_mutating_and_retains_prior_basis() -> None:
    source = {
        "status": "MISSING / NO EVIDENCED DOMESTIC CAPABILITY",
        "india_status": "MISSING / NO EVIDENCED DOMESTIC CAPABILITY",
        "status_basis": "Taxonomy-only prior.",
        "status_epistemic_class": "ASSUMPTION",
        "epistemic_class": "ASSUMPTION",
    }
    corrected = correct_epistemic_status(source)

    assert source["status"] == "MISSING / NO EVIDENCED DOMESTIC CAPABILITY"
    assert corrected["status"] == "UNKNOWN"
    assert corrected["india_status"] == "UNKNOWN"
    assert corrected["status_epistemic_class"] == "UNKNOWN"
    metadata = corrected["status_basis_metadata"]
    assert metadata["prior_status"] == source["status"]
    assert metadata["prior_status_normalized"] == "MISSING"
    assert "corrected_status=UNKNOWN" in corrected["status_basis"]


def test_making_ladder_orders_stages_and_surfaces_dependency_risk() -> None:
    unresolved = {
        "id": "product:05:pump:variant",
        "status": "UNKNOWN",
        "status_epistemic_class": "UNKNOWN",
        "dependency_ids": ["dep:imported", "dep:missing"],
    }
    by_id = {
        "dep:imported": {"status": "IMPORT_DEPENDENT"},
        "dep:missing": {"status": "UNKNOWN"},
    }
    ladder = build_making_ladder(unresolved, by_id)

    assert [stage["stage"] for stage in ladder] == [
        "local_first",
        "initial_import_bridge",
        "integration_and_test",
        "next_localization",
        "harder_later_capability",
        "optional_redesign",
    ]
    assert [stage["sequence"] for stage in ladder] == list(range(1, 7))
    assert ladder[0]["action"] == "DEVELOP"
    assert ladder[1]["required"] is True
    assert {"IMPORT_DEPENDENT", "UNKNOWN"} <= set(ladder[1]["dependency_risk"])
    assert all(
        set(stage["allowed_actions"]) <= set(ALLOWED_ACTIONS)
        for stage in ladder
    )
    assert ladder[-1]["action"] == "REDESIGN"

    evidence_ready = {
        "id": "d01:product:machine-tool:prototype",
        "status": "AVAILABLE",
        "status_epistemic_class": "MEASURED",
    }
    ready_ladder = build_making_ladder(evidence_ready, {})
    assert ready_ladder[0]["allowed_actions"] == ["DEVELOP", "BUILD"]
    assert ready_ladder[1]["required"] is False
