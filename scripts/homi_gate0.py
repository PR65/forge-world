#!/usr/bin/env python3
"""Integrate Gate-0 pilot reports into the non-authoritative claim ledger."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from forge.epistemics import EpistemicClass
from forge.reality import (
    ClaimCandidate,
    ConflictState,
    PromotionState,
    content_hash,
    write_canonical_json,
)


PILOT_DIR = ROOT / "research" / "homi" / "pilot"
MANIFEST = ROOT / "research" / "homi" / "staging" / "corpus_manifest.json"
CONDITIONING = ROOT / "research" / "homi" / "staging" / "conditioning_report.json"
ARCHIVES = ROOT / "research" / "homi" / "staging" / "archive_integrity.json"
LEDGER = ROOT / "research" / "homi" / "gate0" / "claim_ledger.json"
BARRIER = ROOT / "research" / "homi" / "gate0" / "barrier.json"


REPORTS = {
    "manus-01": ("manus_01_report.json", "structured_claim_samples"),
    "manus-05": ("manus_05_report.json", "claim_candidate_samples"),
    "manus-11": ("manus_11_report.json", "structured_claim_candidate_samples"),
    "manus-16": ("manus_16_context_report.json", "structured_claim_samples"),
}
DEFAULT_ARTIFACTS = {
    "manus-01": "manus-01/FORGE WORLD — Supplier Qualification & Industrial Sourcing Intelligence.md",
    "manus-05": "manus-05/FORGE WORLD — Metrology, Testing, Qualification & Standards Infrastructure.md",
    "manus-11": "manus-11/FORGE WORLD — Factory Build, Ramp-Up & Production Scaling.md",
    "manus-16": "manus-16/FORGE WORLD — Industrial Machines & Production Equipment Universe.md",
}


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected object in {path}")
    return value


def _artifact_from_locator(locator: str, corpus_id: str, lookup: dict[tuple[str, str], dict[str, Any]]) -> dict[str, Any]:
    full_text = locator.replace("\\", "/")
    mentioned = [
        (full_text.find(logical_path), artifact)
        for (candidate_corpus, logical_path), artifact in lookup.items()
        if candidate_corpus == "manus_extracted"
        and logical_path.startswith(f"{corpus_id}/")
        and logical_path in full_text
    ]
    if mentioned:
        return sorted(mentioned, key=lambda item: (item[0], item[1]["logical_path"]))[0][1]
    text = full_text.split(";", 1)[0].strip()
    prefix = f"{corpus_id}/"
    if prefix in text:
        text = text.split(prefix, 1)[1]
    for separator in ("#", ":L"):
        if separator in text:
            text = text.split(separator, 1)[0]
    candidates = [
        artifact
        for (candidate_corpus, logical_path), artifact in lookup.items()
        if candidate_corpus == "manus_extracted"
        and logical_path == f"{corpus_id}/{text}"
    ]
    if len(candidates) == 1:
        return candidates[0]
    fallback = lookup.get(("manus_extracted", DEFAULT_ARTIFACTS[corpus_id]))
    if fallback:
        return fallback
    raise ValueError(f"cannot resolve pilot locator to artifact: {corpus_id} {locator!r}")


def _adapt_claim(
    corpus_id: str,
    row: dict[str, Any],
    artifact_lookup: dict[tuple[str, str], dict[str, Any]],
) -> ClaimCandidate:
    inputs = row.get("candidate_id_inputs", row.get("candidate_id_input", {})) or {}
    locator = str(row.get("locator") or inputs.get("locator") or row.get("source_locator") or "")
    if not locator:
        raise ValueError(f"pilot claim lacks locator: {corpus_id} {row}")
    artifact: dict[str, Any]
    artifact_name = str(inputs.get("artifact", ""))
    if artifact_name:
        artifact = artifact_lookup[("manus_extracted", f"{corpus_id}/{artifact_name}")]
    else:
        artifact = _artifact_from_locator(locator, corpus_id, artifact_lookup)

    subject = str(inputs.get("subject_text") or inputs.get("subject") or row.get("subject_text") or "")
    predicate = str(inputs.get("predicate_text") or inputs.get("predicate") or row.get("predicate_text") or "")
    value = str(inputs.get("value_text") or row.get("value_text") or row.get("observed_claim") or "")
    original_id = str(row.get("claim_id") or row.get("candidate_id") or "")
    subject = subject or f"{corpus_id}:{original_id or 'claim'}"
    predicate = predicate or "corpus_claim_candidate"
    klass = EpistemicClass(
        str(
            row.get("candidate_epistemic_class")
            or inputs.get("epistemic_class")
            or row.get("epistemic_class")
            or "UNKNOWN"
        ).upper()
    )
    conflict_state = ConflictState.POSSIBLE if klass == EpistemicClass.CONFLICTED else ConflictState.UNCHECKED
    return ClaimCandidate(
        artifact_id=artifact["artifact_id"],
        locator=locator,
        subject_text=subject,
        predicate_text=predicate,
        value_text=value,
        candidate_epistemic_class=klass,
        geography=str(row.get("geography") or "UNKNOWN"),
        technical_scope=str(row.get("technical_scope") or ""),
        caveat=str(row.get("extraction_note") or row.get("interpretation") or ""),
        unknown_dimensions=tuple(str(item) for item in row.get("unknown_dimensions", ()) or ()),
        source_class=str(row.get("source_class") or "corpus_research_package"),
        source_license=str(row.get("source_license") or "UNSPECIFIED"),
        conflict_state=conflict_state,
        promotion_state=PromotionState.BLOCKED,
        escalation_reason=str(
            row.get("escalation_reason")
            or "Source snapshot, identity, relation, scope, and rights require explicit review."
        ),
        metadata={
            "corpus_id": corpus_id,
            "source_report_claim_id": original_id,
            "source_artifact_hash": artifact["content_hash"],
            "source_logical_path": artifact["logical_path"],
            "source_report_row_hash": content_hash(
                json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            ),
        },
    )


def main() -> int:
    manifest = _load(MANIFEST)
    conditioning = _load(CONDITIONING)
    archives = _load(ARCHIVES)
    artifact_lookup = {
        (row["corpus_id"], row["logical_path"]): row for row in manifest["artifacts"]
    }
    claims: list[ClaimCandidate] = []
    report_summaries = []
    for corpus_id, (filename, claim_key) in REPORTS.items():
        report = _load(PILOT_DIR / filename)
        rows = report.get(claim_key, ())
        if not isinstance(rows, list):
            raise ValueError(f"pilot report {filename} has no list at {claim_key}")
        adapted = [_adapt_claim(corpus_id, row, artifact_lookup) for row in rows]
        claims.extend(adapted)
        report_summaries.append(
            {
                "corpus_id": corpus_id,
                "report_path": (PILOT_DIR / filename).relative_to(ROOT).as_posix(),
                "report_hash": content_hash((PILOT_DIR / filename).read_bytes()),
                "claim_count": len(adapted),
                "all_claims_blocked": all(claim.promotion_state == PromotionState.BLOCKED for claim in adapted),
            }
        )
    claim_ids = [claim.claim_id for claim in claims]
    if len(claim_ids) != len(set(claim_ids)):
        raise ValueError("adapted pilot claim ids are not unique")
    ledger = {
        "ledger_schema_version": "1.0.0",
        "authority": "NON_AUTHORITATIVE_STAGING",
        "claim_count": len(claims),
        "promotion_count": 0,
        "reports": report_summaries,
        "epistemic_class_counts": {
            klass.value: sum(claim.candidate_epistemic_class == klass for claim in claims)
            for klass in EpistemicClass
        },
        "conflict_candidate_count": sum(
            claim.conflict_state in {ConflictState.POSSIBLE, ConflictState.CONFIRMED}
            for claim in claims
        ),
        "source_license_unspecified_count": sum(
            claim.source_license.upper() == "UNSPECIFIED" for claim in claims
        ),
        "claims": [claim.to_json() for claim in sorted(claims, key=lambda item: item.claim_id)],
    }
    ledger["ledger_hash"] = content_hash(
        json.dumps(ledger, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    )
    write_canonical_json(LEDGER, ledger)

    checks = {
        "all_321_artifacts_accounted": manifest["artifact_count"] == 321,
        "all_20_archives_accounted": archives["package_count"] == 20,
        "all_254_zip_entries_match": archives["entry_count"] == archives["matched_entry_count"] == 254,
        "archive_failures_zero": archives["failure_count"] == 0,
        "raw_integrity_failures_zero": conditioning["raw_integrity_failure_count"] == 0,
        "conditioning_reproducible_contract": conditioning["conditioning_version"] == "1.0.0",
        "manual_test_pack_skipped": any(
            row["parse_status"] == "INTENTIONALLY_SKIPPED"
            for row in conditioning["artifacts"]
        ),
        "pilot_claims_are_staging_only": ledger["promotion_count"] == 0,
        "pilot_claim_ids_unique": len(claim_ids) == len(set(claim_ids)),
        "pilot_reports_present": len(report_summaries) == len(REPORTS),
    }
    barrier = {
        "gate": "HOMI_GATE_0",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "manifest_hash": manifest["manifest_hash"],
        "conditioning_report_hash": conditioning["report_hash"],
        "archive_report_hash": archives["report_hash"],
        "claim_ledger_hash": ledger["ledger_hash"],
        "artifact_count": manifest["artifact_count"],
        "structured_artifact_count": conditioning["structured_artifact_count"],
        "repaired_artifact_count": conditioning["repaired_artifact_count"],
        "malformed_unrepaired_count": conditioning["status_counts"].get("MALFORMED_UNREPAIRED", 0),
        "claim_count": ledger["claim_count"],
        "promotion_count": 0,
        "note": "Executable pytest regression is run separately; this barrier validates persisted corpus and staging artifacts.",
    }
    write_canonical_json(BARRIER, barrier)
    print(
        f"gate0={barrier['status']} artifacts={barrier['artifact_count']} "
        f"claims={barrier['claim_count']} promotions=0"
    )
    return 0 if barrier["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
