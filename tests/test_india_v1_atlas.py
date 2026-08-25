"""Deterministic structural tests for the India V1 domains 01-04 atlas."""
from __future__ import annotations

import hashlib
import json

from forge.india_v1 import (
    LADDER_ACTIONS,
    check_integrity,
    domain_counts,
    generate_atlas,
    generate_domain_records,
)


def _digest(atlas):
    payload = json.dumps(atlas.to_dict(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_domains_have_broad_deterministic_coverage_and_shared_foundations():
    atlas = generate_atlas()
    counts = domain_counts(atlas)
    assert set(counts) == {
        "Aerospace & Space",
        "Defense & Strategic Manufacturing",
        "Energy & Nuclear",
        "Electronics, Semiconductors & Computing",
    }
    assert all(800 <= count <= 1100 for count in counts.values())
    assert sum(counts.values()) + len(atlas.records_for_domain("shared_foundations")) == len(atlas)
    assert len(atlas.records_for_domain("shared_foundations")) < min(counts.values())
    assert _digest(atlas) == _digest(generate_atlas())


def test_integrity_contract_and_product_ladders():
    atlas = generate_atlas()
    report = check_integrity(atlas, enforce_domain_counts=True)
    assert report.ok, report.errors
    domain_products = [
        record for record in atlas if record.domain != "shared_foundations" and record.kind == "PRODUCT"
    ]
    assert domain_products
    assert min(len(record.dependencies_flat) for record in domain_products) >= 5
    assert min(len(record.making_ladder) for record in domain_products) >= 5
    assert {step.action for record in domain_products for step in record.making_ladder} == set(LADDER_ACTIONS)


def test_domain_subset_keeps_shared_references_resolvable_and_deduplicated():
    records = generate_domain_records("04")
    assert len(records) == 928
    ids = {record["id"] for record in records}
    full = generate_atlas()
    full_ids = {record.id for record in full}
    assert not any(ref.startswith("shared:") and ref not in full_ids for record in records for refs in record["dependencies"].values() for ref in refs)
    assert len(ids) == len(records)
    assert check_integrity(full, enforce_domain_counts=True).ok
