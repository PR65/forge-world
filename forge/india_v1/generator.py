"""Deterministic generator and integrity checks for the India V1 atlas.

The generator expands a compact set of curated industrial archetypes into
reusable records.  It intentionally creates compatible variant axes per
domain/family rather than a global cross-product: every record is still
traceable to one family, one axis, and one shared primitive profile.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from copy import deepcopy
from functools import lru_cache
import importlib.util
from pathlib import Path
import re
from typing import Any, Dict, List, Sequence, Tuple

try:
    from data.india_v1.domains_01_04 import (
        COMPONENT_GROUPS,
        DOMAIN_SPECS,
        PROFILE_DEPENDENCIES,
        SHARED_PRIMITIVES,
        VARIANT_GROUPS,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - exercised by installed pytest entrypoints
    # Some environments launch ``pytest`` with the repository root absent from
    # sys.path even though ``forge`` is importable from an editable install.
    # Keep the data pack source-local and load it by its stable relative path;
    # the normal repository import above remains the preferred route.
    if not str(exc).startswith("No module named 'data'"):
        raise
    _spec_path = Path(__file__).resolve().parents[2] / "data" / "india_v1" / "domains_01_04.py"
    _spec = importlib.util.spec_from_file_location("_forge_india_v1_domain_spec", _spec_path)
    if _spec is None or _spec.loader is None:
        raise ModuleNotFoundError(f"cannot load India V1 domain spec at {_spec_path}") from exc
    _domain_module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_domain_module)
    COMPONENT_GROUPS = _domain_module.COMPONENT_GROUPS
    DOMAIN_SPECS = _domain_module.DOMAIN_SPECS
    PROFILE_DEPENDENCIES = _domain_module.PROFILE_DEPENDENCIES
    SHARED_PRIMITIVES = _domain_module.SHARED_PRIMITIVES
    VARIANT_GROUPS = _domain_module.VARIANT_GROUPS

from .schema import (
    ATLAS_SCHEMA_VERSION,
    DEPENDENCY_GROUPS,
    EPISTEMIC_CLASSES,
    KINDS,
    LADDER_ACTIONS,
    STATUSES,
    Atlas,
    AtlasIntegrityError,
    AtlasRecord,
    IntegrityReport,
    LadderStep,
)
from .quality import correct_epistemic_status


GENERATOR_VERSION = "1.0.0"
_GROUP_PREFIX = {
    "systems": "system",
    "processes": "process",
    "materials": "material",
    "equipment": "equipment",
    "capabilities": "capability",
}
_DOMAIN_STATUS_BASIS = (
    "Curated India V1 archetype overlay; this broad status is a navigation baseline, "
    "not evidence of a named facility, qualified specification, or available effective capacity."
)
_ACTION_PURPOSES = {
    "IMPORT": "Use an external source as a bridge while India closes the evidence and capability gap.",
    "DEVELOP": "Develop the process, workforce, and supplier knowledge needed for repeatable output.",
    "LICENSE": "Obtain technology rights and controlled process transfer where ownership permits.",
    "JV": "Partner with an experienced external or Indian organisation to share know-how and ramp risk.",
    "BUILD": "Build or expand Indian production, test, tooling, and utility capacity.",
    "SUBSTITUTE": "Evaluate a physically compatible material, component, or process alternative.",
    "REDESIGN": "Change the parent architecture to reduce the binding dependency or qualification burden.",
    "R&D": "Run targeted research, pilot, and first-article work before treating the route as closed.",
}
_ACTION_CONDITIONS = {
    "IMPORT": "Requires eligible external supply, logistics, and a declared residual-dependence tolerance.",
    "DEVELOP": "Requires a specification, anchor demand, process owner, and measurable qualification plan.",
    "LICENSE": "Requires rights, export permission, transfer scope, and a domestic operating team.",
    "JV": "Requires partner incentives, governance, IP/control terms, and a shared qualification route.",
    "BUILD": "Requires capex, utilities, equipment, workforce, process qualification, and ramp time.",
    "SUBSTITUTE": "Requires a graph rewrite plus performance, reliability, and customer requalification evidence.",
    "REDESIGN": "Requires architecture review and explicit trade-offs in performance, cost, time, and risk.",
    "R&D": "Requires an evidence task with a stop/go criterion; unresolved results remain UNKNOWN.",
}
_CAPABILITY_AXES = (
    ("design", "design and architecture capability"),
    ("process", "process knowledge and process control capability"),
    ("qualification", "qualification and acceptance capability"),
    ("scale", "scalable effective-throughput capability"),
    ("integration", "integration and production-system capability"),
)
_PROCESS_AXES = (
    ("prototype", "prototype process route"),
    ("series", "series-production process route"),
    ("qualification", "qualification process route"),
    ("recovery", "repair, recovery, and alternate-source process route"),
)
_MATERIAL_AXES = (
    ("structural", "structural or base-grade material"),
    ("functional", "functional-grade material"),
    ("high_purity", "high-purity or tightly controlled material"),
    ("recycled", "recycled, recovered, or substitution-grade material"),
)
_EQUIPMENT_AXES = (
    ("prototype", "prototype and pilot equipment"),
    ("production", "series-production equipment"),
    ("inspection", "inspection and metrology equipment"),
    ("test", "qualification and acceptance-test equipment"),
)


def _slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", str(value).casefold()).strip("_")
    return value or "unknown"


def _shared_id(group: str, slug: str) -> str:
    return f"shared:{_GROUP_PREFIX[group]}:{slug}"


def _domain_id(code: str, kind: str, family: str, axis: str) -> str:
    return f"d{code}:{kind.casefold()}:{_slug(family)}:{_slug(axis)}"


def _domain_label(domain: Mapping[str, Any]) -> str:
    return str(domain["name"])


def _selected_domains(domains: Iterable[str] | str | None) -> List[Mapping[str, Any]]:
    if domains is None:
        return list(DOMAIN_SPECS)
    requested = [domains] if isinstance(domains, str) else list(domains)
    if not requested:
        return []
    lookup: Dict[str, Mapping[str, Any]] = {}
    for domain in DOMAIN_SPECS:
        for value in (domain["code"], domain["key"], domain["name"]):
            lookup[_slug(value)] = domain
        lookup[str(domain["code"]).casefold()] = domain
    selected: List[Mapping[str, Any]] = []
    seen: set[str] = set()
    for value in requested:
        key = _slug(value)
        if key not in lookup:
            raise KeyError(
                f"unknown India V1 domain {value!r}; expected one of "
                f"{', '.join(d['code'] for d in DOMAIN_SPECS)}"
            )
        domain = lookup[key]
        if domain["code"] not in seen:
            selected.append(domain)
            seen.add(domain["code"])
    return selected


def _shared_index() -> Dict[Tuple[str, str], Mapping[str, Any]]:
    index: Dict[Tuple[str, str], Mapping[str, Any]] = {}
    for spec in SHARED_PRIMITIVES:
        key = (str(spec["group"]), str(spec["slug"]))
        if key in index:
            raise AtlasIntegrityError(f"duplicate shared primitive spec: {key}")
        index[key] = spec
    return index


def _shared_dependencies(
    group: str, slug: str, all_shared: Mapping[Tuple[str, str], Mapping[str, Any]]
) -> Dict[str, Tuple[str, ...]]:
    """Provide a small acyclic-ish dependency spine for shared primitives."""

    def ref(target_group: str, target_slug: str) -> str:
        if (target_group, target_slug) not in all_shared:
            raise AtlasIntegrityError(
                f"shared primitive {group}/{slug} references missing "
                f"{target_group}/{target_slug}"
            )
        return _shared_id(target_group, target_slug)

    deps: Dict[str, List[str]] = {key: [] for key in DEPENDENCY_GROUPS}
    if group == "systems":
        deps["processes"] = [ref("processes", "requirements_systems_engineering")]
        deps["materials"] = [ref("materials", "steel")]
        deps["equipment"] = [ref("equipment", "power_quality_system")]
        deps["capabilities"] = [ref("capabilities", "facility_operations")]
    elif group == "processes":
        deps["systems"] = [ref("systems", "industrial_infrastructure")]
        deps["materials"] = [ref("materials", "steel")]
        deps["equipment"] = [ref("equipment", "cnc_machine")]
        deps["capabilities"] = [ref("capabilities", "process_control_yield")]
    elif group == "materials":
        deps["systems"] = [ref("systems", "industrial_infrastructure")]
        deps["processes"] = [ref("processes", "chemical_synthesis_refining")]
        # Keep a material from depending on itself; steel is the generic
        # reference for all other materials, while steel remains a root input.
        if slug != "steel":
            deps["materials"] = [ref("materials", "steel")]
        deps["equipment"] = [ref("equipment", "chemical_process_skid")]
        deps["capabilities"] = [ref("capabilities", "materials_engineering")]
    elif group == "equipment":
        deps["systems"] = [ref("systems", "industrial_infrastructure")]
        deps["processes"] = [ref("processes", "assembly_integration")]
        deps["materials"] = [ref("materials", "steel")]
        deps["capabilities"] = [ref("capabilities", "precision_manufacturing")]
        if slug != "industrial_compute":
            deps["equipment"] = [ref("equipment", "industrial_compute")]
    elif group == "capabilities":
        deps["systems"] = [ref("systems", "industrial_infrastructure")]
        deps["processes"] = [ref("processes", "metrology_inspection")]
        deps["materials"] = [ref("materials", "steel")]
        deps["equipment"] = [ref("equipment", "coordinate_measuring_machine")]
    return {key: tuple(sorted(set(values))) for key, values in deps.items()}


def _profile_dependencies(profile: str, shared: Mapping[Tuple[str, str], Mapping[str, Any]]) -> Dict[str, Tuple[str, ...]]:
    if profile not in PROFILE_DEPENDENCIES:
        raise AtlasIntegrityError(f"unknown domain dependency profile {profile!r}")
    result: Dict[str, Tuple[str, ...]] = {}
    for group in DEPENDENCY_GROUPS:
        refs: List[str] = []
        for slug in PROFILE_DEPENDENCIES[profile].get(group, []):
            if (group, slug) not in shared:
                raise AtlasIntegrityError(
                    f"profile {profile!r} references missing {group}/{slug}"
                )
            refs.append(_shared_id(group, slug))
        result[group] = tuple(sorted(set(refs)))
    return result


def _add_dependency(deps: Dict[str, Tuple[str, ...]], group: str, *refs: str) -> None:
    deps[group] = tuple(sorted(set(deps[group]).union(ref for ref in refs if ref)))


def _status_for_variant(base: str, kind: str, axis: str) -> str:
    """Apply a transparent, conservative variant overlay.

    A demanding variant cannot improve a broad status.  The overlay only makes
    the status more cautious for qualification-sensitive axes; it never turns
    UNKNOWN/MISSING/CONFLICTED into a positive assertion.
    """

    if base in {"UNKNOWN", "MISSING", "CONFLICTED"}:
        return base
    demanding = {
        "high_reliability",
        "safety_critical",
        "strategic",
        "high_purity",
        "qualification",
        "test",
        "qualified",
        "export_controlled",
    }
    if axis not in demanding:
        return base
    if base in {"STRONG", "AVAILABLE"}:
        return "PARTIAL"
    if base == "PARTIAL":
        return "SCALE_LIMITED" if kind in {"PRODUCT", "CAPABILITY", "PROCESS"} else "IMPORT_DEPENDENT"
    return base


def _ladder(status: str, kind: str, name: str) -> Tuple[LadderStep, ...]:
    """Build the same inspectable eight-action first-order ladder everywhere."""

    steps: List[LadderStep] = []
    for index, action in enumerate(LADDER_ACTIONS, start=1):
        condition = _ACTION_CONDITIONS[action]
        if action == "IMPORT" and status in {"STRONG", "AVAILABLE"}:
            condition = "Use only as a declared bridge or second source; domestic capability is not inferred from import availability."
        if action == "R&D" and status == "UNKNOWN":
            condition = "Priority evidence task: resolve the unknown before selecting a stronger route."
        steps.append(
            LadderStep(
                sequence=index,
                action=action,
                purpose=f"{_ACTION_PURPOSES[action]} Target: {name}.",
                condition=condition,
            )
        )
    return tuple(steps)


def _canonical_aliases(domain_name: str, family: str, axis: str, extra: Sequence[str]) -> Tuple[str, ...]:
    prefix = _slug(domain_name)
    family_slug = _slug(family)
    axis_slug = _slug(axis)
    values = [
        f"{domain_name} {family} {axis}",
        f"{prefix}:{family_slug}:{axis_slug}",
    ]
    values.extend(f"{domain_name} {alias} {axis}" for alias in extra)
    return tuple(sorted(set(values)))


def _record(
    *,
    record_id: str,
    canonical_name: str,
    aliases: Sequence[str],
    domain: str,
    category: str,
    kind: str,
    explanation: str,
    uses: Sequence[str],
    status: str,
    status_basis: str,
    dependencies: Mapping[str, Sequence[str]],
    gap_import_notes: str,
    related: Sequence[str] = (),
    source_spec: str = "data.india_v1.domains_01_04",
) -> AtlasRecord:
    deps = {group: tuple(sorted(set(dependencies.get(group, ())))) for group in DEPENDENCY_GROUPS}
    corrected = correct_epistemic_status(
        {
            "status": status,
            "status_basis": status_basis,
            "status_epistemic_class": "CONFLICTED" if status == "CONFLICTED" else "ASSUMPTION",
        }
    )
    status = str(corrected.get("status", status))
    status_basis = str(corrected.get("status_basis", status_basis))
    status_epistemic_class = str(
        corrected.get(
            "status_epistemic_class",
            "CONFLICTED" if status == "CONFLICTED" else "ASSUMPTION",
        )
    )
    return AtlasRecord(
        id=record_id,
        canonical_name=canonical_name,
        aliases=tuple(aliases),
        domain=domain,
        category=category,
        kind=kind,
        explanation=explanation,
        uses=tuple(uses),
        status=status,
        status_epistemic_class=status_epistemic_class,
        status_basis=status_basis,
        dependencies=deps,
        gap_import_notes=gap_import_notes,
        making_ladder=_ladder(status, kind, canonical_name),
        upstream=tuple(sorted({ref for values in deps.values() for ref in values})),
        related=tuple(sorted(set(related))),
        source_spec=source_spec,
    )


def _make_shared_records(shared: Mapping[Tuple[str, str], Mapping[str, Any]]) -> List[AtlasRecord]:
    records: List[AtlasRecord] = []
    for spec in sorted(shared.values(), key=lambda value: (value["group"], value["slug"])):
        group = str(spec["group"])
        slug = str(spec["slug"])
        record_id = _shared_id(group, slug)
        canonical_name = f"Cross-domain {_GROUP_PREFIX[group]}: {spec['name']}"
        aliases = (
            f"cross-domain {spec['name']}",
            f"shared {_GROUP_PREFIX[group]} {slug.replace('_', ' ')}",
        )
        records.append(
            _record(
                record_id=record_id,
                canonical_name=canonical_name,
                aliases=aliases,
                domain="shared_foundations",
                category=str(spec.get("category", f"shared {_GROUP_PREFIX[group]}")),
                kind=str(spec["kind"]),
                explanation=(
                    f"Reusable cross-domain {group[:-1]} primitive for {', '.join(spec.get('uses', []))}. "
                    "The shared identity is deduplicated across domain views."
                ),
                uses=spec.get("uses", []),
                status=str(spec["status"]),
                status_basis=(
                    "Curated shared-foundation baseline. It identifies a reusable industrial concept; "
                    "specification, facility, qualification, and effective capacity remain evidence questions."
                ),
                dependencies=_shared_dependencies(group, slug, shared),
                gap_import_notes=(
                    "Shared primitive is intentionally broad; import exposure and India capability vary by grade, "
                    "specification, facility, and qualification context."
                ),
                related=(),
            )
        )
    return records


def _family_records(domain: Mapping[str, Any], arch: Mapping[str, Any], shared: Mapping[Tuple[str, str], Mapping[str, Any]]) -> List[AtlasRecord]:
    code = str(domain["code"])
    domain_name = _domain_label(domain)
    family_slug = str(arch["slug"])
    family_name = str(arch["name"])
    base_status = str(arch["status"])
    profile = _profile_dependencies(str(arch["profile"]), shared)
    product_group = str(domain["variant_group"])
    product_variants = VARIANT_GROUPS[product_group]
    component_variants = COMPONENT_GROUPS[product_group]
    aliases = arch.get("aliases", [])
    records: List[AtlasRecord] = []

    # Product/system variants.  Domain-specific process/material/equipment/
    # capability anchors make each finished product recursively useful without
    # creating a global family × family cross-product.
    for variant in product_variants:
        axis = str(variant["code"])
        label = str(variant["label"])
        record_id = _domain_id(code, "product", family_slug, axis)
        deps = deepcopy(profile)
        _add_dependency(deps, "processes", _domain_id(code, "process", family_slug, "series"))
        _add_dependency(deps, "materials", _domain_id(code, "material", family_slug, "structural"))
        _add_dependency(deps, "equipment", _domain_id(code, "equipment", family_slug, "production"))
        _add_dependency(deps, "capabilities", _domain_id(code, "capability", family_slug, "integration"))
        status = _status_for_variant(base_status, "PRODUCT", axis)
        canonical_name = f"{domain_name}: {family_name} - {label}"
        related = [
            _domain_id(code, "product", family_slug, product_variants[(index + 1) % len(product_variants)]["code"])
            for index, current in enumerate(product_variants)
            if current["code"] == axis
        ]
        related.extend(_domain_id(code, "product", family_slug, component_variants[0]["code"]) for _ in [0])
        records.append(
            _record(
                record_id=record_id,
                canonical_name=canonical_name,
                aliases=_canonical_aliases(domain_name, family_name, label, aliases),
                domain=domain_name,
                category=str(arch["category"]),
                kind="PRODUCT",
                explanation=(
                    f"A first-order {label} view of {family_name.lower()}, linking the product to the "
                    "shared industrial primitives and family-level production routes needed to make, test, and sustain it."
                ),
                uses=list(arch["uses"]) + [label],
                status=status,
                status_basis=_DOMAIN_STATUS_BASIS,
                dependencies=deps,
                gap_import_notes=str(arch["gap"]),
                related=related,
            )
        )

    # Component/assembly views are PRODUCT records but use a compatible,
    # bounded axis rather than a Cartesian product with every product variant.
    for component in component_variants:
        axis = str(component["code"])
        label = str(component["label"])
        record_id = _domain_id(code, "product", family_slug, axis)
        deps = deepcopy(profile)
        _add_dependency(deps, "processes", _domain_id(code, "process", family_slug, "series"))
        _add_dependency(deps, "materials", _domain_id(code, "material", family_slug, "functional"))
        _add_dependency(deps, "equipment", _domain_id(code, "equipment", family_slug, "production"))
        _add_dependency(deps, "capabilities", _domain_id(code, "capability", family_slug, "integration"))
        status = _status_for_variant(base_status, "PRODUCT", axis)
        canonical_name = f"{domain_name}: {family_name} - {label}"
        related = [
            _domain_id(code, "product", family_slug, product_variants[0]["code"]),
            _domain_id(code, "process", family_slug, "series"),
        ]
        records.append(
            _record(
                record_id=record_id,
                canonical_name=canonical_name,
                aliases=_canonical_aliases(domain_name, family_name, label, aliases),
                domain=domain_name,
                category=f"{arch['category']} / assembly",
                kind="PRODUCT",
                explanation=(
                    f"A bounded {label} view of {family_name.lower()}; it exposes the subsystem route used by "
                    "the parent product without implying a separate industry or independent capacity claim."
                ),
                uses=list(arch["uses"]) + [label],
                status=status,
                status_basis=_DOMAIN_STATUS_BASIS,
                dependencies=deps,
                gap_import_notes=str(arch["gap"]),
                related=related,
            )
        )

    # Capability axes.
    for axis, axis_label in _CAPABILITY_AXES:
        record_id = _domain_id(code, "capability", family_slug, axis)
        deps = deepcopy(profile)
        status = _status_for_variant(base_status, "CAPABILITY", axis)
        canonical_name = f"{domain_name} capability: {family_name} - {axis_label}"
        related = [
            _domain_id(code, "product", family_slug, product_variants[0]["code"]),
            _domain_id(code, "process", family_slug, "series"),
        ]
        records.append(
            _record(
                record_id=record_id,
                canonical_name=canonical_name,
                aliases=_canonical_aliases(domain_name, family_name, axis_label, aliases),
                domain=domain_name,
                category=f"{arch['category']} capability",
                kind="CAPABILITY",
                explanation=(
                    f"The {axis_label} needed to repeatedly deliver {family_name.lower()} to its stated "
                    "specification, not merely demonstrate an adjacent technology."
                ),
                uses=list(arch["uses"]) + [axis_label],
                status=status,
                status_basis=_DOMAIN_STATUS_BASIS,
                dependencies=deps,
                gap_import_notes=str(arch["gap"]),
                related=related,
            )
        )

    # Process routes.
    for axis, axis_label in _PROCESS_AXES:
        record_id = _domain_id(code, "process", family_slug, axis)
        deps = deepcopy(profile)
        _add_dependency(deps, "materials", _domain_id(code, "material", family_slug, "structural"))
        _add_dependency(deps, "equipment", _domain_id(code, "equipment", family_slug, "production"))
        _add_dependency(deps, "capabilities", _domain_id(code, "capability", family_slug, "process"))
        status = _status_for_variant(base_status, "PROCESS", axis)
        canonical_name = f"{domain_name} process: {family_name} - {axis_label}"
        related = [
            _domain_id(code, "product", family_slug, product_variants[0]["code"]),
            _domain_id(code, "equipment", family_slug, "production"),
        ]
        records.append(
            _record(
                record_id=record_id,
                canonical_name=canonical_name,
                aliases=_canonical_aliases(domain_name, family_name, axis_label, aliases),
                domain=domain_name,
                category=f"{arch['category']} process",
                kind="PROCESS",
                explanation=(
                    f"A {axis_label} for {family_name.lower()} with explicit upstream materials, equipment, "
                    "metrology, and capability prerequisites."
                ),
                uses=list(arch["uses"]) + [axis_label],
                status=status,
                status_basis=_DOMAIN_STATUS_BASIS,
                dependencies=deps,
                gap_import_notes=str(arch["gap"]),
                related=related,
            )
        )

    # Material/grade axes.
    for axis, axis_label in _MATERIAL_AXES:
        record_id = _domain_id(code, "material", family_slug, axis)
        deps = deepcopy(profile)
        _add_dependency(deps, "processes", _domain_id(code, "process", family_slug, "series"))
        _add_dependency(deps, "equipment", _domain_id(code, "equipment", family_slug, "production"))
        _add_dependency(deps, "capabilities", _domain_id(code, "capability", family_slug, "process"))
        status = _status_for_variant(base_status, "MATERIAL", axis)
        canonical_name = f"{domain_name} material: {family_name} - {axis_label}"
        related = [
            _domain_id(code, "product", family_slug, product_variants[0]["code"]),
            _domain_id(code, "process", family_slug, "series"),
        ]
        records.append(
            _record(
                record_id=record_id,
                canonical_name=canonical_name,
                aliases=_canonical_aliases(domain_name, family_name, axis_label, aliases),
                domain=domain_name,
                category=f"{arch['category']} material",
                kind="MATERIAL",
                explanation=(
                    f"A {axis_label} relevant to {family_name.lower()}; grade, purity, morphology, source, "
                    "and qualification remain distinct evidence questions."
                ),
                uses=list(arch["uses"]) + [axis_label],
                status=status,
                status_basis=_DOMAIN_STATUS_BASIS,
                dependencies=deps,
                gap_import_notes=str(arch["gap"]),
                related=related,
            )
        )

    # Equipment axes.
    for axis, axis_label in _EQUIPMENT_AXES:
        record_id = _domain_id(code, "equipment", family_slug, axis)
        deps = deepcopy(profile)
        _add_dependency(deps, "processes", _domain_id(code, "process", family_slug, "series"))
        _add_dependency(deps, "materials", _domain_id(code, "material", family_slug, "structural"))
        _add_dependency(deps, "capabilities", _domain_id(code, "capability", family_slug, "integration"))
        status = _status_for_variant(base_status, "EQUIPMENT", axis)
        canonical_name = f"{domain_name} equipment: {family_name} - {axis_label}"
        related = [
            _domain_id(code, "product", family_slug, product_variants[0]["code"]),
            _domain_id(code, "process", family_slug, "series"),
        ]
        records.append(
            _record(
                record_id=record_id,
                canonical_name=canonical_name,
                aliases=_canonical_aliases(domain_name, family_name, axis_label, aliases),
                domain=domain_name,
                category=f"{arch['category']} equipment",
                kind="EQUIPMENT",
                explanation=(
                    f"The {axis_label} needed to make, inspect, or qualify {family_name.lower()}; "
                    "machine existence is not itself proof of target-grade production capability."
                ),
                uses=list(arch["uses"]) + [axis_label],
                status=status,
                status_basis=_DOMAIN_STATUS_BASIS,
                dependencies=deps,
                gap_import_notes=str(arch["gap"]),
                related=related,
            )
        )

    return records


def _build_records(domains: Sequence[Mapping[str, Any]]) -> List[AtlasRecord]:
    shared = _shared_index()
    records = _make_shared_records(shared)
    for domain in domains:
        for arch in domain["archetypes"]:
            records.extend(_family_records(domain, arch, shared))
    # The reverse links are computed from dependency edges after all records
    # exist.  This keeps generation order independent and makes links auditable.
    ids = {record.id for record in records}
    downstream: Dict[str, set[str]] = defaultdict(set)
    for record in records:
        for upstream in record.upstream:
            downstream[upstream].add(record.id)
    finalized: List[AtlasRecord] = []
    for record in records:
        finalized.append(
            AtlasRecord(
                id=record.id,
                canonical_name=record.canonical_name,
                aliases=record.aliases,
                domain=record.domain,
                category=record.category,
                kind=record.kind,
                explanation=record.explanation,
                uses=record.uses,
                status=record.status,
                status_epistemic_class=record.status_epistemic_class,
                status_basis=record.status_basis,
                dependencies=record.dependencies,
                gap_import_notes=record.gap_import_notes,
                making_ladder=record.making_ladder,
                upstream=record.upstream,
                downstream=tuple(sorted(downstream.get(record.id, set()))),
                related=tuple(ref for ref in record.related if ref in ids),
                source_spec=record.source_spec,
            )
        )
    return sorted(finalized, key=lambda record: record.id)


def _coerce_records(records: Atlas | Iterable[AtlasRecord | Mapping[str, Any]]) -> Tuple[AtlasRecord | Mapping[str, Any], ...]:
    if isinstance(records, Atlas):
        return records.records
    return tuple(records)


def _record_value(record: AtlasRecord | Mapping[str, Any], key: str, default: Any = None) -> Any:
    if isinstance(record, AtlasRecord):
        return getattr(record, key, default)
    return record.get(key, default)


def _record_dependencies(record: AtlasRecord | Mapping[str, Any]) -> Mapping[str, Sequence[str]]:
    deps = _record_value(record, "dependencies", {})
    if not isinstance(deps, Mapping):
        return {}
    return deps


def check_integrity(
    records: Atlas | Iterable[AtlasRecord | Mapping[str, Any]],
    *,
    enforce_domain_counts: bool = False,
) -> IntegrityReport:
    """Run deterministic structural checks without mutating records."""

    rows = _coerce_records(records)
    errors: List[str] = []
    warnings: List[str] = []
    ids: Dict[str, AtlasRecord | Mapping[str, Any]] = {}
    aliases: Dict[str, str] = {}
    domain_counts: Counter[str] = Counter()
    kind_counts: Counter[str] = Counter()
    for index, record in enumerate(rows):
        record_id = str(_record_value(record, "id", ""))
        if not record_id:
            errors.append(f"record[{index}] has no stable id")
            continue
        if record_id in ids:
            errors.append(f"duplicate id: {record_id}")
        ids[record_id] = record
        domain = str(_record_value(record, "domain", ""))
        kind = str(_record_value(record, "kind", ""))
        domain_counts[domain] += 1
        kind_counts[kind] += 1
        if kind not in KINDS:
            errors.append(f"{record_id}: invalid kind {kind!r}")
        status = str(_record_value(record, "status", ""))
        if status not in STATUSES:
            errors.append(f"{record_id}: invalid status {status!r}")
        epistemic = str(_record_value(record, "status_epistemic_class", ""))
        if epistemic not in EPISTEMIC_CLASSES:
            errors.append(f"{record_id}: invalid status epistemic class {epistemic!r}")
        canonical = str(_record_value(record, "canonical_name", ""))
        if not canonical:
            errors.append(f"{record_id}: missing canonical_name")
        for alias in _record_value(record, "aliases", ()) or ():
            normalized = re.sub(r"\s+", " ", str(alias).strip().casefold())
            if not normalized:
                errors.append(f"{record_id}: empty alias")
            elif normalized in aliases and aliases[normalized] != record_id:
                errors.append(f"duplicate alias {alias!r}: {aliases[normalized]} and {record_id}")
            else:
                aliases[normalized] = record_id
        deps = _record_dependencies(record)
        if set(deps) != set(DEPENDENCY_GROUPS):
            errors.append(
                f"{record_id}: dependency groups must be {list(DEPENDENCY_GROUPS)}, got {sorted(deps)}"
            )
        for group in DEPENDENCY_GROUPS:
            for ref in deps.get(group, ()):
                if str(ref) == record_id:
                    errors.append(f"{record_id}: self dependency in {group}")
        ladder = _record_value(record, "making_ladder", ()) or ()
        if kind == "PRODUCT" and domain != "shared_foundations":
            flattened = {ref for values in deps.values() for ref in values}
            if len(flattened) < 5:
                errors.append(f"{record_id}: finished/product record has fewer than five dependencies")
            if len(ladder) < 5:
                errors.append(f"{record_id}: product record has fewer than five making-ladder steps")
        for step in ladder:
            action = step.action if isinstance(step, LadderStep) else str(step.get("action", ""))
            if action not in LADDER_ACTIONS:
                errors.append(f"{record_id}: invalid making-ladder action {action!r}")
        upstream = tuple(_record_value(record, "upstream", ()) or ())
        downstream = tuple(_record_value(record, "downstream", ()) or ())
        related = tuple(_record_value(record, "related", ()) or ())
        if not upstream and not downstream and not related:
            errors.append(f"{record_id}: dead-end record without an upstream/downstream/related link")
        for ref in (*upstream, *downstream, *related):
            # Resolution is checked after the ID pass so forward references are legal.
            if not isinstance(ref, str) or not ref:
                errors.append(f"{record_id}: empty/non-string graph reference")

    for record in rows:
        record_id = str(_record_value(record, "id", ""))
        deps = _record_dependencies(record)
        refs = [ref for values in deps.values() for ref in values]
        refs.extend(_record_value(record, "upstream", ()) or ())
        refs.extend(_record_value(record, "downstream", ()) or ())
        refs.extend(_record_value(record, "related", ()) or ())
        for ref in refs:
            if ref not in ids:
                errors.append(f"{record_id}: unresolved reference {ref}")

    if enforce_domain_counts:
        expected = {str(d["name"]) for d in DOMAIN_SPECS}
        for domain in sorted(expected):
            count = domain_counts.get(domain, 0)
            if count < 800 or count > 1100:
                errors.append(f"{domain}: expected 800-1100 records, got {count}")
        missing = sorted(expected - set(domain_counts))
        if missing:
            errors.extend(f"missing domain: {domain}" for domain in missing)
    if "shared_foundations" not in domain_counts:
        warnings.append("shared_foundations domain is absent; subset validation may be intentional")
    return IntegrityReport(
        ok=not errors,
        record_count=len(rows),
        counts_by_domain=dict(sorted(domain_counts.items())),
        counts_by_kind=dict(sorted(kind_counts.items())),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def validate_atlas(
    records: Atlas | Iterable[AtlasRecord | Mapping[str, Any]],
    *,
    enforce_domain_counts: bool = False,
) -> IntegrityReport:
    """Validate an atlas and raise a concise error if any invariant fails."""

    report = check_integrity(records, enforce_domain_counts=enforce_domain_counts)
    if not report.ok:
        detail = "\n".join(report.errors[:20])
        if len(report.errors) > 20:
            detail += f"\n... {len(report.errors) - 20} more errors"
        raise AtlasIntegrityError(detail)
    return report


def assert_integrity(
    records: Atlas | Iterable[AtlasRecord | Mapping[str, Any]],
    *,
    enforce_domain_counts: bool = False,
) -> None:
    validate_atlas(records, enforce_domain_counts=enforce_domain_counts)


@lru_cache(maxsize=8)
def _generate_cached(domain_codes: Tuple[str, ...]) -> Atlas:
    selected = _selected_domains(domain_codes)
    atlas = Atlas(
        records=tuple(_build_records(selected)),
        schema_version=ATLAS_SCHEMA_VERSION,
        generator_version=GENERATOR_VERSION,
    )
    # Full generation is held to the requested breadth contract.  A selected
    # subset is still validated for referential integrity but not for global
    # domain counts.
    validate_atlas(atlas, enforce_domain_counts=len(selected) == len(DOMAIN_SPECS))
    return atlas


def generate_atlas(domains: Iterable[str] | str | None = None) -> Atlas:
    """Generate the full deterministic atlas, optionally selecting domains."""

    selected = _selected_domains(domains)
    return _generate_cached(tuple(str(domain["code"]) for domain in selected))


def generate_domain(domain: str) -> Atlas:
    """Generate shared foundations plus one requested domain."""

    return generate_atlas([domain])


def generate_records(domains: Iterable[str] | str | None = None) -> List[Dict[str, Any]]:
    """JSON-friendly record list convenience wrapper."""

    return generate_atlas(domains).to_records()


def generate_atlas_dict(domains: Iterable[str] | str | None = None) -> Dict[str, Any]:
    """Return the complete JSON-compatible atlas envelope."""

    return generate_atlas(domains).to_dict()


def generate_atlas_records(domains: Iterable[str] | str | None = None) -> List[Dict[str, Any]]:
    """Explicit alias for clients that prefer a plain list over :class:`Atlas`."""

    return generate_records(domains)


def generate_domain_records(domain: str) -> List[Dict[str, Any]]:
    """Return only domain-owned records (shared records are deduplicated)."""

    atlas = generate_domain(domain)
    selected = _selected_domains(domain)
    domain_names = {str(item["name"]) for item in selected}
    return [record.to_dict() for record in atlas if record.domain in domain_names]


def domain_counts(atlas: Atlas | None = None) -> Dict[str, int]:
    """Return deterministic counts excluding shared foundations."""

    atlas = atlas or generate_atlas()
    return dict(
        sorted(
            Counter(record.domain for record in atlas if record.domain != "shared_foundations").items()
        )
    )


def domain_counts_by_code(atlas: Atlas | None = None) -> Dict[str, int]:
    """Return the same coverage counts keyed by stable domain code."""

    atlas = atlas or generate_atlas()
    return dict(
        sorted(
            Counter(record.domain_code for record in atlas if record.domain_code != "shared").items()
        )
    )


# Friendly aliases for callers that use a registry/atlas vocabulary.
build_atlas = generate_atlas
build_records = generate_records
integrity_check = check_integrity
generate = generate_atlas


__all__ = [
    "GENERATOR_VERSION",
    "generate_atlas",
    "generate_domain",
    "generate_records",
    "generate_atlas_dict",
    "generate_atlas_records",
    "generate_domain_records",
    "build_atlas",
    "build_records",
    "generate",
    "check_integrity",
    "integrity_check",
    "validate_atlas",
    "assert_integrity",
    "domain_counts",
    "domain_counts_by_code",
]
