"""Human-facing buildability composition for the India V1 catalog.

The catalog is intentionally an ontology/read index.  It contains stable IDs,
generated breadth rows, and reference bridges because those are useful to the
engine and to graph APIs.  Those fields are not a suitable public product
surface.  This module is the small presentation adapter between the catalog
and the FORGE India buildability experience.

The adapter is deterministic and read-only.  It does not infer capacity,
facilities, suppliers, time-to-localize, or evidence that is not present in a
catalog row.  In particular, ``overall_index`` remains ``None`` because the
V1 status overlay is ordinal/navigation data rather than an evidence-weighted
capacity calculation.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
import re
import unicodedata
from typing import Any, Iterable

from .catalog import DEP_GROUPS, IndiaCatalog, get_catalog


VIEW_MODEL_SCHEMA_VERSION = "forge.india.buildability.v1"

# These are the only status buckets shown by the product.  The exact source
# status is retained on each requirement and in ``status_counts`` so a broad
# bucket never hides a CONFLICTED or SCALE_LIMITED source label.
STATUS_BUCKETS = (
    "available",
    "partial_or_import_dependent",
    "missing",
    "unknown",
)

_STATUS_ALIASES = {
    "STRONG / AVAILABLE IN INDIA": "AVAILABLE",
    "AVAILABLE IN INDIA": "AVAILABLE",
    "PARTIAL / SCALE-LIMITED": "SCALE_LIMITED",
    "SPECIFICATION GAP": "PARTIAL",
    "QUALIFICATION GAP": "PARTIAL",
    "CAPACITY GAP": "SCALE_LIMITED",
    "IMPORT-DEPENDENT": "IMPORT_DEPENDENT",
    "MISSING / NO EVIDENCED DOMESTIC CAPABILITY": "MISSING",
}

_STATUS_TO_BUCKET = {
    "STRONG": "available",
    "AVAILABLE": "available",
    "PARTIAL": "partial_or_import_dependent",
    "SCALE_LIMITED": "partial_or_import_dependent",
    "IMPORT_DEPENDENT": "partial_or_import_dependent",
    "MISSING": "missing",
    "UNKNOWN": "unknown",
    "CONFLICTED": "unknown",
}

# Lower values are more decision-sensitive when a recorded gap is ranked.
_BOTTLENECK_PRIORITY = {
    "MISSING": 0,
    "IMPORT_DEPENDENT": 1,
    "CONFLICTED": 2,
    "UNKNOWN": 3,
    "SCALE_LIMITED": 4,
    "PARTIAL": 5,
    "AVAILABLE": 9,
    "STRONG": 9,
}

_STATUS_LABELS = {
    "STRONG": "Strong / available",
    "AVAILABLE": "Available",
    "PARTIAL": "Partial",
    "SCALE_LIMITED": "Scale-limited",
    "IMPORT_DEPENDENT": "Import dependent",
    "MISSING": "Missing",
    "UNKNOWN": "Unknown",
    "CONFLICTED": "Conflicted",
}

_GROUP_LABELS = {
    "systems": "Systems",
    "processes": "Processes",
    "materials": "Materials",
    "equipment": "Equipment",
    "capabilities": "Capabilities",
    "components": "Components",
    "tooling": "Tooling and jigs",
    "metrology": "Metrology and testing",
    "qualification": "Qualification and standards",
}

_STAGE_LABELS = {
    "local_first": "Start with an evidence-backed local route",
    "initial_import_bridge": "Bridge unresolved requirements where necessary",
    "integration_and_test": "Integrate, inspect, and test",
    "next_localization": "Localize the next highest-risk requirement",
    "harder_later_capability": "Advance the harder later capability",
    "optional_redesign": "Redesign only if the gap remains binding",
}

_ACRONYMS = {
    "api": "API",
    "atc": "ATC",
    "cmm": "CMM",
    "cnc": "CNC",
    "cfr": "CFR",
    "hv": "HV",
    "hvac": "HVAC",
    "ip": "IP",
    "mri": "MRI",
    "ndt": "NDT",
    "pet": "PET",
    "plc": "PLC",
    "qa": "QA",
    "rf": "RF",
    "rfq": "RFQ",
    "r&d": "R&D",
    "spect": "SPECT",
    "ups": "UPS",
}

_REFERENCE_MARKER = re.compile(r"\breference\s+primitive\s*:\s*", re.IGNORECASE)
_NODE_MARKER = re.compile(r"\bnode\s*[-_:]?\s*\d+\b", re.IGNORECASE)
_RAW_ID = re.compile(
    r"\b(?:shared|reference|product|capability|process|material|equipment|india-v1|node):"
    r"[A-Za-z0-9_.:-]+",
    re.IGNORECASE,
)
_SNAKE_WORD = re.compile(r"\b[a-zA-Z][a-zA-Z0-9]*_[a-zA-Z0-9_]+\b")
_REPEATED_PHRASE = re.compile(r"^(.+?)\s+[—-]\s+\1$", re.IGNORECASE)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_status(value: Any) -> str:
    raw = _text(value).upper()
    normalized = _STATUS_ALIASES.get(raw, raw)
    return normalized if normalized in _STATUS_TO_BUCKET else "UNKNOWN"


def _epistemic(record: Mapping[str, Any]) -> str:
    value = (
        record.get("status_epistemic_class")
        or record.get("status_epistemic")
        or record.get("epistemic_class")
        or "UNKNOWN"
    )
    return _text(value).upper() or "UNKNOWN"


def _humanize_id(value: Any) -> str:
    """Turn a bridge/reference spelling into a readable noun phrase.

    This function is deliberately only a display transform.  It never writes
    the resulting label back to the catalog and never changes a lookup key.
    """

    raw = _text(value)
    if not raw:
        return "Unspecified requirement"
    parts = [part for part in raw.split(":") if part]
    if parts and parts[0].casefold() in {"shared", "reference", "product", "capability", "process", "material", "equipment", "india-v1", "d"}:
        parts = parts[1:]
    if parts and re.fullmatch(r"(?:d|node)?\d{2}", parts[0], re.IGNORECASE):
        parts = parts[1:]
    if parts and parts[0].casefold() == "node":
        parts = parts[1:]
    # ``node:11:textile:...`` and ``product:07:...`` can leave a numeric
    # domain token in the middle.  Numeric tokens are implementation context,
    # not useful public labels.
    parts = [part for part in parts if not re.fullmatch(r"\d+", part)]
    phrase = " ".join(parts).replace("_", " ")
    phrase = phrase.replace("-", " ")
    phrase = re.sub(r"\s+", " ", phrase).strip()
    # ``shared:process:...`` and ``reference:shared_process_...`` carry the
    # source kind as an implementation prefix.  The public label only needs
    # the noun phrase itself.
    phrase = re.sub(r"^(?:shared|reference)\s+", "", phrase, flags=re.IGNORECASE)
    phrase = re.sub(
        r"^(?:system|systems|process|processes|material|materials|equipment|capability|capabilities)\s+",
        "",
        phrase,
        flags=re.IGNORECASE,
    )
    phrase = re.sub(r"^(?:product|node|d)\s*\d{0,2}\s+", "", phrase, flags=re.IGNORECASE)
    return _humanize_text(phrase)


def _humanize_text(value: Any) -> str:
    """Normalize generated/source text for public display."""

    text = unicodedata.normalize("NFKC", _text(value))
    if not text:
        return ""
    text = _REFERENCE_MARKER.sub("", text)
    text = _RAW_ID.sub("", text)
    text = _SNAKE_WORD.sub(lambda match: match.group(0).replace("_", " "), text)
    text = _NODE_MARKER.sub("", text)
    text = re.sub(r"\s+", " ", text).strip(" -—:;")
    repeated = _REPEATED_PHRASE.match(text)
    if repeated:
        text = repeated.group(1).strip()
    # A generated label can repeat the same family phrase around a separator.
    # Remove only exact repeated segments; do not aggressively paraphrase
    # source prose.
    segments = [segment.strip() for segment in re.split(r"\s+[—-]\s+", text) if segment.strip()]
    if len(segments) > 1:
        retained: list[str] = []
        seen: set[str] = set()
        for segment in segments:
            key = re.sub(r"[^a-z0-9]+", " ", segment.casefold()).strip()
            if key and key in seen:
                continue
            seen.add(key)
            retained.append(segment)
        text = " — ".join(retained)
    # Preserve intentional casing such as MRI/CNC/RF while making bridge
    # phrases readable when the source is all lowercase.
    words = []
    for word in text.split(" "):
        key = word.casefold().strip(".,;:()[]")
        words.append(_ACRONYMS.get(key, word))
    text = " ".join(words).strip()
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    return text


def _friendly_label(record: Mapping[str, Any], fallback: Any = None) -> str:
    """Choose a stable family label and never expose a raw bridge label."""

    is_reference = bool(record.get("is_reference_only"))
    record_id = _text(record.get("id") or record.get("record_id") or record.get("canonical_id"))
    candidates = (
        record.get("family_label"),
        record.get("display_name"),
        record.get("canonical_name"),
        record.get("name"),
        fallback,
    )
    chosen = next((_text(value) for value in candidates if _text(value)), "")
    if is_reference or not chosen or _REFERENCE_MARKER.search(chosen):
        chosen = _humanize_id(record_id or fallback)
    else:
        chosen = _humanize_text(chosen)
    # Generic generated prefixes are useful in the catalog but not in the
    # product question.  Keep meaningful cross-domain nouns after the colon.
    chosen = re.sub(r"^(?:Cross-domain|Curated)\s+(?:system|process|material|equipment|capability)\s*:\s*", "", chosen, flags=re.IGNORECASE).strip()
    chosen = re.sub(r"^(?:system|process|material|equipment|capability)\s*:\s*", "", chosen, flags=re.IGNORECASE).strip()
    return chosen or "Unspecified requirement"


def _safe_detail(value: Any, limit: int = 420) -> str:
    text = _humanize_text(value)
    if len(text) <= limit:
        return text
    clipped = text[: limit - 1].rsplit(" ", 1)[0].rstrip(" ,;:")
    return f"{clipped}…"


def _record_key(record: Mapping[str, Any], fallback: Any = None) -> str:
    return _text(
        record.get("id")
        or record.get("record_id")
        or record.get("canonical_id")
        or record.get("family_key")
        or record.get("canonical_name")
        or fallback
    )


def _record_for_reference(catalog: IndiaCatalog | None, reference: Any) -> dict[str, Any]:
    if isinstance(reference, Mapping):
        return dict(reference)
    ref = _text(reference)
    if catalog is not None and ref in catalog.by_id:
        return catalog.by_id[ref]
    # A missing bridge should remain an UNKNOWN display item rather than being
    # silently dropped or turned into a domestic capability claim.
    return {
        "id": ref,
        "canonical_name": _humanize_id(ref),
        "display_name": _humanize_id(ref),
        "family_label": _humanize_id(ref),
        "kind": "CAPABILITY",
        "status": "UNKNOWN",
        "status_epistemic_class": "UNKNOWN",
        "status_basis": "Reference identity is not evidence of a qualified capability or domestic supply.",
        "dependencies": {},
        "is_reference_only": True,
    }


def _iter_refs(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, Mapping) or isinstance(value, str):
        return [value]
    if isinstance(value, Sequence):
        return list(value)
    return [value]


def _dependencies(record: Mapping[str, Any]) -> dict[str, list[Any]]:
    raw = record.get("dependencies") or record.get("dependency_groups") or {}
    groups = {group: [] for group in DEP_GROUPS}
    if isinstance(raw, Mapping):
        for group in DEP_GROUPS:
            groups[group] = _iter_refs(raw.get(group))
    # Lightweight callers sometimes only provide a flat dependency list.  It
    # is kept visible under capabilities, with UNKNOWN remaining the honest
    # fallback for the missing typed grouping.
    if not any(groups.values()):
        groups["capabilities"] = _iter_refs(record.get("dependency_ids"))
    return groups


def _status_item(
    record: Mapping[str, Any],
    *,
    role: str,
    fallback: Any = None,
    derived: bool = False,
    summary: str | None = None,
) -> dict[str, Any]:
    status = _normalize_status(record.get("status") or record.get("india_status"))
    is_reference = bool(record.get("is_reference_only"))
    basis = (
        "No validated India capability or supply record is attached; status remains UNKNOWN."
        if is_reference
        else record.get("status_basis")
        or "Status basis is not specified; treat the requirement as UNKNOWN until validated."
    )
    item = {
        "name": _friendly_label(record, fallback),
        "role": _GROUP_LABELS.get(role, _humanize_text(role)),
        "kind": _humanize_text(record.get("kind") or "CAPABILITY").upper(),
        "status": status,
        "status_label": _STATUS_LABELS[status],
        "epistemic_class": _epistemic(record),
        "summary": _safe_detail(summary or record.get("explanation") or "Recorded requirement in the India V1 route.", 280),
        "basis": _safe_detail(basis, 360),
        "data_state": "LIMITED_DATA" if is_reference else "CATALOG_RECORD",
    }
    if derived:
        item["data_state"] = "DERIVED_FROM_RECORDED_GAP"
    return item


def _dedupe_items(items: Iterable[dict[str, Any]], limit: int = 24) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        key = re.sub(r"[^a-z0-9]+", " ", _text(item.get("name")).casefold()).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
        if len(result) >= limit:
            break
    return result


def _requirement_groups(record: Mapping[str, Any], catalog: IndiaCatalog | None) -> dict[str, list[dict[str, Any]]]:
    dependencies = _dependencies(record)
    base: dict[str, list[dict[str, Any]]] = {group: [] for group in DEP_GROUPS}
    for group in DEP_GROUPS:
        rows = []
        for reference in dependencies[group]:
            row = _record_for_reference(catalog, reference)
            rows.append(_status_item(row, role=group, fallback=reference))
        base[group] = _dedupe_items(rows)

    # Components are only emitted when the source gives an explicit component
    # group or a product-like dependency.  This avoids relabelling a process
    # or capability as a component merely to fill a dashboard card.
    components: list[dict[str, Any]] = []
    for reference in dependencies.get("components", ()):
        row = _record_for_reference(catalog, reference)
        components.append(_status_item(row, role="components", fallback=reference))

    all_rows: list[tuple[str, Mapping[str, Any]]] = []
    for group in DEP_GROUPS:
        all_rows.extend((group, _record_for_reference(catalog, reference)) for reference in dependencies[group])

    def filtered(terms: tuple[str, ...], role: str) -> list[dict[str, Any]]:
        return _dedupe_items(
            _status_item(row, role=role, fallback=reference)
            for _group, row in all_rows
            for reference in (_record_key(row),)
            if any(term in _friendly_label(row, reference).casefold() for term in terms)
        )

    # These are views over existing typed records, not newly asserted
    # capabilities.  The unfiltered capabilities list remains available too.
    tooling = filtered(("tool", "fixture", "jig", "die", "mould", "mold", "holder", "drawbar"), "tooling")
    metrology = filtered(("metrolog", "calibrat", "measure", "inspection", "test", "cmm", "quality"), "metrology")
    qualification = filtered(("qualif", "validat", "acceptance", "standard", "certif", "safety", "regulat", "clinical"), "qualification")

    return {
        "components": _dedupe_items(components),
        "processes": base["processes"],
        "equipment": base["equipment"],
        "tooling": tooling,
        "materials": base["materials"],
        "metrology": metrology,
        "qualification": qualification,
        "capabilities": base["capabilities"],
    }


def _status_from_rows(rows: Sequence[Mapping[str, Any]]) -> str:
    statuses = [_normalize_status(row.get("status") or row.get("india_status")) for row in rows]
    if not statuses:
        return "UNKNOWN"
    return min(statuses, key=lambda status: (_BOTTLENECK_PRIORITY.get(status, 8), status))


def _major_systems(
    record: Mapping[str, Any],
    catalog: IndiaCatalog | None,
    requirement_groups: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    dependencies = _dependencies(record)
    systems: list[dict[str, Any]] = []
    for reference in dependencies.get("systems", ()):
        row = _record_for_reference(catalog, reference)
        systems.append(_status_item(row, role="systems", fallback=reference))
    if systems:
        return _dedupe_items(systems, limit=12)

    # Several breadth records have no explicit ``systems`` group.  Recorded
    # gap categories still provide a useful decomposition without inventing a
    # subsystem record.  Marking these as derived keeps the distinction clear.
    gaps = [gap for gap in _gap_texts(record) if not _is_generic_import_note(gap)]
    for gap in gaps[:6]:
        systems.append(
            _status_item(
                {
                    "canonical_name": gap,
                    "display_name": gap,
                    "kind": "SYSTEM",
                    "status": _normalize_status(record.get("status") or record.get("india_status")),
                    "status_epistemic_class": _epistemic(record),
                    "status_basis": "Derived from a recorded gap category; no separate subsystem record is attached.",
                    "explanation": "Recorded as a decomposition area in the selected product route.",
                },
                role="systems",
                derived=True,
                summary="Derived from the product's recorded buildability gap categories.",
            )
        )
    if systems:
        return _dedupe_items(systems, limit=8)

    # Last resort: expose the typed group headings as an honest high-level
    # decomposition.  Status is aggregated only for navigation, never as a
    # facility/capacity claim.
    for group in ("processes", "equipment", "materials", "capabilities"):
        rows = requirement_groups.get(group, ())
        if not rows:
            continue
        status = _status_from_rows(rows)
        systems.append(
            {
                "name": _GROUP_LABELS[group],
                "role": "Systems",
                "kind": "SYSTEM",
                "status": status,
                "status_label": _STATUS_LABELS[status],
                "epistemic_class": "MODELLED",
                "summary": "High-level decomposition heading aggregated from typed requirements.",
                "basis": "Navigation grouping only; the child requirement statuses remain the source view.",
                "data_state": "DERIVED_FROM_TYPED_REQUIREMENTS",
            }
        )
    return systems


def _gap_texts(record: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("gaps", "gap_notes"):
        value = record.get(key)
        if isinstance(value, Mapping):
            value = list(value.values())
        if isinstance(value, Sequence) and not isinstance(value, str):
            values.extend(_text(item) for item in value)
        elif _text(value):
            values.append(_text(value))
    if not values:
        value = record.get("gap_import_notes") or record.get("gaps_import_notes")
        if _text(value):
            # Generated rows use sentence-like fragments; keep each fragment
            # bounded instead of surfacing a long implementation note.
            values.extend(part.strip() for part in re.split(r"(?<=[.!?])\s+", _text(value)) if part.strip())
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _safe_detail(value, 360)
        key = re.sub(r"[^a-z0-9]+", " ", cleaned.casefold()).strip()
        if not cleaned or key in seen:
            continue
        # This sentence is still useful as an import exposure, but repeating
        # it across every breadth row creates clutter in the bottleneck list.
        seen.add(key)
        result.append(cleaned)
    return result


def _is_generic_import_note(value: str) -> bool:
    lowered = value.casefold()
    return (
        "imported capital equipment, materials, or subcomponents may remain" in lowered
        or "imported content may occur in high-grade materials" in lowered
        or "trade eligibility and a reported factory footprint" in lowered
    )


def _bottlenecks(
    record: Mapping[str, Any],
    catalog: IndiaCatalog | None,
    title: str,
    limit: int = 7,
) -> list[dict[str, Any]]:
    candidates: list[tuple[int, int, str, str, str, Mapping[str, Any]]] = []

    def add(source: Mapping[str, Any], detail: str, depth: int) -> None:
        status = _normalize_status(source.get("status") or source.get("india_status"))
        if status in {"AVAILABLE", "STRONG"}:
            return
        label = _friendly_label(source, title)
        candidates.append(
            (
                _BOTTLENECK_PRIORITY.get(status, 8),
                depth,
                re.sub(r"[^a-z0-9]+", " ", detail.casefold()).strip(),
                label,
                detail,
                source,
            )
        )

    for detail in _gap_texts(record):
        if not _is_generic_import_note(detail):
            add(record, detail, 0)

    dependencies = _dependencies(record)
    for group in DEP_GROUPS:
        for reference in dependencies[group]:
            child = _record_for_reference(catalog, reference)
            if child.get("is_reference_only"):
                label = _friendly_label(child, reference)
                add(child, f"{label} capability remains unknown.", 1)
                continue
            child_gaps = _gap_texts(child)
            if child_gaps:
                for detail in child_gaps[:2]:
                    add(child, detail, 1)
            else:
                status = _normalize_status(child.get("status") or child.get("india_status"))
                if status not in {"AVAILABLE", "STRONG"}:
                    add(child, f"{_friendly_label(child, reference)} remains {_STATUS_LABELS[status].casefold()} in the catalog overlay.", 1)

    candidates.sort(key=lambda item: item[:4])
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rank, (_priority, _depth, detail_key, label, detail, source) in enumerate(candidates, start=1):
        if not detail_key or detail_key in seen:
            continue
        seen.add(detail_key)
        status = _normalize_status(source.get("status") or source.get("india_status"))
        result.append(
            {
                "rank": len(result) + 1,
                "name": label,
                "status": status,
                "status_label": _STATUS_LABELS[status],
                "severity": "high" if _BOTTLENECK_PRIORITY.get(status, 8) <= 3 else "medium",
                "detail": detail,
                "epistemic_class": _epistemic(source),
                "basis": _safe_detail(source.get("status_basis") or "Ranked from the existing status and gap overlay; validate before acting.", 320),
            }
        )
        if len(result) >= max(1, min(int(limit), 7)):
            break
    return result


def _localization_path(record: Mapping[str, Any], title: str) -> list[dict[str, Any]]:
    raw = record.get("making_ladder") or record.get("making_ladder_detail") or ()
    steps: list[dict[str, Any]] = []
    for index, raw_step in enumerate(_iter_refs(raw), start=1):
        if isinstance(raw_step, Mapping):
            action = _text(raw_step.get("action") or "DEVELOP").upper()
            purpose = raw_step.get("purpose") or raw_step.get("text") or raw_step.get("step") or ""
            condition = raw_step.get("condition") or ""
            required = bool(raw_step.get("required", True))
            sequence = raw_step.get("sequence") or index
            stage = _text(raw_step.get("stage"))
            allowed = raw_step.get("allowed_actions") or ()
        else:
            action = _text(getattr(raw_step, "action", "DEVELOP")).upper()
            purpose = getattr(raw_step, "purpose", "")
            condition = getattr(raw_step, "condition", "")
            required = True
            sequence = getattr(raw_step, "sequence", index)
            stage = ""
            allowed = ()
        if action not in {"IMPORT", "DEVELOP", "LICENSE", "JV", "BUILD", "SUBSTITUTE", "REDESIGN", "R&D"}:
            action = "DEVELOP"
        try:
            sequence_value = int(sequence)
        except (TypeError, ValueError):
            sequence_value = index
        clean_purpose = _safe_detail(purpose, 360)
        if not clean_purpose:
            clean_purpose = f"Advance the route for {_humanize_text(title)}."
        steps.append(
            {
                "sequence": sequence_value,
                "action": action,
                "phase": _STAGE_LABELS.get(stage, _humanize_text(stage)) if stage else "Next route step",
                "purpose": clean_purpose,
                "condition": _safe_detail(condition, 360),
                "required": required,
                "allowed_actions": [
                    _text(candidate).upper()
                    for candidate in _iter_refs(allowed)
                    if _text(candidate).upper() in {"IMPORT", "DEVELOP", "LICENSE", "JV", "BUILD", "SUBSTITUTE", "REDESIGN", "R&D"}
                ],
            }
        )
    steps.sort(key=lambda item: (item["sequence"], item["action"], item["purpose"]))
    # Keep the route concise.  The full ladder remains available through the
    # existing record endpoint; this product surface should fit the first view.
    return steps[:6]


def _link_items(record: Mapping[str, Any], catalog: IndiaCatalog | None, relation: str, limit: int = 24) -> list[dict[str, Any]]:
    refs = _iter_refs(record.get(relation))
    rows: list[dict[str, Any]] = []
    for reference in refs:
        child = _record_for_reference(catalog, reference)
        rows.append(
            {
                "name": _friendly_label(child, reference),
                "kind": _humanize_text(child.get("kind") or "CAPABILITY").upper(),
                "domain": _safe_detail(child.get("domain") or "Shared industrial foundation", 160),
                "status": _normalize_status(child.get("status") or child.get("india_status")),
                "status_label": _STATUS_LABELS[_normalize_status(child.get("status") or child.get("india_status"))],
                "epistemic_class": _epistemic(child),
                "data_state": "LIMITED_DATA" if bool(child.get("is_reference_only")) else "CATALOG_RECORD",
            }
        )
    return _dedupe_items(rows, limit=limit)


def _evidence_summary(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    epistemic = _epistemic(record)
    status = _normalize_status(record.get("status") or record.get("india_status"))
    basis = _safe_detail(record.get("status_basis") or "No status basis was attached; keep the result UNKNOWN.", 420)
    return [
        {
            "label": "Status basis",
            "summary": basis,
            "status": status,
            "epistemic_class": epistemic,
        },
        {
            "label": "Evidence coverage",
            "summary": "The India V1 catalog is a navigation overlay. Record-level evidence, qualification, effective capacity, and facility records are not attached to this view.",
            "status": "UNKNOWN",
            "epistemic_class": "UNKNOWN",
        },
    ]


def _import_items(record: Mapping[str, Any], catalog: IndiaCatalog | None) -> list[dict[str, Any]]:
    notes: list[tuple[str, str, str]] = []
    root_status = _normalize_status(record.get("status") or record.get("india_status"))
    for value in _iter_refs(record.get("import_notes")):
        if _text(value):
            notes.append((_safe_detail(value, 360), root_status, _epistemic(record)))
    for group in DEP_GROUPS:
        for reference in _dependencies(record)[group]:
            child = _record_for_reference(catalog, reference)
            child_status = _normalize_status(child.get("status") or child.get("india_status"))
            if child_status != "IMPORT_DEPENDENT":
                continue
            for value in _iter_refs(child.get("import_notes")):
                if _text(value):
                    notes.append((_safe_detail(value, 360), child_status, _epistemic(child)))
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for summary, status, epistemic in notes:
        key = re.sub(r"[^a-z0-9]+", " ", summary.casefold()).strip()
        if not summary or key in seen:
            continue
        seen.add(key)
        result.append({"summary": summary, "status": status, "status_label": _STATUS_LABELS[status], "epistemic_class": epistemic})
        if len(result) >= 8:
            break
    return result


def _resolve_subject(subject: str | Mapping[str, Any], catalog: IndiaCatalog) -> Mapping[str, Any]:
    if isinstance(subject, Mapping):
        record_id = _record_key(subject)
        if record_id and record_id in catalog.by_id:
            return catalog.by_id[record_id]
        return subject
    query = _text(subject)
    if not query:
        raise LookupError("a record id or product search query is required")
    if query in catalog.by_id:
        return catalog.by_id[query]
    search_query = re.sub(r"\bcentres?\b", lambda match: "centers" if match.group(0).casefold().endswith("s") else "center", query, flags=re.IGNORECASE)
    hits = catalog.search_hits(search_query, limit=12, include_variants=False)
    selected = next((hit["record"] for hit in hits if not hit["record"].get("is_reference_only")), None)
    if selected is None:
        selected = next((hit["record"] for hit in hits), None)
    if selected is None:
        raise LookupError(f"no India V1 product matched '{query}'")
    return selected


def _buildability(record: Mapping[str, Any], catalog: IndiaCatalog | None) -> dict[str, Any]:
    status = _normalize_status(record.get("status") or record.get("india_status"))
    groups = _requirement_groups(record, catalog)
    evaluated: list[Mapping[str, Any]] = [record]
    seen = {_record_key(record)}
    for group in DEP_GROUPS:
        for reference in _dependencies(record)[group]:
            row = _record_for_reference(catalog, reference)
            key = _record_key(row, reference)
            if key in seen:
                continue
            seen.add(key)
            evaluated.append(row)
    exact_status_counts = Counter(_normalize_status(row.get("status") or row.get("india_status")) for row in evaluated)
    epistemic_counts = Counter(_epistemic(row) for row in evaluated)
    bucket_counts = Counter(_STATUS_TO_BUCKET[exact_status_counts_key] for exact_status_counts_key in exact_status_counts.elements())
    return {
        "available": int(bucket_counts.get("available", 0)),
        "partial_or_import_dependent": int(bucket_counts.get("partial_or_import_dependent", 0)),
        "missing": int(bucket_counts.get("missing", 0)),
        "unknown": int(bucket_counts.get("unknown", 0)),
        "evaluated_node_count": len(evaluated),
        "status_counts": dict(sorted(exact_status_counts.items())),
        "epistemic_counts": dict(sorted(epistemic_counts.items())),
        "root_status": status,
        "root_status_label": _STATUS_LABELS[status],
        "root_epistemic_class": _epistemic(record),
        "overall_index": None,
        "overall_index_basis": "Not computed: V1 statuses are broad navigation priors, without evidence- or capacity-weighted derivation.",
    }


@dataclass(frozen=True)
class BuildabilityViewModel(Mapping[str, Any]):
    """Stable public composition object; no canonical IDs are serialized."""

    title: str
    domain: str
    kind: str
    plain_summary: str
    buildability: Mapping[str, Any]
    major_systems: Sequence[Mapping[str, Any]]
    critical_bottlenecks: Sequence[Mapping[str, Any]]
    localization_path: Sequence[Mapping[str, Any]]
    components: Sequence[Mapping[str, Any]]
    processes: Sequence[Mapping[str, Any]]
    equipment: Sequence[Mapping[str, Any]]
    tooling: Sequence[Mapping[str, Any]]
    materials: Sequence[Mapping[str, Any]]
    metrology: Sequence[Mapping[str, Any]]
    qualification: Sequence[Mapping[str, Any]]
    capabilities: Sequence[Mapping[str, Any]]
    upstream: Sequence[Mapping[str, Any]]
    downstream: Sequence[Mapping[str, Any]]
    unlocks: Sequence[Mapping[str, Any]]
    related: Sequence[Mapping[str, Any]]
    evidence_summary: Sequence[Mapping[str, Any]]
    imports: Sequence[Mapping[str, Any]] = ()
    facilities: Sequence[Mapping[str, Any]] = ()
    map_points: Sequence[Mapping[str, Any]] = ()
    variant: str = ""
    category: str = ""
    optional_panels: Mapping[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": VIEW_MODEL_SCHEMA_VERSION,
            "title": self.title,
            "variant": self.variant,
            "domain": self.domain,
            "kind": self.kind,
            "category": self.category,
            "plain_summary": self.plain_summary,
            "buildability": deepcopy(dict(self.buildability)),
            "major_systems": deepcopy(list(self.major_systems)),
            "critical_bottlenecks": deepcopy(list(self.critical_bottlenecks)),
            "localization_path": deepcopy(list(self.localization_path)),
            "components": deepcopy(list(self.components)),
            "processes": deepcopy(list(self.processes)),
            "equipment": deepcopy(list(self.equipment)),
            "tooling": deepcopy(list(self.tooling)),
            "materials": deepcopy(list(self.materials)),
            "metrology": deepcopy(list(self.metrology)),
            "qualification": deepcopy(list(self.qualification)),
            "capabilities": deepcopy(list(self.capabilities)),
            "upstream": deepcopy(list(self.upstream)),
            "downstream": deepcopy(list(self.downstream)),
            "unlocks": deepcopy(list(self.unlocks)),
            "related": deepcopy(list(self.related)),
            "evidence_summary": deepcopy(list(self.evidence_summary)),
            "optional_panels": deepcopy(dict(self.optional_panels or {})),
        }
        # Unsupported data is intentionally omitted from the primary panel
        # arrays.  The optional panel state gives a compact honest explanation
        # for clients that want to render a limited-data card.
        if self.imports:
            payload["imports"] = deepcopy(list(self.imports))
        if self.facilities:
            payload["facilities"] = deepcopy(list(self.facilities))
        if self.map_points:
            payload["map_points"] = deepcopy(list(self.map_points))
        return payload

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def __iter__(self):
        return iter(self.to_dict())

    def __len__(self) -> int:
        return len(self.to_dict())


def compose_buildability_view_model(
    subject: str | Mapping[str, Any],
    catalog: IndiaCatalog | None = None,
    *,
    bottleneck_limit: int = 7,
) -> BuildabilityViewModel:
    """Compose one product answer from existing catalog records.

    ``subject`` may be an exact catalog ID (useful to API callers) or a
    human-facing search query (the normal UI path).  The returned object has no
    ``id``, ``canonical_name``, ``record_id``, or source-pack identifiers.
    """

    catalog = catalog or get_catalog()
    record = _resolve_subject(subject, catalog)
    title = _friendly_label(record, "Selected industrial product")
    variant = _safe_detail(record.get("variant_label") or "", 180)
    if variant.casefold() == title.casefold():
        variant = ""
    domain = _safe_detail(record.get("domain") or "Shared industrial foundations", 180)
    kind = _humanize_text(record.get("kind") or "PRODUCT").upper()
    category = _safe_detail(record.get("category") or "Industrial requirement", 160)
    groups = _requirement_groups(record, catalog)
    links = {
        relation: _link_items(record, catalog, relation)
        for relation in ("upstream", "downstream", "related")
    }
    downstream = links["downstream"]
    optional_panels = {
        "facilities": {
            "state": "LIMITED_DATA",
            "message": "No geocoded facility, supplier, or qualified-capacity records are attached to the India V1 catalog.",
        },
        "map": {
            "state": "LIMITED_DATA",
            "message": "No map points are available in this read model; geography must not be inferred from the domain label.",
        },
        "capacity": {
            "state": "LIMITED_DATA",
            "message": "The catalog status overlay does not provide effective capacity, utilization, yield, or allocation.",
        },
    }
    payload = BuildabilityViewModel(
        title=title,
        variant=variant,
        domain=domain,
        kind=kind,
        category=category,
        plain_summary=_safe_detail(record.get("explanation") or "The catalog does not provide a plain-language product summary.", 720),
        buildability=_buildability(record, catalog),
        major_systems=_major_systems(record, catalog, groups),
        critical_bottlenecks=_bottlenecks(record, catalog, title, limit=bottleneck_limit),
        localization_path=_localization_path(record, title),
        components=groups["components"],
        processes=groups["processes"],
        equipment=groups["equipment"],
        tooling=groups["tooling"],
        materials=groups["materials"],
        metrology=groups["metrology"],
        qualification=groups["qualification"],
        capabilities=groups["capabilities"],
        upstream=links["upstream"],
        downstream=downstream,
        unlocks=deepcopy(downstream),
        related=links["related"],
        evidence_summary=_evidence_summary(record),
        imports=_import_items(record, catalog),
        optional_panels=optional_panels,
    )
    return payload


# Friendly aliases make the adapter discoverable without coupling callers to
# one naming preference.
buildability_view_model = compose_buildability_view_model
compose_buildability = compose_buildability_view_model
compose_view_model = compose_buildability_view_model


__all__ = [
    "VIEW_MODEL_SCHEMA_VERSION",
    "STATUS_BUCKETS",
    "BuildabilityViewModel",
    "compose_buildability_view_model",
    "buildability_view_model",
    "compose_buildability",
    "compose_view_model",
]
