"""Frozen founder/adversarial search audit for FORGE India V1 Run 2.

This is an audit harness, not a repair or benchmark gate.  It loads the frozen
query battery, searches the current combined India catalog, and records
observable retrieval, taxonomy, graph, and product-content failures.  The
query set is intentionally external to the catalog and is never generated
from search results.

Usage::

    python scripts/forge_india_v1_run2_audit.py
    python scripts/forge_india_v1_run2_audit.py --output research/india_v1/run2_baseline_metrics.json

The default run writes a concise metrics file and a detail file.  Both are
deterministic: no timestamps, random choices, or live web calls are used.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from math import ceil
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from forge.india_v1.catalog import get_catalog, summary as catalog_summary  # noqa: E402


RUNNER_VERSION = "1.1.0"
BATTERY_SCHEMA_VERSION = "india_v1.run2_search_battery.v1"
METRICS_SCHEMA_VERSION = "india_v1.run2_baseline_metrics.v1"
DETAILS_SCHEMA_VERSION = "india_v1.run2_baseline_findings.v1"
DEFAULT_BATTERY = ROOT / "data" / "india_v1" / "run2_search_battery.json"
DEFAULT_OUTPUT = ROOT / "research" / "india_v1" / "run2_baseline_metrics.json"
DEFAULT_DETAILS_OUTPUT = ROOT / "research" / "india_v1" / "run2_baseline_findings.json"
DEFAULT_FINAL_OUTPUT = ROOT / "research" / "india_v1" / "run2_final_metrics.json"
DEFAULT_FINAL_DETAILS_OUTPUT = ROOT / "research" / "india_v1" / "run2_final_findings.json"
DEFAULT_COMPARISON_OUTPUT = ROOT / "research" / "india_v1" / "run2_baseline_vs_final.json"
DEFAULT_ABUSE_OUTPUT = ROOT / "research" / "india_v1" / "run2_abuse_probe_results.json"

ABUSE_PROBES: tuple[dict[str, Any], ...] = (
    {"id": "a01", "query": "rotary screw compressor", "domain": "05"},
    {"id": "a02", "query": "milk homogenizer", "domain": "08"},
    {"id": "a03", "query": "corrugated box machine", "domain": "11"},
    {"id": "a04", "query": "induction furnace", "domain": "06"},
    {"id": "a05", "query": "industrial chiller", "domain": "06"},
    {"id": "a06", "query": "hydraulic cylinder", "domain": "10"},
    {"id": "a07", "query": "pharmaceutical blister packaging machine", "domain": "11"},
    {"id": "a08", "query": "railway axle", "domain": "09"},
    {"id": "a09", "query": "slurry pump", "domain": "06"},
    {"id": "a10", "query": "seed drill", "domain": "08"},
    {"id": "a11", "query": "industrial sewing machine", "domain": "11"},
    {"id": "a12", "query": "oxygen concentrator", "domain": "07"},
    {"id": "a13", "query": "plate heat exchanger", "domain": "06"},
    {"id": "a14", "query": "elevator traction machine", "domain": "10"},
    {"id": "a15", "query": "autoclave", "domain": "07"},
    {"id": "a16", "query": "vacuum coating machine", "domain": "12"},
    {"id": "a17", "query": "gear hobbing machine", "domain": "05"},
    {"id": "a18", "query": "transformer winding machine", "domain": "03"},
    {"id": "a19", "query": "extruder", "domain": "11"},
    {"id": "a20", "query": "ceramic kiln", "domain": "10"},
)

FAILURE_CATEGORIES = (
    "search_miss",
    "weird_generated_name",
    "duplicate",
    "nonsense_generic_decomposition",
    "bad_domain",
    "useless_status_gap_ladder",
    "broken_dependency",
    "dead_end",
    "weak_related_unlock",
    "misleading_certainty",
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_TOKEN_ALIASES = {
    "5": "five",
    "axis": "axis",
    "centre": "center",
    "centres": "centers",
    "electrolyser": "electrolyzer",
    "uav": "drone",
    "unmanned": "drone",
    "mri": "mri",
    "ct": "ct",
    "xray": "x",
    "humanoid": "robot",
    "humanoids": "robot",
}
_GENERIC_STAGE_RE = re.compile(
    r"(?:design and architecture capability|integration and production-system capability|"
    r"process knowledge and process control capability|qualification and acceptance capability|"
    r"scalable effective-throughput capability)$",
    re.IGNORECASE,
)
_TEMPLATE_MARKERS = (
    "bench/",
    "clinic setting",
    "cell-integrated",
    "farm/workshop",
    "integrated multi-unit",
    "operator-assisted",
    "operator-led",
    "protocol-guided",
    "closed-loop",
    "advanced process control",
    "distributed control system",
    "fixed-floor",
    "hot-weather",
    "monsoon",
    "mass-production",
    "sme-workshop",
    "india domestic-build",
)
_GENERIC_GAP_PHRASES = (
    "specification fit, qualified effective capacity",
    "broad india navigation overlay",
    "curated india v1 archetype overlay",
    "status overlay",
    "evidence before a stronger claim",
)


def _load_battery(path: Path = DEFAULT_BATTERY) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    battery = json.loads(raw.decode("utf-8"))
    if battery.get("schema_version") != BATTERY_SCHEMA_VERSION:
        raise ValueError(f"unsupported battery schema: {battery.get('schema_version')!r}")
    founder = battery.get("founder_20") or []
    unseen = battery.get("unseen_queries") or []
    all_queries = founder + unseen
    ids = [str(row.get("id", "")) for row in all_queries]
    if not all(ids) or len(ids) != len(set(ids)):
        raise ValueError("battery query IDs must be present and unique")
    expected_total = int((battery.get("coverage") or {}).get("total_queries", len(all_queries)))
    if len(all_queries) != expected_total:
        raise ValueError(f"battery total mismatch: {len(all_queries)} != {expected_total}")
    if len(founder) != 20:
        raise ValueError(f"founder_20 must contain 20 queries, got {len(founder)}")
    domains = {str(row.get("domain", "")) for row in all_queries}
    if domains != set(str(value) for value in (battery.get("coverage") or {}).get("domain_codes", ())):
        raise ValueError("battery domain coverage does not match its declared domain codes")
    canonical = json.dumps(battery, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return battery, digest


def _tokens(value: Any) -> tuple[str, ...]:
    values: list[str] = []
    for token in _TOKEN_RE.findall(str(value).casefold()):
        normalized = _TOKEN_ALIASES.get(token, token)
        if normalized not in {"a", "an", "and", "for", "in", "of", "per", "the", "to", "with", "year", "india"}:
            values.append(normalized)
    return tuple(values)


def _field_text(record: Mapping[str, Any]) -> str:
    values: list[str] = []
    for key in ("id", "canonical_name", "name", "aliases", "category", "explanation", "uses", "use"):
        value = record.get(key, "")
        if isinstance(value, (list, tuple, set)):
            values.extend(str(item) for item in value)
        else:
            values.append(str(value))
    return " ".join(values)


def _anchor_overlap(anchors: Sequence[str], record: Mapping[str, Any]) -> int:
    record_tokens = set(_tokens(_field_text(record)))
    return sum(1 for anchor in anchors if _TOKEN_ALIASES.get(str(anchor).casefold(), str(anchor).casefold()) in record_tokens)


def _concept_key(record: Mapping[str, Any]) -> str:
    """Collapse generated variants to the family a user thinks they searched."""

    if record.get("family_key"):
        return str(record["family_key"])
    record_id = str(record.get("id", ""))
    parts = record_id.split(":")
    if record_id.startswith("product:") and len(parts) >= 3:
        return ":".join(parts[:3])
    if record_id.startswith("india-v1:") and len(parts) >= 4:
        return ":".join(parts[:4])
    if len(parts) >= 3 and parts[1] in {"capability", "equipment", "material", "process", "product"}:
        return ":".join(parts[:3])
    name = str(record.get("canonical_name", record.get("name", ""))).casefold()
    name = name.split("(", 1)[0].split(" - ", 1)[0]
    return re.sub(r"[^a-z0-9]+", " ", name).strip()


def _is_template_name(record: Mapping[str, Any]) -> tuple[bool, list[str]]:
    name = str(record.get("display_name") or record.get("name") or record.get("canonical_name", ""))
    lowered = name.casefold()
    reasons: list[str] = []
    if "(" in name and ")" in name and "," in name:
        reasons.append("parenthesized multi-axis variant suffix")
    if any(marker in lowered for marker in _TEMPLATE_MARKERS):
        reasons.append("deterministic variant marker")
    if re.search(r"\s+-\s+(?:Export|Hot Weather|Monsoon|Mass Production|Sme Workshop|Energy And Grid)\s*$", name, re.IGNORECASE):
        reasons.append("context suffix with generated title casing")
    if name.startswith("Reference primitive:"):
        reasons.append("reference bridge name")
    return bool(reasons), reasons


def _dependency_ids(record: Mapping[str, Any]) -> list[str]:
    values = record.get("dependency_ids")
    if values:
        return sorted({str(value) for value in values if str(value)})
    raw = record.get("dependencies") or {}
    output: list[str] = []
    if isinstance(raw, Mapping):
        for group in raw.values():
            output.extend(str(value) for value in (group or ()) if str(value))
    return sorted(set(output))


def _navigation(record: Mapping[str, Any]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for key in ("upstream", "downstream", "related", "unlock"):
        values = record.get(key) or []
        result[key] = sorted({str(value) for value in values if str(value)})
    return result


def _gap_text(record: Mapping[str, Any]) -> str:
    value = record.get("gap_import_notes")
    if value is None:
        value = record.get("gap_notes", record.get("import_notes", ""))
    if isinstance(value, (list, tuple, set)):
        return " ".join(str(item) for item in value if str(item).strip()).strip()
    return str(value or "").strip()


def _ladder_actions(record: Mapping[str, Any]) -> list[str]:
    ladder = record.get("making_ladder") or []
    actions: list[str] = []
    for step in ladder:
        if isinstance(step, Mapping):
            action = step.get("action", "")
        else:
            action = getattr(step, "action", "")
        if str(action).strip():
            actions.append(str(action).strip().upper())
    return actions


def _record_quality(record: Mapping[str, Any], by_id: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    dependencies = _dependency_ids(record)
    missing_dependencies = sorted({ref for ref in dependencies if ref not in by_id})
    navigation = _navigation(record)
    all_navigation = sorted({ref for values in navigation.values() for ref in values})
    missing_navigation = sorted({ref for ref in all_navigation if ref not in by_id})
    self_references = sorted({ref for ref in (*dependencies, *all_navigation) if ref == record.get("id")})
    status = str(record.get("status", record.get("india_status", ""))).upper()
    epistemic = str(record.get("status_epistemic_class", record.get("epistemic_basis", ""))).upper()
    basis = str(record.get("status_basis", "")).strip()
    gaps = record.get("gaps") or []
    imports = record.get("import_notes") or []
    gap_text = _gap_text(record)
    ladder_actions = _ladder_actions(record)
    generated_name, generated_reasons = _is_template_name(record)
    generic_gap = any(phrase in gap_text.casefold() for phrase in _GENERIC_GAP_PHRASES)
    status_missing = not status or not epistemic or not basis
    gap_missing_or_generic = not gap_text or len(gap_text) < 40 or (generic_gap and not gaps and not imports)
    ladder_weak = len(ladder_actions) < 5 or len(set(ladder_actions)) < 4
    generic_stage = bool(_GENERIC_STAGE_RE.search(str(record.get("canonical_name", ""))))
    assertive_unknown = (
        status in {"STRONG", "AVAILABLE"}
        and epistemic in {"ASSUMPTION", "MODELLED", "UNKNOWN"}
        and ("not evidence" in basis.casefold() or "baseline" in basis.casefold() or "curated" in basis.casefold())
    )
    return {
        "record_id": str(record.get("id", "")),
        "canonical_name": str(record.get("canonical_name", record.get("name", ""))),
        "domain_code": str(record.get("domain_code", record.get("domain_id", ""))),
        "kind": str(record.get("kind", "")).upper(),
        "is_reference_only": bool(record.get("is_reference_only", False)),
        "status": status,
        "status_epistemic_class": epistemic,
        "status_basis": basis,
        "dependency_count": len(dependencies),
        "missing_dependency_ids": missing_dependencies,
        "missing_navigation_ids": missing_navigation,
        "self_references": self_references,
        "navigation_counts": {key: len(values) for key, values in navigation.items()},
        "gap_count": len(gaps) if isinstance(gaps, (list, tuple, set)) else int(bool(gaps)),
        "import_note_count": len(imports) if isinstance(imports, (list, tuple, set)) else int(bool(imports)),
        "gap_text": gap_text[:500],
        "ladder_count": len(record.get("making_ladder") or []),
        "ladder_actions": ladder_actions,
        "template_name": generated_name,
        "template_name_reasons": generated_reasons,
        "concept_key": _concept_key(record),
        "generic_stage_name": generic_stage,
        "generic_gap_text": generic_gap,
        "status_missing": status_missing,
        "gap_missing_or_generic": gap_missing_or_generic,
        "ladder_weak": ladder_weak,
        "assertive_unknown": assertive_unknown,
    }


def _compact_result(
    record: Mapping[str, Any],
    score: int,
    rank: int,
    hit: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    generated, generated_reasons = _is_template_name(record)
    return {
        "rank": rank,
        "id": str(record.get("id", "")),
        "canonical_name": str(record.get("canonical_name", record.get("name", ""))),
        "display_name": str(record.get("display_name") or record.get("name") or record.get("canonical_name", "")),
        "domain_code": str(record.get("domain_code", record.get("domain_id", ""))),
        "domain": str(record.get("domain", "")),
        "kind": str(record.get("kind", "")).upper(),
        "status": str(record.get("status", "")).upper(),
        "status_epistemic_class": str(record.get("status_epistemic_class", "")).upper(),
        "is_reference_only": bool(record.get("is_reference_only", False)),
        "score": int(score),
        "family_key": str(record.get("family_key") or _concept_key(record)),
        "match_type": str((hit or {}).get("match_type", "legacy")),
        "matched_on": list((hit or {}).get("matched_on", ())),
        "coverage": float((hit or {}).get("coverage", 0.0)),
        "domain_match": bool((hit or {}).get("domain_match", False)),
        "concept_key": _concept_key(record),
        "template_name": generated,
        "template_name_reasons": generated_reasons,
    }


def _semantic_relevance(results: Sequence[Mapping[str, Any]], expected_domain: str) -> bool:
    """Accept a domain-matched direct family as useful related retrieval.

    Obscure probes often have no exact catalog label (for example a star
    tracker or seed drill).  A direct record in the expected domain with an
    explicit search signal is an honest related result; shared bridges and
    records from another domain do not count.
    """

    useful_types = {"exact", "phrase", "all_tokens", "alias", "partial", "fuzzy", "related"}
    return any(
        not bool(row.get("is_reference_only"))
        and str(row.get("domain_code", "")) == expected_domain
        and str(row.get("match_type", "")) in useful_types
        and bool(row.get("matched_on"))
        for row in results
    )


def _run_query(
    spec: Mapping[str, Any],
    catalog: Any,
    by_id: Mapping[str, Mapping[str, Any]],
    *,
    top_k: int,
) -> dict[str, Any]:
    query = str(spec.get("query", "")).strip()
    if hasattr(catalog, "search_hits"):
        hits = catalog.search_hits(query, limit=max(1, int(top_k)))
        ranked = [(hit["record"], int(hit["score"])) for hit in hits]
        results = [
            _compact_result(hit["record"], int(hit["score"]), rank, hit)
            for rank, hit in enumerate(hits, start=1)
        ]
    else:  # Compatibility for lightweight catalog fakes used by downstream callers.
        ranked = catalog.ranked_search(query, limit=max(1, int(top_k)))
        results = [_compact_result(record, score, rank) for rank, (record, score) in enumerate(ranked, start=1)]
    selected_record: Mapping[str, Any] | None = ranked[0][0] if ranked else None
    selected = _record_quality(selected_record, by_id) if selected_record is not None else None
    anchors = [str(value).casefold() for value in (spec.get("anchor") or ())]
    overlaps = [_anchor_overlap(anchors, record) for record, _score in ranked]
    max_overlap = max(overlaps, default=0)
    top_overlap = overlaps[0] if overlaps else 0
    required_overlap = max(1, ceil(len(anchors) * 0.6)) if anchors else 1
    direct_results = [row for row in results if not row["is_reference_only"]]
    expected_domain = str(spec.get("domain", ""))
    semantic_relevant = _semantic_relevance(results, expected_domain)
    domains = [str(row["domain_code"]) for row in results]
    expected_domain_ranks = [int(row["rank"]) for row in results if str(row["domain_code"]) == expected_domain]
    concept_counts = Counter(str(row["concept_key"]) for row in results)
    duplicate_concepts = [
        {"concept_key": key, "count": count}
        for key, count in sorted(concept_counts.items())
        if count >= 3
    ]
    failures: dict[str, list[str]] = defaultdict(list)

    if not results or not direct_results or (max_overlap < required_overlap and not semantic_relevant):
        failures["search_miss"].append(
            f"no direct relevant result in top {top_k}; anchor overlap top/max={top_overlap}/{max_overlap}, required={required_overlap}"
        )
    if selected is not None:
        if selected["template_name"]:
            failures["weird_generated_name"].extend(selected["template_name_reasons"])
        if duplicate_concepts:
            failures["duplicate"].append(f"{duplicate_concepts[0]['count']} of top {top_k} results collapse to one family")
        if selected["generic_stage_name"]:
            failures["nonsense_generic_decomposition"].append(
                "selected record is a generated lifecycle-stage capability rather than a product-specific decomposition"
            )
        if expected_domain and (not expected_domain_ranks or str(results[0]["domain_code"]) != expected_domain):
            failures["bad_domain"].append(
                f"expected domain {expected_domain}, top result domain {results[0]['domain_code']}; expected ranks={expected_domain_ranks or 'none'}"
            )
        if selected["status_missing"] or selected["gap_missing_or_generic"] or selected["ladder_weak"]:
            weak_parts = []
            if selected["status_missing"]:
                weak_parts.append("missing status/basis")
            if selected["gap_missing_or_generic"]:
                weak_parts.append("missing or generic gap/import note")
            if selected["ladder_weak"]:
                weak_parts.append("short or repetitive making ladder")
            failures["useless_status_gap_ladder"].append("; ".join(weak_parts))
        if selected["missing_dependency_ids"] or selected["missing_navigation_ids"] or selected["self_references"]:
            failures["broken_dependency"].append(
                f"missing dependency/navigation refs={len(selected['missing_dependency_ids']) + len(selected['missing_navigation_ids'])}, self refs={len(selected['self_references'])}"
            )
        if (
            not selected["is_reference_only"]
            and not any(selected["navigation_counts"].values())
        ):
            failures["dead_end"].append("direct record has no upstream, downstream/unlock, related, or unlock links")
        if (
            selected["navigation_counts"].get("downstream", 0) == 0
            or selected["navigation_counts"].get("related", 0) == 0
        ):
            failures["weak_related_unlock"].append(
                f"navigation counts upstream/downstream/related={selected['navigation_counts'].get('upstream', 0)}/{selected['navigation_counts'].get('downstream', 0)}/{selected['navigation_counts'].get('related', 0)}"
            )
        if selected["assertive_unknown"]:
            failures["misleading_certainty"].append(
                f"{selected['status']} is backed by {selected['status_epistemic_class']} while its basis disclaims evidence"
            )

    return {
        "id": str(spec.get("id", "")),
        "query": query,
        "class": str(spec.get("class", "")),
        "expected_domain": expected_domain,
        "anchors": anchors,
        "top_k": int(top_k),
        "result_count": len(results),
        "selected_rank": 1 if results else None,
        "top_anchor_overlap": top_overlap,
        "max_anchor_overlap": max_overlap,
        "required_anchor_overlap": required_overlap,
        "semantic_relevant": semantic_relevant,
        "expected_domain_present": bool(expected_domain_ranks),
        "expected_domain_ranks": expected_domain_ranks,
        "top_result_domain": str(results[0]["domain_code"]) if results else None,
        "top_result_ids": [str(row["id"]) for row in results],
        "results": results,
        "selected": selected,
        "duplicate_concepts": duplicate_concepts,
        "failure_categories": [name for name in FAILURE_CATEGORIES if failures.get(name)],
        "failure_reasons": {name: failures[name] for name in FAILURE_CATEGORIES if failures.get(name)},
        "passed": not any(failures.values()),
    }


def _group_metrics(details: Sequence[Mapping[str, Any]], key: str) -> dict[str, Any]:
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for detail in details:
        groups[str(detail.get(key, ""))].append(detail)
    output: dict[str, Any] = {}
    for group, rows in sorted(groups.items()):
        counts = Counter(category for row in rows for category in row.get("failure_categories", ()))
        output[group] = {
            "query_count": len(rows),
            "queries_with_any_failure": sum(not bool(row.get("passed")) for row in rows),
            "failure_counts": {name: counts.get(name, 0) for name in FAILURE_CATEGORIES},
            "search_miss_count": counts.get("search_miss", 0),
            "top1_expected_domain_count": sum(row.get("top_result_domain") == row.get("expected_domain") for row in rows),
        }
    return output


def _metrics(
    battery: Mapping[str, Any],
    battery_digest: str,
    details: Sequence[Mapping[str, Any]],
    catalog: Any,
    *,
    phase: str,
) -> dict[str, Any]:
    failure_counts = Counter(category for row in details for category in row.get("failure_categories", ()))
    status_counts = Counter(
        str((row.get("selected") or {}).get("status", ""))
        for row in details
        if row.get("selected") is not None
    )
    selected_domain_counts = Counter(
        str((row.get("selected") or {}).get("domain_code", ""))
        for row in details
        if row.get("selected") is not None
    )
    result_count_values = [int(row.get("result_count", 0)) for row in details]
    relevant_count = sum(
        int(row.get("max_anchor_overlap", 0)) >= int(row.get("required_anchor_overlap", 1))
        or bool(row.get("semantic_relevant"))
        for row in details
    )
    top_domain_count = sum(row.get("top_result_domain") == row.get("expected_domain") for row in details)
    examples: dict[str, list[dict[str, Any]]] = {}
    for category in FAILURE_CATEGORIES:
        examples[category] = [
            {
                "id": row.get("id"),
                "query": row.get("query"),
                "top_result": (row.get("selected") or {}).get("canonical_name"),
                "reasons": (row.get("failure_reasons") or {}).get(category, []),
            }
            for row in details
            if category in (row.get("failure_categories") or [])
        ][:8]
    summary = catalog_summary(catalog)
    catalog_view = {
        "record_count": summary.get("record_count"),
        "direct_record_count": summary.get("direct_record_count"),
        "reference_record_count": summary.get("reference_record_count"),
        "domain_counts": summary.get("domain_counts"),
        "kind_counts": summary.get("kind_counts"),
        "status_counts": summary.get("status_counts"),
        "integrity": summary.get("integrity"),
    }
    phase_value = str(phase).strip().casefold()
    if phase_value not in {"baseline", "final"}:
        raise ValueError("phase must be 'baseline' or 'final'")
    return {
        "schema_version": METRICS_SCHEMA_VERSION,
        "runner_version": RUNNER_VERSION,
        "phase": phase_value,
        "battery_id": battery.get("battery_id"),
        "battery_digest_sha256": battery_digest,
        "query_set_frozen_before_baseline": True,
        "baseline_only": phase_value == "baseline",
        "fixes_applied": phase_value == "final",
        "top_k": int(battery.get("top_k", 10)),
        "query_count": len(details),
        "founder_query_count": sum(row.get("class") == "founder" for row in details),
        "unseen_query_count": sum(row.get("class") != "founder" for row in details),
        "domains_covered": sorted({str(row.get("expected_domain", "")) for row in details}),
        "queries_with_results": sum(bool(row.get("result_count")) for row in details),
        "queries_with_relevant_result": relevant_count,
        "relevant_result_rate": relevant_count / len(details) if details else 0.0,
        "top1_expected_domain_count": top_domain_count,
        "top1_expected_domain_rate": top_domain_count / len(details) if details else 0.0,
        "queries_with_any_failure": sum(not bool(row.get("passed")) for row in details),
        "failure_rate": sum(not bool(row.get("passed")) for row in details) / len(details) if details else 0.0,
        "failure_counts": {name: failure_counts.get(name, 0) for name in FAILURE_CATEGORIES},
        "selected_status_counts": dict(sorted(status_counts.items())),
        "selected_domain_counts": dict(sorted(selected_domain_counts.items())),
        "result_count_min": min(result_count_values, default=0),
        "result_count_max": max(result_count_values, default=0),
        "by_class": _group_metrics(details, "class"),
        "by_domain": _group_metrics(details, "expected_domain"),
        "failure_examples": examples,
        "catalog": catalog_view,
    }


def run_audit(
    battery_path: Path = DEFAULT_BATTERY,
    *,
    top_k: int | None = None,
    phase: str = "final",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run a deterministic in-memory audit and return metrics, findings."""

    battery, battery_digest = _load_battery(battery_path)
    effective_top_k = int(top_k if top_k is not None else battery.get("top_k", 10))
    if effective_top_k < 1:
        raise ValueError("top_k must be positive")
    catalog = get_catalog()
    by_id = catalog.by_id
    specs = [*(battery.get("founder_20") or []), *(battery.get("unseen_queries") or [])]
    details = [_run_query(spec, catalog, by_id, top_k=effective_top_k) for spec in specs]
    metrics = _metrics(battery, battery_digest, details, catalog, phase=phase)
    phase_value = str(phase).strip().casefold()
    if phase_value not in {"baseline", "final"}:
        raise ValueError("phase must be 'baseline' or 'final'")
    findings = {
        "schema_version": DETAILS_SCHEMA_VERSION,
        "runner_version": RUNNER_VERSION,
        "phase": phase_value,
        "battery_id": battery.get("battery_id"),
        "battery_digest_sha256": battery_digest,
        "query_set_frozen_before_baseline": True,
        "baseline_only": phase_value == "baseline",
        "fixes_applied": phase_value == "final",
        "top_k": effective_top_k,
        "queries": details,
    }
    return metrics, findings


