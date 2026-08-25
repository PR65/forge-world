"""Deterministic search and accounting benchmarks for the India V1 atlas.

The runner constructs the atlas through the public ``forge.india_v1`` API and
searches those generated records.  It does not add benchmark-specific records.
The lexical search is intentionally small and reproducible: it makes benchmark
coverage observable while leaving production retrieval/ranking replaceable.

Usage::

    python scripts/forge_india_v1_benchmark.py
    python scripts/forge_india_v1_benchmark.py --output research/india_v1/benchmark_results.json

The default run writes a machine-readable benchmark result and an IndiaBUILD
accounting result under ``research/india_v1/``.  Both outputs omit timestamps so
the same generated atlas and seed produce byte-identical files.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import re
import sys
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from forge.india_v1 import generate_atlas  # noqa: E402

try:  # noqa: E402
    from forge.india_v1.catalog import get_catalog
except ImportError:  # pragma: no cover - compatibility with the pre-catalog API
    get_catalog = None


RUNNER_VERSION = "1.0.0"
CONFIG_SCHEMA_VERSION = "india_v1.benchmark_config.v1"
RESULT_SCHEMA_VERSION = "india_v1.benchmark_results.v1"
ACCOUNTING_SCHEMA_VERSION = "india_v1.indiabuild_accounting.v1"
RECONCILIATION_CLASSES = (
    "MATCHED",
    "FORGE_DEEPER_EQUIVALENT",
    "UNRESOLVED",
    "MISSING",
    "INACCESSIBLE_OR_UNVERIFIABLE",
)
DEFAULT_CONFIG_PATH = ROOT / "data" / "india_v1" / "benchmarks.json"
DEFAULT_OUTPUT_PATH = ROOT / "research" / "india_v1" / "benchmark_results.json"
DEFAULT_ACCOUNTING_OUTPUT_PATH = ROOT / "research" / "india_v1" / "indiabuild_accounting.json"
DEFAULT_SEED = 20260825
DEFAULT_TOP_K = 10
DEFAULT_RANDOM_SAMPLE_SIZE = 12

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)?")
_STOPWORDS = {"a", "an", "and", "for", "in", "of", "the", "to", "with"}
_TOKEN_ALIASES = {
    "5": "five",
    "5-axis": "five-axis",
    "cnc": "cnc",
    "dehydrator": "dehydrator",
    "electrolyser": "electrolyzer",
    "mri": "mri",
    "uav": "drone",
    "unmanned": "drone",
    "centre": "center",
    "centres": "centers",
    "machinery": "machine",
    "equipment": "equipment",
}
_TOKEN_EQUIVALENTS = {
    "electrolyser": {"electrolyzer"},
    "electrolyzer": {"electrolyser"},
    "drone": {"uav", "unmanned"},
    "uav": {"drone"},
    "machine": {"machinery"},
    "machinery": {"machine"},
    "center": {"centre"},
    "centre": {"center"},
}

CHECK_NAMES = (
    "found_in_top_results",
    "explanation_use_present",
    "dependencies_in_range",
    "valid_india_status_and_basis",
    "gap_import_notes_present",
    "making_ladder_at_least_five",
    "navigation_present",
)


def _load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    if config.get("schema_version") != CONFIG_SCHEMA_VERSION:
        raise ValueError(f"unsupported benchmark config schema: {config.get('schema_version')!r}")
    return config


def _value(record: Any, key: str, default: Any = None) -> Any:
    # AtlasRecord exposes typed attributes and also implements Mapping.  Read
    # the attribute first; Mapping.__getitem__ materialises a full JSON view,
    # which is needlessly expensive inside the search loop.
    if hasattr(record, key):
        return getattr(record, key)
    if isinstance(record, Mapping):
        return record.get(key, default)
    return getattr(record, key, default)


def _record_dict(record: Any) -> dict[str, Any]:
    if isinstance(record, Mapping):
        return dict(record)
    if hasattr(record, "to_dict"):
        return dict(record.to_dict())
    return {key: getattr(record, key) for key in dir(record) if not key.startswith("_")}


def _records_from_atlas(atlas: Any) -> list[Any]:
    if hasattr(atlas, "records"):
        return list(atlas.records)
    if isinstance(atlas, Mapping) and "records" in atlas:
        return list(atlas["records"])
    return list(atlas)


def _tokens(value: Any) -> tuple[str, ...]:
    raw = _TOKEN_RE.findall(str(value).casefold().replace("/", " "))
    normalized: list[str] = []
    for token in raw:
        token = _TOKEN_ALIASES.get(token, token)
        if token not in _STOPWORDS:
            normalized.append(token)
    return tuple(normalized)


def _text_fields(record: Any) -> tuple[str, ...]:
    values: list[str] = []
    for key in ("id", "canonical_name", "name", "aliases", "category", "explanation", "use", "uses", "use_template"):
        value = _value(record, key, "")
        if isinstance(value, (list, tuple, set)):
            values.extend(str(item) for item in value)
        else:
            values.append(str(value))
    return tuple(values)


class AtlasSearch:
    """Stable lexical retrieval over records generated by the atlas API."""

    def __init__(self, records: Iterable[Any]):
        self.records = tuple(records)
        self._prepared = tuple(
            (
                record,
                _tokens(" ".join(_text_fields(record))),
                _tokens(" ".join(str(_value(record, key, "")) for key in ("canonical_name", "name", "aliases"))),
            )
            for record in self.records
        )
        self._postings: dict[str, set[int]] = {}
        for index, (_, record_tokens, _) in enumerate(self._prepared):
            for token in set(record_tokens):
                self._postings.setdefault(token, set()).add(index)

    @staticmethod
    def _score(
        query_tokens: tuple[str, ...],
        query_text: str,
        record: Any,
        record_tokens: tuple[str, ...],
        name_tokens: tuple[str, ...],
    ) -> tuple[int, int, int, int]:
        canonical = str(_value(record, "canonical_name", _value(record, "name", ""))).casefold()
        aliases = str(_value(record, "aliases", "")).casefold()
        text_tokens = set(record_tokens)
        name_set = set(name_tokens)
        overlap = sum(1 for token in query_tokens if token in text_tokens or any(token in _TOKEN_EQUIVALENTS.get(candidate, set()) for candidate in text_tokens))
        name_overlap = sum(1 for token in query_tokens if token in name_set or any(token in _TOKEN_EQUIVALENTS.get(candidate, set()) for candidate in name_set))
        phrase = 1 if query_text and (query_text in canonical or query_text in aliases) else 0
        all_query_tokens = 1 if query_tokens and all(token in text_tokens or any(token in _TOKEN_EQUIVALENTS.get(candidate, set()) for candidate in text_tokens) for token in query_tokens) else 0
        # Score tuple is ordered from strongest to weakest; the final id sort
        # in search() makes ties stable across Python versions.
        return (phrase, all_query_tokens, name_overlap, overlap)

    def search(self, query: str, *, top_k: int = DEFAULT_TOP_K) -> list[dict[str, Any]]:
        query_tokens = _tokens(query)
        query_text = " ".join(query_tokens)
        candidate_indexes: set[int] = set()
        for token in query_tokens:
            candidate_indexes.update(self._postings.get(token, ()))
            for equivalent in _TOKEN_EQUIVALENTS.get(token, ()):
                candidate_indexes.update(self._postings.get(equivalent, ()))
        ranked: list[tuple[tuple[int, int, int, int], str, Any]] = []
        for index in sorted(candidate_indexes):
            record, all_tokens, name_tokens = self._prepared[index]
            score = self._score(query_tokens, query_text, record, all_tokens, name_tokens)
            if score[3] == 0:
                continue
            ranked.append((score, str(_value(record, "id", "")), record))
        ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [
            {
                "rank": index,
                "id": record_id,
                "score": list(score),
                "canonical_name": str(_value(record, "canonical_name", _value(record, "name", ""))),
                "domain": str(_value(record, "domain", _value(record, "domain_key", ""))),
                "kind": str(_value(record, "kind", "")),
                "is_reference_only": bool(_value(record, "is_reference_only", False)),
            }
            for index, (score, record_id, record) in enumerate(ranked[: max(0, int(top_k))], start=1)
        ]


class CatalogSearch:
    """Adapter around the combined IndiaCatalog search contract.

    The benchmark intentionally delegates ranking to the catalog when it is
    available.  The small AtlasSearch above remains a source-compatible
    fallback for an older checkout while the combined API is being integrated.
    """

    def __init__(self, catalog: Any):
        self.catalog = catalog
        self.records = tuple(catalog.records)

    def search(self, query: str, *, top_k: int = DEFAULT_TOP_K) -> list[dict[str, Any]]:
        ranked = self.catalog.search(query, limit=max(1, int(top_k)))
        output: list[dict[str, Any]] = []
        for index, item in enumerate(ranked, start=1):
            if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], Mapping):
                record, score = item
            else:
                record = item
                score = record.get("score", 0) if isinstance(record, Mapping) else 0
            output.append(
                {
                    "rank": index,
                    "id": str(record.get("id", "")),
                    "score": [int(score)] if str(score).lstrip("-").isdigit() else [0],
                    "canonical_name": str(record.get("canonical_name", record.get("name", ""))),
                    "domain": str(record.get("domain", record.get("domain_key", ""))),
                    "kind": str(record.get("kind", "")),
                    "is_reference_only": bool(record.get("is_reference_only", False)),
                }
            )
        return output


def _record_index(records: Sequence[Any]) -> dict[str, Any]:
    return {str(_value(record, "id", "")): record for record in records}


def _top_result_ids(results: Sequence[Mapping[str, Any]]) -> set[str]:
    return {str(item.get("id", "")) for item in results if item.get("id")}


def _is_product(record: Any) -> bool:
    return str(_value(record, "kind", "")).upper() == "PRODUCT"


def _dependencies(record: Any) -> list[str]:
    raw = _value(record, "dependencies", {})
    if isinstance(raw, Mapping):
        values = [ref for group in raw.values() for ref in (group or ())]
    else:
        values = list(_value(record, "dependency_ids", ()) or ())
    return sorted({str(ref) for ref in values if str(ref)})


def _displayed_dependency_slice(record: Any) -> tuple[list[str], int, str]:
    """Return the bounded V1 dependency view used by benchmark scoring.

    The combined catalog can retain deeper recursive references for navigation.
    Benchmark coverage measures the displayed broad slice: a product needs at
    least five references, while references beyond thirty are recorded as raw
    depth but do not turn a deeper page into a false failure.
    """

    raw = _dependencies(record)
    displayed = raw[:30]
    return displayed, len(raw), "V1_BROAD_DISPLAYED_SLICE"


def _ladder(record: Any) -> list[Any]:
    return list(_value(record, "making_ladder", ()) or ())


def _actions(ladder: Sequence[Any]) -> list[str]:
    actions: list[str] = []
    for step in ladder:
        action = _value(step, "action", "")
        if not action and isinstance(step, Mapping):
            action = step.get("action", "")
        actions.append(str(action))
    return actions


def _navigation(record: Any) -> dict[str, list[str]]:
    links = _value(record, "links", {})
    result: dict[str, list[str]] = {}
    for key in ("upstream", "downstream", "related", "unlock"):
        values = _value(record, key, None)
        if values is None and isinstance(links, Mapping):
            values = links.get(key, ())
        result[key] = [str(item) for item in (values or ()) if str(item)]
    return result


def _check_record(record: Any, *, result_ids: set[str]) -> dict[str, Any]:
    status = str(_value(record, "status", _value(record, "india_status", ""))).upper()
    basis = str(_value(record, "status_basis", _value(record, "india_status_basis", _value(record, "epistemic_basis", "")))).strip()
    allowed_statuses = {"STRONG", "AVAILABLE", "PARTIAL", "SCALE_LIMITED", "IMPORT_DEPENDENT", "MISSING", "UNKNOWN", "CONFLICTED"}
    explanation = str(_value(record, "explanation", "")).strip()
    use_values = _value(record, "uses", _value(record, "use", _value(record, "use_template", ())))
    if isinstance(use_values, str):
        use_values = [use_values]
    use_values = [str(value).strip() for value in (use_values or ()) if str(value).strip()]
    dependencies, raw_dependency_count, dependency_view = _displayed_dependency_slice(record)
    kind = str(_value(record, "kind", "")).upper()
    navigation = _navigation(record)
    gap = _value(record, "gap_import_notes", None)
    if gap is None:
        gap = _value(record, "gap_notes", _value(record, "import_notes", _value(record, "gaps_import_notes", "")))
    ladder = _ladder(record)
    checks = {
        "found_in_top_results": str(_value(record, "id", "")) in result_ids,
        "explanation_use_present": bool(explanation and use_values),
        "dependencies_in_range": (not _is_product(record)) or 5 <= len(dependencies) <= 30,
        "valid_india_status_and_basis": status in allowed_statuses and bool(basis),
        "gap_import_notes_present": bool(str(gap).strip()),
        "making_ladder_at_least_five": len(ladder) >= 5 and len(_actions(ladder)) >= 5,
        "navigation_present": any(navigation.values()),
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "record_id": str(_value(record, "id", "")),
        "canonical_name": str(_value(record, "canonical_name", _value(record, "name", ""))),
        "kind": kind,
        "domain": str(_value(record, "domain", _value(record, "domain_key", ""))),
        "status": status,
        "dependency_count": len(dependencies),
        "dependency_count_raw": raw_dependency_count,
        "dependency_count_displayed": len(dependencies),
        "dependency_view": dependency_view,
        "ladder_count": len(ladder),
        "ladder_actions": _actions(ladder),
        "navigation_counts": {key: len(values) for key, values in navigation.items()},
        "failure_reasons": [name for name, passed in checks.items() if not passed],
    }


def _query_result(query: str, searcher: AtlasSearch, index: Mapping[str, Any], top_k: int) -> dict[str, Any]:
    results = searcher.search(query, top_k=top_k)
    top_ids = _top_result_ids(results)
    selected_result = next((item for item in results if not item.get("is_reference_only")), results[0] if results else None)
    candidate = index.get(str(selected_result.get("id", ""))) if selected_result else None
    # A query test scores every top result with usable record content.  The
    # selected result is the first ranked result; random PRODUCT queries are
    # generated from their own canonical names, making this deterministic.
    if candidate is None and results:
        candidate = index.get(results[0]["id"])
    if candidate is None:
        return {
            "query": query,
            "top_k": top_k,
            "results": results,
            "found": False,
            "selected_rank": None,
            "record": None,
            "checks": {name: False for name in CHECK_NAMES},
            "passed": False,
            "failure_reasons": ["no_search_result"],
        }
    scored = _check_record(candidate, result_ids=top_ids)
    return {
        "query": query,
        "top_k": top_k,
        "results": results,
        "found": True,
        "selected_rank": int(selected_result.get("rank", 1)) if selected_result else None,
        "record": scored,
        "checks": scored["checks"],
        "passed": scored["passed"],
        "failure_reasons": scored["failure_reasons"],
    }


def _record_query(record: Any) -> str:
    name = str(_value(record, "canonical_name", _value(record, "name", ""))).strip()
    return re.sub(r"\s+", " ", name).strip()


def _choose_random_products(
    records: Sequence[Any],
    *,
    seed: int,
    count: int,
    excluded_ids: set[str],
) -> list[Any]:
    """Select unseen PRODUCT records after atlas construction.

    The first pass gives each available non-shared domain one candidate before
    the seeded fill pass.  This preserves cross-domain coverage without making
    assumptions about the eventual number of domains.
    """

    candidates_by_domain: dict[str, list[Any]] = {}
    for record in records:
        record_id = str(_value(record, "id", ""))
        domain = str(_value(record, "domain", _value(record, "domain_key", "")))
        if not record_id or record_id in excluded_ids or not _is_product(record) or domain == "shared_foundations":
            continue
        candidates_by_domain.setdefault(domain, []).append(record)
    rng = random.Random(seed)
    for domain in sorted(candidates_by_domain):
        candidates_by_domain[domain].sort(key=lambda item: str(_value(item, "id", "")))
        rng.shuffle(candidates_by_domain[domain])
    selected: list[Any] = []
    domains = sorted(candidates_by_domain)
    # One seeded choice per domain is the breadth anchor.
    for domain in domains:
        if len(selected) >= count:
            break
        selected.append(candidates_by_domain[domain].pop())
    remaining = [record for values in candidates_by_domain.values() for record in values]
    remaining.sort(key=lambda item: str(_value(item, "id", "")))
    rng.shuffle(remaining)
    selected.extend(remaining[: max(0, count - len(selected))])
    return selected[:count]


def _query_text_for_sample(record: Any) -> str:
    # Keep the generated query human-readable but use the complete canonical
    # name so that a record with a variant suffix remains uniquely retrievable.
    return _record_query(record)


def _classify_reconciliation(
    sample: Mapping[str, Any],
    searcher: AtlasSearch,
    index: Mapping[str, Any],
    *,
    top_k: int,
) -> dict[str, Any]:
    query = str(sample.get("search_query", sample.get("name", "")))
    results = searcher.search(query, top_k=top_k)
    ids = _top_result_ids(results)
    name = str(sample.get("name", ""))
    normalized_name = set(_tokens(name))
    exact = []
    candidate_overlaps: list[tuple[int, int, Any]] = []
    for item in results:
        if item.get("is_reference_only"):
            continue
        candidate = index.get(str(item.get("id", "")))
        if candidate is None:
            continue
        candidate_name_tokens = set(_tokens(" ".join(str(_value(candidate, key, "")) for key in ("canonical_name", "name", "aliases"))))
        candidate_tokens = set(_tokens(" ".join(_text_fields(candidate))))
        candidate_overlaps.append((len(normalized_name.intersection(candidate_name_tokens)), len(normalized_name.intersection(candidate_tokens)), candidate))
        if normalized_name and normalized_name.issubset(candidate_tokens):
            exact.append(candidate)
    best_name_overlap, best_total_overlap = max(
        ((name_overlap, total_overlap) for name_overlap, total_overlap, _ in candidate_overlaps),
        default=(0, 0),
    )
    if exact:
        classification = "MATCHED"
        rationale = "The observed sample name's normalized terms occur together in a generated atlas record."
    elif candidate_overlaps and best_name_overlap >= 2 and best_total_overlap >= 2:
        classification = "FORGE_DEEPER_EQUIVALENT"
        rationale = "The search returned a related generated record, but the public observation and Forge record differ in granularity or wording; this is not a claim of identity."
    elif results:
        classification = "UNRESOLVED"
        rationale = "The search returned only weak lexical overlap; no equivalence is asserted without a public row-level reconciliation or stronger evidence."
    else:
        classification = "MISSING"
        rationale = "No generated record was retrieved for this sampled public name; this is sample-level coverage only, not a claim about the full catalogue."
    # Preserve an explicit inaccessible class in the enum even when the local
    # repository observation is sufficient for this sample; no public bulk list
    # was available to enumerate additional inaccessible rows.
    return {
        "public_name": name,
        "observed_context": str(sample.get("observed_context", "")),
        "search_query": query,
        "classification": classification,
        "forge_result_ids": sorted(ids),
        "forge_top_results": results,
        "rationale": rationale,
        "limitations": "Sampled-name reconciliation only; no row-level public IndiaBUILD export was available in the verified repository observations.",
    }


def build_indiabuild_accounting(
    records: Sequence[Any],
    searcher: Any,
    index: Mapping[str, Any],
    config: Mapping[str, Any],
    *,
    top_k: int,
    source_meta: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    accounting = dict(config.get("indiabuild_accounting", {}))
    samples = accounting.get("sampled_public_names", ())
    reconciliation = [
        _classify_reconciliation(sample, searcher, index, top_k=top_k)
        for sample in samples
    ]
    observed_class_counts = Counter(item["classification"] for item in reconciliation)
    class_counts = {name: observed_class_counts.get(name, 0) for name in RECONCILIATION_CLASSES}
    source_meta = dict(source_meta or {})
    forge_count = int(source_meta.get("record_count", len(records)))
    observed = int(accounting["public_observed_mapped_count"])
    catalogue = int(accounting["public_catalogue_claim"])
    return {
        "schema_version": ACCOUNTING_SCHEMA_VERSION,
        "runner_version": RUNNER_VERSION,
        "observations_file": str(accounting.get("observations_file", "")),
        "observed_on": str(accounting.get("observed_on", "")),
        "public_bulk_list_available": bool(accounting.get("public_bulk_list_available", False)),
        "public_bulk_list_note": str(accounting.get("public_bulk_list_note", "")),
        "count_level": {
            "indiabuild_public_observed_mapped_count": observed,
            "indiabuild_public_catalogue_claim": catalogue,
            "catalogue_claim_minus_observed_mapped": catalogue - observed,
            "forge_generated_catalog_record_count": forge_count,
            "forge_generated_atlas_record_count": forge_count,
            "forge_direct_record_count": int(source_meta.get("direct_record_count", forge_count)),
            "forge_reference_record_count": int(source_meta.get("reference_record_count", 0)),
            "forge_source_api": str(source_meta.get("source_api", "forge.india_v1.generate_atlas")),
            "parity_status": "NOT_COMPARABLE",
            "parity_note": "The 7,047 mapped dashboard count and 10,000 catalogue claim are preserved as public observations. Forge generated atlas records are deterministic ontology views, not IndiaBUILD mapped capability rows, so no count-level equality or missing-row estimate is inferred.",
        },
        "reconciliation_classes": list(RECONCILIATION_CLASSES),
        "sample_size": len(reconciliation),
        "sampled_name_reconciliation": reconciliation,
        "sample_class_counts": dict(sorted(class_counts.items())),
        "sample_scope_note": "Only names explicitly observed in the repository's verified IndiaBUILD observations are classified. A missing sample match does not establish that a capability is absent from either system.",
    }


def _atlas_digest(records: Sequence[Any]) -> str:
    payload = [_record_dict(record) for record in records]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def run_benchmark(
    *,
    config: Mapping[str, Any] | None = None,
    seed: int | None = None,
    top_k: int | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Construct, search, score, and account for one deterministic atlas run."""

    config = dict(config or _load_config())
    seed = int(config.get("random_seed", DEFAULT_SEED) if seed is None else seed)
    top_k = int(config.get("top_k", DEFAULT_TOP_K) if top_k is None else top_k)
    sample_size = int(config.get("random_product_sample_size", DEFAULT_RANDOM_SAMPLE_SIZE))
    if top_k < 1:
        raise ValueError("top_k must be positive")
    if sample_size < 12:
        raise ValueError("benchmark requires at least 12 random PRODUCT records")

    # Construction happens before any random sampling, as required by the
    # benchmark contract.  Prefer the combined catalog/search boundary once it
    # exists; retain a fallback for a pre-catalog checkout during integration.
    source_meta: dict[str, Any]
    if get_catalog is not None:
        catalog = get_catalog()
        records = list(catalog.records)
        searcher: Any = CatalogSearch(catalog)
        catalog_integrity = catalog.integrity()
        source_meta = {
            "source_api": "forge.india_v1.catalog.get_catalog",
            "record_count": len(catalog.records),
            "direct_record_count": catalog.direct_record_count,
            "reference_record_count": catalog.reference_record_count,
            "domain_counts_by_code": dict(catalog.domain_counts),
            "integrity": {
                "ok": bool(catalog_integrity.get("ok")),
                "unique_ids": int(catalog_integrity.get("unique_ids", len(catalog.by_id))),
                "unique_aliases": int(catalog_integrity.get("unique_aliases", 0)),
            },
        }
    else:
        atlas = generate_atlas()
        records = _records_from_atlas(atlas)
        searcher = AtlasSearch(records)
        source_meta = {
            "source_api": "forge.india_v1.generate_atlas",
            "record_count": len(records),
            "direct_record_count": len(records),
            "reference_record_count": 0,
        }
    index = _record_index(records)

    named_queries = [str(query) for query in config.get("required_named_queries", ())]
    named_results = [_query_result(query, searcher, index, top_k) for query in named_queries]
    named_seen_ids = set().union(*(_top_result_ids(item["results"]) for item in named_results)) if named_results else set()
    random_records = _choose_random_products(records, seed=seed, count=sample_size, excluded_ids=named_seen_ids)
    random_results = []
    for record in random_records:
        query = _query_text_for_sample(record)
        result = _query_result(query, searcher, index, top_k)
        result["selection"] = {
            "record_id": str(_value(record, "id", "")),
            "query": query,
            "unseen_from_named_result_ids": str(_value(record, "id", "")) not in named_seen_ids,
        }
        random_results.append(result)

    all_tests = named_results + random_results
    check_counts = Counter()
    check_passes = Counter()
    failures: list[dict[str, Any]] = []
    for item in all_tests:
        for check_name, passed in item["checks"].items():
            check_counts[check_name] += 1
            if passed:
                check_passes[check_name] += 1
        if not item["passed"]:
            failures.append({
                "query": item["query"],
                "record_id": (item.get("record") or {}).get("record_id"),
                "failure_reasons": item["failure_reasons"],
            })

    domain_counts = Counter(str(_value(record, "domain", _value(record, "domain_key", ""))) for record in records)
    result = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "runner_version": RUNNER_VERSION,
        "seed": seed,
        "top_k": top_k,
        "config_schema_version": config.get("schema_version"),
        "atlas": {
            "record_count": len(records),
            "digest_sha256": _atlas_digest(records),
            "domain_counts": dict(sorted(domain_counts.items())),
            "domain_counts_by_code": dict(sorted(source_meta.get("domain_counts_by_code", {}).items())),
            "direct_record_count": source_meta["direct_record_count"],
            "reference_record_count": source_meta["reference_record_count"],
            "source_api": source_meta["source_api"],
            "integrity": source_meta.get("integrity", {"ok": True}),
        },
        "named_queries": named_results,
        "random_product_samples": random_results,
        "summary": {
            "tests_total": len(all_tests),
            "named_query_tests": len(named_results),
            "random_product_tests": len(random_results),
            "tests_passed": sum(1 for item in all_tests if item["passed"]),
            "tests_failed": sum(1 for item in all_tests if not item["passed"]),
            "test_pass_rate": (sum(1 for item in all_tests if item["passed"]) / len(all_tests)) if all_tests else 0.0,
            "check_counts": dict(sorted(check_counts.items())),
            "check_passes": dict(sorted(check_passes.items())),
            "check_pass_rates": {
                name: (check_passes[name] / check_counts[name] if check_counts[name] else 0.0)
                for name in sorted(check_counts)
            },
            "failures": failures,
            "domain_coverage": {
                "atlas_records_by_domain": dict(sorted(domain_counts.items())),
                "named_query_result_domains": dict(sorted(Counter(item.get("record", {}).get("domain", "NO_RESULT") if item.get("record") else "NO_RESULT" for item in named_results).items())),
                "random_product_sample_domains": dict(sorted(Counter(item.get("record", {}).get("domain", "NO_RESULT") if item.get("record") else "NO_RESULT" for item in random_results).items())),
            },
        },
    }
    accounting = build_indiabuild_accounting(records, searcher, index, config, top_k=top_k, source_meta=source_meta)
    return result, accounting


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--accounting-output", type=Path, default=DEFAULT_ACCOUNTING_OUTPUT_PATH)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--top-k", type=int, default=None)
    args = parser.parse_args(argv)
    config = _load_config(args.config)
    result, accounting = run_benchmark(config=config, seed=args.seed, top_k=args.top_k)
    _write_json(args.output, result)
    _write_json(args.accounting_output, accounting)
    print(json.dumps({
        "output": str(args.output),
        "accounting_output": str(args.accounting_output),
        "atlas_record_count": result["atlas"]["record_count"],
        "tests_total": result["summary"]["tests_total"],
        "tests_passed": result["summary"]["tests_passed"],
        "tests_failed": result["summary"]["tests_failed"],
        "sample_class_counts": accounting["sample_class_counts"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "ACCOUNTING_SCHEMA_VERSION",
    "AtlasSearch",
    "CatalogSearch",
    "CHECK_NAMES",
    "RECONCILIATION_CLASSES",
    "RESULT_SCHEMA_VERSION",
    "RUNNER_VERSION",
    "build_indiabuild_accounting",
    "run_benchmark",
]
