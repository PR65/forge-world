"""Deterministic structural accounting for the current India V1 Run 2 atlas.

This is a read-only accounting boundary.  It constructs the current catalog,
measures its direct/reference split, graph and ladder contracts, and records
only top-level IndiaBUILD observations already present in local repository
artifacts.  It does not search the web, alter catalog/search behavior, or
claim row-level IndiaBUILD parity where no public row export is available.

Usage::

    python scripts/forge_india_v1_run2_quality_accounting.py
    python scripts/forge_india_v1_run2_quality_accounting.py --no-write
    python scripts/forge_india_v1_run2_quality_accounting.py --output path.json

The default artifact is intentionally timestamp-free and byte-deterministic.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys
from statistics import median
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.india_v1 import domains_05_08, domains_09_12  # noqa: E402
from forge.india_v1.catalog import get_catalog  # noqa: E402
from forge.india_v1.generator import generate_atlas  # noqa: E402
from forge.india_v1.quality import ALLOWED_ACTIONS, correct_epistemic_status  # noqa: E402


RUNNER_VERSION = "1.0.0"
SCHEMA_VERSION = "india_v1.run2_quality_accounting.v1"
DEFAULT_OUTPUT = ROOT / "research" / "india_v1" / "run2_quality_accounting.json"
INDIABUILD_ACCOUNTING = ROOT / "research" / "india_v1" / "indiabuild_accounting.json"
EXPECTED_STAGES = (
    "local_first",
    "initial_import_bridge",
    "integration_and_test",
    "next_localization",
    "harder_later_capability",
    "optional_redesign",
)
NAVIGATION_FIELDS = ("upstream", "downstream", "related")
GRAPH_FIELDS = ("dependency_ids", *NAVIGATION_FIELDS)
PROFILE_EXPECTATIONS = {
    "patient-monitor": "clinical",
    "infusion-pump": "clinical",
    "dialysis-machine": "clinical",
    "lab-incubator": "lab",
    "cold-storage-system": "cold_chain",
}
GENERIC_STAGE_RE = re.compile(
    r"(?:design and architecture capability|process knowledge and process control capability|"
    r"qualification and acceptance capability|scalable effective-throughput capability|"
    r"integration and production-system capability)$",
    re.IGNORECASE,
)

# This is a top-level observation supplied by the maintainer from the official
# pages on 2026-08-26.  It is deliberately kept separate from local
# row-level/sample accounting and is never used to assert parity.
CURRENT_INDIA_BUILD_OBSERVATION = {
    "observed_on": "2026-08-26",
    "mapped_capability_count": 7049,
    "assessed_capability_count": 3876,
    "unassessed_capability_count": 3173,
    "maturity_counts": {
        "NO_CAPABILITY": 470,
        "EMERGING": 1075,
        "DEMONSTRATED": 682,
        "PRODUCING_LICENSED": 468,
        "PRODUCING_OWN_TECH": 1067,
        "COMPETITIVE": 114,
    },
    "catalogue_claim": 10000,
    "source_urls": [
        "https://indiabuild.wiki/",
        "https://indiabuild.wiki/how-it-works",
    ],
    "scope": "official top-level observation only; no row-level export or parity claim",
}


def _counter(values: Iterable[Any]) -> dict[str, int]:
    return dict(sorted((str(key), int(value)) for key, value in Counter(values).items()))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _records_digest(records: Sequence[Mapping[str, Any]]) -> str:
    fields = []
    for record in sorted(records, key=lambda row: str(row.get("id", ""))):
        fields.append(
            {
                "id": str(record.get("id", "")),
                "canonical_name": str(record.get("canonical_name", "")),
                "display_name": str(record.get("display_name", "")),
                "family_key": str(record.get("family_key", "")),
                "domain_code": str(record.get("domain_code", "")),
                "kind": str(record.get("kind", "")),
                "status": str(record.get("status", "")),
                "status_epistemic_class": str(record.get("status_epistemic_class", "")),
                "dependency_ids": sorted(str(value) for value in record.get("dependency_ids", ())),
                "upstream": sorted(str(value) for value in record.get("upstream", ())),
                "downstream": sorted(str(value) for value in record.get("downstream", ())),
                "related": sorted(str(value) for value in record.get("related", ())),
                "ladder": [
                    {
                        "stage": str(step.get("stage", "")),
                        "action": str(step.get("action", "")),
                        "profile": dict(step.get("ladder_profile", {})) if isinstance(step, Mapping) else {},
                    }
                    for step in record.get("making_ladder", ())
                    if isinstance(step, Mapping)
                ],
            }
        )
    payload = json.dumps(fields, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _scope_rows(records: Sequence[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    return {
        "all": list(records),
        "direct": [row for row in records if not bool(row.get("is_reference_only"))],
        "reference": [row for row in records if bool(row.get("is_reference_only"))],
    }


def _distributions(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    domain_status: dict[str, dict[str, int]] = {}
    for domain in sorted({str(row.get("domain_code", "")) for row in rows}):
        domain_status[domain] = _counter(
            row.get("status", "UNKNOWN") for row in rows if str(row.get("domain_code", "")) == domain
        )
    return {
        "record_count": len(rows),
        "domain_counts": _counter(row.get("domain_code", "") for row in rows),
        "kind_counts": _counter(row.get("kind", "") for row in rows),
        "status_counts": _counter(row.get("status", "UNKNOWN") for row in rows),
        "status_epistemic_counts": _counter(
            row.get("status_epistemic_class", "UNKNOWN") for row in rows
        ),
        "domain_status_counts": domain_status,
    }


def _canonical_names(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        groups[str(row.get("canonical_name", ""))].append(str(row.get("id", "")))
    duplicates = [
        (name, sorted(ids)) for name, ids in groups.items() if name and len(ids) > 1
    ]
    duplicates.sort(key=lambda item: (-len(item[1]), item[0]))
    return {
        "unique_canonical_name_count": len(groups),
        "exact_duplicate_group_count": len(duplicates),
        "exact_duplicate_row_count": sum(len(ids) for _, ids in duplicates),
        "max_rows_per_name": max((len(ids) for ids in groups.values()), default=0),
        "top_duplicate_names": [
            {"canonical_name": name, "count": len(ids), "ids": ids[:12]}
            for name, ids in duplicates[:20]
        ],
    }


def _name_artifacts(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    names = [str(row.get("canonical_name", "")) for row in rows]
    display_names = [str(row.get("display_name", "")) for row in rows]
    return {
        "parenthesized_name_count": sum("(" in name or ")" in name for name in names),
        "space_hyphen_name_count": sum(" - " in name for name in names),
        "generic_lifecycle_suffix_count": sum(bool(GENERIC_STAGE_RE.search(name)) for name in names),
        "duplicate_display_name_row_count": len(display_names) - len(set(display_names)),
    }


def _family_metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    groups = Counter(str(row.get("family_key") or row.get("id", "")) for row in rows)
    values = sorted(groups.values())
    multi = [value for value in values if value > 1]
    top = sorted(groups.items(), key=lambda item: (-item[1], item[0]))[:20]
    return {
        "record_count": len(rows),
        "family_count": len(groups),
        "multi_variant_family_count": len(multi),
        "singleton_family_count": sum(value == 1 for value in values),
        "records_in_multi_variant_families": sum(multi),
        "variant_consolidation_ratio": round(len(rows) / len(groups), 6) if groups else 0.0,
        "variants_per_family": {
            "min": min(values) if values else 0,
            "max": max(values) if values else 0,
            "median": median(values) if values else 0,
            "p95": values[max(0, int(len(values) * 0.95) - 1)] if values else 0,
        },
        "top_families": [
            {"family_key": family, "variant_count": count} for family, count in top
        ],
    }


def _family_by_domain(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for domain in sorted({str(row.get("domain_code", "")) for row in rows}):
        result[domain] = _family_metrics(
            [row for row in rows if str(row.get("domain_code", "")) == domain]
        )
    return result


def _graph_metrics(
    records: Sequence[Mapping[str, Any]],
    *,
    resolution_ids: set[str] | None = None,
) -> dict[str, Any]:
    ids = set(resolution_ids or {str(row.get("id", "")) for row in records})
    edge_counts = Counter()
    unique_edges: set[tuple[str, str, str]] = set()
    missing_edges: list[dict[str, str]] = []
    self_references: list[dict[str, str]] = []
    out_degree: Counter[str] = Counter()
    in_degree: Counter[str] = Counter()
    rows_with_navigation = 0
    dead_end_ids: list[str] = []
    for row in records:
        record_id = str(row.get("id", ""))
        nav_values = [str(value) for field in NAVIGATION_FIELDS for value in row.get(field, ())]
        if any(row.get(field) for field in NAVIGATION_FIELDS):
            rows_with_navigation += 1
        if not any(row.get(field) for field in NAVIGATION_FIELDS):
            dead_end_ids.append(record_id)
        out_degree[record_id] += len(set(nav_values))
        for field in GRAPH_FIELDS:
            refs = sorted(set(str(value) for value in row.get(field, ())))
            edge_counts[field] += len(refs)
            for target in refs:
                unique_edges.add((record_id, field, target))
                if target not in ids and len(missing_edges) < 20:
                    missing_edges.append({"source": record_id, "relation": field, "target": target})
                if target == record_id and len(self_references) < 20:
                    self_references.append({"source": record_id, "relation": field, "target": target})
                if field in NAVIGATION_FIELDS:
                    in_degree[target] += 1
    resolved_edge_count = sum(
        1 for source, _relation, target in unique_edges if target in ids
    )
    top_connectivity = sorted(
        (
            {
                "id": record_id,
                "domain": str(row.get("domain_code", "")),
                "kind": str(row.get("kind", "")),
                "family_key": str(row.get("family_key", "")),
                "out_degree": out_degree.get(record_id, 0),
                "in_degree": in_degree.get(record_id, 0),
                "total_navigation_degree": out_degree.get(record_id, 0) + in_degree.get(record_id, 0),
            }
            for row in records
            for record_id in [str(row.get("id", ""))]
        ),
        key=lambda item: (-item["total_navigation_degree"], -item["out_degree"], item["id"]),
    )[:20]
    return {
        "record_count": len(records),
        "resolution_universe_record_count": len(ids),
        "edge_counts": dict(sorted((key, int(value)) for key, value in edge_counts.items())),
        "unique_edge_count": len(unique_edges),
        "resolved_unique_edge_count": resolved_edge_count,
        "missing_unique_edge_count": len(unique_edges) - resolved_edge_count,
        "missing_edge_samples": missing_edges,
        "self_reference_count": len(self_references),
        "self_reference_samples": self_references,
        "navigation_coverage_count": rows_with_navigation,
        "navigation_coverage_rate": round(rows_with_navigation / len(records), 6) if records else 0.0,
        "dead_end_count": len(dead_end_ids),
        "dead_end_ids_sample": sorted(dead_end_ids)[:20],
        "top_connectivity": top_connectivity,
    }


def _ladder_metrics(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    complete = 0
    ordered = 0
    allowed_violations = 0
    action_diversity_defects = 0
    lengths = Counter()
    action_sequences = Counter()
    semantic_signatures = Counter()
    stage_action_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in records:
        ladder = row.get("making_ladder") or []
        lengths[len(ladder)] += 1
        stages = [step for step in ladder if isinstance(step, Mapping)]
        stage_names = tuple(str(step.get("stage", "")) for step in stages)
        if len(stages) >= len(EXPECTED_STAGES) and stage_names[: len(EXPECTED_STAGES)] == EXPECTED_STAGES:
            complete += 1
        if stage_names == EXPECTED_STAGES:
            ordered += 1
        actions = tuple(str(step.get("action", "")).upper() for step in stages)
        action_sequences[actions] += 1
        if len(set(actions)) < 4:
            action_diversity_defects += 1
        semantic_signatures[tuple(
            (
                str(step.get("stage", "")),
                str(step.get("action", "")).upper(),
                tuple(sorted(str(value).upper() for value in step.get("allowed_actions", ()))),
                tuple(sorted((str(key), str(value)) for key, value in (step.get("ladder_profile") or {}).items())),
                bool(step.get("required", False)),
            )
            for step in stages
        )] += 1
        for step in stages:
            stage_action_counts[str(step.get("stage", ""))][str(step.get("action", "")).upper()] += 1
            if not set(str(value).upper() for value in step.get("allowed_actions", ())).issubset(ALLOWED_ACTIONS):
                allowed_violations += 1
    dominant_semantic_count = max(semantic_signatures.values(), default=0)
    semantic_rate = dominant_semantic_count / len(records) if records else 0.0
    return {
        "record_count": len(records),
        "expected_stages": list(EXPECTED_STAGES),
        "complete_count": complete,
        "incomplete_count": len(records) - complete,
        "ordered_count": ordered,
        "order_defect_count": len(records) - ordered,
        "allowed_action_violation_count": allowed_violations,
        "length_counts": dict(sorted((str(key), int(value)) for key, value in lengths.items())),
        "distinct_action_sequence_count": len(action_sequences),
        "top_action_sequences": [
            {"actions": list(actions), "count": count}
            for actions, count in action_sequences.most_common(12)
        ],
        "semantic_signature_count": len(semantic_signatures),
        "dominant_semantic_signature_count": dominant_semantic_count,
        "dominant_semantic_signature_rate": round(semantic_rate, 6),
        "low_semantic_diversity_threshold": 0.95,
        "low_semantic_diversity_defect": semantic_rate > 0.95,
        "action_diversity_defect_count": action_diversity_defects,
        "stage_action_counts": {
            stage: dict(sorted((action, int(count)) for action, count in values.items()))
            for stage, values in sorted(stage_action_counts.items())
        },
    }


def _source_rows() -> list[Mapping[str, Any]]:
    core_rows = [record.to_dict() for record in generate_atlas()]
    return [*core_rows, *domains_05_08.ALL_RECORDS, *domains_09_12.ALL_RECORDS]


def _epistemic_metrics(source_rows: Sequence[Mapping[str, Any]], catalog_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    changed: list[dict[str, str]] = []
    basis_markers: list[dict[str, str]] = []
    for row in source_rows:
        basis_text = str(row.get("status_basis", ""))
        if "Epistemic correction" in basis_text:
            prior_match = re.search(r"prior_status=([^;]+)", basis_text)
            basis_markers.append(
                {
                    "id": str(row.get("id", "")),
                    "prior_status": prior_match.group(1).strip() if prior_match else "UNKNOWN",
                    "corrected_status": str(row.get("status", "UNKNOWN")),
                }
            )
        before = {
            "status": row.get("status") or row.get("india_status"),
            "india_status": row.get("india_status"),
            "status_basis": row.get("status_basis"),
            "status_epistemic_class": row.get("status_epistemic_class") or row.get("epistemic_class"),
            "epistemic_class": row.get("epistemic_class"),
        }
        after = correct_epistemic_status(before)
        if any(after.get(key) != before.get(key) for key in ("status", "india_status", "status_epistemic_class", "epistemic_class")):
            changed.append(
                {
                    "id": str(row.get("id", "")),
                    "prior_status": str(before.get("status", "")),
                    "corrected_status": str(after.get("status", "")),
                }
            )
    metadata_count = sum(bool(row.get("status_basis_metadata")) for row in catalog_rows)
    # The generator persists the correction in status_basis but the typed
    # AtlasRecord does not carry arbitrary metadata.  Prefer that auditable
    # marker when the post-correction source row is already UNKNOWN.
    derived_count = max(len(changed), len(basis_markers), metadata_count)
    return {
        "source_direct_row_count": len(source_rows),
        "derived_correction_count": derived_count,
        "correction_detection_counts": {
            "status_transition_observed": len(changed),
            "status_basis_marker_observed": len(basis_markers),
            "status_basis_metadata_observed": metadata_count,
        },
        "derived_correction_samples": (basis_markers or changed)[:20],
        "catalog_status_basis_metadata_count": metadata_count,
        "correction_rule": "ASSUMPTION-backed STRONG/MISSING becomes UNKNOWN; prior label remains in status_basis_metadata when present",
    }


def _profile_metrics() -> dict[str, Any]:
    rows = list(domains_05_08.ALL_RECORDS)
    target_rows = [row for row in rows if str(row.get("archetype_id", "")) in PROFILE_EXPECTATIONS]
    per_family = {}
    for family, expected in PROFILE_EXPECTATIONS.items():
        family_rows = [row for row in target_rows if str(row.get("archetype_id", "")) == family]
        observed = Counter(str(row.get("profile", "")) for row in family_rows)
        per_family[family] = {
            "row_count": len(family_rows),
            "expected_profile": expected,
            "observed_profiles": dict(sorted((key, int(value)) for key, value in observed.items())),
            "mismatch_count": sum(str(row.get("profile", "")) != expected for row in family_rows),
        }
    return {
        "source_pack": "data.india_v1.domains_05_08",
        "profile_field_row_count": sum(bool(row.get("profile")) for row in rows),
        "targeted_family_count": len(PROFILE_EXPECTATIONS),
        "targeted_row_count": len(target_rows),
        "targeted_expected_row_count": len(PROFILE_EXPECTATIONS) * 36,
        "targeted_mismatch_count": sum(item["mismatch_count"] for item in per_family.values()),
        "per_family": per_family,
    }


def _indiabuild_metrics(catalog_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    local = json.loads(INDIABUILD_ACCOUNTING.read_text(encoding="utf-8"))
    count_level = dict(local.get("count_level", {}))
    return {
        "source_artifact": str(INDIABUILD_ACCOUNTING.relative_to(ROOT)).replace("\\", "/"),
        "source_artifact_sha256": _sha256(INDIABUILD_ACCOUNTING),
        "repository_verified_snapshot": {
            "observed_on": local.get("observed_on"),
            "mapped_capability_count": count_level.get("indiabuild_public_observed_mapped_count"),
            "catalogue_claim": count_level.get("indiabuild_public_catalogue_claim"),
            "assessed_or_sample_class_counts": local.get("sample_class_counts", {}),
            "sample_size": local.get("sample_size", 0),
        },
        "current_official_top_level_observation": CURRENT_INDIA_BUILD_OBSERVATION,
        "row_level_export_available": bool(local.get("public_bulk_list_available", False)),
        "parity_status": "NOT_COMPARABLE",
        "parity_note": "No verified public row-level IndiaBUILD export is present locally; Forge ontology record counts are not treated as IndiaBUILD row counts.",
        "forge_counts_for_context": {
            "record_count": len(catalog_rows),
            "direct_record_count": sum(not row.get("is_reference_only") for row in catalog_rows),
            "reference_record_count": sum(bool(row.get("is_reference_only")) for row in catalog_rows),
        },
        "source_urls": list(CURRENT_INDIA_BUILD_OBSERVATION["source_urls"]),
    }


def build_quality_accounting() -> dict[str, Any]:
    catalog = get_catalog()
    records = list(catalog.records)
    scopes = _scope_rows(records)
    direct = scopes["direct"]
    integrity = catalog.integrity()
    return {
        "schema_version": SCHEMA_VERSION,
        "runner_version": RUNNER_VERSION,
        "source_api": "forge.india_v1.catalog.get_catalog",
        "record_digest_sha256": _records_digest(records),
        "record_counts": {
            "record_count": len(records),
            "direct_record_count": len(direct),
            "reference_record_count": len(scopes["reference"]),
            "direct_share": round(len(direct) / len(records), 6) if records else 0.0,
            "reference_share": round(len(scopes["reference"]) / len(records), 6) if records else 0.0,
        },
        "integrity": {
            "ok": bool(integrity.get("ok")),
            "unique_ids": int(integrity.get("unique_ids", 0)),
            "unique_aliases": int(integrity.get("unique_aliases", 0)),
            "all_references_resolve": not bool(integrity.get("errors")),
            "error_count": len(integrity.get("errors", ())),
        },
        "distributions": {scope: _distributions(rows) for scope, rows in scopes.items()},
        "canonical_names": {scope: _canonical_names(rows) for scope, rows in scopes.items()},
        "name_artifacts": {scope: _name_artifacts(rows) for scope, rows in scopes.items()},
        "families": {
            "all": _family_metrics(records),
            "direct": _family_metrics(direct),
            "by_domain_direct": _family_by_domain(direct),
        },
        "graph": {
            "all": _graph_metrics(records, resolution_ids={str(row.get("id", "")) for row in records}),
            "direct": _graph_metrics(direct, resolution_ids={str(row.get("id", "")) for row in records}),
            "reference": _graph_metrics(scopes["reference"], resolution_ids={str(row.get("id", "")) for row in records}),
        },
        "ladders": {
            "all": _ladder_metrics(records),
            "direct": _ladder_metrics(direct),
            "reference": _ladder_metrics(scopes["reference"]),
        },
        "epistemic_corrections": _epistemic_metrics(_source_rows(), records),
        "profile_fixes": _profile_metrics(),
        "indiabuild_accounting": _indiabuild_metrics(records),
    }


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.write_text(encoded, encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--no-write", action="store_true", help="print the deterministic JSON without writing it")
    args = parser.parse_args(argv)
    payload = build_quality_accounting()
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.no_write:
        print(encoded, end="")
    else:
        _write_json(args.output, payload)
        print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised by the command contract
    raise SystemExit(main())


__all__ = [
    "DEFAULT_OUTPUT",
    "SCHEMA_VERSION",
    "build_quality_accounting",
    "main",
]
