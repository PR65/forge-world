"""Structured UNKNOWN-resolution workflow for FORGE WORLD.

Research capture is intentionally explicit and non-authoritative.  A captured
source becomes an immutable SourceSnapshot, then an Observation, then an
EvidenceRecord only through explicit promotion.  Even after promotion it does not
silently rewrite a checked-in pack.  A reviewer may choose to use a numeric range
as a traceable *scenario overlay* and re-run; persistent world-state promotion
still requires repository review.
"""
from __future__ import annotations

import re
from dataclasses import replace
from datetime import date
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from .engine import ForgeEngine, ObjectiveSpecInput
from .epistemics import EpistemicClass
from .evidence import EvidenceRecord, snapshot_hash
from .pack import KnowledgePack
from .registry import Observation, SourceSnapshot, promote_observation


_SAFE_ID = re.compile(r"[^A-Za-z0-9_.-]+")


def _safe_id(value: str, fallback: str) -> str:
    cleaned = _SAFE_ID.sub("-", value.strip()).strip("-.")
    return cleaned or fallback


def _epistemic(value: Any) -> EpistemicClass:
    try:
        return EpistemicClass(str(value or "UNKNOWN").upper())
    except ValueError as exc:
        raise ValueError(f"unsupported epistemic class '{value}'") from exc


def _numeric_range(capture: Mapping[str, Any]) -> Optional[Tuple[float, float]]:
    raw = capture.get("capacity_range")
    if raw is None:
        return None
    if not isinstance(raw, (list, tuple)) or len(raw) != 2:
        raise ValueError("capacity_range must be [lo, hi]")
    lo, hi = float(raw[0]), float(raw[1])
    if lo < 0 or hi < lo:
        raise ValueError("capacity_range must satisfy 0 <= lo <= hi")
    return lo, hi


def _reconcile(
    pack: KnowledgePack,
    new_record: EvidenceRecord,
    *,
    target_entity_id: str,
) -> Dict[str, Any]:
    relevant = []
    for record in pack.evidence.values():
        if (
            record.subject in {new_record.subject, target_entity_id}
            and record.predicate == new_record.predicate
            and record.geographic_scope.strip().upper()
            == new_record.geographic_scope.strip().upper()
            and record.technical_scope.strip().casefold()
            == new_record.technical_scope.strip().casefold()
        ):
            relevant.append(record)

    new_signature = (new_record.value_text, new_record.value_quantity, new_record.unit_note)
    conflicting = [
        record.claim_id
        for record in relevant
        if (record.value_text, record.value_quantity, record.unit_note) != new_signature
        and not (
            record.epistemic_class == EpistemicClass.UNKNOWN
            or new_record.epistemic_class == EpistemicClass.UNKNOWN
        )
    ]
    consistent = [
        record.claim_id
        for record in relevant
        if (record.value_text, record.value_quantity, record.unit_note) == new_signature
    ]
    if conflicting:
        status = "CONFLICTED_REVIEW_REQUIRED"
    elif consistent:
        status = "CORROBORATES_EXISTING"
    else:
        status = "NOVEL_OBSERVATION_REVIEW_REQUIRED"
    return {
        "status": status,
        "conflicting_claim_ids": sorted(conflicting),
        "consistent_claim_ids": sorted(consistent),
        "compared_claim_count": len(relevant),
        "automatic_overwrite": False,
    }


