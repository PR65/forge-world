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

from .architecture import compile_product_architecture
from .catalog import DEP_GROUPS, IndiaCatalog, get_catalog
from .objective_models import ArchitectureNodeKind


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
    "SCALE_LIMITED": 2,
    "PARTIAL": 3,
    "CONFLICTED": 4,
    "AVAILABLE": 9,
    "STRONG": 9,
    "UNKNOWN": 9,
}

_BOTTLENECK_ELIGIBLE = {
    "MISSING",
    "IMPORT_DEPENDENT",
    "SCALE_LIMITED",
    "PARTIAL",
    "CONFLICTED",
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
    "industrial_environment": "Industrial environment",
}

_VIEW_DEP_GROUPS = (*DEP_GROUPS, "components")

_INDUSTRIAL_ENVIRONMENT_CATEGORIES = (
    "shared industrial system",
    "shared utility system",
    "shared digital system",
    "shared assurance system",
    "shared logistics system",
    "shared thermal system",
    "shared controlled environment",
)

_STAGE_LABELS = {
    "start_locally": "Start locally",
    "source_initially": "Source initially",
    "integrate_and_test": "Integrate and test",
    "localize_next": "Localize next",
    "develop_later": "Develop later",
}

# Small presentation scaffolds for the launch-candidate products whose source
# records contain good manufacturing dependencies but no explicit subsystem
# group.  These are physical architecture labels only: every generated node is
# MODELLED/UNKNOWN and therefore makes no India capability or supply claim.
_PRODUCT_ARCHITECTURES: tuple[tuple[re.Pattern[str], tuple[str, ...]], ...] = (
    (re.compile(r"freeze[-_: ]?dryer|lyophili", re.I), (
        "Vacuum chamber and shelf assembly", "Condenser and refrigeration package",
        "Vacuum system", "Thermal control", "Instrumentation and controls", "Loading and containment",
    )),
    (re.compile(r"battery[_: -]?energy[_: -]?storage|\bbess\b", re.I), (
        "Battery cells and modules", "Battery management system", "Racks and enclosure",
        "Power conversion system", "Thermal management", "Protection and site controls",
    )),
    (re.compile(r"cnc|machining[_: -]?cent", re.I), (
        "Machine structure", "Spindle system", "Axes and motion system", "Servo drives and controller",
        "Tooling interface", "Metrology and feedback", "Cooling and lubrication",
    )),
    (re.compile(r"centrifugal[_: -]?pump", re.I), (
        "Casing and impeller", "Shaft and bearings", "Seals", "Motor and coupling",
        "Baseplate and piping interface", "Instrumentation and protection",
    )),
    (re.compile(r"industrial[_: -]?compressor", re.I), (
        "Compression element", "Driver", "Lubrication and sealing", "Cooling package",
        "Controls and protection", "Pressure package and enclosure",
    )),
    (re.compile(r"transformer", re.I), (
        "Magnetic core", "Windings", "Insulation system", "Tank and cooling",
        "Bushings and tap changer", "Protection and test interfaces",
    )),
    (re.compile(r"robot|manipulator", re.I), (
        "Structure and joints", "Actuators and reducers", "Servo drives", "Controller",
        "Sensors and safety", "End-effector interface",
    )),
    (re.compile(r"magnetic[_: -]?resonance|\bmri\b", re.I), (
        "Magnet and cryogenic system", "Gradient coil system", "RF transmit and receive chain",
        "Patient handling", "Power and cooling", "Control and image reconstruction",
    )),
    (re.compile(r"hemodialysis|dialysis[_: -]?machine", re.I), (
        "Blood circuit and pump", "Dialyzer and fluid path", "Dialysate preparation",
        "Ultrafiltration and pressure control", "Sensors and alarms", "Cleaning and disinfection",
    )),
)

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
    chosen = re.sub(r"^(?:Foundational|Infrastructure|Equipment|Product|System)\s+(?=[A-Za-z])", "", chosen, flags=re.IGNORECASE).strip()
    return chosen or "Unspecified requirement"


def _public_qualifier(record: Mapping[str, Any], title: str) -> str:
    display = _text(record.get("display_name") or record.get("canonical_name"))
    if display:
        parts = [part.strip() for part in re.split(r"\s+[—–\ufffd]\s+", display) if part.strip()]
        if len(parts) > 1:
            qualifier = " · ".join(parts[1:])
            if qualifier.casefold() != title.casefold():
                return _safe_detail(qualifier, 180)
    return _safe_detail(record.get("variant_label") or "", 180)


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
    groups = {group: [] for group in _VIEW_DEP_GROUPS}
    if isinstance(raw, Mapping):
        for group in _VIEW_DEP_GROUPS:
            groups[group] = _iter_refs(raw.get(group))
    # Lightweight callers sometimes only provide a flat dependency list.  It
    # is kept visible under capabilities, with UNKNOWN remaining the honest
    # fallback for the missing typed grouping.
    if not any(groups.values()):
        groups["capabilities"] = _iter_refs(record.get("dependency_ids"))
    return groups


