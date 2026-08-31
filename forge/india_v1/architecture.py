"""Deterministic product-understanding compiler for the India V1 atlas.

The compiler interprets typed atlas structure; it does not turn graph proximity
into a bill of materials.  Physical product nodes, manufacturing requirements,
and industrial environment nodes remain separate throughout the output.
"""
from __future__ import annotations

import re
from collections import deque
from collections.abc import Mapping
from typing import Any

from .catalog import IndiaCatalog, get_catalog
from .objective_models import (
    ArchitectureEdge,
    ArchitectureNode,
    ArchitectureNodeKind,
    DerivationClass,
    ProductArchitecture,
)


_ENVIRONMENT_CATEGORY_PREFIXES = (
    "shared industrial system",
    "shared utility system",
    "shared digital system",
    "shared assurance system",
    "shared logistics system",
    "shared thermal system",
    "shared controlled environment",
    "plant infrastructure",
    "utility equipment",
)
_ENVIRONMENT_TERMS = re.compile(
    r"\b(?:industrial infrastructure|industrial power|reliable electricity|industrial water|"
    r"industrial gases|industrial logistics|site services|factory infrastructure|general utilities|"
    r"power-quality and backup|facility operations)\b",
    re.I,
)
_METROLOGY_TERMS = re.compile(r"\b(?:metrolog|measurement|inspection|calibrat|cmm|test bench|tester)\b", re.I)
_QUALIFICATION_TERMS = re.compile(
    r"\b(?:qualif|certif|validation|acceptance|standard|regulat|safety|reliability test|burn-in)\b",
    re.I,
)


def _text(value: Any) -> str:
    return str(value or "").replace("\ufffd", " — ").strip()


def _label(record: Mapping[str, Any], fallback: str) -> str:
    value = _text(
        record.get("display_name")
        or record.get("family_label")
        or record.get("canonical_name")
        or fallback
    )
    return re.sub(r"\s+", " ", value).strip(" —-") or fallback.replace("_", " ")


def _record(catalog: IndiaCatalog, reference: Any) -> Mapping[str, Any]:
    if isinstance(reference, Mapping):
        return reference
    record = catalog.by_id.get(str(reference))
    if record is not None:
        return record
    return {
        "id": str(reference),
        "canonical_name": str(reference).replace("_", " "),
        "kind": "CAPABILITY",
        "category": "unresolved reference",
        "status": "UNKNOWN",
        "status_epistemic_class": "UNKNOWN",
        "is_reference_only": True,
        "dependencies": {},
    }


def _is_environment(record: Mapping[str, Any]) -> bool:
    category = _text(record.get("category")).casefold()
    identity = " ".join(
        _text(record.get(key)) for key in ("id", "family_label", "display_name", "canonical_name")
    )
    return category.startswith(_ENVIRONMENT_CATEGORY_PREFIXES) or bool(_ENVIRONMENT_TERMS.search(identity))


def _node_kind(group: str, record: Mapping[str, Any]) -> tuple[ArchitectureNodeKind, DerivationClass]:
    identity = " ".join(
        _text(record.get(key)) for key in ("id", "category", "family_label", "display_name", "canonical_name")
    )
    kind = _text(record.get("kind")).upper()
    if group == "systems":
        if _is_environment(record):
            return ArchitectureNodeKind.INDUSTRIAL_ENVIRONMENT, DerivationClass.DERIVED
        if kind in {"PRODUCT", "EQUIPMENT"} and not record.get("is_reference_only"):
            return ArchitectureNodeKind.PRODUCT_SYSTEM, DerivationClass.EXPLICIT
        return ArchitectureNodeKind.EVIDENCE_ONLY, DerivationClass.DERIVED
    if group == "components":
        return ArchitectureNodeKind.PRODUCT_COMPONENT, DerivationClass.EXPLICIT
    if _QUALIFICATION_TERMS.search(identity):
        return ArchitectureNodeKind.QUALIFICATION, DerivationClass.DERIVED
    if _METROLOGY_TERMS.search(identity):
        return ArchitectureNodeKind.METROLOGY, DerivationClass.DERIVED
    if group == "processes" or kind == "PROCESS":
        return ArchitectureNodeKind.MANUFACTURING_PROCESS, DerivationClass.EXPLICIT
    if group == "materials" or kind == "MATERIAL":
        return ArchitectureNodeKind.MATERIAL, DerivationClass.EXPLICIT
    if group == "equipment" or kind == "EQUIPMENT":
        return ArchitectureNodeKind.MANUFACTURING_EQUIPMENT, DerivationClass.EXPLICIT
    if group == "capabilities" or kind == "CAPABILITY":
        return ArchitectureNodeKind.MANUFACTURING_CAPABILITY, DerivationClass.EXPLICIT
    return ArchitectureNodeKind.EVIDENCE_ONLY, DerivationClass.DERIVED


def _relation(kind: ArchitectureNodeKind) -> str:
    return {
        ArchitectureNodeKind.PRODUCT_SYSTEM: "contains_system",
        ArchitectureNodeKind.PRODUCT_COMPONENT: "contains_component",
        ArchitectureNodeKind.MANUFACTURING_PROCESS: "requires_process",
        ArchitectureNodeKind.MANUFACTURING_EQUIPMENT: "requires_equipment",
        ArchitectureNodeKind.MANUFACTURING_CAPABILITY: "requires_capability",
        ArchitectureNodeKind.MATERIAL: "requires_material",
        ArchitectureNodeKind.METROLOGY: "requires_metrology",
        ArchitectureNodeKind.QUALIFICATION: "requires_qualification",
        ArchitectureNodeKind.INDUSTRIAL_ENVIRONMENT: "requires_environment",
        ArchitectureNodeKind.EVIDENCE_ONLY: "supported_by_structure",
    }[kind]


