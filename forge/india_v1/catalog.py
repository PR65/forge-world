"""Cached cross-domain catalog and read indexes for the India V1 API.

The four-domain core atlas and the two breadth data packs were authored at
different times and consequently expose slightly different field names.  This
module is the deliberately small adapter boundary: it normalizes the three
packs into one read model, keeps source epistemics intact, and builds indexes
once per process.  It does not assert that a curated ontology node is a
qualified supplier or an effective production capacity.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
import importlib.util
import re
from pathlib import Path
import sys
import unicodedata
from typing import Any, Iterable

from .generator import generate_atlas

try:
    from data.india_v1 import domains_05_08 as _domains_05_08
    from data.india_v1 import domains_09_12 as _domains_09_12
except ModuleNotFoundError as exc:  # pragma: no cover - repository imports are the normal path
    if not str(exc).startswith("No module named 'data'"):
        raise
    # ``pytest`` entrypoints can omit the repository root from ``sys.path``.
    # Load the sibling packs by their stable source-local paths, matching the
    # fallback already used by the 01-04 generator.
    _DATA_ROOT = Path(__file__).resolve().parents[2] / "data" / "india_v1"

    def _load_pack_module(name: str, path: Path):
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise ModuleNotFoundError(f"cannot load India V1 data pack at {path}") from exc
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    _domains_05_08 = _load_pack_module("_forge_india_v1_domains_05_08", _DATA_ROOT / "domains_05_08.py")
    _domains_09_12 = _load_pack_module("_forge_india_v1_domains_09_12", _DATA_ROOT / "domains_09_12.py")


DEP_GROUPS = ("systems", "processes", "materials", "equipment", "capabilities")
KINDS = ("PRODUCT", "CAPABILITY", "PROCESS", "MATERIAL", "EQUIPMENT")
STATUSES = (
    "STRONG",
    "AVAILABLE",
    "PARTIAL",
    "SCALE_LIMITED",
    "IMPORT_DEPENDENT",
    "MISSING",
    "UNKNOWN",
    "CONFLICTED",
)
EPISTEMIC_CLASSES = (
    "MEASURED",
    "REPORTED",
    "DERIVED",
    "ESTIMATED",
    "MODELLED",
    "ASSUMPTION",
    "SCENARIO",
    "UNKNOWN",
    "CONFLICTED",
)
DEPTH_PROFILE = "V1_BROAD"

DOMAIN_META: dict[str, dict[str, str]] = {
    "01": {"key": "aerospace_space", "name": "Aerospace & Space"},
    "02": {"key": "defense_strategic_manufacturing", "name": "Defense & Strategic Manufacturing"},
    "03": {"key": "energy_nuclear", "name": "Energy & Nuclear"},
    "04": {"key": "electronics_semiconductors_computing", "name": "Electronics, Semiconductors & Computing"},
    "05": {"key": "machines_robotics_automation", "name": "Machines, Robotics, and Industrial Automation"},
    "06": {"key": "materials_metals_chemicals_process", "name": "Materials, Metals, Chemicals, and Process Industries"},
    "07": {"key": "medical_scientific_pharma_biotech_equipment", "name": "Medical, Scientific, Pharma, and Biotech Equipment"},
    "08": {"key": "food_agriculture_biological_production", "name": "Food, Agriculture, and Biological Production Systems"},
    "09": {"key": "09_transport_mobility", "name": "Transport & Mobility"},
    "10": {"key": "10_infrastructure_construction_heavy_equipment", "name": "Infrastructure, Construction, and Heavy Equipment"},
    "11": {"key": "11_consumer_textile_packaging_general_manufacturing", "name": "Consumer, Textile, Packaging, and General Manufacturing"},
    "12": {"key": "12_foundational_industrial_capabilities", "name": "Foundational Industrial Capabilities"},
}
DOMAIN_ORDER = tuple(DOMAIN_META)

_STATUS_MAP = {
    "STRONG / AVAILABLE IN INDIA": "AVAILABLE",
    "AVAILABLE IN INDIA": "AVAILABLE",
    "PARTIAL / SCALE-LIMITED": "SCALE_LIMITED",
    "SPECIFICATION GAP": "PARTIAL",
    "QUALIFICATION GAP": "PARTIAL",
    "CAPACITY GAP": "SCALE_LIMITED",
    "IMPORT-DEPENDENT": "IMPORT_DEPENDENT",
    "MISSING / NO EVIDENCED DOMESTIC CAPABILITY": "MISSING",
    "INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN": "PARTIAL",
    "INDIA_PRESENT_BUT_DEPTH_UNKNOWN": "PARTIAL",
    "INDIA_EMERGING_OR_LIMITED": "SCALE_LIMITED",
    "INDIA_IMPORT_DEPENDENT_OR_QUALIFICATION_UNKNOWN": "IMPORT_DEPENDENT",
    "INDIA_ASSEMBLY_OR_SERVICE_BASE_UNKNOWN": "PARTIAL",
}

_KIND_MAP = {
    "FINISHED_PRODUCT": "PRODUCT",
    "PRODUCT": "PRODUCT",
    "COMPONENT": "PRODUCT",
    "MACHINE": "EQUIPMENT",
    "HEAVY_EQUIPMENT": "EQUIPMENT",
    "EQUIPMENT": "EQUIPMENT",
    "INSTRUMENT": "EQUIPMENT",
    "MATERIAL": "MATERIAL",
    "CHEMICAL": "MATERIAL",
    "CAPABILITY": "CAPABILITY",
    "UTILITY_CAPABILITY": "CAPABILITY",
    "SERVICE_CAPABILITY": "CAPABILITY",
    "PROCESS_CAPABILITY": "PROCESS",
    "PROCESS": "PROCESS",
}

_GROUP_MAP = {
    "system": "systems",
    "systems": "systems",
    "infrastructure": "systems",
    "utility": "systems",
    "utilities": "systems",
    "process": "processes",
    "processes": "processes",
    "proc": "processes",
    "material": "materials",
    "materials": "materials",
    "mat": "materials",
    "equipment": "equipment",
    "equipments": "equipment",
    "machine": "equipment",
    "machines": "equipment",
    "capability": "capabilities",
    "capabilities": "capabilities",
    "cap": "capabilities",
    "design": "capabilities",
    "quality": "capabilities",
    "component": "capabilities",
    "components": "capabilities",
    "service": "capabilities",
}

_REF_PREFIX_MAP = {
    "system": "system",
    "systems": "system",
    "util": "system",
    "utility": "system",
    "material": "material",
    "materials": "material",
    "mat": "material",
    "process": "process",
    "processes": "process",
    "proc": "process",
    "equipment": "equipment",
    "equip": "equipment",
    "capability": "capability",
    "capabilities": "capability",
    "cap": "capability",
}


@lru_cache(maxsize=100_000)
def _normalize_cached(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).casefold()
    text = text.replace("&", " and ")
    return re.sub(r"[^\w]+", " ", text, flags=re.UNICODE).strip()


def normalize_text(value: Any) -> str:
    """Normalize user/search text without locale-specific behaviour."""

    return _normalize_cached(str(value or ""))


def _slug(value: Any) -> str:
    text = normalize_text(value).replace(" ", "_")
    return text or "unknown"


@lru_cache(maxsize=100_000)
def _tokens_cached(value: str) -> tuple[str, ...]:
    text = _normalize_cached(value)
    return tuple(dict.fromkeys(part for part in text.split() if part))


def _tokens(value: Any) -> tuple[str, ...]:
    return _tokens_cached(str(value or ""))


def _as_dict(record: Any) -> dict[str, Any]:
    # AtlasRecord is a frozen dataclass.  Its fields already contain the
    # normalized core shape; avoiding ``to_dict`` here saves a second deep
    # serialization pass over the 3,793 core rows during API cold start.
    if hasattr(record, "__dataclass_fields__") and hasattr(record, "id"):
        return dict(vars(record))
    if isinstance(record, Mapping):
        return dict(record)
    to_dict = getattr(record, "to_dict", None)
    if callable(to_dict):
        return dict(to_dict())
    raise TypeError(f"India V1 record is not mapping-like: {type(record)!r}")


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        return [value]
    if isinstance(value, Sequence):
        return list(value)
    return [value]


@lru_cache(maxsize=100_000)
def _clean_string_tuple(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item.strip() for item in values if item and item.strip()))


def _string_list(value: Any) -> list[str]:
    result: list[str] = []
    if value is None:
        return result
    if isinstance(value, str):
        values = (value,)
    elif isinstance(value, Mapping):
        values = (value,)
    elif isinstance(value, Sequence):
        values = value
    else:
        values = (value,)
    if isinstance(values, (list, tuple)) and all(isinstance(item, str) for item in values):
        return list(_clean_string_tuple(tuple(values)))
    for item in values:
        if isinstance(item, str):
            text = item.strip()
            if text and text not in result:
                result.append(text)
            continue
        if isinstance(item, Mapping):
            item = item.get("note") or item.get("text") or item.get("purpose") or item.get("id")
        text = str(item or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def _status(value: Any) -> str:
    text = str(value or "UNKNOWN").strip()
    if text in STATUSES:
        return text
    mapped = _STATUS_MAP.get(text.upper())
    if mapped:
        return mapped
    return "UNKNOWN"


def _kind(value: Any) -> str:
    text = str(value or "").strip().upper().replace("-", "_").replace(" ", "_")
    return _KIND_MAP.get(text, "CAPABILITY")


def _domain_code(row: Mapping[str, Any]) -> str:
    for value in (row.get("domain_code"), row.get("domain_number"), row.get("domain_number")):
        if value not in (None, ""):
            try:
                code = f"{int(value):02d}"
            except (TypeError, ValueError):
                code = str(value).strip()
            if code in DOMAIN_META:
                return code
    domain_id = str(row.get("domain_id") or "")
    if domain_id[:2].isdigit() and domain_id[:2] in DOMAIN_META:
        return domain_id[:2]
    domain_name = normalize_text(row.get("domain") or row.get("domain_name"))
    for code, meta in DOMAIN_META.items():
        if domain_name in {normalize_text(meta["name"]), normalize_text(meta["key"])}:
            return code
    return "shared"


def _domain_name(code: str, row: Mapping[str, Any]) -> str:
    if code in DOMAIN_META:
        return DOMAIN_META[code]["name"]
    return str(row.get("domain") or row.get("domain_name") or "shared_foundations")


def _status_basis(row: Mapping[str, Any]) -> str:
    basis = row.get("status_basis") or row.get("india_status_basis") or row.get("epistemic_basis")
    if isinstance(basis, Mapping):
        basis = basis.get("basis") or basis.get("text")
    text = str(basis or "").strip()
    return text or "Curated India V1 navigation overlay; qualified depth and effective capacity remain UNKNOWN."


def _epistemic(row: Mapping[str, Any]) -> str:
    value = (
        row.get("status_epistemic_class")
        or row.get("epistemic_class")
        or row.get("india_status_epistemic")
    )
    text = str(value or "UNKNOWN").strip().upper()
    return text if text in EPISTEMIC_CLASSES else "UNKNOWN"


def _dependencies(row: Mapping[str, Any]) -> dict[str, list[str]]:
    raw = row.get("dependencies")
    if not isinstance(raw, Mapping):
        raw = row.get("dependency_groups")
    groups = {group: [] for group in DEP_GROUPS}
    if isinstance(raw, Mapping) and set(raw).issubset(DEP_GROUPS):
        # Core and domains 05-08 already use the common five-group contract.
        # Preserve the lists directly; reference canonicalization happens in
        # ``_normalize_refs`` and does not require another group pass.
        return {
            group: list(raw.get(group, ())) if isinstance(raw.get(group, ()), (list, tuple)) else _string_list(raw.get(group))
            for group in DEP_GROUPS
        }
    if isinstance(raw, Mapping):
        iterator = raw.items()
    elif isinstance(raw, Sequence) and not isinstance(raw, str):
        pairs = []
        for item in raw:
            if isinstance(item, Mapping):
                pairs.append((item.get("group"), item.get("ids")))
        iterator = pairs
    else:
        iterator = []
    for source_group, values in iterator:
        target_group = _GROUP_MAP.get(str(source_group or "").casefold(), "capabilities")
        for value in _string_list(values):
            if value not in groups[target_group]:
                groups[target_group].append(value)
    if not any(groups.values()):
        for value in _string_list(row.get("dependency_ids")):
            groups["capabilities"].append(value)
    return groups


def _ladder(row: Mapping[str, Any], name: str) -> list[dict[str, Any]]:
    raw = row.get("making_ladder") or row.get("making_ladder_detail") or []
    result: list[dict[str, Any]] = []
    actions = {"IMPORT", "DEVELOP", "LICENSE", "JV", "BUILD", "SUBSTITUTE", "REDESIGN", "R&D"}
    raw_items = raw if isinstance(raw, (list, tuple)) else _as_list(raw)
    for index, item in enumerate(raw_items, start=1):
        if isinstance(item, Mapping):
            action = str(item.get("action") or "DEVELOP").strip().upper()
            text = item.get("purpose") or item.get("text") or item.get("step") or ""
            condition = str(item.get("condition") or "").strip()
            sequence = item.get("sequence") or item.get("step") or index
        elif hasattr(item, "action"):
            action = str(getattr(item, "action", "DEVELOP")).strip().upper()
            text = getattr(item, "purpose", "") or getattr(item, "text", "") or ""
            condition = str(getattr(item, "condition", "") or "").strip()
            sequence = getattr(item, "sequence", index)
        else:
            action = "DEVELOP"
            text = str(item)
            condition = ""
            sequence = index
        if action not in actions:
            action = "DEVELOP"
        result.append(
            {
                "sequence": int(sequence) if str(sequence).isdigit() else index,
                "action": action,
                "purpose": str(text or f"Advance the route for {name}.").strip(),
                "condition": condition or "Requires an explicit specification, owner, and acceptance basis.",
            }
        )
    if not result:
        for index, action in enumerate(("IMPORT", "DEVELOP", "BUILD", "SUBSTITUTE", "REDESIGN", "R&D"), start=1):
            result.append(
                {
                    "sequence": index,
                    "action": action,
                    "purpose": f"{action.title()} the route for {name}.",
                    "condition": "Requires explicit specification, qualification, and residual-dependence controls.",
                }
            )
    return result


def _reference_id(value: str) -> str:
    """Collapse readable primitive spellings while preserving family refs."""

    text = str(value).strip()
    if not text:
        return "reference:unknown"
    prefix, separator, suffix = text.partition(":")
    normalized_prefix = _REF_PREFIX_MAP.get(prefix.casefold())
    if normalized_prefix and separator:
        return f"shared:{normalized_prefix}:{_slug(suffix)}"
    # ``node:09:foo`` and ``product:05:foo`` are family-level references from
    # the sibling packs.  They are not silently treated as a particular
    # variant; retaining the readable source in a bridge ID keeps that
    # uncertainty auditable and navigable.
    if separator:
        return f"reference:{_slug(text)}"
    return f"reference:{_slug(text)}"


def _normalize_refs(
    values: Any,
    ids: set[str],
    cache: dict[str, str],
    sequence_cache: dict[tuple[str, ...], tuple[str, ...]],
) -> list[str]:
    # Most generated variants reuse exactly the same bounded dependency tuple.
    # Cache the normalized sequence so the 12k-row adapter does not repeat the
    # same prefix/slug work for every compatible axis.
    if values is None or values == () or values == [] or values == "":
        return []
    if isinstance(values, (list, tuple)):
        # Generated packs guarantee reference lists are strings.  Avoid the
        # repeated ``all(isinstance(...))`` scan here; this function is called
        # for every dependency group on every compatible variant.
        raw_values = tuple(value for value in values if value)
    else:
        raw_values = tuple(_string_list(values))
    cached = sequence_cache.get(raw_values)
    if cached is not None:
        return list(cached)
    result: list[str] = []
    for value in raw_values:
        if value in ids:
            ref = value
        else:
            ref = cache.get(value)
            if ref is None:
                ref = _reference_id(value)
                cache[value] = ref
        if ref not in result:
            result.append(ref)
    sequence_cache[raw_values] = tuple(result)
    return result


def _normalize_row(
    raw: Mapping[str, Any],
    ids: set[str],
    reference_cache: dict[str, str],
    sequence_cache: dict[tuple[str, ...], tuple[str, ...]],
) -> tuple[dict[str, Any], tuple[str, ...]]:
    row = dict(raw)
    record_id = str(row.get("id") or row.get("record_id") or row.get("canonical_id") or "").strip()
    if not record_id:
        raise ValueError("India V1 record is missing a stable id")
    code = _domain_code(row)
    name = str(row.get("canonical_name") or row.get("name") or record_id).strip()
    aliases = _string_list(row.get("aliases"))
    if not aliases:
        aliases = [name]
    search_aliases = tuple(dict.fromkeys((*aliases, name, record_id, str(row.get("archetype_id") or ""))))
    deps = _dependencies(row)
    # The core 01-04 generator has already resolved every dependency and graph
    # edge to a canonical ID.  Avoid a second normalization pass for those
    # rows; the sibling packs still take the bridge path below.
    core_resolved = str(row.get("source_spec") or "") == "data.india_v1.domains_01_04"
    if core_resolved:
        normalized_deps = {group: list(deps[group]) for group in DEP_GROUPS}
        dependency_ids = [ref for group in DEP_GROUPS for ref in normalized_deps[group]]
        upstream = _string_list(row.get("upstream") or row.get("upstream_links"))
        downstream = _string_list(row.get("downstream") or row.get("downstream_links"))
        related = _string_list(row.get("related") or row.get("related_links"))
    else:
        normalized_deps = {
            group: _normalize_refs(values, ids, reference_cache, sequence_cache) for group, values in deps.items()
        }
        dependency_ids = [ref for group in DEP_GROUPS for ref in normalized_deps[group]]
        upstream = _normalize_refs([*(_string_list(row.get("upstream") or row.get("upstream_links"))), *dependency_ids], ids, reference_cache, sequence_cache)
        downstream = _normalize_refs(row.get("downstream") or row.get("downstream_links"), ids, reference_cache, sequence_cache)
        related = _normalize_refs(row.get("related") or row.get("related_links"), ids, reference_cache, sequence_cache)
    gaps = _string_list(row.get("gaps") or row.get("gap_notes"))
    imports = _string_list(row.get("import_notes"))
    gap_notes = row.get("gap_import_notes") or row.get("gaps_import_notes")
    if isinstance(gap_notes, Sequence) and not isinstance(gap_notes, str):
        gap_notes = " ".join(_string_list(gap_notes))
    gap_text = str(gap_notes or "").strip()
    if not gap_text:
        gap_text = " ".join((*gaps, *imports)).strip()
    status = _status(row.get("status") or row.get("india_status"))
    normalized = {
        "id": record_id,
        "canonical_name": name,
        "aliases": aliases,
        "domain_code": code,
        "domain_id": code,
        "domain_key": DOMAIN_META.get(code, {}).get("key", "shared_foundations"),
        "domain": _domain_name(code, row) if code != "shared" else "shared_foundations",
        "category": str(row.get("category") or "industrial capability").strip(),
        "kind": _kind(row.get("kind")),
        "explanation": str(row.get("explanation") or "Curated India V1 industrial ontology record.").strip(),
        "uses": _string_list(row.get("uses") or row.get("use")),
        "status": status,
        "status_epistemic_class": _epistemic(row),
        "status_basis": _status_basis(row),
        "dependencies": normalized_deps,
        "dependency_ids": dependency_ids,
        "gaps": gaps,
        "import_notes": imports,
        "gap_import_notes": gap_text,
        "making_ladder": _ladder(row, name),
        "upstream": upstream,
        "downstream": downstream,
        "related": related,
        "source_spec": str(row.get("source_spec") or row.get("source_basis") or "india_v1"),
        "is_reference_only": False,
        "_search_aliases": search_aliases,
    }
    return normalized, search_aliases


def _stub_record(record_id: str) -> dict[str, Any]:
    prefix, _, suffix = record_id.partition(":")
    kind = {
        "shared": {
            "system": "CAPABILITY",
            "process": "PROCESS",
            "material": "MATERIAL",
            "equipment": "EQUIPMENT",
            "capability": "CAPABILITY",
        }.get(suffix.partition(":")[0], "CAPABILITY"),
    }.get(prefix, "CAPABILITY")
    label = suffix.replace(":", " ").replace("_", " ").replace("-", " ").strip() or record_id
    name = f"Reference primitive: {label}"
    ladder = [
        {"sequence": index, "action": action, "purpose": f"{action.title()} the unresolved reference route for {label}.", "condition": "The bridge is a navigation reference; qualification remains UNKNOWN."}
        for index, action in enumerate(("IMPORT", "DEVELOP", "LICENSE", "JV", "BUILD", "SUBSTITUTE", "REDESIGN", "R&D"), start=1)
    ]
    return {
        "id": record_id,
        "canonical_name": name,
        "aliases": [record_id, label],
        "domain_code": "shared",
        "domain_id": "shared",
        "domain_key": "shared_foundations",
        "domain": "shared_foundations",
        "category": "reference primitive",
        "kind": kind,
        "explanation": "A readable bridge for a dependency named by a breadth domain pack; it is not a producer or supply claim.",
        "uses": ["Navigate the dependency graph and identify the evidence task for this primitive."],
        "status": "UNKNOWN",
        "status_epistemic_class": "UNKNOWN",
        "status_basis": "Reference-only bridge created because the source pack names a primitive without a canonical V1 record; capability and supply remain UNKNOWN.",
        "dependencies": {group: [] for group in DEP_GROUPS},
        "dependency_ids": [],
        "gaps": ["Canonical specification, owner, qualification, and effective capacity are UNKNOWN."],
        "import_notes": ["Reference identity is not evidence of domestic availability or production."],
        "gap_import_notes": "Canonical specification, owner, qualification, and effective capacity are UNKNOWN.",
        "making_ladder": ladder,
        "upstream": [],
        "downstream": [],
        "related": [],
        "source_spec": "reference_bridge",
        "is_reference_only": True,
        "_search_aliases": (record_id, label),
    }


def _direct_rows() -> list[dict[str, Any]]:
    atlas_rows = [_as_dict(item) for item in generate_atlas().records]
    rows = atlas_rows + [dict(item) for item in _domains_05_08.ALL_RECORDS] + [dict(item) for item in _domains_09_12.ALL_RECORDS]
    # All direct IDs are known before references are normalized, so a sibling
    # pack can point at a variant generated by another pack without creating a
    # duplicate bridge node.
    ids = {str(row.get("id") or row.get("record_id") or row.get("canonical_id") or "") for row in rows}
    normalized: list[dict[str, Any]] = []
    reference_cache: dict[str, str] = {}
    sequence_cache: dict[tuple[str, ...], tuple[str, ...]] = {}
    for raw in rows:
        item, _ = _normalize_row(raw, ids, reference_cache, sequence_cache)
        normalized.append(item)
    return normalized


@dataclass(frozen=True)
class IndiaCatalog:
    """Immutable-ish read catalog with precomputed deterministic indexes."""

    records: tuple[dict[str, Any], ...]
    by_id: dict[str, dict[str, Any]]
    token_index: dict[str, tuple[str, ...]]
    alias_index: dict[str, tuple[str, ...]]
    domain_index: dict[str, tuple[str, ...]]
    kind_index: dict[str, tuple[str, ...]]
    status_index: dict[str, tuple[str, ...]]
    domain_aliases: dict[str, str]
    search_fields: dict[str, tuple[str, ...]]
    normalized_fields: dict[str, tuple[str, ...]]
    search_token_sets: dict[str, frozenset[str]]
    direct_record_count: int

    @property
    def reference_record_count(self) -> int:
        return len(self.records) - self.direct_record_count

    @property
    def domain_counts(self) -> dict[str, int]:
        return {
            code: sum(1 for record in self.records if not record["is_reference_only"] and record["domain_code"] == code)
            for code in DOMAIN_ORDER
        }

    @property
    def kind_counts(self) -> dict[str, int]:
        return dict(sorted(Counter(record["kind"] for record in self.records).items()))

    @property
    def status_counts(self) -> dict[str, int]:
        return dict(sorted(Counter(record["status"] for record in self.records).items()))

    @property
    def epistemic_counts(self) -> dict[str, int]:
        return dict(sorted(Counter(record["status_epistemic_class"] for record in self.records).items()))

    def resolve_domain(self, value: str | None) -> str | None:
        if value is None or not str(value).strip():
            return None
        key = normalize_text(value).replace(" ", "_")
        return self.domain_aliases.get(key)

    def ranked_search(
        self,
        query: str = "",
        *,
        domain: str | None = None,
        kind: str | None = None,
        status: str | None = None,
        limit: int = 25,
    ) -> list[tuple[dict[str, Any], int]]:
        """Return deterministic ranked records using only prebuilt indexes."""

        domain_code = self.resolve_domain(domain)
        if domain is not None and domain_code is None:
            return []
        kind_value = str(kind).upper() if kind else None
        status_value = _status(status) if status else None
        candidate: set[str] | None = None
        normalized_query = normalize_text(query)
        query_tokens = set(_tokens(query))
        if normalized_query:
            exact = set(self.alias_index.get(normalized_query, ()))
            token_sets = [set(self.token_index.get(token, ())) for token in query_tokens]
            union = set().union(*token_sets) if token_sets else set()
            candidate = exact | union
        else:
            candidate = None
        if domain_code:
            values = set(self.domain_index.get(domain_code, ()))
            candidate = values if candidate is None else candidate & values
        if kind_value:
            values = set(self.kind_index.get(kind_value, ()))
            candidate = values if candidate is None else candidate & values
        if status_value:
            values = set(self.status_index.get(status_value, ()))
            candidate = values if candidate is None else candidate & values
        if candidate is None:
            candidate = set(self.by_id)

        prefer_direct = any(not self.by_id[record_id]["is_reference_only"] for record_id in candidate)
        scored: list[tuple[tuple[Any, ...], dict[str, Any], int]] = []
        for record_id in candidate:
            record = self.by_id[record_id]
            fields = self.search_fields[record_id]
            normalized_fields = self.normalized_fields[record_id]
            exact_name = int(bool(normalized_query and normalized_query == normalized_fields[1]))
            exact_alias = int(bool(normalized_query and normalized_query in normalized_fields))
            starts = int(bool(normalized_query and any(field.startswith(normalized_query) for field in normalized_fields)))
            coverage = len(query_tokens.intersection(self.search_token_sets[record_id])) if query_tokens else 0
            source_priority = 5000 if prefer_direct and not record["is_reference_only"] else 0
            score = source_priority + exact_name * 1000 + exact_alias * 900 + starts * 100 + coverage
            # The negative score keeps richer matches first; ID makes every
            # tie stable across Python process/hash seeds.
            scored.append(((-score, -coverage, record_id), record, score))
        scored.sort(key=lambda item: item[0])
        return [(record, score) for _, record, score in scored[: max(1, int(limit))]]

    def search(
        self,
        query: str = "",
        *,
        domain: str | None = None,
        kind: str | None = None,
        status: str | None = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        """Return JSON-ready records; use :meth:`ranked_search` for scores."""

        return [
            dict(record)
            for record, _score in self.ranked_search(
                query,
                domain=domain,
                kind=kind,
                status=status,
                limit=limit,
            )
        ]

    def integrity(self) -> dict[str, Any]:
        errors: list[str] = []
        ids = [record["id"] for record in self.records]
        if len(ids) != len(set(ids)):
            errors.append("duplicate record id")
        aliases: dict[str, str] = {}
        for record in self.records:
            for alias in record["aliases"]:
                key = normalize_text(alias)
                owner = aliases.get(key)
                if owner and owner != record["id"]:
                    errors.append(f"duplicate alias {alias!r}: {owner} and {record['id']}")
                aliases[key] = record["id"]
            if record["kind"] not in KINDS:
                errors.append(f"{record['id']}: invalid kind")
            if record["status"] not in STATUSES:
                errors.append(f"{record['id']}: invalid status")
            if record["status_epistemic_class"] not in EPISTEMIC_CLASSES:
                errors.append(f"{record['id']}: invalid epistemic class")
            if set(record["dependencies"]) != set(DEP_GROUPS):
                errors.append(f"{record['id']}: invalid dependency groups")
            if record["kind"] == "PRODUCT" and not record["is_reference_only"] and record["domain_code"] != "shared":
                if len(record["dependency_ids"]) < 5:
                    errors.append(f"{record['id']}: product has fewer than five dependencies")
                if len(record["making_ladder"]) < 5:
                    errors.append(f"{record['id']}: product ladder is too short")
            for group in DEP_GROUPS:
                for reference in record["dependencies"][group]:
                    if reference not in self.by_id:
                        errors.append(f"{record['id']}: unresolved dependency {reference}")
            for reference in (*record["upstream"], *record["downstream"], *record["related"]):
                if reference not in self.by_id:
                    errors.append(f"{record['id']}: unresolved link {reference}")
            if not record["is_reference_only"] and not (record["upstream"] or record["downstream"] or record["related"]):
                errors.append(f"{record['id']}: dead-end record")
        return {
            "ok": not errors,
            "record_count": len(self.records),
            "direct_record_count": self.direct_record_count,
            "reference_record_count": self.reference_record_count,
            "domain_counts": self.domain_counts,
            "kind_counts": self.kind_counts,
            "status_counts": self.status_counts,
            "unique_ids": len(set(ids)),
            "unique_aliases": len(aliases),
            "errors": errors,
        }


def _build_catalog() -> IndiaCatalog:
    direct = _direct_rows()
    direct_ids = {record["id"] for record in direct}
    bridges: dict[str, dict[str, Any]] = {}
    for record in direct:
        references = [
            *record["dependency_ids"],
            *record["upstream"],
            *record["downstream"],
            *record["related"],
        ]
        for reference in references:
            if reference not in direct_ids and reference not in bridges:
                bridges[reference] = _stub_record(reference)

    all_records = direct + [bridges[key] for key in sorted(bridges)]
    # Reverse edges make a bridge node useful from the graph endpoint and
    # expose the ``unlocks`` view without changing source-pack assertions.
    reverse_downstream: dict[str, set[str]] = defaultdict(set)
    for record in all_records:
        for reference in (*record["dependency_ids"], *record["upstream"]):
            reverse_downstream[reference].add(record["id"])
    for record in all_records:
        record["downstream"] = sorted(set(record["downstream"]) | reverse_downstream.get(record["id"], set()))

    # Keep the source aliases available to search while making the public
    # aliases globally unique for registry integrity.  A repeated family alias
    # is suffixed only on the later records; token search still finds every
    # variant because its raw alias is indexed below.
    alias_owner: dict[str, str] = {}
    search_fields: dict[str, tuple[str, ...]] = {}
    normalized_fields_build: dict[str, tuple[str, ...]] = {}
    search_token_sets_build: dict[str, frozenset[str]] = {}
    alias_index_build: dict[str, set[str]] = defaultdict(set)
    token_index_build: dict[str, set[str]] = defaultdict(set)
    for record in all_records:
        public_aliases: list[str] = []
        raw_aliases = tuple(record.pop("_search_aliases", ()))
        for alias in record["aliases"]:
            norm = normalize_text(alias)
            if not norm:
                continue
            owner = alias_owner.get(norm)
            public_alias = alias
            if owner and owner != record["id"]:
                public_alias = f"{alias} [{record['id']}]"
                norm = normalize_text(public_alias)
            if norm not in alias_owner:
                alias_owner[norm] = record["id"]
                public_aliases.append(public_alias)
        if not public_aliases:
            public_aliases = [record["id"]]
            alias_owner.setdefault(normalize_text(record["id"]), record["id"])
        record["aliases"] = public_aliases
        field_values = tuple(dict.fromkeys((record["id"], record["canonical_name"], *raw_aliases, *public_aliases, record["category"], *record["uses"])))
        search_fields[record["id"]] = field_values
        normalized_values = tuple(normalize_text(field) for field in field_values)
        normalized_fields_build[record["id"]] = normalized_values
        search_token_sets_build[record["id"]] = frozenset(token for field in field_values for token in _tokens(field))
        for field in field_values:
            normalized = normalize_text(field)
            if normalized:
                alias_index_build[normalized].add(record["id"])
            for token in _tokens(field):
                token_index_build[token].add(record["id"])

    by_id = {record["id"]: record for record in all_records}
    domain_index_build: dict[str, set[str]] = defaultdict(set)
    kind_index_build: dict[str, set[str]] = defaultdict(set)
    status_index_build: dict[str, set[str]] = defaultdict(set)
    for record in all_records:
        domain_index_build[record["domain_code"]].add(record["id"])
        kind_index_build[record["kind"]].add(record["id"])
        status_index_build[record["status"]].add(record["id"])

    domain_aliases: dict[str, str] = {"shared": "shared"}
    for code, meta in DOMAIN_META.items():
        for value in (code, str(int(code)), meta["key"], meta["name"]):
            domain_aliases[normalize_text(value).replace(" ", "_")] = code

    catalog = IndiaCatalog(
        records=tuple(sorted(all_records, key=lambda record: record["id"])),
        by_id=by_id,
        token_index={key: tuple(sorted(value)) for key, value in token_index_build.items()},
        alias_index={key: tuple(sorted(value)) for key, value in alias_index_build.items()},
        domain_index={key: tuple(sorted(value)) for key, value in domain_index_build.items()},
        kind_index={key: tuple(sorted(value)) for key, value in kind_index_build.items()},
        status_index={key: tuple(sorted(value)) for key, value in status_index_build.items()},
        domain_aliases=domain_aliases,
        search_fields=search_fields,
        normalized_fields=normalized_fields_build,
        search_token_sets=search_token_sets_build,
        direct_record_count=len(direct),
    )
    report = catalog.integrity()
    if not report["ok"]:
        raise ValueError("India V1 catalog integrity failed: " + "; ".join(report["errors"][:12]))
    return catalog


@lru_cache(maxsize=1)
def get_catalog() -> IndiaCatalog:
    """Build the combined catalog once and reuse it for all API queries."""

    return _build_catalog()


def clear_catalog_cache() -> None:
    """Test/dev hook; production API callers should use the cached catalog."""

    get_catalog.cache_clear()


def summary(catalog: IndiaCatalog | None = None) -> dict[str, Any]:
    catalog = catalog or get_catalog()
    direct = [record for record in catalog.records if not record["is_reference_only"]]
    owned = [record for record in direct if record["domain_code"] != "shared"]
    return {
        "depth_profile": DEPTH_PROFILE,
        "record_count": len(catalog.records),
        "direct_record_count": catalog.direct_record_count,
        "owned_record_count": len(owned),
        "shared_source_record_count": len(direct) - len(owned),
        "reference_record_count": catalog.reference_record_count,
        "domain_count": len(DOMAIN_ORDER),
        "domain_counts": catalog.domain_counts,
        "kind_counts": catalog.kind_counts,
        "status_counts": catalog.status_counts,
        "status_epistemic_counts": catalog.epistemic_counts,
        "direct_kind_counts": dict(sorted(Counter(record["kind"] for record in direct).items())),
        "direct_status_counts": dict(sorted(Counter(record["status"] for record in direct).items())),
        "direct_status_epistemic_counts": dict(sorted(Counter(record["status_epistemic_class"] for record in direct).items())),
        "all_record_kind_counts": catalog.kind_counts,
        "all_record_status_counts": catalog.status_counts,
        "all_record_status_epistemic_counts": catalog.epistemic_counts,
        "integrity": {
            "unique_ids": len(catalog.by_id),
            "unique_aliases": sum(len(record["aliases"]) for record in catalog.records),
            "all_references_resolve": True,
        },
    }


def domains(catalog: IndiaCatalog | None = None) -> list[dict[str, Any]]:
    catalog = catalog or get_catalog()
    rows: list[dict[str, Any]] = []
    for code in DOMAIN_ORDER:
        owned = [record for record in catalog.records if not record["is_reference_only"] and record["domain_code"] == code]
        rows.append(
            {
                "id": code,
                "code": code,
                "key": DOMAIN_META[code]["key"],
                "name": DOMAIN_META[code]["name"],
                "description": f"Broad V1 ontology coverage for {DOMAIN_META[code]['name']}; status overlays are not qualified supply or effective capacity claims.",
                "record_count": len(owned),
                "kind_counts": dict(sorted(Counter(record["kind"] for record in owned).items())),
                "status_counts": dict(sorted(Counter(record["status"] for record in owned).items())),
                "depth_profile": DEPTH_PROFILE,
            }
        )
    return rows


__all__ = [
    "DEPTH_PROFILE",
    "DEP_GROUPS",
    "DOMAIN_META",
    "DOMAIN_ORDER",
    "EPISTEMIC_CLASSES",
    "IndiaCatalog",
    "KINDS",
    "STATUSES",
    "clear_catalog_cache",
    "domains",
    "get_catalog",
    "normalize_text",
    "summary",
]
