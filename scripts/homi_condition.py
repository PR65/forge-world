#!/usr/bin/env python3
"""Condition HOMI corpus artifacts into reproducible, non-authoritative staging.

The script validates structured files, writes repaired CSV/TSV copies only under
``research/homi/staging/repaired``, and verifies every external source hash after
processing.  It never edits, renames, or deletes an external corpus artifact.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from forge.reality import (
    SourceLayer,
    content_hash,
    inventory_corpus,
    repair_csv_bytes,
    write_canonical_json,
)


CORPUS_ROOTS = {
    "manus_raw_zips": (Path(r"C:\FORGE-RESEARCH-CORPUS\manus\raw-zips"), SourceLayer.RAW),
    "manus_extracted": (Path(r"C:\FORGE-RESEARCH-CORPUS\manus\extracted"), SourceLayer.EXTRACTED),
    "glm_foundry": (Path(r"C:\FORGE-GLM-FOUNDRY"), SourceLayer.EXTRACTED),
}
SKIP_IMPORT_NAMES = {"materials_minerals_foundational_MANUAL_TEST_DO_NOT_IMPORT.yaml"}
STRUCTURED_SUFFIXES = {".csv", ".tsv", ".json", ".jsonl", ".yaml", ".yml"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "research" / "homi" / "staging" / "conditioning_report.json",
    )
    parser.add_argument(
        "--repair-root",
        type=Path,
        default=ROOT / "research" / "homi" / "staging" / "repaired",
    )
    return parser.parse_args()


def _shape(value: Any) -> tuple[int, list[str]]:
    if isinstance(value, list):
        keys = sorted(
            {str(key) for row in value if isinstance(row, dict) for key in row}
        )
        return len(value), keys
    if isinstance(value, dict):
        list_rows = sum(len(item) for item in value.values() if isinstance(item, list))
        return list_rows or 1, sorted(str(key) for key in value)
    return 1, []


def _validate_delimited(payload: bytes, suffix: str) -> tuple[dict[str, Any], bytes | None]:
    delimiter = "\t" if suffix == ".tsv" else ","
    result = repair_csv_bytes(payload, delimiter=delimiter)
    decoded = result.repaired_bytes.decode("utf-8")
    rows = list(csv.reader(io.StringIO(decoded, newline=""), delimiter=delimiter))
    widths = {len(row) for row in rows}
    validation = "VALID" if len(widths) <= 1 else "INVALID_ROW_WIDTH"
    report = result.to_json()
    report["validation_result"] = validation
    report["field_names"] = rows[0] if rows else []
    report["repair_action_count"] = len(result.actions)
    report["ambiguous_repair_count"] = sum(
        action.severity.value == "AMBIGUOUS" for action in result.actions
    )
    repaired = result.repaired_bytes if result.actions else None
    return report, repaired


def main() -> int:
    args = parse_args()
    all_snapshots = []
    path_lookup: dict[tuple[str, str], Path] = {}
    for corpus_id, (root, layer) in CORPUS_ROOTS.items():
        for snapshot in inventory_corpus(root, corpus_id=corpus_id, source_layer=layer):
            all_snapshots.append(snapshot)
            path_lookup[(corpus_id, snapshot.logical_path)] = root / Path(snapshot.logical_path)

    hashes: dict[str, list[str]] = defaultdict(list)
    for snapshot in all_snapshots:
        hashes[snapshot.content_hash].append(snapshot.artifact_id)

    artifacts: list[dict[str, Any]] = []
    repaired_count = 0
    raw_integrity_failures: list[str] = []
    status_counts: Counter[str] = Counter()
    for snapshot in sorted(all_snapshots, key=lambda item: item.artifact_id):
        path = path_lookup[(snapshot.corpus_id, snapshot.logical_path)]
        payload = path.read_bytes()
        suffix = path.suffix.lower()
        row: dict[str, Any] = {
            "artifact_id": snapshot.artifact_id,
            "corpus_id": snapshot.corpus_id,
            "logical_path": snapshot.logical_path,
            "original_hash": snapshot.content_hash,
            "byte_length": snapshot.byte_length,
            "duplicate_hash": len(hashes[snapshot.content_hash]) > 1,
            "duplicate_artifact_ids": sorted(
                item for item in hashes[snapshot.content_hash] if item != snapshot.artifact_id
            ),
        }
        try:
            if path.name in SKIP_IMPORT_NAMES:
                row.update(
                    parse_status="INTENTIONALLY_SKIPPED",
                    skip_reason="manual test fixture explicitly barred from import",
                )
            elif suffix in {".csv", ".tsv"}:
                detail, repaired = _validate_delimited(payload, suffix)
                row.update(parse_status="STRUCTURED_VALIDATED", structured=detail)
                if repaired is not None:
                    destination = args.repair_root / snapshot.corpus_id / Path(snapshot.logical_path)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(repaired)
                    row["repaired_staging_path"] = destination.relative_to(ROOT).as_posix()
                    repaired_count += 1
            elif suffix == ".json":
                value = json.loads(payload.decode("utf-8-sig"))
                record_count, fields = _shape(value)
                row.update(
                    parse_status="STRUCTURED_VALIDATED",
                    structured={"record_count": record_count, "field_names": fields},
                )
            elif suffix == ".jsonl":
                values = [
                    json.loads(line)
                    for line in payload.decode("utf-8-sig").splitlines()
                    if line.strip()
                ]
                record_count, fields = _shape(values)
                row.update(
                    parse_status="STRUCTURED_VALIDATED",
                    structured={"record_count": record_count, "field_names": fields},
                )
            elif suffix in {".yaml", ".yml"}:
                value = yaml.safe_load(payload.decode("utf-8-sig"))
                record_count, fields = _shape(value)
                row.update(
                    parse_status="STRUCTURED_VALIDATED",
                    structured={"record_count": record_count, "field_names": fields},
                )
            elif suffix in STRUCTURED_SUFFIXES:
                row.update(parse_status="UNSUPPORTED", skip_reason="unsupported structured type")
            else:
                row.update(parse_status="INVENTORIED_CONTEXT")
        except Exception as exc:
            row.update(
                parse_status="MALFORMED_UNREPAIRED",
                error_type=type(exc).__name__,
                error=str(exc),
            )
        current_hash = content_hash(path.read_bytes())
        row["post_condition_hash"] = current_hash
        row["raw_unchanged"] = current_hash == snapshot.content_hash
        if not row["raw_unchanged"]:
            raw_integrity_failures.append(snapshot.artifact_id)
        status_counts[row["parse_status"]] += 1
        artifacts.append(row)

    report: dict[str, Any] = {
        "conditioning_version": "1.0.0",
        "artifact_count": len(artifacts),
        "unique_hash_count": len(hashes),
        "duplicate_artifact_count": sum(row["duplicate_hash"] for row in artifacts),
        "structured_artifact_count": sum(
            row["parse_status"] == "STRUCTURED_VALIDATED" for row in artifacts
        ),
        "repaired_artifact_count": repaired_count,
        "raw_integrity_failure_count": len(raw_integrity_failures),
        "raw_integrity_failures": raw_integrity_failures,
        "status_counts": dict(sorted(status_counts.items())),
        "artifacts": artifacts,
    }
    report["report_hash"] = content_hash(json.dumps(report, sort_keys=True, separators=(",", ":")))
    write_canonical_json(args.output, report)
    print(f"conditioned {len(artifacts)} artifacts; structured={report['structured_artifact_count']}")
    print(f"repaired={repaired_count}; raw_integrity_failures={len(raw_integrity_failures)}")
    print(f"report_hash={report['report_hash']}")
    return 1 if raw_integrity_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