def run_abuse_probe_audit(*, top_k: int = 3) -> dict[str, Any]:
    """Audit additional explicit probes without changing the frozen battery."""

    catalog = get_catalog()
    rows: list[dict[str, Any]] = []
    for spec in ABUSE_PROBES:
        hits = catalog.search_hits(str(spec["query"]), limit=max(1, int(top_k)))
        rows.append(
            {
                "id": spec["id"],
                "query": spec["query"],
                "expected_domain": spec["domain"],
                "results": [
                    {
                        "rank": rank,
                        "id": hit["record"]["id"],
                        "canonical_name": hit["record"].get("canonical_name", ""),
                        "display_name": hit["record"].get("display_name", ""),
                        "domain_code": hit["record"].get("domain_code", ""),
                        "family_key": hit.get("family_key", hit["record"].get("id", "")),
                        "match_type": hit.get("match_type", ""),
                        "matched_on": list(hit.get("matched_on", ())),
                        "score": int(hit.get("score", 0)),
                    }
                    for rank, hit in enumerate(hits, start=1)
                ],
            }
        )
    return {
        "schema_version": "india_v1.run2_abuse_probe_results.v1",
        "probe_count": len(rows),
        "top_k": max(1, int(top_k)),
        "probes": rows,
    }


def compare_metrics(
    baseline: Mapping[str, Any],
    final: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a compact deterministic baseline-vs-final delta artifact."""

    if baseline.get("battery_digest_sha256") != final.get("battery_digest_sha256"):
        raise ValueError("baseline and final metrics use different frozen batteries")
    failure_delta = {
        name: int((final.get("failure_counts") or {}).get(name, 0))
        - int((baseline.get("failure_counts") or {}).get(name, 0))
        for name in FAILURE_CATEGORIES
    }
    return {
        "schema_version": "india_v1.run2_baseline_vs_final.v1",
        "battery_id": final.get("battery_id"),
        "battery_digest_sha256": final.get("battery_digest_sha256"),
        "baseline_phase": baseline.get("phase", "baseline"),
        "final_phase": final.get("phase", "final"),
        "query_count": int(final.get("query_count", 0)),
        "baseline": {
            "relevant_result_rate": baseline.get("relevant_result_rate", 0.0),
            "top1_expected_domain_rate": baseline.get("top1_expected_domain_rate", 0.0),
            "failure_rate": baseline.get("failure_rate", 0.0),
            "failure_counts": baseline.get("failure_counts", {}),
        },
        "final": {
            "relevant_result_rate": final.get("relevant_result_rate", 0.0),
            "top1_expected_domain_rate": final.get("top1_expected_domain_rate", 0.0),
            "failure_rate": final.get("failure_rate", 0.0),
            "failure_counts": final.get("failure_counts", {}),
        },
        "delta": {
            "relevant_result_rate": float(final.get("relevant_result_rate", 0.0)) - float(baseline.get("relevant_result_rate", 0.0)),
            "top1_expected_domain_rate": float(final.get("top1_expected_domain_rate", 0.0)) - float(baseline.get("top1_expected_domain_rate", 0.0)),
            "failure_rate": float(final.get("failure_rate", 0.0)) - float(baseline.get("failure_rate", 0.0)),
            "failure_counts": failure_delta,
        },
    }


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--battery", type=Path, default=DEFAULT_BATTERY)
    parser.add_argument("--phase", choices=("baseline", "final"), default="final")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--details-output", type=Path, default=None)
    parser.add_argument("--compare-to", type=Path, default=None, help="baseline metrics JSON to compare with a final run")
    parser.add_argument("--comparison-output", type=Path, default=DEFAULT_COMPARISON_OUTPUT)
    parser.add_argument("--abuse-output", type=Path, default=None, help="write compact results for the separate abuse-probe set")
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--no-write", action="store_true", help="print metrics without writing output files")
    args = parser.parse_args(argv)
    metrics, findings = run_audit(args.battery, top_k=args.top_k, phase=args.phase)
    output = args.output or (DEFAULT_OUTPUT if args.phase == "baseline" else DEFAULT_FINAL_OUTPUT)
    details_output = args.details_output or (DEFAULT_DETAILS_OUTPUT if args.phase == "baseline" else DEFAULT_FINAL_DETAILS_OUTPUT)
    if not args.no_write:
        _write_json(output, metrics)
        _write_json(details_output, findings)
        if args.compare_to is not None:
            baseline = json.loads(args.compare_to.read_text(encoding="utf-8"))
            _write_json(args.comparison_output, compare_metrics(baseline, metrics))
        if args.abuse_output is not None:
            _write_json(args.abuse_output, run_abuse_probe_audit(top_k=3))
    print(json.dumps(metrics, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
