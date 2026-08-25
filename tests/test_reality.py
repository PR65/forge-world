from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from forge.epistemics import EpistemicClass
from forge.reality import (
    ClaimCandidate,
    ConflictState,
    EntityResolution,
    GeographicResolution,
    PromotionState,
    QuantityCandidate,
    RawArtifactSnapshot,
    RelationNormalization,
    RelationState,
    RepairSeverity,
    ResolutionState,
    SourceLayer,
    SupplierState,
    content_hash,
    inventory_corpus,
    manifest_payload,
    repair_csv_bytes,
)
from forge.registry import SourceSnapshot
from forge.registry import promote_observation


def artifact() -> RawArtifactSnapshot:
    return RawArtifactSnapshot(
        corpus_id="pilot",
        logical_path="manus-11/claims.csv",
        content_hash=content_hash(b"payload"),
        byte_length=7,
        source_layer=SourceLayer.EXTRACTED,
    )


def claim(**overrides) -> ClaimCandidate:
    values = {
        "artifact_id": artifact().artifact_id,
        "locator": "row:2",
        "subject_text": "precision grinding",
        "predicate_text": "requires equipment",
        "value_text": "Requires a grinding machine",
    }
    values.update(overrides)
    return ClaimCandidate(**values)


def test_staging_ids_are_deterministic_and_path_safe():
    assert artifact().artifact_id == artifact().artifact_id
    assert claim().claim_id == claim().claim_id
    with pytest.raises(ValueError, match="corpus-relative"):
        RawArtifactSnapshot("pilot", "../escape.csv", "0" * 64, 0)


def test_staging_records_are_immutable_and_unknown_stays_unknown():
    candidate = claim(unknown_dimensions=("yield", "qualification", "yield"))
    assert candidate.candidate_epistemic_class == EpistemicClass.UNKNOWN
    assert candidate.unknown_dimensions == ("qualification", "yield")
    with pytest.raises(FrozenInstanceError):
        candidate.value_text = "invented"  # type: ignore[misc]


def test_conflict_state_and_epistemic_class_cannot_diverge():
    with pytest.raises(ValueError, match="must use CONFLICTED"):
        claim(
            conflict_state=ConflictState.CONFIRMED,
            conflicting_claim_ids=("claim:other",),
        )
    conflicted = claim(
        candidate_epistemic_class=EpistemicClass.CONFLICTED,
        conflict_state=ConflictState.CONFIRMED,
        conflicting_claim_ids=("claim:other",),
    )
    assert "conflict_unresolved" in conflicted.promotion_blockers()


def test_fuzzy_matching_can_never_resolve_canonical_identity():
    with pytest.raises(ValueError, match="fuzzy"):
        EntityResolution(
            state=ResolutionState.RESOLVED_EXISTING,
            canonical_ids=("cap:metrology",),
            method="fuzzy_name_match",
        )


def test_relation_normalization_rejects_ontology_invention():
    with pytest.raises(ValueError, match="outside the canonical ontology"):
        RelationNormalization("makes", RelationState.NORMALIZED, "probably_makes")


def test_geography_resolution_is_explicit_and_never_fuzzy():
    with pytest.raises(ValueError, match="fuzzy"):
        GeographicResolution("Chakan", "geo:chakan", True, "fuzzy_match")
    candidate = claim(
        geography="Chakan industrial area",
        entity_resolution=EntityResolution(
            ResolutionState.RESOLVED_EXISTING, ("cap:test",), method="manual_exact"
        ),
        relation=RelationNormalization("requires", RelationState.NORMALIZED, "requires_input"),
        conflict_state=ConflictState.NONE_FOUND,
        promotion_state=PromotionState.READY_FOR_OBSERVATION,
    )
    assert "geography_unresolved" in candidate.promotion_blockers()


def test_claim_cannot_cross_boundary_without_every_gate():
    candidate = claim()
    assert set(candidate.promotion_blockers()) >= {
        "promotion_state_not_ready",
        "entity_identity_unresolved",
        "relation_not_normalized",
        "conflict_unresolved",
    }
    source = SourceSnapshot(source_id="corpus", content_hash="a" * 64, license="UNSPECIFIED")
    with pytest.raises(ValueError, match="cannot become an observation"):
        candidate.to_observation(source)


def test_explicit_reviewed_unknown_can_become_observation_without_becoming_supply():
    candidate = claim(
        entity_resolution=EntityResolution(
            ResolutionState.RESOLVED_EXISTING, ("cap:precision-grinding",), method="manual_exact"
        ),
        relation=RelationNormalization(
            "requires equipment", RelationState.NORMALIZED, "requires_equipment"
        ),
        conflict_state=ConflictState.NONE_FOUND,
        promotion_state=PromotionState.READY_FOR_OBSERVATION,
    )
    source = SourceSnapshot(
        source_id="corpus", content_hash="a" * 64, license="UNSPECIFIED", metadata={"publisher": "user corpus"}
    )
    observation = candidate.to_observation(source)
    assert observation.epistemic_class == EpistemicClass.UNKNOWN
    assert observation.predicate == "requires_equipment"


def test_reported_claim_license_propagates_across_staging_boundary():
    candidate = claim(
        candidate_epistemic_class=EpistemicClass.REPORTED,
        source_license="public-domain",
        entity_resolution=EntityResolution(
            ResolutionState.RESOLVED_EXISTING, ("cap:precision-grinding",), method="manual_exact"
        ),
        relation=RelationNormalization(
            "requires equipment", RelationState.NORMALIZED, "requires_equipment"
        ),
        conflict_state=ConflictState.NONE_FOUND,
        promotion_state=PromotionState.READY_FOR_OBSERVATION,
    )
    source = SourceSnapshot(
        source_id="src:official",
        content_hash="b" * 64,
        license="public-domain",
        url="https://example.test/source",
    )
    observation = candidate.to_observation(source)
    assert observation.source_snapshot_id == source.snapshot_id
    with pytest.raises(ValueError, match="license"):
        candidate.to_observation(
            SourceSnapshot(source_id="src:other", content_hash="c" * 64, license="reference-only")
        )


