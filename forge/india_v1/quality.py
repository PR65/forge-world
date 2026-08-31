"""Deterministic quality helpers for the India V1 breadth atlas.

The breadth packs deliberately generate many read-model records from a much
smaller family table.  This module keeps the identity and next-action logic in
one place so callers do not have to infer a family from a display string or
turn a broad status label into a claim of local production.

The helpers are intentionally read-only: they accept a mapping (or stable
record id), return ordinary JSON-compatible values, and never mutate the input
record.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
import re
import unicodedata
from typing import Any


QUALITY_SCHEMA_VERSION = "india_v1.quality.v1"

# Keep this in sync with the public atlas ladder vocabulary without importing
# the schema module (the data packs are also importable as standalone modules).
ALLOWED_ACTIONS = (
    "IMPORT",
    "DEVELOP",
    "LICENSE",
    "JV",
    "BUILD",
    "SUBSTITUTE",
    "REDESIGN",
    "R&D",
)

_STATUS_ALIASES = {
    "STRONG / AVAILABLE IN INDIA": "STRONG",
    "AVAILABLE IN INDIA": "AVAILABLE",
    "PARTIAL / SCALE-LIMITED": "SCALE_LIMITED",
    "MISSING / NO EVIDENCED DOMESTIC CAPABILITY": "MISSING",
    "IMPORT-DEPENDENT": "IMPORT_DEPENDENT",
    "QUALIFICATION GAP": "PARTIAL",
    "SPECIFICATION GAP": "PARTIAL",
    "CAPACITY GAP": "SCALE_LIMITED",
}

_STAGE_NAMES = (
    "local_first",
    "initial_import_bridge",
    "integration_and_test",
    "next_localization",
    "harder_later_capability",
    "optional_redesign",
)

_DOMAIN_PREFIX = {
    "10": "Infrastructure",
    "12": "Foundational",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _slug(value: Any) -> str:
    text = unicodedata.normalize("NFKC", _text(value)).casefold()
    text = text.replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_") or "unknown"


def _record_id(record_or_id: Mapping[str, Any] | str) -> str:
    if isinstance(record_or_id, Mapping):
        return _text(record_or_id.get("id") or record_or_id.get("record_id") or record_or_id.get("canonical_id"))
    return _text(record_or_id)


def _record_name(record_or_id: Mapping[str, Any] | str) -> str:
    if isinstance(record_or_id, Mapping):
        return _text(record_or_id.get("canonical_name") or record_or_id.get("name"))
    return ""


def family_key(record_or_id: Mapping[str, Any] | str) -> str:
    """Return a stable family identity for all three V1 id schemes.

    ``d01:kind:family:axis`` (the 01--04 generator),
    ``product:05:family:variant`` (the 05--08 pack), and
    ``india-v1:09:family:architecture:context`` (the 09--12 pack) all collapse
    to their first three id components.  A record's explicit family/archetype
    field wins when available; the name fallback is only for lightweight
    callers that have no id.
    """

    if isinstance(record_or_id, Mapping):
        explicit = record_or_id.get("family_key")
        if explicit:
            return _text(explicit)
        archetype = record_or_id.get("archetype_id")
        record_id = _record_id(record_or_id)
        # The breadth packs use archetype_id as either a bare family slug or a
        # node:<domain>:<family> reference.  Normalize it only when it does not
        # already carry a complete public id scheme.
        if archetype and not record_id.startswith(("d", "product:", "india-v1:")):
            archetype_text = _text(archetype)
            if archetype_text.startswith("node:"):
                parts = archetype_text.split(":")
                if len(parts) >= 3:
                    return f"india-v1:{parts[1]}:{_slug(parts[2])}"
            if archetype_text:
                return f"family:{_slug(archetype_text)}"
    else:
        record_id = _record_id(record_or_id)

    parts = record_id.split(":")
    if record_id.startswith("india-v1:") and len(parts) >= 4:
        return ":".join(parts[:4])
    if record_id.startswith("product:") and len(parts) >= 3:
        return ":".join(parts[:3])
    if len(parts) >= 3 and re.fullmatch(r"d\d{2}", parts[0]) and parts[1] in {
        "product",
        "capability",
        "process",
        "material",
        "equipment",
    }:
        return ":".join(parts[:3])

    name = _record_name(record_or_id)
    if name:
        base = re.sub(r"\s*\([^)]*\)\s*$", "", name)
        base = re.sub(
            r"\s*[—-]\s*(?:design and architecture capability|process knowledge and process control capability|"
            r"qualification and acceptance capability|scalable effective-throughput capability|"
            r"integration and production-system capability|prototype process route|series-production process route|"
            r"qualification process route|repair, recovery, and alternate-source process route|"
            r"prototype and pilot equipment|series-production equipment|inspection and metrology equipment|"
            r"qualification and acceptance-test equipment)\s*$",
            "",
            base,
            flags=re.IGNORECASE,
        )
        return f"name:{_slug(base)}"
    return f"id:{_slug(record_id)}"


def variant_label(record_or_id: Mapping[str, Any] | str) -> str:
    """Return a human-readable variant label without exposing raw id syntax."""

    if isinstance(record_or_id, Mapping):
        variant = record_or_id.get("variant")
        if isinstance(variant, Mapping):
            labels = variant.get("labels") or variant.get("keys")
            if isinstance(labels, Sequence) and not isinstance(labels, str) and labels:
                return " · ".join(_text(item) for item in labels if _text(item))
        axes = record_or_id.get("variant_axes")
        if isinstance(axes, Mapping) and axes:
            return " · ".join(
                _text(value).replace("_", " ").replace("-", " ")
                for value in axes.values()
                if _text(value)
            )
        explicit = record_or_id.get("variant_label")
        if explicit:
            return _text(explicit)
        name = _record_name(record_or_id)
        parenthesized = re.search(r"\(([^()]*)\)\s*$", name)
        if parenthesized:
            return parenthesized.group(1).strip()
        record_id = _record_id(record_or_id)
    else:
        record_id = _record_id(record_or_id)

    parts = record_id.split(":")
    if record_id.startswith("india-v1:") and len(parts) >= 5:
        return " · ".join(part.replace("_", " ").replace("-", " ") for part in parts[3:5])
    if record_id.startswith("product:") and len(parts) >= 4:
        return parts[3].replace("-", " · ")
    if len(parts) >= 4 and re.fullmatch(r"d\d{2}", parts[0]):
        return parts[3].replace("_", " ")
    return ""


def _clean_generated_name(name: str) -> str:
    value = re.sub(r"\s+", " ", _text(name)).strip()
    value = value.replace(" - ", " — ")
    value = value.replace(" / ", "/")
    return value


def _phrase_key(value: Any) -> str:
    """Normalize a rendered label for idempotence checks only."""

    return re.sub(r"[^a-z0-9]+", " ", _text(value).casefold()).strip()


def display_name(record_or_id: Mapping[str, Any] | str) -> str:
    """Build a compact display name while retaining family and variant context.

    The canonical name remains a source-facing field; this helper is intended
    for UI/read-model names and deterministic tests.  It removes parenthesized
    Cartesian suffixes and the title-case ``architecture - context`` artifact
    used by the 09--12 generator.
    """

    if not isinstance(record_or_id, Mapping):
        return _clean_generated_name(_text(record_or_id))

    record_id = _record_id(record_or_id)
    name = _clean_generated_name(_record_name(record_or_id))
    parts = record_id.split(":")
    if record_id.startswith("product:") and len(parts) >= 4:
        base = re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()
        # The breadth source packs already emit a variant-qualified canonical
        # name.  Do not append an ID-derived label a second time when the
        # catalog normalizer calls this helper on that row.
        if " — " in base:
            return base
        label = variant_label(record_or_id)
        return f"{base} — {label}" if label else base

    if record_id.startswith("india-v1:") and len(parts) >= 5:
        architecture = parts[3].replace("-", " ")
        context = parts[4].replace("-", " ")
        architecture_key = _phrase_key(architecture)
        context_key = _phrase_key(context)
        if " — " in name:
            rendered_suffix = name.rsplit(" — ", 1)[-1]
            rendered_key = _phrase_key(rendered_suffix)
            # A cleaned source name contains both architecture and context in
            # its suffix.  It is already canonical and must remain unchanged.
            if architecture_key in rendered_key and context_key in rendered_key:
                prefix_scope = _DOMAIN_PREFIX.get(parts[1]) if parts[2] in {
                    "industrial-compressor",
                    "positive-displacement-pump",
                } else None
                if prefix_scope and not _phrase_key(name).startswith(_phrase_key(prefix_scope) + " "):
                    return f"{prefix_scope} {name}".strip()
                return name
        # The old name starts with a title-cased architecture and ends with a
        # title-cased context.  Remove those generated wrappers while keeping
        # the curated archetype noun phrase's original spelling.
        base = name
        prefix = architecture.title() + " "
        if base.casefold().startswith(prefix.casefold()):
            base = base[len(prefix) :]
        suffix = " — " + context.title()
        if base.casefold().endswith(suffix.casefold()):
            base = base[: -len(suffix)].rstrip()
        label = f"{architecture} · {context}"
        prefix_scope = _DOMAIN_PREFIX.get(parts[1]) if parts[2] in {
            "industrial-compressor",
            "positive-displacement-pump",
        } else None
        if prefix_scope:
            if not _phrase_key(base).startswith(_phrase_key(prefix_scope) + " "):
                base = f"{prefix_scope} {base}"
        return f"{base} — {label}".strip()

    # Core 01--04 names contain a domain/kind prefix and a generated lifecycle
    # suffix.  Keep the family noun and the useful lifecycle stage.
    if len(parts) >= 4 and re.fullmatch(r"d\d{2}", parts[0]):
        if ":" in name:
            name = name.split(":", 1)[1].strip()
        stage = variant_label(record_or_id)
        name = re.sub(r"\s*[—-]\s*[^—-]+$", "", name).strip()
        return f"{name} — {stage}" if stage else name
    return name or _text(record_id)


def _status_label(value: Any) -> str:
    raw = _text(value).upper()
    return _STATUS_ALIASES.get(raw, raw)


def _epistemic_label(record: Mapping[str, Any]) -> str:
    return _text(
        record.get("status_epistemic_class")
        or record.get("status_epistemic")
        or record.get("epistemic_class")
    ).upper()


def correct_epistemic_status(record: Mapping[str, Any]) -> dict[str, Any]:
    """Downgrade unsupported assumption-based STRONG/MISSING labels.

    A broad taxonomy cannot prove either positive domestic capability or a
    complete absence of capability.  When those labels are backed only by an
    ``ASSUMPTION`` class, the public status becomes ``UNKNOWN``.  The previous
    label is retained in both structured metadata and an auditable basis
    suffix; all other records are returned unchanged (apart from a shallow
    copy).
    """

    output = deepcopy(dict(record))
    original = _text(output.get("status") or output.get("india_status"))
    normalized = _status_label(original)
    epistemic = _epistemic_label(output)
    if normalized not in {"STRONG", "MISSING"} or epistemic != "ASSUMPTION":
        return output

    metadata = output.get("status_basis_metadata")
    if not isinstance(metadata, Mapping):
        metadata = {}
    basis_metadata = dict(metadata)
    basis_metadata.update(
        {
            "prior_status": original,
            "prior_status_normalized": normalized,
            "prior_status_epistemic_class": epistemic,
            "correction": "unsupported_assumption_downgraded_to_UNKNOWN",
        }
    )
    output["status_basis_metadata"] = basis_metadata
    basis = _text(output.get("status_basis"))
    correction_note = (
        f" Epistemic correction: prior_status={original}; prior_status_epistemic_class={epistemic}; "
        "corrected_status=UNKNOWN because no qualifying evidence or derivation is attached."
    )
    output["status_basis"] = (basis + correction_note).strip()
    if "status" in output:
        output["status"] = "UNKNOWN"
    if "india_status" in output:
        output["india_status"] = "UNKNOWN"
    for key in ("status_epistemic_class", "status_epistemic", "epistemic_class"):
        if key in output:
            output[key] = "UNKNOWN"
    return output


def _dependency_ids(record: Mapping[str, Any]) -> list[str]:
    values = record.get("dependency_ids")
    if isinstance(values, Sequence) and not isinstance(values, str):
        return sorted({_text(value) for value in values if _text(value)})
    dependencies = record.get("dependencies") or {}
    result: list[str] = []
    if isinstance(dependencies, Mapping):
        for group in dependencies.values():
            if isinstance(group, Sequence) and not isinstance(group, str):
                result.extend(_text(value) for value in group if _text(value))
    return sorted(set(result))


def _dependency_risk(record: Mapping[str, Any]) -> set[str]:
    status = _status_label(record.get("status") or record.get("india_status"))
    risk = {"UNKNOWN", "MISSING", "IMPORT_DEPENDENT", "CONFLICTED", "SCALE_LIMITED"}
    return {status} if status in risk else set()


_DEPENDENCY_FOCUS = {
    "systems": "site, utilities, and logistics",
    "processes": "process window, yield, and validation",
    "materials": "grade, purity, and precursor route",
    "equipment": "tooling, metrology, and maintenance",
    "capabilities": "design, workforce, and qualification",
}
_KIND_FOCUS = {
    "PRODUCT": "product interfaces, BOM, and acceptance",
    "EQUIPMENT": "equipment envelope, tooling, and maintenance",
    "MATERIAL": "grade, purity, and incoming qualification",
    "PROCESS": "process route, window, and yield",
    "CAPABILITY": "design, workforce, and qualification",
}
_FOCUS_PRIORITY = ("materials", "processes", "equipment", "capabilities", "systems")


def _ladder_context(record: Mapping[str, Any], dependency_ids: Sequence[str]) -> dict[str, str]:
    """Derive a small, deterministic ladder focus from normalized record data."""

    kind = _text(record.get("kind")).upper()
    dependencies = record.get("dependencies")
    group_counts: dict[str, int] = {}
    if isinstance(dependencies, Mapping):
        for group, values in dependencies.items():
            if isinstance(values, Sequence) and not isinstance(values, str):
                group_counts[str(group).casefold()] = len([value for value in values if _text(value)])
    if not group_counts and dependency_ids:
        for dependency_id in dependency_ids:
            prefix = _text(dependency_id).split(":", 2)
            group = {
                "shared": prefix[1] if len(prefix) > 1 else "",
                "reference": prefix[1] if len(prefix) > 1 else "",
            }.get(prefix[0], prefix[0])
            group_counts[group] = group_counts.get(group, 0) + 1
    dominant_group = ""
    if group_counts:
        dominant_group = max(
            _FOCUS_PRIORITY,
            key=lambda group: (group_counts.get(group, 0), -_FOCUS_PRIORITY.index(group)),
        )
        if group_counts.get(dominant_group, 0) == 0:
            dominant_group = ""
    focus = _DEPENDENCY_FOCUS.get(dominant_group) or _KIND_FOCUS.get(kind) or "specification, evidence, and qualification"
    target = _text(record.get("family_label") or record.get("family_key") or record.get("canonical_name") or record.get("id"))
    target = re.split(r"\s+[—-]\s+", target, maxsplit=1)[0].strip() or "the record"
    return {
        "kind": kind,
        "dominant_dependency_group": dominant_group,
        "focus": focus,
        "target": target,
    }


def build_making_ladder(
    record: Mapping[str, Any],
    by_id: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Return a status/dependency-aware, non-claiming making ladder.

    The stages deliberately separate a local-first evidence/design route from
    an initial import bridge, integration/test, the next localization tranche,
    harder later capabilities, and optional redesign.  ``allowed_actions``
    uses the public ladder vocabulary; it is a set of candidate transformations
    rather than a claim that any route is currently executable.
    """

    current_status = _status_label(record.get("status") or record.get("india_status"))
    current_epistemic = _epistemic_label(record)
    dependency_ids = _dependency_ids(record)
    dependency_risks: set[str] = set()
    if by_id:
        for dependency_id in dependency_ids:
            dependency = by_id.get(dependency_id)
            if dependency is None:
                dependency_risks.add("UNKNOWN")
            elif isinstance(dependency, Mapping):
                dependency_risks.update(_dependency_risk(dependency))
    else:
        # Without a registry, unresolved dependency state is intentionally not
        # assumed closed; the action remains evidence-first.
        dependency_risks.add("UNKNOWN") if dependency_ids else None

    ladder_context = _ladder_context(record, dependency_ids)
    kind = ladder_context["kind"]
    dominant_group = ladder_context["dominant_dependency_group"]
    target = ladder_context["target"]
    focus = ladder_context["focus"]
    risky = current_status in {"UNKNOWN", "MISSING", "IMPORT_DEPENDENT", "CONFLICTED", "SCALE_LIMITED"} or bool(dependency_risks)
    evidence_ready = current_epistemic in {"MEASURED", "REPORTED", "DERIVED"} and current_status in {"STRONG", "AVAILABLE"}
    # Records without a normalized kind retain the generic fallback for
    # lightweight callers.  Catalog records carry kind and grouped
    # dependencies, allowing the route to vary without pretending that any
    # route is already locally qualified.
    if kind and (current_status in {"UNKNOWN", "MISSING", "CONFLICTED"} or current_epistemic == "UNKNOWN"):
        local_actions = ["R&D", "DEVELOP"]
    else:
        local_actions = ["DEVELOP", "BUILD"] if evidence_ready and not risky else ["DEVELOP", "R&D"]
    integration_action = {
        "materials": "R&D",
        "processes": "BUILD",
        "equipment": "JV",
        "capabilities": "DEVELOP",
        "systems": "JV",
    }.get(dominant_group, "JV")
    localization_action = {
        "materials": "SUBSTITUTE",
        "processes": "DEVELOP",
        "equipment": "BUILD",
        "capabilities": "DEVELOP",
        "systems": "BUILD",
    }.get(dominant_group, "BUILD")
    harder_action = "LICENSE" if kind == "CAPABILITY" and current_status in {"IMPORT_DEPENDENT", "UNKNOWN"} else "R&D"
    redesign_action = "SUBSTITUTE" if dominant_group == "materials" else "REDESIGN"
    import_actions = ["IMPORT", "LICENSE", "JV"]
    stages = [
        {
            "sequence": 1,
            "stage": _STAGE_NAMES[0],
            "action": local_actions[0],
            "allowed_actions": local_actions,
            "required": True,
            "purpose": f"Freeze {focus} for {target}; local-first is an evidence and development route, not a local-supply claim.",
            "condition": "Local-first means investigate and develop the route; it does not imply an existing qualified Indian supplier.",
        },
        {
            "sequence": 2,
            "stage": _STAGE_NAMES[1],
            "action": import_actions[0],
            "allowed_actions": import_actions,
            "required": risky,
            "purpose": f"Bridge unresolved {focus} for {target} only where import, licensing, or partnership is needed.",
            "condition": "Eligibility is not supply; allocation, logistics, licensing, and residual dependence remain explicit.",
        },
        {
            "sequence": 3,
            "stage": _STAGE_NAMES[2],
            "action": integration_action,
            "allowed_actions": ["JV", "BUILD", "DEVELOP", "R&D"],
            "required": True,
            "purpose": f"Integrate, inspect, and test {target} around {focus} before scale or customer acceptance.",
            "condition": f"Gate {focus} with prototype, metrology, process validation, and customer or regulatory acceptance.",
        },
        {
            "sequence": 4,
            "stage": _STAGE_NAMES[3],
            "action": localization_action,
            "allowed_actions": ["DEVELOP", "BUILD", "SUBSTITUTE", "R&D"],
            "required": True,
            "purpose": f"Localize the next {focus} node for {target} by dependency risk and qualification path.",
            "condition": f"Prioritize {focus} dependencies by risk or shortest credible qualification path; substitution is a graph rewrite.",
        },
        {
            "sequence": 5,
            "stage": _STAGE_NAMES[4],
            "action": harder_action,
            "allowed_actions": ["R&D", "BUILD", "LICENSE", "JV"],
            "required": False,
            "purpose": f"Advance harder later {focus} for {target} after the near-term route and evidence stabilize.",
            "condition": f"Keep {focus}, yield, scale, and effective capacity UNKNOWN until measured; licensing does not equal local know-how.",
        },
        {
            "sequence": 6,
            "stage": _STAGE_NAMES[5],
            "action": redesign_action,
            "allowed_actions": ["REDESIGN", "SUBSTITUTE"],
            "required": False,
            "purpose": f"Optionally {redesign_action.casefold()} {target} if {focus} remains binding.",
            "condition": "Expose performance, cost, time, qualification, and new-dependency trade-offs; never treat redesign or substitution as free.",
        },
    ]
    for stage in stages:
        stage["record_id"] = _record_id(record)
        stage["family_key"] = family_key(record)
        stage["dependency_ids"] = dependency_ids
        stage["dependency_risk"] = sorted(dependency_risks)
        stage["status"] = current_status
        stage["ladder_profile"] = {
            "kind": kind,
            "dominant_dependency_group": dominant_group,
            "focus": focus,
        }
    return stages


# Descriptive aliases make the helper easy to discover without forcing clients
# to couple to one internal naming choice.
making_ladder = build_making_ladder
quality_making_ladder = build_making_ladder
correct_unsupported_status = correct_epistemic_status
epistemic_correction = correct_epistemic_status


__all__ = [
    "QUALITY_SCHEMA_VERSION",
    "ALLOWED_ACTIONS",
    "family_key",
    "variant_label",
    "display_name",
    "correct_epistemic_status",
    "correct_unsupported_status",
    "epistemic_correction",
    "build_making_ladder",
    "making_ladder",
    "quality_making_ladder",
]