def process_research_capture(
    pack: KnowledgePack,
    objective: ObjectiveSpecInput,
    task: Mapping[str, Any],
    capture: Mapping[str, Any],
    *,
    reviewer: str,
    approve_for_scenario: bool = False,
) -> Dict[str, Any]:
    """Capture, promote, reconcile, and optionally re-run one research result."""

    target_entity_id = str(task.get("target_entity_id", "")).strip()
    if not target_entity_id or not pack.world.has(target_entity_id):
        raise ValueError(f"research task target '{target_entity_id}' is not in pack world")
    if not reviewer.strip():
        raise ValueError("reviewer is required for explicit promotion")

    source_url = str(capture.get("source_url", "")).strip()
    publisher = str(capture.get("publisher", "")).strip()
    license_value = str(capture.get("license", "UNSPECIFIED")).strip()
    source_type = str(capture.get("source_type", "research_capture")).strip()
    source_id = _safe_id(
        str(capture.get("source_id", f"research-{target_entity_id}")),
        "research-source",
    )
    access_date = str(capture.get("access_date", date.today().isoformat()))
    source_payload = {
        "source_id": source_id,
        "url": source_url,
        "publisher": publisher,
        "license": license_value,
        "source_type": source_type,
        "access_date": access_date,
        "document_date": capture.get("document_date"),
        "page_or_table": capture.get("page_or_table"),
        "quoted_extract": capture.get("quoted_extract"),
    }
    source_snapshot = SourceSnapshot(
        source_id=source_id,
        content_hash=snapshot_hash(source_payload),
        hash_scope="reference_metadata",
        raw_payload_stored=False,
        access_date=access_date,
        license=license_value,
        storage_posture="reference_only",
        url=source_url,
        source_type=source_type,
        metadata={
            "publisher": publisher,
            "page_or_table": str(capture.get("page_or_table", "")),
            "document_date": str(capture.get("document_date", "")),
        },
    )

    epistemic = _epistemic(capture.get("epistemic_class"))
    predicate = str(
        capture.get("predicate", task.get("missing_variable", "observed_value"))
    ).strip()
    value_text = str(capture.get("value_text", "")).strip()
    capacity_range = _numeric_range(capture)
    unit = str(capture.get("unit", "pcs/year")).strip()
    if capacity_range and not value_text:
        value_text = (
            f"Captured range {capacity_range[0]:g}–{capacity_range[1]:g} {unit}; "
            "range endpoints are retained as scenario bounds, not collapsed to a point."
        )
    if not value_text:
        raise ValueError("value_text or capacity_range is required")

    observed_at = str(capture.get("effective_date", capture.get("document_date", "")))
    observation_id = _safe_id(
        str(capture.get("observation_id", f"obs.{pack.pack_id}.{target_entity_id}.{predicate}")),
        f"obs.{pack.pack_id}.{target_entity_id}",
    )
    quantity = None
    if capture.get("value_quantity") is not None:
        raw_quantity = capture["value_quantity"]
        if not isinstance(raw_quantity, (list, tuple)) or len(raw_quantity) != 2:
            raise ValueError("value_quantity must be [value, unit]")
        quantity = (float(raw_quantity[0]), str(raw_quantity[1]))
    observation = Observation(
        observation_id=observation_id,
        source_snapshot_id=source_snapshot.snapshot_id,
        subject=target_entity_id,
        predicate=predicate,
        value_text=value_text,
        value_quantity=quantity,
        epistemic_class=epistemic,
        observed_at=observed_at,
        geographic_scope=str(capture.get("geographic_scope", objective.geography)),
        technical_scope=str(
            capture.get(
                "technical_scope",
                getattr(pack.world.entities[target_entity_id], "spec", ""),
            )
        ),
        caveat=str(capture.get("caveat", "Research capture pending persistent world review.")),
        metadata={
            "publication_date": str(capture.get("document_date", "")),
            "extraction_method": str(capture.get("extraction_method", "human_research_capture")),
            "confidence": dict(capture.get("confidence", {}) or {}),
            "capture_range": list(capacity_range) if capacity_range else None,
        },
    )
    claim_id = _safe_id(
        str(capture.get("claim_id", f"research.{pack.pack_id}.{target_entity_id}.{predicate}")),
        f"research.{pack.pack_id}.{target_entity_id}",
    )
    record, promotion = promote_observation(
        observation,
        source_snapshot,
        claim_id=claim_id,
        reviewer=reviewer,
        promoted_at=date.today().isoformat(),
        rationale=str(
            capture.get(
                "promotion_rationale",
                "Explicit human-reviewed research capture; persistent pack mutation remains pending.",
            )
        ),
    )
    reconciliation = _reconcile(pack, record, target_entity_id=target_entity_id)

    overlay = None
    rerun = None
    overlay_allowed = (
        approve_for_scenario
        and capacity_range is not None
        and predicate in {"qualified_effective_capacity", "capacity_range"}
        and reconciliation["status"] != "CONFLICTED_REVIEW_REQUIRED"
    )
    if overlay_allowed:
        assumptions = dict(objective.analyst_capacity_assumptions)
        assumptions[target_entity_id] = capacity_range
        overlay_objective = replace(objective, analyst_capacity_assumptions=assumptions)
        overlay = {
            "type": "ANALYST_SCENARIO_CAPACITY_OVERRIDE",
            "item_id": target_entity_id,
            "range": list(capacity_range),
            "unit": unit,
            "source_snapshot_id": source_snapshot.snapshot_id,
            "evidence_claim_id": record.claim_id,
            "epistemic_class": "ASSUMPTION",
            "persistent": False,
            "reviewer": reviewer,
        }
        rerun = ForgeEngine(pack).run_scenario(overlay_objective, include_deep=False)

    return {
        "task": dict(task),
        "source_snapshot": source_snapshot.to_json(),
        "observation": observation.to_json(),
        "evidence_record": record.to_json(),
        "promotion": promotion.to_json(),
        "reconciliation": reconciliation,
        "scenario_overlay": overlay,
        "rerun": rerun,
        "persistent_world_update": {
            "status": "PENDING_REPOSITORY_REVIEW",
            "automatic": False,
            "required_checks": [
                "source rights and license",
                "entity and specification match",
                "scope and validity period",
                "conflict reconciliation",
                "capacity decomposition into nameplate, utilization, yield, qualification, and allocation",
                "test and code review before checked-in promotion",
            ],
        },
    }