def _public_record_text(value: Any, *, fallback: str) -> str:
    text = _safe_detail(value, 360)
    if re.search(
        r"\b(?:reference primitive|shared-foundation baseline|reusable industrial concept|"
        r"category is visible|deduplicated|source pack|canonical (?:v1 )?record|catalog overlay)\b",
        text,
        re.IGNORECASE,
    ):
        return fallback
    return text or fallback


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
    public_summary = _public_record_text(
        summary or record.get("explanation"),
        fallback="Mapped industrial requirement; confirm the objective-specific specification and production route.",
    )
    public_basis = _public_record_text(
        basis,
        fallback=(
            "The requirement is structurally mapped, but its supplier, facility, specification, qualification, "
            "and effective capacity still need validation."
        ),
    )
    item = {
        "name": _friendly_label(record, fallback),
        "role": _GROUP_LABELS.get(role, _humanize_text(role)),
        "kind": _humanize_text(record.get("kind") or "CAPABILITY").upper(),
        "status": status,
        "status_label": _STATUS_LABELS[status],
        "epistemic_class": _epistemic(record),
        "summary": _safe_detail(public_summary, 280),
        "basis": public_basis,
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
    subject_label = _friendly_label(record).casefold()
    for group in _VIEW_DEP_GROUPS:
        rows = []
        for reference in dependencies[group]:
            row = _record_for_reference(catalog, reference)
            if _friendly_label(row, reference).casefold() == subject_label:
                continue
            rows.append(_status_item(row, role=group, fallback=reference))
        base[group] = _dedupe_items(rows)

    # Components are only emitted when the source gives an explicit component
    # group or a product-like dependency.  This avoids relabelling a process
    # or capability as a component merely to fill a dashboard card.
    components: list[dict[str, Any]] = []
    for reference in dependencies.get("components", ()):
        row = _record_for_reference(catalog, reference)
        if _friendly_label(row, reference).casefold() == subject_label:
            continue
        components.append(_status_item(row, role="components", fallback=reference))

    all_rows: list[tuple[str, Mapping[str, Any]]] = []
    for group in _VIEW_DEP_GROUPS:
        all_rows.extend(
            (group, child)
            for reference in dependencies[group]
            for child in (_record_for_reference(catalog, reference),)
            if _friendly_label(child, reference).casefold() != subject_label
        )

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
    architecture = compile_product_architecture(record, catalog, max_depth=2)
    physical = [
        node
        for node in architecture.nodes
        if node.id != architecture.product_record_id
        and node.kind in {ArchitectureNodeKind.PRODUCT_SYSTEM, ArchitectureNodeKind.PRODUCT_COMPONENT}
        and node.depth <= 2
    ]
    if physical:
        return _dedupe_items(
            {
                "name": node.label,
                "role": "Product architecture",
                "kind": "SYSTEM" if node.kind is ArchitectureNodeKind.PRODUCT_SYSTEM else "COMPONENT",
                "status": _normalize_status(node.status),
                "status_label": _STATUS_LABELS[_normalize_status(node.status)],
                "epistemic_class": node.epistemic_class,
                "summary": node.description or "Explicit physical node in the mapped product architecture.",
                "basis": "Physical relationship compiled from typed India V1 record structure.",
                "data_state": "COMPILED_PRODUCT_ARCHITECTURE",
                "derivation_class": node.derivation_class.value,
            }
            for node in physical
        )

    identity = " ".join(
        _text(record.get(key))
        for key in ("id", "family_key", "family_label", "display_name", "canonical_name")
    )
    architecture = next((labels for pattern, labels in _PRODUCT_ARCHITECTURES if pattern.search(identity)), ())
    return [
        {
            "name": label,
            "role": "Product architecture",
            "kind": "SYSTEM",
            "status": "UNKNOWN",
            "status_label": "India status not verified",
            "epistemic_class": "MODELLED",
            "summary": "Physical subsystem in the first-order product architecture.",
            "basis": "Architecture scaffold only; it does not assert a supplier, qualification, or effective capacity.",
            "data_state": "MODELLED_PRODUCT_ARCHITECTURE",
            "derivation_class": "MODELLED",
        }
        for label in architecture
    ]


def _is_industrial_environment(record: Mapping[str, Any]) -> bool:
    category = _text(record.get("category")).casefold()
    label = _friendly_label(record).casefold()
    if any(category.startswith(prefix) for prefix in _INDUSTRIAL_ENVIRONMENT_CATEGORIES):
        return True
    return bool(re.search(
        r"\b(?:industrial infrastructure base|industrial power supply|industrial water|utility services|"
        r"industrial logistics|factory infrastructure|site services|general utilities)\b",
        label,
    ))


def _industrial_environment(record: Mapping[str, Any], catalog: IndiaCatalog | None) -> list[dict[str, Any]]:
    dependencies = _dependencies(record)
    rows: list[dict[str, Any]] = []
    for reference in dependencies.get("systems", ()):
        child = _record_for_reference(catalog, reference)
        if _is_industrial_environment(child):
            rows.append(_status_item(child, role="industrial_environment", fallback=reference))
    return _dedupe_items(rows, limit=12)


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


def _is_evidence_gap(value: str) -> bool:
    return bool(re.search(
        r"\b(?:no validated india capability|status remains unknown|requires? evidence|"
        r"canonical specification.*unknown|qualification and effective capacity.*unknown|"
        r"eligibility is not supply|trade or assembly is not treated|"
        r"shared primitive is intentionally broad|catalog overlay)\b",
        value,
        re.IGNORECASE,
    ))


def _public_bottleneck_detail(status: str, name: str, detail: str) -> str:
    """Translate catalog/status boilerplate into an operational decision statement."""

    lowered = detail.casefold()
    boilerplate = (
        detail.casefold() == name.casefold()
        or any(
            marker in lowered
            for marker in (
                "category is visible",
                "curated shared-foundation baseline",
                "reusable industrial concept",
                "catalog overlay",
                "canonical record",
                "source pack",
                "remain unknown",
            )
        )
    )
    if not boilerplate:
        return detail
    templates = {
        "MISSING": "No qualified Indian route is currently mapped for this requirement; identify a make, partner, or redesign path.",
        "IMPORT_DEPENDENT": "Confirm the imported subcomponents, qualified source, lead time, service coverage, and localization route.",
        "SCALE_LIMITED": "Demonstrate the required throughput, yield, quality consistency, and ramp path at production scale.",
        "PARTIAL": "Capability exists in some form, but the required specification, qualification, yield, and scalable throughput are not yet established.",
        "CONFLICTED": "Available evidence disagrees; resolve the supplier, facility, specification, and qualification facts before committing.",
    }
    return templates.get(status, detail)


def _bottlenecks(
    record: Mapping[str, Any],
    catalog: IndiaCatalog | None,
    title: str,
    limit: int = 7,
) -> list[dict[str, Any]]:
    candidates: list[tuple[int, int, str, str, str, Mapping[str, Any]]] = []

    def add(source: Mapping[str, Any], detail: str, depth: int) -> None:
        status = _normalize_status(source.get("status") or source.get("india_status"))
        if status not in _BOTTLENECK_ELIGIBLE or _is_evidence_gap(detail):
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
        if not _is_generic_import_note(detail) and not _is_evidence_gap(detail):
            add(record, detail, 0)

    dependencies = _dependencies(record)
    for group in DEP_GROUPS:
        for reference in dependencies[group]:
            child = _record_for_reference(catalog, reference)
            if _friendly_label(child, reference).casefold() == title.casefold():
                continue
            if child.get("is_reference_only"):
                continue
            child_gaps = [
                detail for detail in _gap_texts(child)
                if not _is_generic_import_note(detail) and not _is_evidence_gap(detail)
            ]
            if child_gaps:
                for detail in child_gaps[:2]:
                    add(child, detail, 1)
                continue
            status = _normalize_status(child.get("status") or child.get("india_status"))
            if status in _BOTTLENECK_ELIGIBLE:
                add(child, _friendly_label(child, reference), 1)

    candidates.sort(key=lambda item: item[:4])
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rank, (_priority, _depth, detail_key, label, detail, source) in enumerate(candidates, start=1):
        if not detail_key or detail_key in seen:
            continue
        seen.add(detail_key)
        status = _normalize_status(source.get("status") or source.get("india_status"))
        public_detail = _public_bottleneck_detail(status, label, detail)
        result.append(
            {
                "rank": len(result) + 1,
                "name": label,
                "status": status,
                "status_label": _STATUS_LABELS[status],
                "severity": "high" if _BOTTLENECK_PRIORITY.get(status, 8) <= 3 else "medium",
                "detail": public_detail,
                "epistemic_class": _epistemic(source),
                "basis": (
                    "Current atlas status; validate the supplier, facility, specification, qualification, "
                    "and effective capacity before acting."
                ),
            }
        )
        if len(result) >= max(1, min(int(limit), 7)):
            break
    return result


def _frontier_questions(groups: Mapping[str, Sequence[Mapping[str, Any]]], limit: int = 6) -> list[dict[str, Any]]:
    templates = {
        "components": "Can {name} be sourced or made in India at the required specification and qualification?",
        "processes": "Can {name} be performed locally at the required process window, yield, and repeatability?",
        "equipment": "Is {name} available in India with the required accuracy, duty cycle, and service support?",
        "materials": "Is {name} available domestically in the required grade, purity, and volume?",
        "capabilities": "Is {name} available in India for this product's specification and qualification route?",
        "metrology": "Can {name} be measured and accepted locally at the required tolerance?",
        "qualification": "Can {name} be completed locally for the target customer or regulator?",
    }
    questions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for group in ("components", "equipment", "processes", "materials", "capabilities", "metrology", "qualification"):
        for item in groups.get(group, ()):
            status = _normalize_status(item.get("status"))
            epistemic = _text(item.get("epistemic_class")).upper()
            if status != "UNKNOWN" and not (epistemic == "ASSUMPTION" and status in _BOTTLENECK_ELIGIBLE):
                continue
            name = _text(item.get("name"))
            key = re.sub(r"[^a-z0-9]+", " ", name.casefold()).strip()
            if not key or key in seen or name.casefold() in {"detailed product requirements", "unspecified requirement"}:
                continue
            seen.add(key)
            question = templates[group].format(name=name)
            if status == "IMPORT_DEPENDENT":
                question = f"Which part of {name} remains import-sensitive at the required specification and scale?"
            questions.append({
                "question": question,
                "subject": name,
                "reason": "The dependency is structurally mapped, but its objective-specific India status is not verified.",
                "status": "UNKNOWN",
                "epistemic_class": item.get("epistemic_class") or "UNKNOWN",
            })
            if len(questions) >= max(1, min(int(limit), 8)):
                return questions
    return questions


def _names(items: Sequence[Mapping[str, Any]], limit: int = 2) -> str:
    labels = [_text(item.get("name")) for item in items if _text(item.get("name"))][:limit]
    if len(labels) > 1:
        return f"{', '.join(labels[:-1])} and {labels[-1]}"
    return labels[0] if labels else ""


def _localization_path(
    record: Mapping[str, Any],
    title: str,
    groups: Mapping[str, Sequence[Mapping[str, Any]]],
    systems: Sequence[Mapping[str, Any]],
    bottlenecks: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    all_requirements = [item for group in groups.values() for item in group]
    available = [item for item in all_requirements if _normalize_status(item.get("status")) in {"AVAILABLE", "STRONG"}]
    constrained = [item for item in all_requirements if _normalize_status(item.get("status")) in {"IMPORT_DEPENDENT", "MISSING", "SCALE_LIMITED"}]
    quality = [*groups.get("metrology", ()), *groups.get("qualification", ())]
    first_systems = _names(systems, 2)
    product = _humanize_text(title)
    steps: list[dict[str, Any]] = []

    start_focus = _names(available, 2) or first_systems
    steps.append({
        "sequence": 1,
        "action": "BUILD",
        "phase": _STAGE_LABELS["start_locally"],
        "purpose": (
            f"Begin with the mapped local base around {start_focus}, then define a narrow assembly and integration boundary."
            if available else
            f"Start by defining the fabrication, assembly, and integration boundary for {product} around {start_focus or 'its mapped architecture'}."
        ),
        "condition": "Confirm specification, supplier readiness, and acceptance criteria before treating any item as locally production-ready.",
        "required": True,
        "status": available[0].get("status") if available else "UNKNOWN",
    })
    source_focus = _names(constrained, 3) or _names(groups.get("equipment", ()), 3)
    if source_focus:
        steps.append({
            "sequence": len(steps) + 1,
            "action": "IMPORT",
            "phase": _STAGE_LABELS["source_initially"],
            "purpose": f"Keep {source_focus} open to initial external sourcing while local integration evidence develops.",
            "condition": "This is a starting boundary, not a claim that imports are available, allocated, or qualified.",
            "required": True,
            "status": constrained[0].get("status") if constrained else "UNKNOWN",
        })
    quality_focus = _names(quality, 3)
    steps.append({
        "sequence": len(steps) + 1,
        "action": "DEVELOP",
        "phase": _STAGE_LABELS["integrate_and_test"],
        "purpose": (
            f"Establish assembly, inspection, and acceptance around {quality_focus}."
            if quality_focus else
            f"Create a product-specific integration, inspection, and acceptance test for {product}."
        ),
        "condition": "Do not claim production readiness until product-specific acceptance and qualification gates pass.",
        "required": True,
        "status": quality[0].get("status") if quality else "UNKNOWN",
    })
    if bottlenecks:
        focus = _text(bottlenecks[0].get("detail") or bottlenecks[0].get("name"))
        steps.append({
            "sequence": len(steps) + 1,
            "action": "DEVELOP",
            "phase": _STAGE_LABELS["localize_next"],
            "purpose": f"Localize or redesign around {focus} after the initial integration route is stable.",
            "condition": "Prioritize this only after verifying that it remains decision-critical for the chosen specification.",
            "required": True,
            "status": bottlenecks[0].get("status") or "UNKNOWN",
        })
    later = [item for item in groups.get("capabilities", ()) if _normalize_status(item.get("status")) != "AVAILABLE"]
    later_focus = _names(later, 2)
    if later_focus:
        steps.append({
            "sequence": len(steps) + 1,
            "action": "R&D",
            "phase": _STAGE_LABELS["develop_later"],
            "purpose": f"Deepen {later_focus} once demand, interfaces, and the qualification route are stable.",
            "condition": "Treat this as capability development; licensing or equipment purchase alone does not establish local know-how.",
            "required": False,
            "status": later[0].get("status") or "UNKNOWN",
        })
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
    basis = _public_record_text(
        "No validated India capability or supply record is attached; status remains UNKNOWN."
        if record.get("is_reference_only")
        else record.get("status_basis")
        or "No status basis was attached; keep the result UNKNOWN.",
        fallback=(
            "The current atlas establishes a first-order India status, but the product-specific supplier, "
            "facility, qualification, and effective-capacity evidence still needs validation."
        ),
    )
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
    frontier_questions: Sequence[Mapping[str, Any]]
    components: Sequence[Mapping[str, Any]]
    processes: Sequence[Mapping[str, Any]]
    equipment: Sequence[Mapping[str, Any]]
    tooling: Sequence[Mapping[str, Any]]
    materials: Sequence[Mapping[str, Any]]
    metrology: Sequence[Mapping[str, Any]]
    qualification: Sequence[Mapping[str, Any]]
    capabilities: Sequence[Mapping[str, Any]]
    industrial_environment: Sequence[Mapping[str, Any]]
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
            "frontier_questions": deepcopy(list(self.frontier_questions)),
            "components": deepcopy(list(self.components)),
            "processes": deepcopy(list(self.processes)),
            "equipment": deepcopy(list(self.equipment)),
            "tooling": deepcopy(list(self.tooling)),
            "materials": deepcopy(list(self.materials)),
            "metrology": deepcopy(list(self.metrology)),
            "qualification": deepcopy(list(self.qualification)),
            "capabilities": deepcopy(list(self.capabilities)),
            "industrial_environment": deepcopy(list(self.industrial_environment)),
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
    variant = _public_qualifier(record, title)
    if variant.casefold() == title.casefold():
        variant = ""
    domain = _safe_detail(record.get("domain") or "Shared industrial foundations", 180)
    kind = _humanize_text(record.get("kind") or "PRODUCT").upper()
    category = _safe_detail(record.get("category") or "Industrial requirement", 160)
    is_reference = bool(record.get("is_reference_only"))
    if category.casefold() == "reference primitive":
        category = "Industrial family bridge"
    groups = _requirement_groups(record, catalog)
    systems = _major_systems(record, catalog, groups)
    bottlenecks = _bottlenecks(record, catalog, title, limit=bottleneck_limit)
    frontier_questions = _frontier_questions(groups)
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
        plain_summary=_safe_detail(
            "Exact product detail is limited; this family bridge does not establish a producer or supply claim."
            if is_reference
            else record.get("explanation")
            or "The catalog does not provide a plain-language product summary.",
            720,
        ),
        buildability=_buildability(record, catalog),
        major_systems=systems,
        critical_bottlenecks=bottlenecks,
        localization_path=_localization_path(record, title, groups, systems, bottlenecks),
        frontier_questions=frontier_questions,
        components=groups["components"],
        processes=groups["processes"],
        equipment=groups["equipment"],
        tooling=groups["tooling"],
        materials=groups["materials"],
        metrology=groups["metrology"],
        qualification=groups["qualification"],
        capabilities=groups["capabilities"],
        industrial_environment=_industrial_environment(record, catalog),
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