def compile_product_architecture(
    record: Mapping[str, Any] | str,
    catalog: IndiaCatalog | None = None,
    *,
    family_level: bool = False,
    requires_confirmation: bool = False,
    max_depth: int = 3,
) -> ProductArchitecture:
    """Compile one atlas record into a bounded typed architecture.

    ``family_level`` is set only after a caller explicitly confirms a broader
    family match.  It changes provenance, never India status or capacity.
    """

    catalog = catalog or get_catalog()
    source = catalog.by_id.get(record) if isinstance(record, str) else record
    if not source or source.get("is_reference_only"):
        rid = str(record if isinstance(record, str) else (source or {}).get("id") or "unresolved")
        return ProductArchitecture(
            product_record_id=rid,
            product_name=_label(source or {}, rid),
            family_key=_text((source or {}).get("family_key") or rid),
            nodes=(),
            edges=(),
            coverage_class="UNRESOLVED",
            requires_confirmation=requires_confirmation,
            diagnostics=("No concrete India V1 product/family record was available.",),
        )

    root_id = _text(source.get("id"))
    provenance = DerivationClass.FAMILY_LEVEL if family_level else DerivationClass.EXPLICIT
    root = ArchitectureNode(
        id=root_id,
        label=_label(source, root_id),
        kind=ArchitectureNodeKind.PRODUCT_SYSTEM,
        source_record_ids=(root_id,),
        derivation_class=provenance,
        status=_text(source.get("status") or "UNKNOWN").upper(),
        epistemic_class=_text(source.get("status_epistemic_class") or "UNKNOWN").upper(),
        family_key=_text(source.get("family_key") or root_id),
        description=_text(source.get("explanation")),
        depth=0,
    )
    nodes: dict[str, ArchitectureNode] = {root.id: root}
    edges: dict[tuple[str, str, str], ArchitectureEdge] = {}
    diagnostics: list[str] = []
    queue: deque[tuple[Mapping[str, Any], str, int]] = deque([(source, root_id, 0)])
    expanded: set[str] = set()

    while queue:
        parent, parent_id, depth = queue.popleft()
        if parent_id in expanded:
            continue
        expanded.add(parent_id)
        raw_groups = parent.get("dependencies") or {}
        if not isinstance(raw_groups, Mapping):
            continue
        for group in ("components", "systems", "processes", "equipment", "materials", "capabilities"):
            references = raw_groups.get(group) or ()
            for reference in sorted(references, key=lambda item: str(item.get("id") if isinstance(item, Mapping) else item)):
                child = _record(catalog, reference)
                child_id = _text(child.get("id") or reference)
                if not child_id or child_id == parent_id:
                    continue
                kind, derived = _node_kind(group, child)
                child_provenance = DerivationClass.FAMILY_LEVEL if family_level else derived
                existing = nodes.get(child_id)
                candidate = ArchitectureNode(
                    id=child_id,
                    label=_label(child, child_id),
                    kind=kind,
                    source_record_ids=(child_id,),
                    derivation_class=child_provenance,
                    status=_text(child.get("status") or "UNKNOWN").upper(),
                    epistemic_class=_text(child.get("status_epistemic_class") or "UNKNOWN").upper(),
                    family_key=_text(child.get("family_key") or child_id),
                    description=_text(child.get("explanation")),
                    depth=depth + 1,
                )
                if existing is None or (candidate.kind.value, candidate.id) < (existing.kind.value, existing.id):
                    nodes[child_id] = candidate
                key = (parent_id, child_id, _relation(kind))
                edges[key] = ArchitectureEdge(
                    source_id=parent_id,
                    destination_id=child_id,
                    relation=key[2],
                    source_record_ids=tuple(sorted({parent_id, child_id})),
                    derivation_class=child_provenance,
                )
                if kind in {ArchitectureNodeKind.PRODUCT_SYSTEM, ArchitectureNodeKind.PRODUCT_COMPONENT}:
                    if depth + 1 < max_depth:
                        queue.append((child, child_id, depth + 1))
                    elif child.get("dependencies"):
                        diagnostics.append(f"Physical recursion stopped at max_depth={max_depth} for {child_id}.")

    physical = [
        node for node in nodes.values()
        if node.id != root_id and node.kind in {ArchitectureNodeKind.PRODUCT_SYSTEM, ArchitectureNodeKind.PRODUCT_COMPONENT}
    ]
    if family_level:
        coverage = "FAMILY_LEVEL_ARCHITECTURE"
    elif physical:
        coverage = "EXACT_ARCHITECTURE"
    elif len(nodes) > 1:
        coverage = "STRUCTURAL_REQUIREMENTS_ONLY"
        diagnostics.append("No explicit physical subsystem/component edges were present; manufacturing requirements remain usable.")
    else:
        coverage = "UNRESOLVED"

    return ProductArchitecture(
        product_record_id=root_id,
        product_name=root.label,
        family_key=root.family_key,
        nodes=tuple(sorted(nodes.values(), key=lambda item: (item.depth, item.kind.value, item.label.casefold(), item.id))),
        edges=tuple(sorted(edges.values(), key=lambda item: (item.source_id, item.relation, item.destination_id))),
        coverage_class=coverage,
        requires_confirmation=requires_confirmation,
        diagnostics=tuple(sorted(set(diagnostics))),
    )


__all__ = ["compile_product_architecture"]