def test_canonical_integration_proof_preserves_staged_lineage():
    candidate = claim(
        candidate_epistemic_class=EpistemicClass.REPORTED,
        source_license="public-domain",
        publication_date="2026-08-01",
        effective_date="2026-07-01",
        retrieval_date="2026-08-25",
        entity_resolution=EntityResolution(
            ResolutionState.RESOLVED_EXISTING, ("cap:precision-grinding",), method="manual_exact"
        ),
        relation=RelationNormalization(
            "requires equipment", RelationState.NORMALIZED, "requires_equipment"
        ),
        conflict_state=ConflictState.NONE_FOUND,
        promotion_state=PromotionState.READY_FOR_OBSERVATION,
    )
    source = SourceSnapshot(
        source_id="src:official",
        content_hash="d" * 64,
        hash_scope="content",
        access_date="2026-08-25",
        license="public-domain",
        url="https://example.test/official",
        metadata={"publisher": "Example Standards Authority"},
    )
    observation = candidate.to_observation(source)
    record, promotion = promote_observation(
        observation,
        source,
        claim_id=candidate.claim_id,
        reviewer="gate0-test",
        promoted_at="2026-08-25",
        rationale="bounded canonical integration proof",
    )
    assert record.claim_id == candidate.claim_id
    assert record.source_ids == (source.source_id,)
    assert record.license == candidate.source_license
    assert record.effective_date == candidate.effective_date
    assert promotion.observation_id == candidate.claim_id
    assert promotion.source_snapshot_id == source.snapshot_id


@pytest.mark.parametrize(
    ("predicate", "relation", "blocker"),
    [
        ("reported trade flow", "supplied_by", "trade_is_not_capability_or_supply"),
        ("factory exists", "has_capacity", "facility_existence_is_not_capacity"),
        ("project announcement", "has_capacity", "announcement_is_not_operating_capacity"),
        ("mineral reserves", "requires_input", "mineral_reserve_is_not_usable_supply"),
        ("nameplate capacity", "has_capacity", "nameplate_is_not_effective_capacity"),
    ],
)
def test_weak_proxies_are_blocked_from_strong_semantics(predicate, relation, blocker):
    candidate = claim(
        predicate_text=predicate,
        entity_resolution=EntityResolution(
            ResolutionState.RESOLVED_EXISTING, ("cap:test",), method="manual_exact"
        ),
        relation=RelationNormalization(predicate, RelationState.NORMALIZED, relation),
        conflict_state=ConflictState.NONE_FOUND,
        promotion_state=PromotionState.READY_FOR_OBSERVATION,
    )
    assert blocker in candidate.promotion_blockers()


def test_nameplate_requires_all_effective_capacity_dimensions():
    candidate = claim(
        predicate_text="nameplate capacity",
        entity_resolution=EntityResolution(
            ResolutionState.RESOLVED_EXISTING, ("cap:test",), method="manual_exact"
        ),
        relation=RelationNormalization("nameplate", RelationState.NORMALIZED, "has_capacity"),
        conflict_state=ConflictState.NONE_FOUND,
        promotion_state=PromotionState.READY_FOR_OBSERVATION,
        metadata={
            "availability": 0.8,
            "utilization": 0.7,
            "yield_fraction": 0.9,
            "qualification_fraction": 0.6,
        },
    )
    assert "nameplate_is_not_effective_capacity" not in candidate.promotion_blockers()


def test_supplier_qualification_is_not_available_capacity():
    qualified = claim(supplier_state=SupplierState.QUALIFIED_SUPPLIER)
    assert "available_capacity_dimensions_unresolved" not in qualified.promotion_blockers()
    available = claim(supplier_state=SupplierState.AVAILABLE_CAPACITY)
    assert set(available.promotion_blockers()) >= {
        "available_capacity_requires_quantity",
        "available_capacity_dimensions_unresolved",
    }


def test_csv_repair_is_reproducible_and_ambiguity_is_visible():
    payload = b"a,b\r\n1\x00\r\n2,3,4\r\n"
    first = repair_csv_bytes(payload)
    second = repair_csv_bytes(payload)
    assert first.repaired_bytes == second.repaired_bytes
    assert first.actions == second.actions
    assert any(action.severity == RepairSeverity.AMBIGUOUS for action in first.actions)
    assert {action.code for action in first.actions} >= {
        "REMOVE_NUL",
        "PAD_SHORT_ROW",
        "JOIN_OVERFLOW_FIELDS",
    }


def test_inventory_hashes_without_mutating_source(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    raw = source / "claims.csv"
    raw.write_bytes(b"a,b\n1,2\n")
    before = raw.read_bytes()
    rows = inventory_corpus(
        source, corpus_id="test", source_layer=SourceLayer.RAW
    )
    assert raw.read_bytes() == before
    assert rows[0].content_hash == content_hash(before)
    assert manifest_payload(rows) == manifest_payload(rows)


def test_quantity_ranges_are_not_collapsed_to_false_precision():
    quantity = QuantityCandidate(
        original_text="10-20 t/y", low=10, high=20, original_unit="t/y"
    )
    candidate = claim(quantity=quantity)
    assert candidate.quantity.low == 10
    assert candidate.quantity.high == 20
