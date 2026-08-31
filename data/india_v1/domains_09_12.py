"""FORGE India V1 breadth catalog for presentation domains 09--12.

This module is deliberately an ontology/data pack rather than a capacity
dataset.  It gives the India-first UI and later registry work a broad,
deterministic set of product and capability nodes while preserving the hard
epistemic boundary: an India status is a navigation-level prior, not evidence
of qualified supply, effective capacity, or a named supplier.

The catalog uses bounded, domain-specific axes instead of a free Cartesian
product.  Each domain contains 30 archetypes and each archetype has four
compatible architecture variants across nine operating contexts (1,080 direct
read-model records per domain).  The sibling atlas generator uses the same 30
archetypes with its bounded 29-record ladder (870 atlas records per domain).
The axes are intentionally coarse enough for discovery and specific enough to
point to different dependencies, gaps, and making steps.

Shared primitive IDs use readable prefixes such as ``mat:``, ``cap:``,
``proc:``, and ``util:``.  They are references only; the shared registry is
responsible for resolving and de-duplicating them across domains.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable, Mapping, Sequence

from forge.india_v1.quality import (
    correct_epistemic_status,
    display_name,
    family_key,
    variant_label,
)


# These are the human-facing overlays defined by the FORGE India operating
# vision.  They must not be interpreted as capacity or qualification claims.
INDIA_STATUS_ENUM = (
    "STRONG / AVAILABLE IN INDIA",
    "PARTIAL / SCALE-LIMITED",
    "SPECIFICATION GAP",
    "QUALIFICATION GAP",
    "CAPACITY GAP",
    "IMPORT-DEPENDENT",
    "MISSING / NO EVIDENCED DOMESTIC CAPABILITY",
    "UNKNOWN",
    "CONFLICTED",
)

EPISTEMIC_CLASS = "ASSUMPTION"


@dataclass(frozen=True)
class Archetype:
    """A compact seed from which compatible presentation records are made."""

    id: str
    name: str
    kind: str
    category: str
    explanation: str
    use: str
    architectures: tuple[str, str, str, str]
    contexts: tuple[str, str, str, str, str, str, str, str, str]
    status: str = "PARTIAL / SCALE-LIMITED"
    tags: tuple[str, ...] = ()
    upstream: tuple[str, ...] = ()
    downstream: tuple[str, ...] = ()
    related: tuple[str, ...] = ()


@dataclass(frozen=True)
class DomainSpec:
    id: str
    number: int
    name: str
    purpose: str
    archetypes: tuple[Archetype, ...]


def _a(
    id: str,
    name: str,
    kind: str,
    category: str,
    explanation: str,
    use: str,
    architectures: Sequence[str],
    contexts: Sequence[str],
    *,
    status: str = "PARTIAL / SCALE-LIMITED",
    tags: Sequence[str] = (),
    upstream: Sequence[str] = (),
    downstream: Sequence[str] = (),
    related: Sequence[str] = (),
) -> Archetype:
    """Create an archetype while checking the bounded axis contract."""

    if len(architectures) != 4:
        raise ValueError(f"{id}: exactly four compatible architectures required")
    if len(contexts) != 9:
        raise ValueError(f"{id}: exactly nine operating contexts required")
    if status not in INDIA_STATUS_ENUM:
        raise ValueError(f"{id}: unsupported India status {status!r}")
    return Archetype(
        id=id,
        name=name,
        kind=kind,
        category=category,
        explanation=explanation,
        use=use,
        architectures=tuple(architectures),  # type: ignore[arg-type]
        contexts=tuple(contexts),  # type: ignore[arg-type]
        status=status,
        tags=tuple(tags),
        upstream=tuple(upstream),
        downstream=tuple(downstream),
        related=tuple(related),
    )


# ---------------------------------------------------------------------------
# Shared readable primitive vocabulary
# ---------------------------------------------------------------------------

_BASE_MATERIALS = [
    "mat:carbon-steel",
    "mat:alloy-steel",
    "mat:stainless-steel",
    "mat:aluminium",
    "mat:copper",
    "mat:engineering-polymers",
]
_BASE_COMPONENTS = [
    "cap:bearings",
    "cap:seals-and-gaskets",
    "cap:motors",
    "cap:power-electronics",
    "cap:industrial-controls",
]
_BASE_PROCESSES = [
    "proc:cutting-and-forming",
    "proc:machining",
    "proc:welding-and-joining",
    "proc:surface-treatment",
    "proc:assembly-and-test",
]
_BASE_CAPABILITIES = [
    "cap:tooling-and-fixtures",
    "cap:industrial-metrology",
    "cap:process-quality",
    "cap:maintenance-and-service",
]
_BASE_UTILITIES = [
    "util:reliable-electricity",
    "util:industrial-water",
    "util:industrial-gases",
    "util:material-and-logistics-handling",
]


def _unique(values: Iterable[str], limit: int | None = None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            out.append(value)
            seen.add(value)
    return out if limit is None else out[:limit]


def _slug(value: str) -> str:
    value = value.lower().replace("&", "and")
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def _label(value: str) -> str:
    return value.replace("-", " ")


def _status_for_variant(archetype: Archetype, architecture: str) -> str:
    """Apply a deliberately broad overlay to an archetype/variant.

    This is not a capability inference.  It only keeps visibly advanced or
    specification-sensitive variants from inheriting the same broad label as
    a conventional product family.
    """

    advanced = {
        "hydrogen",
        "fuel-cell",
        "autonomous",
        "high-voltage",
        "nuclear-grade",
        "space-grade",
        "ultra-precision",
        "digital-twin-ready",
        "safety-class",
        "high-speed",
        "smart",
        "servo-controlled",
    }
    if any(token in architecture.lower().replace("_", "-") for token in advanced):
        if archetype.status in {"UNKNOWN", "MISSING / NO EVIDENCED DOMESTIC CAPABILITY"}:
            return archetype.status
        return "SPECIFICATION GAP"
    return archetype.status


def _dependency_groups(
    domain_id: str,
    archetype: Archetype,
    architecture: str,
    context: str,
) -> dict[str, list[str]]:
    """Build grouped, readable dependencies for one variant.

    The returned groups stay compact (normally 12--20 IDs) and include
    architecture-sensitive nodes.  They are references, not claims that an
    Indian producer exists for any node.
    """

    text = f"{archetype.id} {architecture} {context}".lower().replace("_", "-")
    materials = list(_BASE_MATERIALS)
    components = list(_BASE_COMPONENTS)
    processes = list(_BASE_PROCESSES)
    capabilities = list(_BASE_CAPABILITIES)
    utilities = list(_BASE_UTILITIES)

    if domain_id == "09_transport_mobility":
        materials += ["mat:tyre-and-elastomer", "mat:glass-and-coatings"]
        components += ["cap:braking-and-steering", "cap:vehicle-wiring"]
        processes += ["proc:body-fabrication", "proc:paint-and-corrosion-control"]
        capabilities += ["cap:vehicle-integration", "cap:safety-qualification"]
        utilities += ["util:road-rail-port-infrastructure", "util:charging-or-fueling"]
        if any(x in text for x in ("electric", "battery", "hybrid")):
            components += ["cap:battery-cells-and-packs", "cap:traction-inverter"]
            utilities += ["util:high-power-charging"]
        if any(x in text for x in ("ice", "diesel", "cng", "lng", "combustion")):
            components += ["cap:combustion-engine", "cap:emissions-aftertreatment"]
        if any(x in text for x in ("hydrogen", "fuel-cell")):
            components += ["cap:hydrogen-storage-and-fuel-cell", "cap:gas-safety"]
        if any(x in text for x in ("rail", "locomotive", "metro", "coach", "wagon")):
            components += ["cap:rail-bogies-and-wheelsets", "cap:rail-signalling"]
            utilities += ["util:rail-corridor-and-depot"]
        if any(x in text for x in ("marine", "ferry", "barge", "vessel", "boat")):
            processes += ["proc:marine-hull-fabrication", "proc:marine-corrosion-control"]
            utilities += ["util:port-and-dry-dock"]
        if any(x in text for x in ("forklift", "mining", "airport", "port-tractor")):
            components += ["cap:hydraulics-and-actuation", "cap:industrial-tyres"]
    elif domain_id == "10_infrastructure_construction_heavy_equipment":
        materials += ["mat:transformer-steel", "mat:refractory-and-insulation"]
        components += ["cap:fluid-power", "cap:industrial-sensors"]
        processes += ["proc:pressure-boundary-fabrication", "proc:electrical-assembly"]
        capabilities += ["cap:equipment-integration", "cap:site-commissioning"]
        utilities += ["util:construction-site-services", "util:grid-connection"]
        if any(x in text for x in ("transformer", "switchgear", "switchboard", "busduct", "ups")):
            materials += ["mat:electrical-insulation", "mat:electrical-copper"]
            components += ["cap:protection-and-relays", "cap:power-quality"]
            processes += ["proc:vacuum-drying-and-impregnation", "proc:high-voltage-test"]
        if any(x in text for x in ("pump", "compressor", "chiller", "boiler", "heat-exchanger", "cooling")):
            components += ["cap:mechanical-seals", "cap:fluid-control-valves"]
            processes += ["proc:pressure-and-leak-test", "proc:balancing-and-vibration-test"]
        if any(x in text for x in ("water", "wastewater")):
            components += ["cap:filtration-and-membranes", "cap:chemical-dosing"]
            utilities += ["util:process-water-and-effluent"]
        if any(x in text for x in ("crane", "excavator", "loader", "bulldozer", "road", "concrete")):
            components += ["cap:hydraulic-cylinders", "cap:heavy-duty-drivetrain"]
            processes += ["proc:large-weldment-fabrication", "proc:wear-surface-treatment"]
            utilities += ["util:heavy-lift-and-site-logistics"]
    elif domain_id == "11_consumer_textile_packaging_general_manufacturing":
        materials += ["mat:textile-fibres", "mat:paper-and-board", "mat:rubber-and-elastomer"]
        components += ["cap:small-motors", "cap:embedded-electronics", "cap:heating-and-cooling"]
        processes += ["proc:forming-and-moulding", "proc:printing-and-decoration"]
        capabilities += ["cap:production-line-integration", "cap:consumer-product-testing"]
        utilities += ["util:steam-and-thermal-services", "util:packaging-and-distribution"]
        if any(x in text for x in ("textile", "garment", "footwear", "knit", "weav", "spinn", "dye")):
            materials += ["mat:yarn-and-fabric", "mat:dyes-and-auxiliaries"]
            processes += ["proc:textile-forming", "proc:textile-wet-processing"]
            capabilities += ["cap:textile-quality-and-testing"]
            utilities += ["util:water-and-effluent-treatment"]
        if any(x in text for x in ("packaging", "box", "bottle", "container", "printing")):
            materials += ["mat:films-and-laminates", "mat:inks-and-adhesives"]
            processes += ["proc:slitting-and-converting", "proc:packaging-line-validation"]
            capabilities += ["cap:food-contact-and-packaging-compliance"]
        if any(x in text for x in ("moulding", "molding", "plastic")):
            components += ["cap:injection-and-blow-moulding-tools", "cap:hot-runner-and-nozzle"]
            processes += ["proc:polymer-compounding", "proc:tool-steel-heat-treatment"]
        if any(x in text for x in ("appliance", "fan", "luminaire", "electronics")):
            components += ["cap:motors-and-drives", "cap:electrical-safety"]
    elif domain_id == "12_foundational_industrial_capabilities":
        materials += ["mat:tool-steel", "mat:cast-iron", "mat:electrical-steel"]
        components += ["cap:seals-and-lubrication", "cap:industrial-sensors"]
        processes += ["proc:heat-treatment", "proc:calibration-and-acceptance"]
        capabilities += ["cap:process-development", "cap:supplier-qualification"]
        utilities += ["util:compressed-air-and-vacuum", "util:maintenance-spares"]
        if any(x in text for x in ("pump", "valve", "compressor", "heat-exchanger")):
            components += ["cap:fluid-control", "cap:pressure-and-leak-testing"]
        if any(x in text for x in ("motor", "drive", "control")):
            materials += ["mat:magnetic-materials", "mat:lamination-steel"]
            components += ["cap:windings-and-insulation", "cap:power-semiconductor"]
            processes += ["proc:electrical-winding-and-balancing", "proc:firmware-and-control-validation"]
        if any(x in text for x in ("bearing", "gear", "grinding", "machine-tool", "turning", "milling")):
            materials += ["mat:high-carbon-bearing-steel", "mat:precision-lubricants"]
            processes += ["proc:precision-grinding-and-lapping", "proc:gear-cutting"]
            capabilities += ["cap:precision-assembly", "cap:accuracy-traceability"]
        if any(x in text for x in ("casting", "forging")):
            processes += ["proc:melting-and-metal-treatment", "proc:non-destructive-testing"]
            capabilities += ["cap:pattern-and-die-making", "cap:foundry-and-forge-quality"]
        if any(x in text for x in ("gas", "utility", "maintenance")):
            utilities += ["util:hazardous-area-and-safety", "util:spares-and-service-network"]

    groups = {
        "materials": _unique(materials, 9),
        "components": _unique(components, 9),
        "processes": _unique(processes, 9),
        "capabilities": _unique(capabilities, 7),
        "utilities": _unique(utilities, 7),
    }

    # Finished-product dependency lists are intentionally bounded.  Trim from
    # the later/enabling groups first, retaining at least three references in
    # every group so the grouped shape remains useful.  The trim is applied to
    # every node (including capability records) so downstream consumers can
    # rely on one simple 5..30 contract.
    while sum(len(values) for values in groups.values()) > 30:
        removed = False
        for group_name in ("utilities", "capabilities", "processes", "components", "materials"):
            values = groups[group_name]
            if len(values) > 3:
                values.pop()
                removed = True
                break
        if not removed:  # pragma: no cover - defensive guard for future edits
            break
    return groups


def _making_ladder(archetype: Archetype, architecture: str, context: str) -> list[dict[str, str]]:
    target = f"{_label(architecture)} {archetype.name.lower()} for {_label(context)}"
    return [
        {"action": "IMPORT", "step": f"Secure interim inputs and benchmark references for {target}; eligibility is not supply."},
        {"action": "DEVELOP", "step": "Freeze the duty, interfaces, safety envelope, BOM, process route, and acceptance basis."},
        {"action": "REDESIGN", "step": "Select a compatible architecture and remove avoidable specification, tooling, and import choke points."},
        {"action": "BUILD", "step": "Prototype the route with work instructions, process controls, traceable measurements, and maintainable fixtures."},
        {"action": "R&D", "step": "Resolve process windows, qualification tests, yield learning, reliability, and customer or regulatory acceptance."},
        {"action": "LICENSE", "step": "Use licensing, JV, supplier development, or validated substitution where domestic capability is not yet closed."},
    ]


def _status_basis(status: str) -> dict[str, str]:
    return {
        "epistemic_class": EPISTEMIC_CLASS,
        "basis": (
            f"{status} is a broad India navigation overlay for discovery only. "
            "It does not establish a named producer, effective capacity, yield, "
            "qualification, allocation, or current import availability. "
            "Variant-specific evidence remains UNKNOWN."
        ),
    }


def _record(
    domain: DomainSpec,
    archetype: Archetype,
    architecture: str,
    context: str,
    ordinal: int,
) -> dict[str, Any]:
    architecture_label = _label(architecture)
    context_label = _label(context)
    record_id = (
        f"india-v1:{domain.number:02d}:{_slug(archetype.id)}:"
        f"{_slug(architecture)}:{_slug(context)}"
    )
    canonical_name = display_name(
        {
            "id": record_id,
            "canonical_name": f"{architecture_label.title()} {archetype.name} — {context_label.title()}",
            "variant_axes": {"architecture": architecture, "operating_context": context},
        }
    )
    dependencies = _dependency_groups(domain.id, archetype, architecture, context)
    dependency_ids = _unique(item for group in dependencies.values() for item in group)
    status = _status_for_variant(archetype, architecture)
    basis = _status_basis(status)
    corrected = correct_epistemic_status(
        {
            "status": status,
            "india_status": status,
            "status_basis": basis["basis"],
            "status_epistemic_class": basis["epistemic_class"],
            # The 09--12 pack intentionally keeps its source overlay class;
            # the correction helper only changes it when an unsupported
            # STRONG/MISSING assumption is actually present.
            "epistemic_class": basis["epistemic_class"],
        }
    )
    status = str(corrected.get("status", status))
    basis_text = str(corrected.get("status_basis", basis["basis"]))
    basis_epistemic = str(corrected.get("status_epistemic_class", basis["epistemic_class"]))

    # Relations intentionally point at shared primitives and stable archetype
    # nodes.  The registry can later resolve an archetype node to all variants.
    upstream = _unique(
        list(archetype.upstream)
        + dependency_ids[:5]
        + [f"node:{domain.number:02d}:{archetype.id}"],
        12,
    )
    downstream = _unique(
        list(archetype.downstream)
        + [f"node:{domain.number:02d}:{item}" for item in archetype.downstream],
        12,
    )
    related = _unique(
        list(archetype.related)
        + list(archetype.tags)
        + [f"node:{domain.number:02d}:{item}" for item in archetype.related],
        12,
    )

    gaps = [
        "Variant-specific design ownership, process maturity, yield, and effective qualified capacity are UNKNOWN.",
        "Material grade, tooling envelope, metrology traceability, and acceptance evidence must be resolved before a build decision.",
        "Ramp time, maintenance burden, workforce depth, and allocation against competing demand are not inferred here.",
    ]
    import_notes = [
        "Imported content may occur in high-grade materials, controls, sensors, power electronics, or capital equipment; product presence is not proof of domestic supply.",
        "Trade eligibility and a reported factory footprint must not be converted into qualified, available Indian output.",
    ]
    if status in {"IMPORT-DEPENDENT", "SPECIFICATION GAP", "MISSING / NO EVIDENCED DOMESTIC CAPABILITY"}:
        import_notes.append(
            "This overlay flags a likely specification or import exposure; exact origin, substitutes, qualification path, and available allocation remain UNKNOWN."
        )

    record = {
        "id": record_id,
        "domain_id": domain.id,
        "domain_number": domain.number,
        "archetype_id": f"node:{domain.number:02d}:{archetype.id}",
        "family_key": family_key(record_id),
        "ordinal": ordinal,
        "canonical_name": canonical_name,
        "name": canonical_name,
        "display_name": canonical_name,
        "variant_label": variant_label({"variant_axes": {"architecture": architecture, "operating_context": context}}),
        "profile": _atlas_profile(domain.id, archetype),
        "aliases": _unique(
            [
                archetype.name,
                f"{architecture_label} {archetype.name}",
                f"{archetype.name} ({context_label})",
                archetype.id.replace("_", " "),
            ]
        ),
        "kind": archetype.kind,
        "category": archetype.category,
        "explanation": (
            f"A {architecture_label} variant of {archetype.name.lower()} for {context_label.lower()}. "
            f"{archetype.explanation}"
        ),
        "use": f"{archetype.use} This variant is framed for {context_label.lower()}.",
        "india_status": str(corrected.get("india_status", status)),
        "status": status,
        "status_basis": basis_text,
        "status_basis_epistemic_class": basis_epistemic,
        "status_epistemic_class": basis_epistemic,
        "status_basis_metadata": corrected.get("status_basis_metadata", {}),
        "epistemic_class": basis_epistemic,
        "variant_axes": {
            "architecture": architecture,
            "operating_context": context,
        },
        # `dependencies` is the grouped contract.  `dependency_ids` is a
        # convenient flattened view for registry loaders and tests.
        "dependencies": dependencies,
        "dependency_groups": dependencies,
        "dependency_ids": dependency_ids,
        "gaps": gaps,
        "import_notes": import_notes,
        "making_ladder": _making_ladder(archetype, architecture, context),
        "upstream": upstream,
        "downstream": downstream,
        "related": related,
        "source_basis": "ASSUMPTION: curated archetype taxonomy; no web research or company/facility claim.",
    }
    return record


# ---------------------------------------------------------------------------
# Domain archetypes
# ---------------------------------------------------------------------------

_ROAD_CONTEXTS = (
    "urban-fleet",
    "periurban",
    "intercity",
    "rural",
    "shared-mobility",
    "export",
    "hot-weather",
    "monsoon",
    "low-total-cost",
)
_RAIL_CONTEXTS = (
    "commuter",
    "intercity",
    "freight",
    "heavy-haul",
    "metro",
    "maintenance-fleet",
    "export",
    "hot-weather",
    "monsoon",
)
_MARINE_CONTEXTS = (
    "inland-waterway",
    "coastal",
    "port-service",
    "fishing",
    "passenger",
    "short-haul-cargo",
    "export",
    "hot-weather",
    "monsoon",
)
_OFFHIGHWAY_CONTEXTS = (
    "warehouse",
    "port",
    "mine",
    "construction-site",
    "agriculture",
    "municipal",
    "fleet",
    "hot-weather",
    "monsoon",
)


_DOMAIN_09_ARCHETYPES = (
    _a("two_wheeler", "Two-wheeler", "finished_product", "road_mobility", "A powered two-wheel vehicle with a compact chassis, steering, braking, and rider interface.", "Personal, delivery, and shared short-distance movement.", ("battery-electric", "internal-combustion", "hybrid", "battery-swap"), _ROAD_CONTEXTS, upstream=("mat:steel", "cap:tyres"), downstream=("node:09:charging-network", "node:09:service-and-spares"), related=("cap:vehicle-integration",)),
    _a("three_wheeler", "Three-wheeler", "finished_product", "road_mobility", "A three-wheel vehicle architecture balancing payload, stability, and maneuverability.", "Passenger and last-mile goods movement.", ("battery-electric", "cng", "diesel", "hybrid"), _ROAD_CONTEXTS, upstream=("mat:steel", "cap:vehicle-wiring"), downstream=("node:09:charging-network", "node:09:fleets"), related=("node:09:two_wheeler",)),
    _a("passenger_car", "Passenger car", "finished_product", "road_mobility", "A road vehicle integrating body, powertrain, restraint, thermal, electrical, and software systems.", "Private, fleet, and shared passenger transport.", ("battery-electric", "internal-combustion", "hybrid", "cng"), _ROAD_CONTEXTS, upstream=("cap:motors", "cap:vehicle-safety"), downstream=("node:09:charging-network", "node:09:service-and-spares"), related=("node:09:light-commercial-vehicle",)),
    _a("light_commercial_vehicle", "Light commercial vehicle", "finished_product", "road_mobility", "A van or small truck architecture optimized for payload, uptime, and route economics.", "Urban delivery, service, and regional distribution.", ("diesel", "cng", "battery-electric", "hybrid"), _ROAD_CONTEXTS, upstream=("cap:drivetrain", "cap:vehicle-wiring"), downstream=("node:09:fleets", "node:09:logistics"), related=("node:09:passenger-car",)),
    _a("medium_truck", "Medium truck", "finished_product", "road_mobility", "A rigid truck platform with chassis, axle, braking, body, and commercial-duty powertrain.", "Regional freight, municipal service, and industrial logistics.", ("diesel", "cng", "battery-electric", "fuel-cell"), _ROAD_CONTEXTS, upstream=("cap:heavy-duty-drivetrain", "cap:braking-and-steering"), downstream=("node:09:fleets", "node:09:service-and-spares"), related=("node:09:heavy-truck",)),
    _a("heavy_truck", "Heavy truck", "finished_product", "road_mobility", "A high-payload tractor or rigid platform requiring durable axles, brakes, thermal management, and long-duty power.", "Long-haul freight and heavy logistics.", ("diesel", "lng", "battery-electric", "hydrogen"), _ROAD_CONTEXTS, upstream=("cap:heavy-duty-drivetrain", "cap:industrial-tyres"), downstream=("node:09:trailer", "node:09:logistics"), related=("node:09:medium-truck",)),
    _a("city_bus", "City bus", "finished_product", "road_mobility", "A high-cadence passenger vehicle designed for repeated stops, accessibility, and depot operations.", "Urban public transit.", ("diesel", "cng", "battery-electric", "hybrid"), _ROAD_CONTEXTS, upstream=("cap:vehicle-safety", "cap:traction-inverter"), downstream=("node:09:depot-charging", "node:09:public-transit"), related=("node:09:intercity-bus",)),
    _a("intercity_bus", "Intercity bus", "finished_product", "road_mobility", "A long-distance passenger vehicle emphasizing ride quality, range, thermal comfort, and maintainability.", "Intercity and staff transport.", ("diesel", "cng", "battery-electric", "fuel-cell"), _ROAD_CONTEXTS, upstream=("cap:vehicle-safety", "cap:thermal-management"), downstream=("node:09:depot-charging", "node:09:public-transit"), related=("node:09:city-bus",)),
    _a("ambulance", "Ambulance", "finished_product", "special-purpose_mobility", "A special-purpose vehicle with a converted body, medical payload interfaces, and emergency duty requirements.", "Emergency response and patient transport.", ("diesel", "battery-electric", "hybrid", "cng"), _ROAD_CONTEXTS, upstream=("cap:vehicle-integration", "cap:medical-interiors"), downstream=("node:09:emergency-fleet", "node:09:service-and-spares"), related=("node:09:fire-apparatus",)),
    _a("fire_apparatus", "Fire apparatus", "finished_product", "special-purpose_mobility", "A heavy special-purpose vehicle integrating pump, tank, access, rescue, and emergency control systems.", "Firefighting, rescue, and disaster response.", ("diesel", "hybrid", "battery-electric", "cng"), _ROAD_CONTEXTS, upstream=("cap:fluid-control", "cap:heavy-duty-drivetrain"), downstream=("node:09:emergency-fleet", "node:09:maintenance"), related=("node:09:ambulance",)),
    _a("road_tractor", "Road tractor", "finished_product", "freight_mobility", "A tractor unit coupling to trailers and distributing high torque through a commercial drivetrain.", "Heavy road freight and logistics corridors.", ("diesel", "cng", "battery-electric", "hydrogen"), _ROAD_CONTEXTS, upstream=("cap:heavy-duty-drivetrain", "cap:couplings-and-fifth-wheel"), downstream=("node:09:trailer", "node:09:logistics"), related=("node:09:heavy-truck",)),
    _a("agricultural_tractor", "Agricultural tractor", "finished_product", "off_highway_mobility", "A low-speed, high-traction vehicle platform with implement interfaces, hydraulics, and field durability.", "Farm power, hauling, and implement operation.", ("diesel", "battery-electric", "cng", "hybrid"), _OFFHIGHWAY_CONTEXTS, upstream=("cap:fluid-power", "cap:heavy-duty-drivetrain"), downstream=("node:09:implements", "node:09:service-and-spares"), related=("node:10:construction-equipment",)),
    _a("rail_locomotive", "Rail locomotive", "finished_product", "rail_mobility", "A traction unit integrating bogies, traction power, braking, controls, and railway protection interfaces.", "Freight, passenger, and yard rail traction.", ("diesel-electric", "overhead-electric", "battery-electric", "hydrogen-electric"), _RAIL_CONTEXTS, status="SPECIFICATION GAP", upstream=("cap:rail-bogies-and-wheelsets", "cap:traction-inverter"), downstream=("node:09:rail-depot", "node:09:rail-signalling"), related=("node:09:rail-coach",)),
    _a("rail_coach", "Rail coach", "finished_product", "rail_mobility", "A passenger or service coach body and running gear engineered for railway loading, safety, and maintainability.", "Passenger, sleeper, and service rail formations.", ("stainless-steel", "aluminium", "composite", "double-deck"), _RAIL_CONTEXTS, upstream=("cap:rail-bogies-and-wheelsets", "cap:rail-interiors"), downstream=("node:09:rail-depot", "node:09:rail-signalling"), related=("node:09:metro-trainset",)),
    _a("freight_wagon", "Freight wagon", "finished_product", "rail_mobility", "A rail vehicle for bulk or unitized cargo with load-bearing body, bogies, braking, and coupling interfaces.", "Bulk, container, and industrial freight movement.", ("covered-wagon", "open-wagon", "container-flat", "tank-wagon"), _RAIL_CONTEXTS, upstream=("cap:rail-bogies-and-wheelsets", "cap:rail-braking"), downstream=("node:09:rail-depot", "node:09:freight-terminals"), related=("node:09:rail-locomotive",)),
    _a("metro_trainset", "Metro trainset", "finished_product", "rail_mobility", "A high-frequency electric trainset with distributed traction, doors, passenger systems, and train control.", "Urban mass transit on dedicated corridors.", ("steel-body", "aluminium-body", "stainless-body", "driverless-ready"), _RAIL_CONTEXTS, status="SPECIFICATION GAP", upstream=("cap:rail-bogies-and-wheelsets", "cap:rail-signalling"), downstream=("node:09:metro-depot", "node:09:public-transit"), related=("node:09:rail-coach",)),
    _a("rail_maintenance_vehicle", "Rail maintenance vehicle", "finished_product", "rail_mobility", "A work vehicle carrying inspection, lifting, maintenance, or track-service equipment.", "Track, overhead-line, and railway asset maintenance.", ("diesel-hydraulic", "battery-electric", "overhead-electric", "hybrid"), _RAIL_CONTEXTS, upstream=("cap:hydraulics-and-actuation", "cap:rail-bogies-and-wheelsets"), downstream=("node:09:rail-depot", "node:09:rail-maintenance"), related=("node:10:mobile-crane",)),
    _a("inland_barge", "Inland cargo barge", "finished_product", "marine_mobility", "A shallow-draft cargo vessel with hull, propulsion, cargo handling, and river-service systems.", "Bulk and container movement on inland waterways.", ("diesel", "hybrid-electric", "battery-electric", "shore-power-ready"), _MARINE_CONTEXTS, upstream=("cap:marine-hull", "cap:marine-propulsion"), downstream=("node:09:inland-terminal", "node:09:logistics"), related=("node:09:coastal-vessel",)),
    _a("coastal_vessel", "Coastal cargo vessel", "finished_product", "marine_mobility", "A coastal ship architecture balancing cargo, range, hull integrity, navigation, and port turnaround.", "Short-sea cargo and coastal supply chains.", ("diesel", "lng", "hybrid-electric", "shore-power-ready"), _MARINE_CONTEXTS, upstream=("cap:marine-hull", "cap:marine-navigation"), downstream=("node:09:port-services", "node:09:logistics"), related=("node:09:inland-barge",)),
    _a("passenger_ferry", "Passenger ferry", "finished_product", "marine_mobility", "A passenger vessel with hull, propulsion, lifesaving, accessibility, and boarding systems.", "River, island, and coastal passenger service.", ("diesel", "battery-electric", "hybrid-electric", "hydrogen-electric"), _MARINE_CONTEXTS, status="SPECIFICATION GAP", upstream=("cap:marine-hull", "cap:marine-safety"), downstream=("node:09:port-services", "node:09:public-transit"), related=("node:09:inland-barge",)),
    _a("fishing_vessel", "Fishing vessel", "finished_product", "marine_mobility", "A working vessel integrating propulsion, hull, deck machinery, cold handling, and marine safety.", "Nearshore and coastal fishing operations.", ("diesel", "hybrid-electric", "battery-electric", "shore-power-ready"), _MARINE_CONTEXTS, upstream=("cap:marine-hull", "cap:deck-machinery"), downstream=("node:09:fish-cold-chain", "node:09:port-services"), related=("node:09:coastal-vessel",)),
    _a("warehouse_forklift", "Warehouse forklift", "finished_product", "material_handling_mobility", "A counterbalanced or reach vehicle with mast, lifting hydraulics, drive, and operator safety systems.", "Indoor and yard material handling.", ("lead-acid-electric", "lithium-electric", "cng", "diesel"), _OFFHIGHWAY_CONTEXTS, upstream=("cap:fluid-power", "cap:industrial-tyres"), downstream=("node:09:warehouse-systems", "node:09:service-and-spares"), related=("node:10:material-handling-equipment",)),
    _a("mining_haul_truck", "Mining haul truck", "finished_product", "off_highway_mobility", "A high-payload off-highway truck requiring frame, dump body, traction, braking, and harsh-environment controls.", "Open-pit mine haulage and heavy bulk movement.", ("diesel-electric", "trolley-assist", "battery-electric", "hydrogen-electric"), _OFFHIGHWAY_CONTEXTS, status="SPECIFICATION GAP", upstream=("cap:heavy-duty-drivetrain", "cap:wear-resistant-materials"), downstream=("node:09:mine-maintenance", "node:10:mining-equipment"), related=("node:09:road-tractor",)),
    _a("airport_ground_vehicle", "Airport ground vehicle", "finished_product", "special-purpose_mobility", "A specialized service vehicle adapted for aircraft handling, passenger service, cargo, or ramp operations.", "Airport ramp, baggage, catering, and ground support.", ("diesel", "battery-electric", "hybrid", "hydrogen-electric"), _OFFHIGHWAY_CONTEXTS, status="SPECIFICATION GAP", upstream=("cap:vehicle-integration", "cap:industrial-sensors"), downstream=("node:09:airport-infrastructure", "node:09:service-and-spares"), related=("node:09:warehouse-forklift",)),
    _a("port_terminal_tractor", "Port terminal tractor", "finished_product", "material_handling_mobility", "A low-speed, high-torque tractor engineered for repetitive container-yard cycles and coupling.", "Container-terminal and intermodal yard movement.", ("diesel", "battery-electric", "hybrid", "hydrogen-electric"), _OFFHIGHWAY_CONTEXTS, upstream=("cap:heavy-duty-drivetrain", "cap:couplings-and-fifth-wheel"), downstream=("node:09:port-services", "node:09:freight-terminals"), related=("node:09:warehouse-forklift",)),
    _a("freight_trailer", "Freight trailer", "finished_product", "freight_mobility", "A towed road-freight body with frame, axles, suspension, coupling, brakes, and cargo-protection systems.", "Dry, refrigerated, tank, and flatbed freight movement.", ("dry-van", "flatbed", "refrigerated", "tank"), _ROAD_CONTEXTS, upstream=("cap:industrial-tyres", "cap:couplings-and-fifth-wheel"), downstream=("node:09:road-tractor", "node:09:logistics"), related=("node:09:heavy-truck",)),
    _a("electric_charging_system", "Electric vehicle charging system", "infrastructure_system", "mobility_infrastructure", "A charging installation combining power conversion, protection, connectors, thermal management, communications, and user or fleet controls.", "Depot, public, workplace, and heavy-vehicle charging.", ("ac-destination", "dc-fast", "battery-swap", "megawatt-class"), _ROAD_CONTEXTS, status="SPECIFICATION GAP", upstream=("cap:power-electronics", "cap:industrial-controls"), downstream=("node:09:city-bus", "node:09:passenger-car"), related=("node:10:industrial-utility",)),
    _a("rail_signalling_system", "Rail signalling system", "equipment", "rail_mobility", "A railway train-detection, interlocking, route-control, communications, and safety-critical control system.", "Safe separation, routing, and traffic management for rail operations.", ("relay-interlocking", "electronic-interlocking", "communications-based", "automatic-train-control"), _RAIL_CONTEXTS, status="SPECIFICATION GAP", upstream=("cap:rail-signalling", "cap:industrial-controls"), downstream=("node:09:rail-locomotive", "node:09:metro-trainset"), related=("node:12:industrial-controls",)),
    _a("port_cargo_handling_equipment", "Port cargo-handling equipment", "heavy_equipment", "marine_mobility", "A crane, reach stacker, conveyor, or ship-to-shore handling system integrating structure, drives, controls, lifting, and safety.", "Container, bulk, and intermodal cargo transfer at ports.", ("ship-to-shore", "rubber-tyred-gantry", "reach-stacker", "bulk-conveyor"), _MARINE_CONTEXTS, status="SPECIFICATION GAP", upstream=("cap:heavy-lift", "cap:industrial-controls"), downstream=("node:09:port-services", "node:09:logistics"), related=("node:09:port-terminal-tractor",)),
    _a("mobility_fleet_maintenance", "Mobility fleet maintenance", "service_capability", "mobility_services", "A service capability covering diagnostics, preventive maintenance, overhaul, spares, charging or fueling support, and fleet reliability.", "Keeping road, rail, marine, and off-highway fleets available and safe.", ("workshop", "mobile-service", "condition-monitoring", "remanufacture"), _OFFHIGHWAY_CONTEXTS, status="PARTIAL / SCALE-LIMITED", upstream=("cap:industrial-metrology", "cap:maintenance-and-service"), downstream=("node:09:road-tractor", "node:09:rail-locomotive"), related=("node:12:maintenance-systems",)),
)


_INFRA_CONTEXTS = (
    "urban-utility",
    "industrial-park",
    "rural-distribution",
    "renewable-integration",
    "water-and-wastewater",
    "construction-site",
    "process-plant",
    "hot-weather",
    "monsoon",
)
_CONSTRUCTION_CONTEXTS = (
    "urban-site",
    "highway",
    "rail-corridor",
    "industrial-plant",
    "mine",
    "water-project",
    "rural-site",
    "hot-weather",
    "monsoon",
)


_DOMAIN_10_ARCHETYPES = (
    _a("power_transformer", "Power transformer", "infrastructure_system", "heavy_electrical", "A static electromagnetic machine transferring AC power between voltage levels with insulation, cooling, protection, and test systems.", "Grid transmission, generation evacuation, and industrial substations.", ("oil-immersed", "dry-type", "auto-transformer", "phase-shifting"), _INFRA_CONTEXTS, status="SPECIFICATION GAP", upstream=("mat:electrical-steel", "cap:high-voltage-test"), downstream=("node:10:substation", "node:10:industrial-utility"), related=("node:12:industrial-controls",)),
    _a("distribution_transformer", "Distribution transformer", "infrastructure_system", "heavy_electrical", "A utility transformer stepping distribution voltage down for local feeders and loads.", "Distribution networks, campuses, and industrial consumers.", ("oil-immersed", "dry-type", "compact-substation", "smart-monitoring"), _INFRA_CONTEXTS, status="PARTIAL / SCALE-LIMITED", upstream=("mat:electrical-steel", "cap:distribution-protection"), downstream=("node:10:substation", "node:10:industrial-utility"), related=("node:10:power-transformer",)),
    _a("medium_voltage_switchgear", "Medium-voltage switchgear", "infrastructure_system", "heavy_electrical", "A switch, protection, busbar, and enclosure system interrupting and isolating medium-voltage circuits.", "Substations, industrial feeders, and renewable interconnection.", ("air-insulated", "gas-insulated", "solid-insulated", "digital-protection"), _INFRA_CONTEXTS, status="SPECIFICATION GAP", upstream=("cap:protection-and-relays", "cap:high-voltage-test"), downstream=("node:10:substation", "node:10:grid-connection"), related=("node:12:industrial-controls",)),
    _a("low_voltage_switchboard", "Low-voltage switchboard", "infrastructure_system", "heavy_electrical", "A power-distribution assembly combining busbars, breakers, protection, metering, and enclosure.", "Buildings, factories, utilities, and data or process loads.", ("fixed-type", "draw-out", "motor-control-center", "smart-monitoring"), _INFRA_CONTEXTS, upstream=("cap:protection-and-relays", "cap:busbars-and-cables"), downstream=("node:10:industrial-utility", "node:12:industrial-controls"), related=("node:10:medium-voltage-switchgear",)),
    _a("busduct_system", "Busduct system", "infrastructure_system", "heavy_electrical", "An enclosed conductor system distributing high current between transformers, boards, and equipment.", "Factory, building, and utility power distribution.", ("sandwich-busduct", "air-insulated", "plug-in", "fire-rated"), _INFRA_CONTEXTS, upstream=("mat:electrical-copper", "cap:electrical-insulation"), downstream=("node:10:low-voltage-switchboard", "node:10:industrial-utility"), related=("node:12:industrial-cables",)),
    _a("diesel_generator_set", "Diesel generator set", "infrastructure_system", "distributed_power", "A packaged engine-generator with fuel, cooling, exhaust, controls, and synchronization interfaces.", "Backup, islanded, and temporary industrial power.", ("stationary-diesel", "dual-fuel", "containerized", "hybrid-battery"), _INFRA_CONTEXTS, upstream=("cap:combustion-engine", "cap:alternator-and-excitation"), downstream=("node:10:microgrid", "node:10:industrial-utility"), related=("node:12:industrial-controls",)),
    _a("industrial_ups", "Industrial UPS", "infrastructure_system", "power_quality", "An uninterruptible power system combining conversion, storage, bypass, protection, and monitoring.", "Ride-through and clean power for critical industrial loads.", ("double-conversion", "line-interactive", "modular", "lithium-storage"), _INFRA_CONTEXTS, status="SPECIFICATION GAP", upstream=("cap:power-electronics", "cap:battery-cells-and-packs"), downstream=("node:10:industrial-utility", "node:12:industrial-controls"), related=("node:10:low-voltage-switchboard",)),
    _a("centrifugal_pump_skid", "Centrifugal pump skid", "heavy_equipment", "fluid_equipment", "A pump, driver, baseplate, piping, valves, instrumentation, and alignment package for continuous fluid service.", "Water, process, cooling, irrigation, and industrial circulation.", ("end-suction", "split-case", "multistage", "vertical-turbine"), _INFRA_CONTEXTS, upstream=("cap:motors", "cap:mechanical-seals"), downstream=("node:10:water-treatment", "node:10:process-plant"), related=("node:12:centrifugal-pump",)),
    _a("positive_displacement_pump", "Positive-displacement pump", "heavy_equipment", "fluid_equipment", "A pump that moves a measured volume per cycle through reciprocating or rotary displacement.", "Dosing, viscous fluids, high-pressure, and metering service.", ("gear", "screw", "diaphragm", "plunger"), _INFRA_CONTEXTS, upstream=("cap:mechanical-seals", "cap:fluid-control"), downstream=("node:10:process-plant", "node:10:water-treatment"), related=("node:12:positive-displacement-pump",)),
    _a("industrial_compressor", "Industrial compressor", "heavy_equipment", "fluid_equipment", "A compressor package with compression train, driver, cooling, separation, controls, and protection.", "Plant air, gas service, refrigeration, and process compression.", ("reciprocating", "screw", "centrifugal", "high-pressure"), _INFRA_CONTEXTS, status="SPECIFICATION GAP", upstream=("cap:motors", "cap:pressure-and-leak-testing"), downstream=("node:10:industrial-gas-utility", "node:10:process-plant"), related=("node:12:industrial-compressor",)),
    _a("industrial_chiller", "Industrial chiller", "heavy_equipment", "thermal_equipment", "A refrigeration package providing controlled chilled fluid through compressor, heat exchangers, controls, and pumps.", "Process cooling, HVAC, cold chain, and data or equipment thermal management.", ("air-cooled", "water-cooled", "absorption", "low-gwp-refrigerant"), _INFRA_CONTEXTS, status="SPECIFICATION GAP", upstream=("cap:compressors", "cap:heat-exchangers"), downstream=("node:10:process-plant", "node:10:cold-chain"), related=("node:10:cooling-tower",)),
    _a("industrial_boiler", "Industrial boiler", "heavy_equipment", "thermal_equipment", "A steam or hot-water generator with pressure boundary, burner or heater, feedwater, controls, and safety systems.", "Process heat, steam networks, and utility service.", ("gas-fired", "oil-fired", "biomass-fired", "electric"), _INFRA_CONTEXTS, status="QUALIFICATION GAP", upstream=("cap:pressure-boundary-fabrication", "cap:combustion-and-burners"), downstream=("node:10:steam-network", "node:10:process-plant"), related=("node:12:industrial-valves",)),
    _a("heat_exchanger_skid", "Heat exchanger skid", "heavy_equipment", "thermal_equipment", "A thermal-transfer package combining exchanger, piping, valves, instrumentation, supports, and pressure or leak testing.", "Heating, cooling, condensation, recovery, and process integration.", ("shell-and-tube", "plate-and-frame", "air-cooled", "spiral"), _INFRA_CONTEXTS, status="PARTIAL / SCALE-LIMITED", upstream=("cap:heat-exchangers", "cap:pressure-and-leak-testing"), downstream=("node:10:process-plant", "node:10:industrial-utility"), related=("node:12:heat-exchanger",)),
    _a("cooling_tower", "Cooling tower", "heavy_equipment", "thermal_equipment", "An evaporative or dry heat-rejection system with fan, fill, basin, water treatment, and controls.", "Rejecting heat from plants, HVAC, and utility systems.", ("induced-draft", "forced-draft", "natural-draft", "closed-circuit"), _INFRA_CONTEXTS, upstream=("cap:industrial-fans", "cap:water-treatment"), downstream=("node:10:process-plant", "node:10:industrial-utility"), related=("node:10:industrial-chiller",)),
    _a("water_treatment_package", "Water treatment package", "infrastructure_system", "water_infrastructure", "A modular treatment train combining pumps, filtration, membranes, dosing, disinfection, instrumentation, and residual handling.", "Potable, industrial process, and reuse water production.", ("filtration", "reverse-osmosis", "ultrafiltration", "zero-liquid-discharge"), _INFRA_CONTEXTS, status="PARTIAL / SCALE-LIMITED", upstream=("cap:filtration-and-membranes", "cap:chemical-dosing"), downstream=("node:10:industrial-utility", "node:10:wastewater-package"), related=("node:12:industrial-pumps",)),
    _a("wastewater_package", "Wastewater treatment package", "infrastructure_system", "water_infrastructure", "A treatment system for biological, chemical, physical, and sludge-handling stages with monitoring and controls.", "Municipal, industrial, and process-effluent treatment.", ("activated-sludge", "moving-bed-biofilm", "membrane-bioreactor", "anaerobic"), _INFRA_CONTEXTS, status="QUALIFICATION GAP", upstream=("cap:water-treatment", "cap:industrial-controls"), downstream=("node:10:water-reuse", "node:10:industrial-utility"), related=("node:10:water-treatment-package",)),
    _a("pressure_vessel", "Pressure vessel", "heavy_equipment", "process_equipment", "A fabricated pressure boundary with shells, heads, nozzles, supports, inspection, and relief interfaces.", "Storage, separation, reaction, and process containment.", ("carbon-steel", "stainless-steel", "lined", "composite"), _INFRA_CONTEXTS, status="QUALIFICATION GAP", upstream=("cap:pressure-boundary-fabrication", "cap:nondestructive-testing"), downstream=("node:10:process-plant", "node:12:industrial-valves"), related=("node:10:industrial-boiler",)),
    _a("mobile_crane", "Mobile crane", "heavy_equipment", "construction_equipment", "A transportable lifting machine with boom, counterweight, hydraulics, chassis, controls, and load safety.", "Construction, erection, maintenance, and recovery lifts.", ("truck-mounted", "rough-terrain", "crawler", "all-terrain"), _CONSTRUCTION_CONTEXTS, upstream=("cap:fluid-power", "cap:heavy-duty-drivetrain"), downstream=("node:10:construction-site", "node:10:heavy-lift"), related=("node:12:hydraulic-systems",)),
    _a("tower_crane", "Tower crane", "heavy_equipment", "construction_equipment", "A fixed or climbing crane with mast, jib, trolley, hoist, slew, foundation, and site control systems.", "High-rise and large-site construction lifting.", ("top-slewing", "self-erecting", "luffing-jib", "climbing"), _CONSTRUCTION_CONTEXTS, status="SPECIFICATION GAP", upstream=("cap:hoists-and-winch", "cap:structural-fabrication"), downstream=("node:10:construction-site", "node:10:heavy-lift"), related=("node:10:mobile-crane",)),
    _a("excavator", "Hydraulic excavator", "heavy_equipment", "construction_equipment", "A tracked or wheeled machine using boom, arm, bucket, hydraulics, engine or battery, and operator controls.", "Digging, loading, trenching, demolition, and site preparation.", ("tracked-diesel", "wheeled-diesel", "battery-electric", "hybrid"), _CONSTRUCTION_CONTEXTS, upstream=("cap:fluid-power", "cap:wear-resistant-materials"), downstream=("node:10:construction-site", "node:10:mine"), related=("node:10:wheel-loader",)),
    _a("wheel_loader", "Wheel loader", "heavy_equipment", "construction_equipment", "A wheeled loading machine integrating articulated frame, bucket, hydraulics, drivetrain, and safety controls.", "Loading, stockpile handling, quarry, and site logistics.", ("diesel", "hybrid", "battery-electric", "biofuel-compatible"), _CONSTRUCTION_CONTEXTS, upstream=("cap:fluid-power", "cap:heavy-duty-drivetrain"), downstream=("node:10:construction-site", "node:10:mine"), related=("node:10:excavator",)),
    _a("bulldozer", "Bulldozer", "heavy_equipment", "construction_equipment", "A tracked or wheeled machine with blade, ripper, undercarriage, powertrain, hydraulics, and grade-control interfaces.", "Earthmoving, grading, reclamation, and mine works.", ("crawler-diesel", "wheel-diesel", "hybrid", "battery-electric"), _CONSTRUCTION_CONTEXTS, upstream=("cap:undercarriage", "cap:fluid-power"), downstream=("node:10:construction-site", "node:10:mine"), related=("node:10:excavator",)),
    _a("concrete_batching_plant", "Concrete batching plant", "heavy_equipment", "construction_equipment", "A plant metering aggregate, cement, water, and admixtures into controlled concrete batches.", "Construction supply, precast, and infrastructure projects.", ("stationary", "mobile", "dry-batch", "wet-batch"), _CONSTRUCTION_CONTEXTS, upstream=("cap:weighing-and-dosing", "cap:industrial-controls"), downstream=("node:10:concrete-pump", "node:10:construction-site"), related=("node:11:packaging-machinery",)),
    _a("asphalt_paver", "Asphalt paver", "heavy_equipment", "construction_equipment", "A paving machine receiving, spreading, screeding, and compacting hot or warm asphalt mix.", "Road, airport, and industrial pavement construction.", ("tracked", "wheeled", "electric-assist", "high-precision-grade"), _CONSTRUCTION_CONTEXTS, status="SPECIFICATION GAP", upstream=("cap:thermal-management", "cap:hydraulic-systems"), downstream=("node:10:road-roller", "node:10:construction-site"), related=("node:10:road-roller",)),
    _a("road_roller", "Road roller", "heavy_equipment", "construction_equipment", "A compaction machine with drum, vibration or oscillation, propulsion, water or emulsion system, and operator controls.", "Soil, aggregate, and asphalt compaction.", ("single-drum", "tandem-drum", "pneumatic-tyre", "electric"), _CONSTRUCTION_CONTEXTS, upstream=("cap:vibration-and-balancing", "cap:heavy-duty-drivetrain"), downstream=("node:10:construction-site", "node:10:asphalt-paver"), related=("node:10:asphalt-paver",)),
    _a("air_handling_unit", "Air handling unit", "heavy_equipment", "thermal_equipment", "A conditioned-air package combining fans, coils, filters, dampers, controls, casing, and thermal or hygiene requirements.", "Factory, commercial, healthcare, data, and process-environment air handling.", ("fresh-air", "recirculating", "hygienic", "energy-recovery"), _INFRA_CONTEXTS, status="SPECIFICATION GAP", upstream=("cap:industrial-fans", "cap:heat-exchangers"), downstream=("node:10:industrial-utility", "node:10:industrial-chiller"), related=("node:10:cooling-tower",)),
    _a("industrial_fan", "Industrial fan", "heavy_equipment", "thermal_equipment", "A fan assembly with impeller, casing, driver, bearings, balancing, controls, and duty-specific pressure-flow envelope.", "Ventilation, combustion air, dust extraction, cooling, and process gas movement.", ("centrifugal", "axial", "mixed-flow", "explosion-protected"), _INFRA_CONTEXTS, status="PARTIAL / SCALE-LIMITED", upstream=("cap:motors", "cap:precision-balancing"), downstream=("node:10:air-handling-unit", "node:10:industrial-utility"), related=("node:12:induction-motor",)),
    _a("concrete_pump", "Concrete pump", "heavy_equipment", "construction_equipment", "A pumping machine with hopper, valves, cylinders, delivery line, chassis or trailer, and washout and safety systems.", "Placing concrete on building, civil, tunnel, and infrastructure sites.", ("truck-mounted", "trailer-mounted", "line-pump", "electric"), _CONSTRUCTION_CONTEXTS, upstream=("cap:fluid-power", "cap:wear-resistant-materials"), downstream=("node:10:construction-site", "node:10:concrete-batching-plant"), related=("node:10:centrifugal-pump-skid",)),
    _a("piling_rig", "Piling rig", "heavy_equipment", "construction_equipment", "A drilling or driven-pile machine integrating mast, rotary or impact head, hydraulics, winch, tooling, and ground-control systems.", "Foundations for buildings, bridges, ports, rail, and energy infrastructure.", ("rotary-drilling", "impact-hammer", "continuous-flight", "micro-piling"), _CONSTRUCTION_CONTEXTS, status="SPECIFICATION GAP", upstream=("cap:fluid-power", "cap:heavy-duty-drivetrain"), downstream=("node:10:construction-site", "node:10:heavy-lift"), related=("node:10:mobile-crane",)),
    _a("tunnel_boring_machine", "Tunnel boring machine", "heavy_equipment", "construction_equipment", "A tunnel excavation system combining cutterhead, main bearing, thrust, spoil handling, lining erection, guidance, and controls.", "Metro, rail, road, water, and utility tunnel construction.", ("earth-pressure-balance", "slurry", "hard-rock", "roadheader"), _CONSTRUCTION_CONTEXTS, status="CAPACITY GAP", upstream=("cap:precision-bearings", "cap:heavy-duty-drivetrain"), downstream=("node:10:construction-site", "node:10:rail-corridor"), related=("node:10:mobile-crane",)),
)


_GENERAL_CONTEXTS = (
    "mass-market",
    "small-batch",
    "export",
    "institutional",
    "rural-market",
    "premium",
    "hot-weather",
    "monsoon",
    "repairable-and-local",
)
_TEXTILE_CONTEXTS = (
    "cotton",
    "synthetic-fibre",
    "technical-textile",
    "home-textile",
    "apparel",
    "export",
    "hot-weather",
    "monsoon",
    "small-batch",
)
_PACKAGING_CONTEXTS = (
    "food-contact",
    "pharma-contact",
    "beverage",
    "e-commerce",
    "industrial",
    "export",
    "hot-weather",
    "monsoon",
    "recyclable-format",
)
_MACHINE_CONTEXTS = (
    "sme-workshop",
    "mass-production",
    "export",
    "food-contact",
    "pharma-contact",
    "textile-cluster",
    "hot-weather",
    "monsoon",
    "repairable-and-local",
)


_DOMAIN_11_ARCHETYPES = (
    _a("basic_garment", "Basic garment", "finished_product", "apparel", "A cut, sewn, finished, and inspected apparel product with fabric, trims, closures, and packaging.", "Everyday clothing and uniform supply.", ("woven-cotton", "knit-cotton", "synthetic-blend", "technical-fabric"), _TEXTILE_CONTEXTS, upstream=("cap:textile-fabric", "cap:cut-sew-assembly"), downstream=("node:11:retail-and-distribution", "node:11:textile-recycling"), related=("node:11:home-textile",)),
    _a("technical_textile", "Technical textile", "finished_product", "textile", "An engineered textile product with controlled fabric construction, coating, strength, or thermal and filtration behavior.", "Industrial, medical, protective, geotextile, and automotive applications.", ("nonwoven", "coated-fabric", "woven-high-strength", "knitted-technical"), _TEXTILE_CONTEXTS, status="SPECIFICATION GAP", upstream=("cap:textile-fabric", "mat:technical-fibres"), downstream=("node:11:industrial-users", "node:11:qualification"), related=("node:11:home-textile",)),
    _a("home_textile", "Home textile", "finished_product", "textile", "A household textile made through spinning or fabric conversion, cut or sewn into a finished home-use article.", "Bed, bath, furnishing, and household textile products.", ("woven-cotton", "knit", "nonwoven", "blended-fibre"), _TEXTILE_CONTEXTS, upstream=("cap:textile-fabric", "cap:dyeing-and-finishing"), downstream=("node:11:retail-and-distribution", "node:11:textile-recycling"), related=("node:11:basic-garment",)),
    _a("footwear", "Footwear", "finished_product", "consumer_goods", "A footwear assembly combining upper, sole, adhesives or stitching, forming, finishing, and fit or durability checks.", "Everyday, work, sports, and protective footwear.", ("stitched-upper", "injection-sole", "cemented", "moulded-rubber"), _GENERAL_CONTEXTS, upstream=("mat:leather-and-synthetic-upper", "cap:polymer-moulding"), downstream=("node:11:retail-and-distribution", "node:11:repair-and-recycling"), related=("node:11:basic-garment",)),
    _a("furniture", "Furniture", "finished_product", "consumer_goods", "A furniture product combining boards or solid material, hardware, joining, surface finish, and assembly.", "Household, office, hospitality, and institutional furnishing.", ("solid-wood", "engineered-board", "metal-frame", "modular-flat-pack"), _GENERAL_CONTEXTS, upstream=("mat:wood-and-board", "cap:joinery-and-surface-finish"), downstream=("node:11:retail-and-distribution", "node:11:repair-and-reuse"), related=("node:11:mattress",)),
    _a("mattress", "Mattress", "finished_product", "consumer_goods", "A layered comfort and support product combining foam, springs or other core, textiles, adhesive, cover, and inspection.", "Residential, hospitality, and healthcare sleeping systems.", ("spring", "foam", "hybrid", "latex"), _GENERAL_CONTEXTS, upstream=("mat:foams-and-elastomers", "cap:textile-fabric"), downstream=("node:11:retail-and-distribution", "node:11:repair-and-recycling"), related=("node:11:furniture",)),
    _a("cookware", "Cookware", "finished_product", "consumer_goods", "A formed or cast cooking vessel with body, handle, surface treatment, lid, and food-contact inspection.", "Household, hospitality, and institutional cooking.", ("stainless-steel", "aluminium", "cast-iron", "ceramic-coated"), _GENERAL_CONTEXTS, upstream=("mat:sheet-metal", "cap:coatings-and-enamels"), downstream=("node:11:retail-and-distribution", "node:11:repair-and-reuse"), related=("node:11:small-appliance",)),
    _a("small_appliance", "Small appliance", "finished_product", "consumer_electrical", "A compact electrical appliance combining enclosure, motor or heater, controls, wiring, insulation, and safety testing.", "Household, food-service, and personal-use electrical work.", ("motor-driven", "resistive-heating", "compressor-based", "smart-connected"), _GENERAL_CONTEXTS, status="SPECIFICATION GAP", upstream=("cap:small-motors", "cap:embedded-electronics"), downstream=("node:11:retail-and-distribution", "node:11:repair-and-recycling"), related=("node:11:ceiling-fan",)),
    _a("ceiling_fan", "Ceiling fan", "finished_product", "consumer_electrical", "An electric fan integrating motor, blades, housing, controls, balancing, insulation, and safety testing.", "Household, commercial, and institutional air movement.", ("induction-motor", "bldc-motor", "remote-controlled", "smart-connected"), _GENERAL_CONTEXTS, upstream=("cap:small-motors", "cap:industrial-controls"), downstream=("node:11:retail-and-distribution", "node:11:repair-and-recycling"), related=("node:11:small-appliance",)),
    _a("led_luminaire", "LED luminaire", "finished_product", "consumer_electrical", "A light source and optical, thermal, driver, enclosure, and wiring assembly with electrical and photometric tests.", "Indoor, outdoor, street, industrial, and commercial lighting.", ("mains-led", "solar-led", "smart-led", "high-bay-led"), _GENERAL_CONTEXTS, status="SPECIFICATION GAP", upstream=("cap:power-electronics", "cap:thermal-management"), downstream=("node:11:retail-and-distribution", "node:11:building-systems"), related=("node:12:industrial-controls",)),
    _a("household_plasticware", "Household plasticware", "finished_product", "consumer_goods", "A moulded polymer household article with tool, resin, forming, trimming, decoration, and dimensional inspection.", "Storage, kitchen, cleaning, and household organization.", ("injection-moulded", "blow-moulded", "rotomoulded", "recycled-polymer"), _GENERAL_CONTEXTS, upstream=("mat:engineering-polymers", "cap:injection-and-blow-moulding-tools"), downstream=("node:11:retail-and-distribution", "node:11:polymer-recycling"), related=("node:11:packaging-container",)),
    _a("paperboard_packaging", "Paperboard packaging", "finished_product", "packaging", "A converted board package with printing, die-cutting, creasing, folding, gluing, and pack-out controls.", "Cartons, sleeves, retail packaging, and transport protection.", ("folding-carton", "corrugated", "laminated-board", "recycled-board"), _PACKAGING_CONTEXTS, upstream=("mat:paper-and-board", "cap:printing-and-converting"), downstream=("node:11:packaging-lines", "node:11:recycling"), related=("node:11:flexible-packaging",)),
    _a("flexible_packaging", "Flexible packaging", "finished_product", "packaging", "A film, foil, laminate, or pouch package made through printing, coating, slitting, forming, sealing, and inspection.", "Food, pharma, consumer, and industrial flexible packs.", ("mono-material-film", "laminated-film", "foil-laminate", "recyclable-pouch"), _PACKAGING_CONTEXTS, status="SPECIFICATION GAP", upstream=("mat:films-and-laminates", "mat:inks-and-adhesives"), downstream=("node:11:packaging-lines", "node:11:recycling"), related=("node:11:paperboard-packaging",)),
    _a("corrugated_box", "Corrugated box", "finished_product", "packaging", "A fluted-board transport package made by corrugating, printing, slotting, folding, gluing, and testing.", "E-commerce, industrial, food, and general distribution packaging.", ("single-wall", "double-wall", "water-resistant", "heavy-duty"), _PACKAGING_CONTEXTS, upstream=("mat:paper-and-board", "cap:corrugation-and-converting"), downstream=("node:11:packaging-lines", "node:11:recycling"), related=("node:11:paperboard-packaging",)),
    _a("bottle_container", "Bottle or container", "finished_product", "packaging", "A formed glass, polymer, or metal container with neck, closure, label, barrier, and dimensional or leak checks.", "Beverage, food, pharma, cosmetic, and industrial containment.", ("pet-blow-moulded", "hdpe-blow-moulded", "glass-formed", "metal-drawn"), _PACKAGING_CONTEXTS, status="SPECIFICATION GAP", upstream=("mat:packaging-polymers", "cap:blow-moulding-tools"), downstream=("node:11:packaging-lines", "node:11:recycling"), related=("node:11:flexible-packaging",)),
    _a("packaging_machine", "Packaging machine", "machine", "packaging_machinery", "A machine or line that forms, fills, seals, labels, codes, packs, or palletizes products with synchronized motion and inspection.", "Primary, secondary, and end-of-line packaging operations.", ("form-fill-seal", "cartoning", "bottling-and-capping", "case-packing"), _MACHINE_CONTEXTS, status="SPECIFICATION GAP", upstream=("cap:industrial-controls", "cap:servo-motors"), downstream=("node:11:paperboard-packaging", "node:11:flexible-packaging"), related=("node:11:printing-press",)),
    _a("printing_press", "Printing press", "machine", "printing_machinery", "A roll or sheet printing system with ink delivery, registration, drying, substrate handling, and inspection.", "Packaging, labels, commercial print, and industrial decoration.", ("flexographic", "offset", "digital-inkjet", "gravure"), _MACHINE_CONTEXTS, status="SPECIFICATION GAP", upstream=("cap:industrial-controls", "cap:precision-rollers"), downstream=("node:11:flexible-packaging", "node:11:paperboard-packaging"), related=("node:11:packaging-machine",)),
    _a("injection_moulding_machine", "Injection moulding machine", "machine", "polymer_machinery", "A machine controlling polymer plasticization, injection, clamping, cooling, tooling, and part ejection.", "High-volume polymer component and consumer-product production.", ("hydraulic", "all-electric", "servo-hydraulic", "multi-material"), _MACHINE_CONTEXTS, status="SPECIFICATION GAP", upstream=("cap:injection-and-blow-moulding-tools", "cap:servo-motors"), downstream=("node:11:household-plasticware", "node:11:packaging-container"), related=("node:11:blow-moulding-machine",)),
    _a("blow_moulding_machine", "Blow moulding machine", "machine", "polymer_machinery", "A machine forming hollow polymer articles through parison or preform control, moulding, cooling, trimming, and inspection.", "Bottles, containers, tanks, and hollow technical parts.", ("extrusion-blow", "injection-stretch-blow", "accumulator-head", "continuous"), _MACHINE_CONTEXTS, status="SPECIFICATION GAP", upstream=("cap:blow-moulding-tools", "cap:industrial-controls"), downstream=("node:11:bottle-container", "node:11:household-plasticware"), related=("node:11:injection-moulding-machine",)),
    _a("textile_spinning_machine", "Textile spinning machine", "machine", "textile_machinery", "A fibre-to-yarn machine integrating opening, drafting, twisting, winding, suction, controls, and yarn quality measurement.", "Spinning natural, synthetic, blended, and recycled fibres.", ("ring-spinning", "open-end", "air-jet", "compact-spinning"), _TEXTILE_CONTEXTS, status="SPECIFICATION GAP", upstream=("mat:textile-fibres", "cap:precision-spindles"), downstream=("node:11:textile-weaving-machine", "node:11:textile-knitting-machine"), related=("node:11:textile-weaving-machine",)),
    _a("textile_weaving_machine", "Textile weaving machine", "machine", "textile_machinery", "A loom coordinating warp preparation, shedding, insertion, beat-up, take-up, tension, and fabric inspection.", "Woven apparel, home, technical, and industrial fabrics.", ("air-jet-loom", "rapier-loom", "water-jet-loom", "shuttle-loom"), _TEXTILE_CONTEXTS, status="SPECIFICATION GAP", upstream=("cap:textile-yarn", "cap:industrial-controls"), downstream=("node:11:technical-textile", "node:11:home-textile"), related=("node:11:textile-spinning-machine",)),
    _a("textile_knitting_machine", "Textile knitting machine", "machine", "textile_machinery", "A knitting machine forming loops through needle, yarn-feed, take-up, pattern, and tension control.", "Knitted apparel, hosiery, technical, and home textiles.", ("circular", "flat-bed", "warp-knit", "seamless"), _TEXTILE_CONTEXTS, status="SPECIFICATION GAP", upstream=("cap:textile-yarn", "cap:precision-needles"), downstream=("node:11:basic-garment", "node:11:technical-textile"), related=("node:11:textile-weaving-machine",)),
    _a("textile_dyeing_finishing_line", "Textile dyeing and finishing line", "machine", "textile_machinery", "A wet or dry textile process line combining preparation, dyeing or coating, washing, drying, finishing, and effluent control.", "Colouration, handle, shrinkage, coating, and performance finishing.", ("jet-dyeing", "continuous-pad", "digital-printing", "coating-and-lamination"), _TEXTILE_CONTEXTS, status="QUALIFICATION GAP", upstream=("cap:textile-fabric", "cap:water-and-effluent-treatment"), downstream=("node:11:basic-garment", "node:11:technical-textile"), related=("node:11:textile-weaving-machine",)),
    _a("food_processing_machine", "Food processing machine", "machine", "food_machinery", "A hygienic machine or line for preparation, thermal treatment, separation, filling, or cleaning with product-contact controls.", "Food, dairy, beverage, and ingredient processing.", ("cutting-and-preparation", "thermal-processing", "filling-and-dosing", "clean-in-place"), _MACHINE_CONTEXTS, status="QUALIFICATION GAP", upstream=("cap:stainless-fabrication", "cap:hygienic-design"), downstream=("node:11:packaging-machine", "node:10:cold-chain"), related=("node:11:packaging-machine",)),
    _a("paper_converting_machine", "Paper converting machine", "machine", "paper_machinery", "A machine for slitting, coating, corrugating, folding, die-cutting, gluing, or rewinding paper and board webs.", "Paper, board, label, tissue, and transport-packaging conversion.", ("slitter-rewinder", "corrugator", "folder-gluer", "die-cutter"), _MACHINE_CONTEXTS, status="SPECIFICATION GAP", upstream=("mat:paper-and-board", "cap:precision-rollers"), downstream=("node:11:paperboard-packaging", "node:11:corrugated-box"), related=("node:11:packaging-machine",)),
    _a("electrical_cable", "Electrical cable", "finished_product", "general_manufacturing", "An insulated conductor or cable assembly combining conductor, insulation, shielding or armour, terminations, and electrical testing.", "Power distribution, controls, buildings, vehicles, machines, and communications.", ("low-voltage", "medium-voltage", "control-cable", "flexible-cable"), _GENERAL_CONTEXTS, status="PARTIAL / SCALE-LIMITED", upstream=("mat:copper-conductor", "cap:polymer-insulation"), downstream=("node:10:low-voltage-switchboard", "node:12:industrial-controls"), related=("node:11:led-luminaire",)),
    _a("industrial_fasteners", "Industrial fasteners", "component", "general_manufacturing", "Bolts, screws, nuts, washers, rivets, or threaded inserts with controlled material, forming, heat treatment, coating, and inspection.", "Joining structures, machines, vehicles, buildings, and consumer products.", ("carbon-steel", "alloy-steel", "stainless-steel", "specialty-coated"), _GENERAL_CONTEXTS, upstream=("mat:alloy-steel", "proc:heat-treatment"), downstream=("node:11:furniture", "node:12:tooling-and-fixtures"), related=("node:12:closed-die-forging",)),
    _a("hand_tools", "Hand tools", "finished_product", "general_manufacturing", "A forged, machined, ground, or moulded manual tool with handle, working edge, heat treatment, coating, and safety checks.", "Workshop, construction, maintenance, agriculture, and household work.", ("forged-steel", "stainless-steel", "polymer-handled", "insulated-electrician"), _GENERAL_CONTEXTS, upstream=("mat:tool-steel", "cap:heat-treatment"), downstream=("node:11:retail-and-distribution", "node:12:maintenance-systems"), related=("node:12:cutting-tools",)),
    _a("paper_recycling_machine", "Paper recycling machine", "machine", "paper_machinery", "A line for pulping, screening, cleaning, de-inking, water management, and sheet or board formation from recovered fibre.", "Recovered-fibre preparation and recycled paper or board production.", ("pulping-and-screening", "de-inking", "stock-preparation", "sheet-forming"), _MACHINE_CONTEXTS, status="QUALIFICATION GAP", upstream=("mat:paper-and-board", "cap:water-and-effluent-treatment"), downstream=("node:11:paperboard-packaging", "node:11:corrugated-box"), related=("node:11:paper-converting-machine",)),
    _a("woodworking_machine", "Woodworking machine", "machine", "general_machinery", "A machine for sawing, routing, drilling, edging, sanding, or finishing wood and engineered boards with tooling and dust control.", "Furniture, cabinetry, building components, and general joinery production.", ("panel-saw", "cnc-router", "edge-bander", "sanding-line"), _MACHINE_CONTEXTS, status="PARTIAL / SCALE-LIMITED", upstream=("mat:wood-and-board", "cap:tooling-and-fixtures"), downstream=("node:11:furniture", "node:11:repair-and-reuse"), related=("node:12:cnc-machining-center",)),
)


_FOUNDATION_CONTEXTS = (
    "automotive",
    "energy-and-grid",
    "construction",
    "process-plant",
    "rail-and-marine",
    "machine-tools",
    "aerospace-and-defense",
    "hot-weather",
    "sme-workshop",
)
_METROLOGY_CONTEXTS = (
    "shop-floor",
    "incoming-inspection",
    "process-control",
    "final-acceptance",
    "calibration-lab",
    "supplier-qualification",
    "aerospace-and-defense",
    "hot-weather",
    "sme-workshop",
)
_PROCESS_CONTEXTS = (
    "general-industry",
    "automotive",
    "energy-and-grid",
    "construction",
    "process-plant",
    "rail-and-marine",
    "aerospace-and-defense",
    "hot-weather",
    "sme-workshop",
)


_DOMAIN_12_ARCHETYPES = (
    _a("centrifugal_pump", "Centrifugal pump", "component", "fluid_machinery", "A rotating impeller pump with casing, shaft, seal, bearing, driver, and hydraulic performance envelope.", "Moving water, chemicals, cooling fluid, fuel, and process streams.", ("end-suction", "split-case", "multistage", "vertical-turbine"), _FOUNDATION_CONTEXTS, upstream=("cap:motors", "cap:precision-machining"), downstream=("node:10:centrifugal-pump-skid", "node:12:industrial-utilities"), related=("node:12:positive-displacement-pump",)),
    _a("positive_displacement_pump", "Positive-displacement pump", "component", "fluid_machinery", "A rotary or reciprocating pump delivering controlled volume through gears, screws, pistons, diaphragms, or plungers.", "Dosing, metering, viscous, high-pressure, and hydraulic service.", ("gear", "screw", "diaphragm", "plunger"), _FOUNDATION_CONTEXTS, upstream=("cap:mechanical-seals", "cap:precision-machining"), downstream=("node:10:positive-displacement-pump", "node:12:industrial-utilities"), related=("node:12:centrifugal-pump",)),
    _a("industrial_valve", "Industrial valve", "component", "fluid_control", "A pressure-boundary component regulating, isolating, or preventing reverse flow through a fluid system.", "Process piping, water, energy, chemical, and utility isolation or control.", ("gate", "globe", "ball", "butterfly"), _FOUNDATION_CONTEXTS, upstream=("cap:castings-and-forgings", "cap:seals-and-gaskets"), downstream=("node:10:pressure-vessel", "node:10:water-treatment-package"), related=("node:12:control-valve",)),
    _a("control_valve", "Control valve", "component", "fluid_control", "A modulating valve with actuator, positioner, trim, sensing, and control-loop interface.", "Flow, pressure, temperature, and level control in process systems.", ("pneumatic", "electric", "hydraulic", "smart-positioner"), _FOUNDATION_CONTEXTS, status="SPECIFICATION GAP", upstream=("cap:industrial-controls", "cap:precision-machining"), downstream=("node:10:process-plant", "node:12:industrial-utilities"), related=("node:12:industrial-valve",)),
    _a("induction_motor", "Induction motor", "component", "electric_machines", "A rotating electric machine with stator, rotor, bearings, insulation, cooling, and electromagnetic performance envelope.", "Pumps, fans, compressors, conveyors, vehicles, and general industrial drives.", ("squirrel-cage", "wound-rotor", "high-efficiency", "explosion-protected"), _FOUNDATION_CONTEXTS, upstream=("mat:electrical-steel", "cap:windings-and-insulation"), downstream=("node:10:centrifugal-pump-skid", "node:12:industrial-drive"), related=("node:12:servo-motor",)),
    _a("servo_motor", "Servo motor", "component", "electric_machines", "A controlled motor with feedback, winding, rotor, bearings, thermal management, and motion-performance envelope.", "Robotics, CNC axes, packaging, textile, and precision automation.", ("permanent-magnet", "synchronous-reluctance", "brushless-dc", "rare-earth-free"), _FOUNDATION_CONTEXTS, status="SPECIFICATION GAP", upstream=("mat:lamination-steel", "cap:encoders"), downstream=("node:11:packaging-machine", "node:12:machine-tool"), related=("node:12:induction-motor",)),
    _a("motor_drive", "Motor drive", "component", "power_electronics", "A converter and control assembly regulating motor voltage, current, torque, speed, protection, and communications.", "Variable-speed pumping, motion control, traction, fans, compressors, and factory automation.", ("ac-inverter", "servo-drive", "dc-drive", "wide-bandgap"), _FOUNDATION_CONTEXTS, status="IMPORT-DEPENDENT", upstream=("cap:power-semiconductor", "cap:industrial-controls"), downstream=("node:12:servo-motor", "node:10:industrial-compressor"), related=("node:12:industrial-controls",)),
    _a("precision_bearing", "Precision bearing", "component", "precision_mechanics", "A rolling or sliding bearing with controlled geometry, material, heat treatment, surface finish, preload, and cleanliness.", "Spindles, gearboxes, motors, pumps, rail, aerospace, and robotic joints.", ("deep-groove", "angular-contact", "tapered-roller", "crossed-roller"), _FOUNDATION_CONTEXTS, status="SPECIFICATION GAP", upstream=("mat:bearing-steel", "proc:precision-grinding"), downstream=("node:12:gearbox", "node:12:machine-tool"), related=("node:12:heat-treatment",)),
    _a("industrial_gearbox", "Industrial gearbox", "component", "power_transmission", "A geared transmission with housing, gears, shafts, bearings, seals, lubrication, and defined torque, speed, and life.", "Conveyors, mixers, hoists, mills, pumps, and industrial drives.", ("helical", "bevel-helical", "worm", "parallel-shaft"), _FOUNDATION_CONTEXTS, upstream=("cap:precision-gears", "cap:precision-bearings"), downstream=("node:10:mobile-crane", "node:12:industrial-utilities"), related=("node:12:planetary-gearbox",)),
    _a("planetary_gearbox", "Planetary gearbox", "component", "power_transmission", "A compact coaxial transmission using sun, planet, ring, carrier, bearings, and controlled backlash or stiffness.", "Robotics, wind, traction, machine tools, and high-torque compact drives.", ("standard", "precision", "high-torque", "low-backlash"), _FOUNDATION_CONTEXTS, status="SPECIFICATION GAP", upstream=("cap:precision-gears", "cap:precision-bearings"), downstream=("node:09:robotic-mobility", "node:12:servo-motor"), related=("node:12:industrial-gearbox",)),
    _a("cnc_machining_center", "CNC machining center", "machine", "machine_tools", "A numerically controlled machine combining structure, spindle, axes, tool change, coolant, probing, controls, and acceptance metrology.", "Multi-axis milling, drilling, tapping, and production machining.", ("three-axis", "four-axis", "five-axis", "horizontal"), _FOUNDATION_CONTEXTS, status="SPECIFICATION GAP", upstream=("cap:machine-castings", "cap:cnc-controls"), downstream=("node:09:vehicle-components", "node:12:tooling-and-fixtures"), related=("node:12:turning-center",)),
    _a("turning_center", "CNC turning center", "machine", "machine_tools", "A numerically controlled lathe with spindle, chuck, turret, tooling, chips and coolant, controls, and dimensional acceptance.", "Turning, boring, threading, milling, and production of rotational parts.", ("two-axis", "live-tooling", "twin-spindle", "bar-fed"), _FOUNDATION_CONTEXTS, status="SPECIFICATION GAP", upstream=("cap:machine-castings", "cap:cnc-controls"), downstream=("node:12:industrial-gearbox", "node:12:precision-bearing"), related=("node:12:cnc-machining-center",)),
    _a("precision_grinding_machine", "Precision grinding machine", "machine", "machine_tools", "A grinding machine controlling wheel, workholding, dressing, coolant, thermal stability, and geometric measurement.", "Finishing bearings, gears, shafts, ballscrews, tools, and precision surfaces.", ("cylindrical", "surface", "internal", "gear-grinding"), _FOUNDATION_CONTEXTS, status="SPECIFICATION GAP", upstream=("cap:precision-spindles", "cap:industrial-metrology"), downstream=("node:12:precision-bearing", "node:12:precision-gears"), related=("node:12:metrology-and-calibration",)),
    _a("tooling_and_fixtures", "Tooling and fixtures", "capability", "production_enablers", "Design and manufacture of jigs, fixtures, dies, moulds, toolholders, gauges, and workholding interfaces.", "Holding, locating, forming, cutting, assembling, and repeating production geometry.", ("machining-fixtures", "forming-dies", "injection-moulds", "assembly-jigs"), _FOUNDATION_CONTEXTS, status="PARTIAL / SCALE-LIMITED", upstream=("mat:tool-steel", "cap:precision-machining"), downstream=("node:11:packaging-machine", "node:12:machine-tool"), related=("node:12:cutting-tools",)),
    _a("cutting_tools", "Cutting tools", "component", "tooling", "A cutting tool or insert with substrate, geometry, coating, edge preparation, holder, and life envelope.", "Turning, milling, drilling, tapping, gear cutting, and composite machining.", ("cemented-carbide", "high-speed-steel", "ceramic", "diamond-or-cbn"), _FOUNDATION_CONTEXTS, status="SPECIFICATION GAP", upstream=("mat:tool-steel", "cap:coatings-and-surface-engineering"), downstream=("node:12:cnc-machining-center", "node:12:turning-center"), related=("node:12:tooling-and-fixtures",)),
    _a("metrology_and_calibration", "Metrology and calibration", "capability", "quality_infrastructure", "Measurement, calibration, inspection, and uncertainty-control capability linking parts and processes to traceable references.", "Incoming inspection, process control, final acceptance, supplier qualification, and repair decisions.", ("dimensional", "geometric", "materials-and-hardness", "electrical-and-thermal"), _METROLOGY_CONTEXTS, status="QUALIFICATION GAP", upstream=("cap:reference-standards", "cap:environmental-control"), downstream=("node:12:machine-tool", "node:12:heat-treatment"), related=("cap:industrial-metrology",)),
    _a("heat_treatment", "Heat treatment", "process_capability", "special_processes", "Controlled heating, soaking, quenching, tempering, ageing, or case treatment that sets material structure and performance.", "Steels, aluminium, bearings, gears, tools, castings, forgings, and special alloys.", ("carburizing", "nitriding", "quench-and-temper", "vacuum-heat-treatment"), _PROCESS_CONTEXTS, status="QUALIFICATION GAP", upstream=("mat:alloy-steel", "cap:industrial-furnaces"), downstream=("node:12:precision-bearing", "node:12:precision-gears"), related=("node:12:metrology-and-calibration",)),
    _a("welding_and_joining", "Welding and joining", "process_capability", "special_processes", "Joining capability covering process selection, consumables, procedure control, preparation, inspection, and repair.", "Structures, pressure boundaries, frames, vessels, piping, and maintenance.", ("arc-welding", "resistance-welding", "brazing", "laser-welding"), _PROCESS_CONTEXTS, status="QUALIFICATION GAP", upstream=("mat:welding-consumables", "cap:weld-procedure-qualification"), downstream=("node:10:pressure-vessel", "node:12:castings-and-forgings"), related=("node:12:nondestructive-testing",)),
    _a("sand_casting", "Sand casting", "process_capability", "metal_forming", "A foundry route from pattern and mould preparation through melting, pouring, solidification, fettling, heat treatment, and inspection.", "Iron, steel, aluminium, and non-ferrous castings for equipment and structures.", ("green-sand", "resin-sand", "no-bake", "lost-foam"), _PROCESS_CONTEXTS, status="PARTIAL / SCALE-LIMITED", upstream=("mat:cast-iron", "cap:foundry-patterns"), downstream=("node:10:construction-equipment", "node:12:machine-castings"), related=("node:12:precision-casting",)),
    _a("precision_casting", "Precision casting", "process_capability", "metal_forming", "A close-tolerance casting route using expendable or ceramic tooling, controlled melt, shell, finishing, and inspection.", "Complex alloy parts where machining or forging alone is inefficient.", ("investment-casting", "ceramic-shell", "centrifugal-casting", "die-casting"), _PROCESS_CONTEXTS, status="SPECIFICATION GAP", upstream=("mat:investment-wax-and-ceramic", "cap:vacuum-melting"), downstream=("node:09:vehicle-components", "node:12:industrial-valves"), related=("node:12:sand-casting",)),
    _a("closed_die_forging", "Closed-die forging", "process_capability", "metal_forming", "A high-load forming route using dies, controlled billet, heating, forging, trimming, heat treatment, and inspection.", "Automotive, rail, energy, aerospace, and high-strength mechanical parts.", ("hot-forging", "warm-forging", "cold-forging", "precision-forging"), _PROCESS_CONTEXTS, status="SPECIFICATION GAP", upstream=("mat:alloy-steel", "cap:forging-dies"), downstream=("node:09:vehicle-components", "node:12:industrial-gearbox"), related=("node:12:heavy-forging",)),
    _a("heavy_forging", "Heavy forging", "process_capability", "metal_forming", "Large-section forging capability combining ingot quality, high-load deformation, heat treatment, machining, and non-destructive inspection.", "Large shafts, pressure-boundary parts, turbines, generators, and strategic equipment.", ("open-die", "ring-rolling", "press-forging", "upset-forging"), _PROCESS_CONTEXTS, status="CAPACITY GAP", upstream=("mat:vacuum-degassed-steel", "cap:heavy-forging-press"), downstream=("node:10:power-transformer", "node:12:industrial-gearbox"), related=("node:12:closed-die-forging",)),
    _a("industrial_gases", "Industrial gases", "utility_capability", "process_utilities", "Production, separation, storage, distribution, and quality control for gases used in inerting, cutting, heat treatment, welding, and process chemistry.", "Oxygen, nitrogen, argon, hydrogen, carbon dioxide, and specialty gas service.", ("cryogenic-separation", "pressure-swing-adsorption", "electrolytic-hydrogen", "packaged-cylinder"), _PROCESS_CONTEXTS, status="PARTIAL / SCALE-LIMITED", upstream=("cap:compressors", "cap:gas-purification"), downstream=("node:12:heat-treatment", "node:12:welding-and-joining"), related=("node:10:industrial-compressor",)),
    _a("industrial_controls", "Industrial controls", "capability", "automation_and_controls", "Control hardware and software integration covering PLC, motion, drives, instrumentation, networks, safety, and commissioning.", "Automation of machines, lines, utilities, process plants, and maintenance data.", ("plc-and-hmi", "motion-control", "scada", "safety-and-process-control"), _FOUNDATION_CONTEXTS, status="IMPORT-DEPENDENT", upstream=("cap:embedded-electronics", "cap:industrial-networks"), downstream=("node:10:industrial-utility", "node:12:machine-tool"), related=("node:12:motor-drive",)),
    _a("utility_systems", "Industrial utility systems", "infrastructure_system", "plant_infrastructure", "Plant-level electricity, compressed air, water, steam, cooling, vacuum, gas, drainage, and environmental support systems.", "Keeping factories and process equipment powered, cooled, supplied, and safe.", ("electrical-distribution", "compressed-air", "steam-and-condensate", "water-and-cooling"), _FOUNDATION_CONTEXTS, status="CAPACITY GAP", upstream=("cap:transformers-and-switchgear", "cap:industrial-pumps"), downstream=("node:12:maintenance-systems", "node:10:industrial-utility"), related=("node:12:industrial-gases",)),
    _a("maintenance_systems", "Maintenance systems", "service_capability", "industrial_operations", "Reliability, inspection, spares, lubrication, repair, calibration, shutdown, and condition-monitoring capability.", "Preserving equipment availability, safety, yield, and learning during operation and ramp.", ("preventive", "predictive", "condition-based", "overhaul-and-repair"), _FOUNDATION_CONTEXTS, status="PARTIAL / SCALE-LIMITED", upstream=("cap:industrial-metrology", "cap:maintenance-spares"), downstream=("node:12:utility-systems", "node:12:process-quality"), related=("node:12:industrial-controls",)),
    _a("industrial_compressor", "Industrial compressor", "component", "fluid_machinery", "A compressor train with compression elements, driver, cooling, separation, lubrication, controls, and pressure or leak performance envelope.", "Plant air, gas service, refrigeration, and process compression.", ("reciprocating", "screw", "centrifugal", "high-pressure"), _FOUNDATION_CONTEXTS, status="SPECIFICATION GAP", upstream=("cap:motors", "cap:pressure-and-leak-testing"), downstream=("node:10:industrial-compressor", "node:12:industrial-gases"), related=("node:12:centrifugal-pump",)),
    _a("heat_exchanger", "Industrial heat exchanger", "component", "thermal_equipment", "A heat-transfer component with fluid passages, materials, joining, supports, fouling allowance, and pressure or leak assurance.", "Heating, cooling, condensation, recovery, and process thermal integration.", ("shell-and-tube", "plate-and-frame", "air-cooled", "spiral"), _FOUNDATION_CONTEXTS, status="PARTIAL / SCALE-LIMITED", upstream=("cap:heat-exchangers", "cap:pressure-and-leak-testing"), downstream=("node:10:heat-exchanger-skid", "node:12:utility-systems"), related=("node:12:industrial-compressor",)),
    _a("industrial_transformer", "Industrial transformer", "component", "heavy_electrical", "A transformer assembly with magnetic core, windings, insulation, enclosure or tank, cooling, protection, and test interfaces.", "Factory, process plant, renewable, traction, and distribution power conversion.", ("oil-immersed", "dry-type", "isolation", "traction"), _FOUNDATION_CONTEXTS, status="SPECIFICATION GAP", upstream=("mat:electrical-steel", "cap:high-voltage-test"), downstream=("node:10:power-transformer", "node:12:utility-systems"), related=("node:12:industrial-controls",)),
    _a("welding_power_source", "Welding power source", "equipment", "joining_equipment", "A controlled power source and interface for arc or resistance joining with current, voltage, duty, sensing, and safety control.", "Manual, robotic, repair, structural, pressure-boundary, and production welding.", ("arc-inverter", "resistance", "laser", "multi-process"), _PROCESS_CONTEXTS, status="PARTIAL / SCALE-LIMITED", upstream=("cap:power-electronics", "cap:industrial-controls"), downstream=("node:12:welding-and-joining", "node:10:pressure-vessel"), related=("node:12:industrial-controls",)),
)


TYPED_DOMAIN_SPECS: tuple[DomainSpec, ...] = (
    DomainSpec(
        id="09_transport_mobility",
        number=9,
        name="Transport & Mobility",
        purpose="Automotive, road, rail, marine, special-purpose, and off-highway mobility products with their enabling systems.",
        archetypes=_DOMAIN_09_ARCHETYPES,
    ),
    DomainSpec(
        id="10_infrastructure_construction_heavy_equipment",
        number=10,
        name="Infrastructure, Construction & Heavy Industrial Equipment",
        purpose="Grid, utility, water, thermal, process, lifting, earthmoving, and construction equipment.",
        archetypes=_DOMAIN_10_ARCHETYPES,
    ),
    DomainSpec(
        id="11_consumer_textile_packaging_general_manufacturing",
        number=11,
        name="Consumer, Textile, Packaging & General Manufacturing",
        purpose="Consumer goods plus textile, packaging, printing, polymer, food, and general-purpose manufacturing machines.",
        archetypes=_DOMAIN_11_ARCHETYPES,
    ),
    DomainSpec(
        id="12_foundational_industrial_capabilities",
        number=12,
        name="Foundational Industrial Capabilities",
        purpose="Cross-sector backbone capabilities and enabling products from fluids and power transmission through machine tools, special processes, utilities, controls, and maintenance.",
        archetypes=_DOMAIN_12_ARCHETYPES,
    ),
)


# ---------------------------------------------------------------------------
# Shared atlas-generator contract
# ---------------------------------------------------------------------------
#
# ``domains_01_04.py`` is the sibling breadth packet used by the V1 atlas
# generator.  It intentionally exposes plain dictionaries (domain ``code``,
# ``key``, ``variant_group``, archetype ``profile`` and grouped primitive
# slugs).  Keep the typed read model above for direct users, and expose this
# compatibility view so all twelve presentation domains can be loaded by the
# same generator.  The generator, not this module, owns conversion to
# ``forge.india_v1.schema.AtlasRecord``.

_STATUS_TO_ATLAS = {
    "STRONG / AVAILABLE IN INDIA": "STRONG",
    "PARTIAL / SCALE-LIMITED": "SCALE_LIMITED",
    "SPECIFICATION GAP": "PARTIAL",
    "QUALIFICATION GAP": "PARTIAL",
    "CAPACITY GAP": "SCALE_LIMITED",
    "IMPORT-DEPENDENT": "IMPORT_DEPENDENT",
    "MISSING / NO EVIDENCED DOMESTIC CAPABILITY": "MISSING",
    "UNKNOWN": "UNKNOWN",
    "CONFLICTED": "CONFLICTED",
}


def _atlas_profile(domain_id: str, archetype: Archetype) -> str:
    """Select a dependency profile without multiplying arbitrary axes."""

    if domain_id == "09_transport_mobility":
        if "rail" in archetype.category:
            return "transport_rail"
        if "marine" in archetype.category:
            return "transport_marine"
        if "off_highway" in archetype.category or "material_handling" in archetype.category:
            return "transport_offhighway"
        return "transport_road"
    if domain_id == "10_infrastructure_construction_heavy_equipment":
        if archetype.category == "heavy_electrical" or archetype.category == "power_quality":
            return "infrastructure_electrical"
        if archetype.category == "fluid_equipment" or archetype.category == "water_infrastructure":
            return "infrastructure_fluid"
        if archetype.category == "thermal_equipment" or archetype.category == "process_equipment":
            return "infrastructure_thermal_process"
        return "infrastructure_construction"
    if domain_id == "11_consumer_textile_packaging_general_manufacturing":
        if "machinery" in archetype.category or archetype.kind == "machine":
            return "consumer_machinery"
        if archetype.category in {"textile", "apparel"} or "textile" in archetype.category:
            return "consumer_textile"
        if archetype.category == "packaging" or "packaging" in archetype.category or "paper" in archetype.category:
            return "consumer_packaging"
        return "consumer_general"
    if archetype.category in {"fluid_machinery", "fluid_control"}:
        return "foundation_fluid"
    if archetype.category in {"electric_machines", "power_electronics", "power_transmission", "precision_mechanics"}:
        return "foundation_motion"
    if archetype.category in {"machine_tools", "tooling", "production_enablers"}:
        return "foundation_machine_tools"
    if archetype.category in {"special_processes", "metal_forming"}:
        return "foundation_special_process"
    if archetype.category in {"process_utilities", "plant_infrastructure", "industrial_operations"}:
        return "foundation_utilities"
    return "foundation_controls"


def _profile(
    systems: Sequence[str],
    processes: Sequence[str],
    materials: Sequence[str],
    equipment: Sequence[str],
    capabilities: Sequence[str],
) -> dict[str, list[str]]:
    """Return a compact profile using the shared 01--04 primitive slugs."""

    return {
        "systems": list(systems),
        "processes": list(processes),
        "materials": list(materials),
        "equipment": list(equipment),
        "capabilities": list(capabilities),
    }


_CORE_SYSTEMS = (
    "industrial_infrastructure",
    "industrial_power",
    "industrial_water_utilities",
    "test_qualification_infrastructure",
    "logistics_supply_chain",
)
_CORE_PROCESSES = (
    "requirements_systems_engineering",
    "cnc_machining",
    "assembly_integration",
    "metrology_inspection",
    "environmental_testing",
)
_CORE_CAPABILITIES = (
    "systems_engineering",
    "process_control_yield",
    "industrial_metrology",
    "reliability_qualification",
    "supply_chain_qualification",
)


PROFILE_DEPENDENCIES: dict[str, dict[str, list[str]]] = {
    "transport_road": _profile(
        _CORE_SYSTEMS,
        (*_CORE_PROCESSES, "forming_stamping", "welding_joining"),
        ("steel", "aluminum_alloy", "copper_conductor", "polymer_elastomer", "battery_materials"),
        ("cnc_machine", "assembly_cell", "electrical_test_bench", "power_quality_system"),
        (*_CORE_CAPABILITIES, "power_conversion"),
    ),
    "transport_rail": _profile(
        _CORE_SYSTEMS,
        (*_CORE_PROCESSES, "forming_stamping", "welding_joining", "high_reliability_qualification"),
        ("steel", "aluminum_alloy", "copper_conductor", "polymer_elastomer", "lubricants"),
        ("cnc_machine", "welding_cell", "assembly_cell", "coordinate_measuring_machine"),
        (*_CORE_CAPABILITIES, "high_voltage_insulation"),
    ),
    "transport_marine": _profile(
        _CORE_SYSTEMS,
        (*_CORE_PROCESSES, "welding_joining", "coating_surface_treatment"),
        ("steel", "aluminum_alloy", "copper_conductor", "polymer_elastomer", "lubricants"),
        ("cnc_machine", "welding_cell", "assembly_cell", "non_destructive_testing"),
        (*_CORE_CAPABILITIES, "thermal_management"),
    ),
    "transport_offhighway": _profile(
        _CORE_SYSTEMS,
        (*_CORE_PROCESSES, "forming_stamping", "welding_joining", "heat_treatment"),
        ("steel", "aluminum_alloy", "copper_conductor", "polymer_elastomer", "lubricants"),
        ("cnc_machine", "welding_cell", "assembly_cell", "power_quality_system"),
        (*_CORE_CAPABILITIES, "facility_operations"),
    ),
    "infrastructure_electrical": _profile(
        _CORE_SYSTEMS,
        (*_CORE_PROCESSES, "forming_stamping", "electrical_test_burnin", "software_validation"),
        ("steel", "copper_conductor", "ceramic", "polymer_elastomer", "industrial_gases"),
        ("cnc_machine", "assembly_cell", "electrical_test_bench", "power_quality_system"),
        (*_CORE_CAPABILITIES, "power_conversion", "high_voltage_insulation"),
    ),
    "infrastructure_fluid": _profile(
        _CORE_SYSTEMS,
        (*_CORE_PROCESSES, "welding_joining", "coating_surface_treatment"),
        ("steel", "aluminum_alloy", "copper_conductor", "polymer_elastomer", "lubricants"),
        ("cnc_machine", "welding_cell", "assembly_cell", "non_destructive_testing"),
        (*_CORE_CAPABILITIES, "thermal_management"),
    ),
    "infrastructure_thermal_process": _profile(
        _CORE_SYSTEMS,
        (*_CORE_PROCESSES, "welding_joining", "heat_treatment", "coating_surface_treatment"),
        ("steel", "nickel_superalloy", "ceramic", "industrial_gases", "lubricants"),
        ("cnc_machine", "heat_treatment_furnace", "welding_cell", "non_destructive_testing"),
        (*_CORE_CAPABILITIES, "thermal_management"),
    ),
    "infrastructure_construction": _profile(
        _CORE_SYSTEMS,
        (*_CORE_PROCESSES, "casting", "forging", "welding_joining"),
        ("steel", "aluminum_alloy", "concrete", "polymer_elastomer", "lubricants"),
        ("casting_cell", "forging_press", "cnc_machine", "welding_cell"),
        (*_CORE_CAPABILITIES, "facility_operations"),
    ),
    "consumer_general": _profile(
        _CORE_SYSTEMS,
        (*_CORE_PROCESSES, "forming_stamping", "coating_surface_treatment"),
        ("steel", "aluminum_alloy", "copper_conductor", "polymer_elastomer", "lubricants"),
        ("cnc_machine", "assembly_cell", "coating_line", "electrical_test_bench"),
        (*_CORE_CAPABILITIES, "facility_operations"),
    ),
    "consumer_textile": _profile(
        _CORE_SYSTEMS,
        (*_CORE_PROCESSES, "coating_surface_treatment", "chemical_synthesis_refining"),
        ("polymer_elastomer", "industrial_gases", "high_purity_chemicals", "lubricants", "copper_conductor"),
        ("assembly_cell", "coating_line", "chemical_process_skid", "electrical_test_bench"),
        (*_CORE_CAPABILITIES, "facility_operations"),
    ),
    "consumer_packaging": _profile(
        _CORE_SYSTEMS,
        (*_CORE_PROCESSES, "forming_stamping", "coating_surface_treatment"),
        ("polymer_elastomer", "glass", "aluminum_alloy", "paper_and_board", "solder_interconnect"),
        ("assembly_cell", "coating_line", "electrical_test_bench", "industrial_compute"),
        (*_CORE_CAPABILITIES, "facility_operations"),
    ),
    "consumer_machinery": _profile(
        _CORE_SYSTEMS,
        (*_CORE_PROCESSES, "forming_stamping", "welding_joining", "software_validation"),
        ("steel", "aluminum_alloy", "copper_conductor", "polymer_elastomer", "lubricants"),
        ("cnc_machine", "assembly_cell", "electrical_test_bench", "industrial_compute"),
        (*_CORE_CAPABILITIES, "embedded_control_software", "power_conversion"),
    ),
    "foundation_fluid": _profile(
        _CORE_SYSTEMS,
        (*_CORE_PROCESSES, "casting", "forging", "welding_joining"),
        ("steel", "aluminum_alloy", "polymer_elastomer", "ceramic", "lubricants"),
        ("casting_cell", "forging_press", "cnc_machine", "coordinate_measuring_machine"),
        (*_CORE_CAPABILITIES, "thermal_management"),
    ),
    "foundation_motion": _profile(
        _CORE_SYSTEMS,
        (*_CORE_PROCESSES, "precision_grinding", "heat_treatment", "electrical_test_burnin"),
        ("steel", "copper_conductor", "rare_earth_magnet", "ceramic", "lubricants"),
        ("cnc_machine", "precision_grinder", "heat_treatment_furnace", "electrical_test_bench"),
        (*_CORE_CAPABILITIES, "power_conversion"),
    ),
    "foundation_machine_tools": _profile(
        _CORE_SYSTEMS,
        (*_CORE_PROCESSES, "precision_grinding", "heat_treatment", "coating_surface_treatment"),
        ("steel", "aluminum_alloy", "ceramic", "lubricants", "copper_conductor"),
        ("cnc_machine", "precision_grinder", "heat_treatment_furnace", "coordinate_measuring_machine"),
        (*_CORE_CAPABILITIES, "precision_manufacturing", "workforce_tacit_knowledge"),
    ),
    "foundation_special_process": _profile(
        _CORE_SYSTEMS,
        (*_CORE_PROCESSES, "casting", "forging", "heat_treatment", "welding_joining"),
        ("steel", "nickel_superalloy", "ceramic", "industrial_gases", "lubricants"),
        ("casting_cell", "forging_press", "heat_treatment_furnace", "welding_cell"),
        (*_CORE_CAPABILITIES, "materials_engineering", "workforce_tacit_knowledge"),
    ),
    "foundation_utilities": _profile(
        _CORE_SYSTEMS,
        (*_CORE_PROCESSES, "welding_joining", "electrical_test_burnin", "software_validation"),
        ("steel", "copper_conductor", "ceramic", "industrial_gases", "lubricants"),
        ("assembly_cell", "welding_cell", "electrical_test_bench", "power_quality_system"),
        (*_CORE_CAPABILITIES, "facility_operations", "thermal_management"),
    ),
    "foundation_controls": _profile(
        _CORE_SYSTEMS,
        (*_CORE_PROCESSES, "electrical_test_burnin", "software_validation", "high_reliability_qualification"),
        ("copper_conductor", "ceramic", "silicon", "compound_semiconductor", "solder_interconnect"),
        ("assembly_cell", "cleanroom_line", "electrical_test_bench", "industrial_compute"),
        (*_CORE_CAPABILITIES, "embedded_control_software", "power_conversion", "industrial_cybersecurity"),
    ),
}

# Additional shared primitive identities used by these four domains.  Existing
# slugs from domains 01--04 are intentionally not repeated here; the parent
# registry can merge this list with the sibling packet without collisions.
SHARED_PRIMITIVES: list[dict[str, Any]] = [
    {"slug": "paper_and_board", "group": "materials", "kind": "MATERIAL", "category": "paper and board", "name": "Paper and board substrates", "status": "AVAILABLE", "uses": ["cartons", "corrugated packaging", "labels and converting"]},
    {"slug": "vehicle_wiring", "group": "capabilities", "kind": "CAPABILITY", "category": "transport electrical capability", "name": "Vehicle wiring and harness integration", "status": "PARTIAL", "uses": ["vehicle power and signal distribution", "diagnostics", "serviceability"]},
    {"slug": "rail_bogies", "group": "capabilities", "kind": "CAPABILITY", "category": "rail mechanical capability", "name": "Rail bogie and wheelset integration", "status": "PARTIAL", "uses": ["rail running gear", "braking and suspension", "wheelset inspection"]},
    {"slug": "marine_hull", "group": "capabilities", "kind": "CAPABILITY", "category": "marine fabrication capability", "name": "Marine hull and corrosion-control integration", "status": "PARTIAL", "uses": ["hulls", "marine outfitting", "corrosion control"]},
    {"slug": "fluid_power", "group": "capabilities", "kind": "CAPABILITY", "category": "fluid power capability", "name": "Hydraulic and fluid-power integration", "status": "PARTIAL", "uses": ["construction equipment", "actuation", "mobile machinery"]},
    {"slug": "textile_fabric", "group": "materials", "kind": "MATERIAL", "category": "textile material", "name": "Textile yarns and fabrics", "status": "PARTIAL", "uses": ["apparel", "home textiles", "technical textiles"]},
    {"slug": "packaging_films", "group": "materials", "kind": "MATERIAL", "category": "packaging material", "name": "Packaging films and laminates", "status": "PARTIAL", "uses": ["pouches", "labels", "barrier packaging"]},
    {"slug": "industrial_pumps", "group": "capabilities", "kind": "CAPABILITY", "category": "fluid machinery capability", "name": "Industrial pump design and integration", "status": "PARTIAL", "uses": ["water systems", "process plants", "cooling and circulation"]},
    {"slug": "industrial_valves", "group": "capabilities", "kind": "CAPABILITY", "category": "fluid-control capability", "name": "Industrial valve design and qualification", "status": "PARTIAL", "uses": ["isolation", "modulation", "pressure-boundary control"]},
    {"slug": "electric_motors", "group": "capabilities", "kind": "CAPABILITY", "category": "electric-machine capability", "name": "Electric motor design and manufacture", "status": "PARTIAL", "uses": ["pumps", "drives", "vehicles and machines"]},
    {"slug": "precision_bearings", "group": "capabilities", "kind": "CAPABILITY", "category": "precision-mechanics capability", "name": "Precision bearing design and manufacture", "status": "PARTIAL", "uses": ["spindles", "gearboxes", "motors and actuators"]},
    {"slug": "industrial_gearboxes", "group": "capabilities", "kind": "CAPABILITY", "category": "power-transmission capability", "name": "Industrial gearbox design and manufacture", "status": "PARTIAL", "uses": ["conveyors", "hoists", "robots and vehicles"]},
    {"slug": "machine_tools", "group": "equipment", "kind": "EQUIPMENT", "category": "machine tools", "name": "Industrial machine tools", "status": "PARTIAL", "uses": ["machining", "turning", "grinding and finishing"]},
    {"slug": "tooling_fixtures", "group": "capabilities", "kind": "CAPABILITY", "category": "production tooling", "name": "Tooling, fixtures, and workholding", "status": "PARTIAL", "uses": ["repeatable production", "forming", "assembly and inspection"]},
    {"slug": "industrial_controls", "group": "capabilities", "kind": "CAPABILITY", "category": "industrial automation", "name": "Industrial controls and automation", "status": "IMPORT_DEPENDENT", "uses": ["PLC and motion", "SCADA", "machine and process control"]},
    {"slug": "maintenance_services", "group": "capabilities", "kind": "CAPABILITY", "category": "industrial operations", "name": "Maintenance, repair, and overhaul services", "status": "PARTIAL", "uses": ["uptime", "spares", "condition monitoring"]},
]


VARIANT_GROUPS: dict[str, list[dict[str, str]]] = {
    "transport_product": [
        {"code": "prototype", "label": "prototype configuration"},
        {"code": "urban", "label": "urban-duty configuration"},
        {"code": "regional", "label": "regional-duty configuration"},
        {"code": "heavy_duty", "label": "heavy-duty configuration"},
        {"code": "electric", "label": "electrified configuration"},
        {"code": "export", "label": "export configuration"},
        {"code": "high_reliability", "label": "high-reliability configuration"},
        {"code": "repairable", "label": "repairable and serviceable configuration"},
    ],
    "infrastructure_product": [
        {"code": "prototype", "label": "prototype configuration"},
        {"code": "modular", "label": "modular configuration"},
        {"code": "stationary", "label": "stationary configuration"},
        {"code": "mobile", "label": "mobile configuration"},
        {"code": "high_duty", "label": "high-duty configuration"},
        {"code": "grid_ready", "label": "grid-ready configuration"},
        {"code": "export", "label": "export configuration"},
        {"code": "repairable", "label": "repairable and serviceable configuration"},
    ],
    "consumer_product": [
        {"code": "prototype", "label": "prototype configuration"},
        {"code": "sme", "label": "SME-scale configuration"},
        {"code": "mass_production", "label": "mass-production configuration"},
        {"code": "export", "label": "export configuration"},
        {"code": "premium", "label": "premium configuration"},
        {"code": "recycled_input", "label": "recycled-input configuration"},
        {"code": "high_reliability", "label": "high-reliability configuration"},
        {"code": "repairable", "label": "repairable and serviceable configuration"},
    ],
    "foundation_capability": [
        {"code": "prototype", "label": "prototype route"},
        {"code": "standard", "label": "standard industrial route"},
        {"code": "precision", "label": "precision route"},
        {"code": "heavy_duty", "label": "heavy-duty route"},
        {"code": "high_efficiency", "label": "high-efficiency route"},
        {"code": "export", "label": "export route"},
        {"code": "qualification_grade", "label": "qualification-grade route"},
        {"code": "repairable", "label": "repairable and serviceable route"},
    ],
}

COMPONENT_GROUPS: dict[str, list[dict[str, str]]] = {
    "transport_product": [
        {"code": "structure", "label": "structure and running gear"},
        {"code": "powertrain", "label": "powertrain and energy system"},
        {"code": "controls", "label": "controls, safety, and interfaces"},
        {"code": "qualification", "label": "qualification and service package"},
    ],
    "infrastructure_product": [
        {"code": "structure", "label": "structure or pressure boundary"},
        {"code": "drive_or_fluid", "label": "drive, fluid, or thermal island"},
        {"code": "controls", "label": "controls, protection, and utilities"},
        {"code": "qualification", "label": "qualification and commissioning package"},
    ],
    "consumer_product": [
        {"code": "forming", "label": "forming, textile, or package body"},
        {"code": "drive_and_controls", "label": "drive, controls, and finishing"},
        {"code": "line_integration", "label": "line integration and pack-out"},
        {"code": "qualification", "label": "quality, compliance, and acceptance package"},
    ],
    "foundation_capability": [
        {"code": "body_or_process", "label": "body, material, or process route"},
        {"code": "motion", "label": "motion, drive, or workholding"},
        {"code": "metrology", "label": "metrology, controls, and process data"},
        {"code": "qualification", "label": "qualification, maintenance, and acceptance package"},
    ],
}


def _variant_group(domain_id: str) -> str:
    if domain_id == "09_transport_mobility":
        return "transport_product"
    if domain_id == "10_infrastructure_construction_heavy_equipment":
        return "infrastructure_product"
    if domain_id == "11_consumer_textile_packaging_general_manufacturing":
        return "consumer_product"
    return "foundation_capability"


def _atlas_kind(archetype: Archetype) -> str:
    if archetype.kind in {"machine", "heavy_equipment"}:
        return "EQUIPMENT"
    if archetype.kind == "process_capability":
        return "PROCESS"
    if archetype.kind in {"capability", "utility_capability", "service_capability"}:
        return "CAPABILITY"
    return "PRODUCT"


def _atlas_archetype(domain: DomainSpec, archetype: Archetype) -> dict[str, Any]:
    profile = _atlas_profile(domain.id, archetype)
    return {
        "slug": archetype.id,
        "name": archetype.name,
        "category": archetype.category,
        "profile": profile,
        "kind": _atlas_kind(archetype),
        "status": _STATUS_TO_ATLAS[archetype.status],
        "uses": [archetype.use],
        "explanation": archetype.explanation,
        "aliases": [archetype.name, archetype.id.replace("_", " ")],
        "gap": "Variant-specific grade, process qualification, yield, available allocation, and effective capacity remain UNKNOWN; imported content may exist in specialty materials, controls, sensors, and capital equipment. This is a curated navigation prior only, not a supply claim.",
        "upstream": list(archetype.upstream),
        "downstream": list(archetype.downstream),
        "related": list(archetype.related),
    }


DOMAINS_09_12: list[dict[str, Any]] = [
    {
        "code": f"{domain.number:02d}",
        "key": domain.id,
        "name": domain.name,
        "purpose": domain.purpose,
        "variant_group": _variant_group(domain.id),
        "archetypes": [_atlas_archetype(domain, archetype) for archetype in domain.archetypes],
    }
    for domain in TYPED_DOMAIN_SPECS
]

# Same symbol used by the sibling domain packet and by the shared generator.
DOMAIN_SPECS = DOMAINS_09_12


def generate_domain_records(domain: DomainSpec | str | int) -> tuple[dict[str, Any], ...]:
    """Generate one domain in stable archetype/axis order."""

    if isinstance(domain, DomainSpec):
        spec = domain
    else:
        key = str(domain).lower()
        aliases = {
            "9": "09_transport_mobility",
            "09": "09_transport_mobility",
            "10": "10_infrastructure_construction_heavy_equipment",
            "11": "11_consumer_textile_packaging_general_manufacturing",
            "12": "12_foundational_industrial_capabilities",
        }
        key = aliases.get(key, key)
        try:
            spec = next(item for item in TYPED_DOMAIN_SPECS if item.id == key)
        except StopIteration as exc:
            raise KeyError(f"unknown India V1 domain: {domain!r}") from exc

    records: list[dict[str, Any]] = []
    for archetype in spec.archetypes:
        for architecture in archetype.architectures:
            for context in archetype.contexts:
                records.append(_record(spec, archetype, architecture, context, len(records)))
    return tuple(records)


DOMAIN_RECORDS: dict[str, tuple[dict[str, Any], ...]] = {
    spec.id: generate_domain_records(spec) for spec in TYPED_DOMAIN_SPECS
}
ALL_RECORDS: tuple[dict[str, Any], ...] = tuple(
    record for spec in TYPED_DOMAIN_SPECS for record in DOMAIN_RECORDS[spec.id]
)
# Friendly aliases for consumers that do not distinguish the two read models.
RECORDS = ALL_RECORDS
DOMAINS = {spec.id: spec for spec in TYPED_DOMAIN_SPECS}
DOMAIN_COUNTS = {domain_id: len(records) for domain_id, records in DOMAIN_RECORDS.items()}


def _flatten_dependencies(record: Mapping[str, Any]) -> list[str]:
    dependencies = record.get("dependencies", {})
    if isinstance(dependencies, Mapping):
        return [
            str(item)
            for group in dependencies.values()
            for item in (group if isinstance(group, Sequence) and not isinstance(group, str) else [group])
        ]
    if isinstance(dependencies, Sequence) and not isinstance(dependencies, str):
        return [str(item) for item in dependencies]
    return []


def validate_records(records: Iterable[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    """Validate the breadth-packet contract without touching core code.

    The function returns a deterministic report rather than raising so callers
    can display the exact failure.  ``assert_valid`` is provided for tests and
    CI-style use.
    """

    rows = list(ALL_RECORDS if records is None else records)
    errors: list[str] = []
    ids: set[str] = set()
    by_domain: dict[str, int] = {}
    for index, row in enumerate(rows):
        row_id = str(row.get("id", ""))
        domain_id = str(row.get("domain_id", ""))
        if not row_id:
            errors.append(f"row {index}: missing id")
        elif row_id in ids:
            errors.append(f"duplicate id: {row_id}")
        ids.add(row_id)
        by_domain[domain_id] = by_domain.get(domain_id, 0) + 1
        for field in (
            "canonical_name",
            "aliases",
            "kind",
            "category",
            "explanation",
            "use",
            "india_status",
            "status_basis",
            "dependencies",
            "gaps",
            "import_notes",
            "making_ladder",
            "upstream",
            "downstream",
            "related",
        ):
            if field not in row or row[field] in (None, "", [], (), {}):
                errors.append(f"{row_id or index}: missing {field}")
        status = row.get("india_status")
        if status not in INDIA_STATUS_ENUM:
            errors.append(f"{row_id}: invalid india_status {status!r}")
        if row.get("epistemic_class") != EPISTEMIC_CLASS:
            errors.append(f"{row_id}: status epistemic class must remain ASSUMPTION")
        dependency_ids = _flatten_dependencies(row)
        if not 5 <= len(set(dependency_ids)) <= 30:
            errors.append(f"{row_id}: dependency count outside 5..30 ({len(set(dependency_ids))})")
        if not isinstance(row.get("making_ladder"), Sequence) or len(row["making_ladder"]) < 4:
            errors.append(f"{row_id}: making ladder too short")

    expected = {spec.id: len(spec.archetypes) * 4 * 9 for spec in TYPED_DOMAIN_SPECS}
    for domain_id, expected_count in expected.items():
        if by_domain.get(domain_id, 0) != expected_count:
            errors.append(
                f"{domain_id}: expected {expected_count} records, got {by_domain.get(domain_id, 0)}"
            )
    return {
        "ok": not errors,
        "record_count": len(rows),
        "domain_counts": dict(sorted(by_domain.items())),
        "expected_domain_counts": expected,
        "unique_ids": len(ids),
        "errors": errors,
    }


def assert_valid(records: Iterable[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    report = validate_records(records)
    if not report["ok"]:
        raise ValueError("India V1 domains 09-12 validation failed: " + "; ".join(report["errors"][:8]))
    return report


__all__ = [
    "ALL_RECORDS",
    "Archetype",
    "DOMAINS",
    "DOMAINS_09_12",
    "DOMAIN_COUNTS",
    "DOMAIN_RECORDS",
    "DOMAIN_SPECS",
    "DomainSpec",
    "INDIA_STATUS_ENUM",
    "COMPONENT_GROUPS",
    "PROFILE_DEPENDENCIES",
    "RECORDS",
    "SHARED_PRIMITIVES",
    "TYPED_DOMAIN_SPECS",
    "VARIANT_GROUPS",
    "assert_valid",
    "generate_domain_records",
    "validate_records",
]
