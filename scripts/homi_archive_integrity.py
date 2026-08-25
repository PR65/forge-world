#!/usr/bin/env python3
"""Verify all Manus ZIP entries against the immutable extracted corpus."""
from __future__ import annotations

import csv
import hashlib
import sys
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from forge.reality import content_hash, write_canonical_json


MANUS_ROOT = Path(r"C:\FORGE-RESEARCH-CORPUS\manus")
MANIFEST = MANUS_ROOT / "_meta" / "manus_corpus_manifest.csv"
RAW_ZIPS = MANUS_ROOT / "raw-zips"
EXTRACTED = MANUS_ROOT / "extracted"
OUTPUT = ROOT / "research" / "homi" / "staging" / "archive_integrity.json"


def _safe_entry(name: str) -> PurePosixPath:
    value = PurePosixPath(name.replace("\\", "/"))
    if value.is_absolute() or ".." in value.parts:
        raise ValueError(f"unsafe ZIP entry path: {name!r}")
    return value


def main() -> int:
    with MANIFEST.open("r", encoding="utf-8-sig", newline="") as handle:
        mappings = list(csv.DictReader(handle))
    packages = []
    failure_count = 0
    for mapping in sorted(mappings, key=lambda row: row["CorpusID"]):
        corpus_id = mapping["CorpusID"]
        zip_path = RAW_ZIPS / mapping["OriginalZip"]
        extracted_root = EXTRACTED / corpus_id
        zip_before = content_hash(zip_path.read_bytes())
        entries = []
        extracted_files = [path for path in extracted_root.rglob("*") if path.is_file()]
        extracted_hashes: dict[str, list[Path]] = {}
        for extracted_file in extracted_files:
            extracted_hashes.setdefault(content_hash(extracted_file.read_bytes()), []).append(extracted_file)
        with zipfile.ZipFile(zip_path, "r") as archive:
            for info in sorted(archive.infolist(), key=lambda item: item.filename.casefold()):
                if info.is_dir():
                    continue
                logical = _safe_entry(info.filename)
                payload = archive.read(info)
                direct = extracted_root / Path(*logical.parts)
                # Several archives carry one harmless wrapper directory.  Match
                # only by a unique relative suffix; ambiguity remains a failure.
                candidates = [direct] if direct.is_file() else []
                if not candidates:
                    candidates = [
                        path
                        for path in extracted_root.rglob(logical.name)
                        if path.is_file() and tuple(path.relative_to(extracted_root).parts[-len(logical.parts) :]) == logical.parts
                    ]
                if not candidates:
                    candidates = [path for path in extracted_root.rglob(logical.name) if path.is_file()]
                status = "MISSING_EXTRACTED"
                extracted_path = ""
                extracted_hash = ""
                if len(candidates) == 1:
                    candidate = candidates[0]
                    extracted_path = candidate.relative_to(extracted_root).as_posix()
                    extracted_hash = content_hash(candidate.read_bytes())
                    status = "MATCH" if extracted_hash == content_hash(payload) else "HASH_MISMATCH"
                elif len(candidates) > 1:
                    status = "AMBIGUOUS_EXTRACTED_MATCH"
                if not candidates:
                    hash_candidates = extracted_hashes.get(content_hash(payload), [])
                    if len(hash_candidates) == 1:
                        candidate = hash_candidates[0]
                        extracted_path = candidate.relative_to(extracted_root).as_posix()
                        extracted_hash = content_hash(candidate.read_bytes())
                        status = "MATCH_SANITIZED_PATH"
                    elif len(hash_candidates) > 1:
                        status = "AMBIGUOUS_HASH_MATCH"
                if not status.startswith("MATCH"):
                    failure_count += 1
                entries.append(
                    {
                        "zip_entry": logical.as_posix(),
                        "zip_entry_bytes": len(payload),
                        "zip_entry_hash": content_hash(payload),
                        "extracted_path": extracted_path,
                        "extracted_hash": extracted_hash,
                        "status": status,
                    }
                )
        extracted_paths = {
            path.relative_to(extracted_root).as_posix()
            for path in extracted_root.rglob("*")
            if path.is_file()
        }
        matched_paths = {entry["extracted_path"] for entry in entries if entry["extracted_path"]}
        unexpected = sorted(extracted_paths - matched_paths)
        failure_count += len(unexpected)
        zip_after = content_hash(zip_path.read_bytes())
        if zip_before != zip_after:
            failure_count += 1
        packages.append(
            {
                "corpus_id": corpus_id,
                "zip_name": zip_path.name,
                "zip_hash": zip_before,
                "zip_unchanged": zip_before == zip_after,
                "declared_file_count": int(mapping["FileCount"]),
                "zip_entry_count": len(entries),
                "extracted_file_count": len(extracted_paths),
                "match_count": sum(entry["status"].startswith("MATCH") for entry in entries),
                "sanitized_path_match_count": sum(
                    entry["status"] == "MATCH_SANITIZED_PATH" for entry in entries
                ),
                "failure_count": sum(not entry["status"].startswith("MATCH") for entry in entries) + len(unexpected),
                "unexpected_extracted_paths": unexpected,
                "entries": entries,
            }
        )
    report = {
        "archive_integrity_version": "1.0.0",
        "package_count": len(packages),
        "entry_count": sum(row["zip_entry_count"] for row in packages),
        "matched_entry_count": sum(row["match_count"] for row in packages),
        "failure_count": failure_count,
        "packages": packages,
    }
    report["report_hash"] = hashlib.sha256(
        str([(row["corpus_id"], row["zip_hash"], row["failure_count"]) for row in packages]).encode("utf-8")
    ).hexdigest()
    write_canonical_json(OUTPUT, report)
    print(
        f"packages={report['package_count']} entries={report['entry_count']} "
        f"matched={report['matched_entry_count']} failures={failure_count}"
    )
    return 1 if failure_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
