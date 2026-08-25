"""FORGE India V1 domain cards for domains 05--08.

This module is intentionally an ontology/data pack, not a capacity database.  It
provides deterministic, broad industrial records that a later registry loader can
materialise into canonical capabilities, processes, materials, and equipment.

The records use a small, explicit schema:

``id`` / ``canonical_id``
    Stable readable identity.  Shared primitives use the same vocabulary across
    domains (for example ``process:welding`` and ``material:stainless-steel``).
``kind`` / ``category`` / ``name`` / ``aliases``
    Human and machine-facing ontology fields.
``variant`` / ``archetype_id``
    A deterministic compatible-axis expansion of a curated archetype.  The axes
    are deliberately domain-specific; this is not an unbounded Cartesian product.
``dependencies`` / ``dependency_ids``
    Grouped upstream requirements and a deduplicated flat view.  Finished-product
    cards have 5--30 meaningful primitive dependencies.
``india_status`` / ``india_status_epistemic`` / ``india_status_basis``
    Broad status only.  No company, capacity, specification, or market claim is
    implied.  ``UNKNOWN`` is retained wherever public evidence would be needed to
    adjudicate qualified depth.
``gaps_import_notes`` / ``making_ladder``
    First-order closure and execution prompts, not asserted project plans.
``upstream_links`` / ``downstream_links`` / ``related_links``
    Stable graph links for registry auto-materialisation and cross-sector reuse.

Each domain intentionally expands to a predictable count by combining 30 or fewer
curated archetypes with three compatible variant axes (normally 4 x 3 x 3).  The
axes describe usable configuration choices for that archetype; they are not claims
that every combination is currently manufactured in India.
"""

from __future__ import annotations

from itertools import product
from typing import Any, Iterable, Mapping


SCHEMA_VERSION = "india_v1.domain_cards.v1"
DOMAIN_ORDER = ("05", "06", "07", "08")


def _dedupe(values: Iterable[str]) -> list[str]:
    """Stable de-duplication without relying on hash iteration order."""

    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        value = str(value)
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out


def _option(
    key: str,
    label: str,
    *,
    dependencies: Iterable[str] = (),
    note: str = "",
) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "dependencies": tuple(dependencies),
        "note": note,
    }


def _profile(
    axis_1: tuple[str, list[dict[str, Any]]],
    axis_2: tuple[str, list[dict[str, Any]]],
    axis_3: tuple[str, list[dict[str, Any]]],
    *,
    compatibility_note: str,
) -> dict[str, Any]:
    """Describe three compatible axes used by a family of archetypes."""

    return {
        "axes": (axis_1, axis_2, axis_3),
        "compatibility_note": compatibility_note,
    }


# ---------------------------------------------------------------------------
# Variant profiles
# ---------------------------------------------------------------------------

MACHINE_PROFILE = _profile(
    (
        "scale",
        [
            _option("compact", "compact/workshop scale", dependencies=("capability:machine-tool-build",)),
            _option("cell", "cell-integrated scale", dependencies=("capability:industrial-automation",)),
            _option("production", "production scale", dependencies=("capability:production-engineering",)),
            _option("high-throughput", "high-throughput scale", dependencies=("capability:throughput-ramp",)),
        ],
    ),
    (
        "configuration",
        [
            _option("fixed", "fixed-floor configuration", dependencies=("process:machine-alignment",)),
            _option("gantry", "gantry/modular configuration", dependencies=("capability:precision-assembly",)),
            _option("enclosed", "enclosed process configuration", dependencies=("capability:industrial-safety",)),
        ],
    ),
    (
        "automation",
        [
            _option("operator-assisted", "operator-assisted control", dependencies=("capability:skilled-operators",)),
            _option("programmable", "programmable control", dependencies=("capability:process-control",)),
            _option("closed-loop", "closed-loop monitored control", dependencies=("capability:metrology",)),
        ],
    ),
    compatibility_note="Scale, physical configuration, and automation axes are combined only within a machine-tool duty family.",
)

MOTOR_PROFILE = _profile(
    (
        "power_class",
        [
            _option("fractional", "fractional-power duty", dependencies=("material:copper",)),
            _option("industrial", "industrial-power duty", dependencies=("material:electrical-steel",)),
            _option("heavy", "heavy-duty power", dependencies=("process:thermal-management",)),
            _option("high-speed", "high-speed power", dependencies=("capability:rotordynamics",)),
        ],
    ),
    (
        "topology",
        [
            _option("induction", "induction topology", dependencies=("process:electrical-steel-stamping",)),
            _option("permanent-magnet", "permanent-magnet topology", dependencies=("material:rare-earth-magnet",)),
            _option("reluctance", "synchronous-reluctance topology", dependencies=("capability:power-electronics",)),
        ],
    ),
    (
        "integration",
        [
            _option("standalone", "standalone motor", dependencies=("capability:motor-assembly",)),
            _option("drive-integrated", "drive-integrated motor", dependencies=("equipment:servo-drive",)),
            _option("sensor-integrated", "sensor-integrated motor", dependencies=("capability:position-feedback",)),
        ],
    ),
    compatibility_note="Power class, electromagnetic topology, and integration axes are restricted to motor/drive architectures.",
)

ROBOT_PROFILE = _profile(
    (
        "payload",
        [
            _option("light", "light-payload duty", dependencies=("material:aluminum",)),
            _option("medium", "medium-payload duty", dependencies=("material:alloy-steel",)),
            _option("heavy", "heavy-payload duty", dependencies=("process:heat-treatment",)),
            _option("precision", "precision-payload duty", dependencies=("capability:precision-motion",)),
        ],
    ),
    (
        "reach",
        [
            _option("compact", "compact reach", dependencies=("equipment:precision-bearing",)),
            _option("standard", "standard reach", dependencies=("process:robot-calibration",)),
            _option("extended", "extended reach", dependencies=("capability:robotics-integration",)),
        ],
    ),
    (
        "control",
        [
            _option("teach-and-repeat", "teach-and-repeat control", dependencies=("capability:robot-programming",)),
            _option("vision-guided", "vision-guided control", dependencies=("equipment:machine-vision",)),
            _option("force-aware", "force/torque-aware control", dependencies=("capability:force-sensing",)),
        ],
    ),
    compatibility_note="Payload, reach, and control axes describe deployable robot configurations rather than arbitrary robot products.",
)

PROCESS_PLANT_PROFILE = _profile(
    (
        "scale",
        [
            _option("bench", "bench/laboratory scale", dependencies=("capability:process-development",)),
            _option("pilot", "pilot scale", dependencies=("capability:pilot-plant-operation",)),
            _option("industrial", "industrial scale", dependencies=("capability:production-engineering",)),
            _option("integrated", "integrated multi-unit scale", dependencies=("capability:utilities-integration",)),
        ],
    ),
    (
        "configuration",
        [
            _option("batch", "batch configuration", dependencies=("capability:batch-processing",)),
            _option("continuous", "continuous configuration", dependencies=("capability:continuous-processing",)),
            _option("skid", "modular skid configuration", dependencies=("capability:modular-process-skids",)),
        ],
    ),
    (
        "control",
        [
            _option("operator", "operator-supervised control", dependencies=("capability:process-operators",)),
            _option("distributed", "distributed control system", dependencies=("equipment:distributed-control-system",)),
            _option("advanced", "advanced process control", dependencies=("capability:process-analytics",)),
        ],
    ),
    compatibility_note="Scale, process configuration, and control axes are offered only for compatible process-plant routes.",
)

MATERIAL_PROFILE = _profile(
    (
        "form",
        [
            _option("sheet", "sheet/strip form", dependencies=("process:rolling",)),
            _option("bar", "bar/ billet form", dependencies=("process:forging",)),
            _option("powder", "powder form", dependencies=("process:powder-processing",)),
            _option("near-net", "near-net-shape form", dependencies=("process:casting",)),
        ],
    ),
    (
        "grade",
        [
            _option("general", "general industrial grade", dependencies=("capability:materials-characterisation",)),
            _option("corrosion-resistant", "corrosion-resistant grade", dependencies=("process:surface-treatment",)),
            _option("high-temperature", "high-temperature grade", dependencies=("process:heat-treatment",)),
        ],
    ),
    (
        "route",
        [
            _option("melt-route", "melt and cast route", dependencies=("equipment:melting-furnace",)),
            _option("powder-route", "powder consolidation route", dependencies=("equipment:controlled-atmosphere-furnace",)),
            _option("recycle-route", "recycled feedstock route", dependencies=("capability:materials-recycling",)),
        ],
    ),
    compatibility_note="Form, grade, and production-route axes are restricted to a material family with physically plausible processing choices.",
)

CHEMICAL_PROFILE = _profile(
    (
        "scale",
        [
            _option("lab", "laboratory scale", dependencies=("capability:chemical-lab",)),
            _option("pilot", "pilot scale", dependencies=("capability:pilot-plant-operation",)),
            _option("plant", "plant scale", dependencies=("capability:process-safety",)),
            _option("integrated", "integrated site scale", dependencies=("capability:utilities-integration",)),
        ],
    ),
    (
        "mode",
        [
            _option("batch", "batch synthesis mode", dependencies=("capability:batch-processing",)),
            _option("continuous", "continuous synthesis mode", dependencies=("capability:continuous-processing",)),
            _option("modular", "modular synthesis mode", dependencies=("capability:modular-process-skids",)),
        ],
    ),
    (
        "assurance",
        [
            _option("operator", "operator-supervised assurance", dependencies=("capability:process-operators",)),
            _option("instrumented", "instrumented process assurance", dependencies=("capability:process-analytics",)),
            _option("closed-loop", "closed-loop process assurance", dependencies=("capability:advanced-process-control",)),
        ],
    ),
    compatibility_note="Scale, synthesis mode, and process-assurance axes are compatible only within a chemical product family.",
)

IMAGING_PROFILE = _profile(
    (
        "setting",
        [
            _option("research", "research setting", dependencies=("capability:clinical-research",)),
            _option("clinic", "clinic setting", dependencies=("capability:medical-service",)),
            _option("hospital", "hospital setting", dependencies=("capability:clinical-engineering",)),
            _option("mobile", "mobile/field setting", dependencies=("capability:medical-logistics",)),
        ],
    ),
    (
        "configuration",
        [
            _option("compact", "compact configuration", dependencies=("capability:medical-device-design",)),
            _option("standard", "standard configuration", dependencies=("process:medical-device-assembly",)),
            _option("high-performance", "high-performance configuration", dependencies=("capability:medical-qualification",)),
        ],
    ),
    (
        "workflow",
        [
            _option("operator-led", "operator-led workflow", dependencies=("capability:clinical-operators",)),
            _option("protocol-guided", "protocol-guided workflow", dependencies=("capability:clinical-protocols",)),
            _option("integrated", "integrated data workflow", dependencies=("capability:medical-data-systems",)),
        ],
    ),
    compatibility_note="Care setting, instrument configuration, and workflow axes are constrained to plausible imaging/instrument deployments.",
)

LAB_PROFILE = _profile(
    (
        "throughput",
        [
            _option("low", "low-throughput laboratory", dependencies=("capability:lab-operations",)),
            _option("mid", "mid-throughput laboratory", dependencies=("capability:sample-preparation",)),
            _option("high", "high-throughput laboratory", dependencies=("capability:lab-automation",)),
            _option("core", "core-facility throughput", dependencies=("capability:instrument-service",)),
        ],
    ),
    (
        "workflow",
        [
            _option("research", "research workflow", dependencies=("capability:research-assurance",)),
            _option("diagnostic", "diagnostic workflow", dependencies=("capability:diagnostic-quality",)),
            _option("regulated", "regulated workflow", dependencies=("capability:quality-system",)),
        ],
    ),
    (
        "automation",
        [
            _option("manual", "manual sample handling", dependencies=("capability:lab-technicians",)),
            _option("assisted", "assisted sample handling", dependencies=("capability:sample-preparation",)),
            _option("robotic", "robotic sample handling", dependencies=("equipment:lab-liquid-handler",)),
        ],
    ),
    compatibility_note="Throughput, workflow, and sample-handling axes are compatible laboratory operating modes.",
)

BIOPROCESS_PROFILE = _profile(
    (
        "scale",
        [
            _option("benchtop", "benchtop scale", dependencies=("capability:bioprocess-development",)),
            _option("pilot", "pilot scale", dependencies=("capability:pilot-bioprocessing",)),
            _option("clinical", "clinical-production scale", dependencies=("capability:regulated-bioprocessing",)),
            _option("commercial", "commercial scale", dependencies=("capability:bioprocess-ramp",)),
        ],
    ),
    (
        "vessel",
        [
            _option("stainless", "stainless-steel vessel", dependencies=("material:stainless-steel",)),
            _option("single-use", "single-use vessel", dependencies=("material:single-use-polymer",)),
            _option("perfusion", "perfusion vessel train", dependencies=("capability:cell-retention",)),
        ],
    ),
    (
        "control",
        [
            _option("operator", "operator-supervised control", dependencies=("capability:bioprocess-operators",)),
            _option("recipe", "recipe-based control", dependencies=("capability:process-control",)),
            _option("advanced", "advanced model-based control", dependencies=("capability:process-analytics",)),
        ],
    ),
    compatibility_note="Scale, vessel architecture, and control axes represent qualified bioprocess routes, not arbitrary vessel combinations.",
)

STERILE_PROFILE = _profile(
    (
        "throughput",
        [
            _option("development", "development throughput", dependencies=("capability:aseptic-development",)),
            _option("clinical", "clinical-batch throughput", dependencies=("capability:aseptic-qualification",)),
            _option("commercial", "commercial throughput", dependencies=("capability:sterile-production",)),
            _option("high-volume", "high-volume throughput", dependencies=("capability:throughput-ramp",)),
        ],
    ),
    (
        "format",
        [
            _option("vial", "vial format", dependencies=("process:sterile-filling",)),
            _option("syringe", "syringe format", dependencies=("process:container-closure",)),
            _option("cartridge", "cartridge format", dependencies=("capability:drug-device-assembly",)),
        ],
    ),
    (
        "automation",
        [
            _option("operator-assisted", "operator-assisted filling", dependencies=("capability:aseptic-operators",)),
            _option("isolator", "isolator-based filling", dependencies=("equipment:isolator",)),
            _option("closed-line", "closed-line filling", dependencies=("capability:aseptic-process-control",)),
        ],
    ),
    compatibility_note="Throughput, container format, and aseptic automation axes are constrained to sterile manufacturing routes.",
)

FOOD_PROFILE = _profile(
    (
        "throughput",
        [
            _option("farm", "farm/workshop throughput", dependencies=("capability:food-operator",)),
            _option("small-plant", "small-plant throughput", dependencies=("capability:food-quality",)),
            _option("industrial", "industrial throughput", dependencies=("capability:food-process-engineering",)),
            _option("high-throughput", "high-throughput line", dependencies=("capability:line-balancing",)),
        ],
    ),
    (
        "product_form",
        [
            _option("solid", "solid product form", dependencies=("process:food-size-reduction",)),
            _option("liquid", "liquid product form", dependencies=("process:food-pumping",)),
            _option("powder", "powder product form", dependencies=("process:food-drying",)),
        ],
    ),
    (
        "automation",
        [
            _option("operator-assisted", "operator-assisted line", dependencies=("capability:food-operators",)),
            _option("programmable", "programmable line", dependencies=("capability:food-process-control",)),
            _option("closed-loop", "closed-loop hygienic line", dependencies=("capability:food-sensor-control",)),
        ],
    ),
    compatibility_note="Throughput, product form, and hygienic automation axes are kept within plausible food-processing duties.",
)

AGRICULTURE_PROFILE = _profile(
    (
        "scale",
        [
            _option("smallholder", "smallholder scale", dependencies=("capability:agri-service",)),
            _option("cooperative", "cooperative scale", dependencies=("capability:agri-logistics",)),
            _option("commercial", "commercial farm scale", dependencies=("capability:agri-operations",)),
            _option("regional", "regional production scale", dependencies=("capability:agri-supply-chain",)),
        ],
    ),
    (
        "configuration",
        [
            _option("stationary", "stationary installation", dependencies=("capability:utility-connection",)),
            _option("mobile", "mobile field configuration", dependencies=("capability:field-maintenance",)),
            _option("protected", "protected-environment configuration", dependencies=("capability:controlled-environment-agriculture",)),
        ],
    ),
    (
        "control",
        [
            _option("manual", "manual operation", dependencies=("capability:field-operators",)),
            _option("assisted", "operator-assisted control", dependencies=("capability:agri-instrumentation",)),
            _option("precision", "precision/closed-loop control", dependencies=("capability:agri-data-systems",)),
        ],
    ),
    compatibility_note="Farm scale, deployment configuration, and control axes are limited to plausible agricultural systems.",
)

BIO_FOOD_PROFILE = _profile(
    (
        "scale",
        [
            _option("pilot", "pilot biological-production scale", dependencies=("capability:bio-process-development",)),
            _option("community", "community production scale", dependencies=("capability:bio-production-operators",)),
            _option("commercial", "commercial production scale", dependencies=("capability:bio-production-quality",)),
            _option("integrated", "integrated production scale", dependencies=("capability:bio-resource-cycling",)),
        ],
    ),
    (
        "substrate",
        [
            _option("crop-residue", "crop-residue substrate", dependencies=("material:biomass-feedstock",)),
            _option("food-grade", "food-grade substrate", dependencies=("capability:food-hygiene",)),
            _option("waste-derived", "waste-derived substrate", dependencies=("capability:waste-preprocessing",)),
        ],
    ),
    (
        "control",
        [
            _option("manual", "manual batch control", dependencies=("capability:bio-production-operators",)),
            _option("instrumented", "instrumented batch control", dependencies=("capability:bio-monitoring",)),
            _option("closed-loop", "closed-loop biological control", dependencies=("capability:bioprocess-control",)),
        ],
    ),
    compatibility_note="Scale, substrate, and biological-control axes are constrained to plausible biological production systems.",
)


PROFILES = {
    "machine": MACHINE_PROFILE,
    "motor": MOTOR_PROFILE,
    "robot": ROBOT_PROFILE,
    "process": PROCESS_PLANT_PROFILE,
    "material": MATERIAL_PROFILE,
    "chemical": CHEMICAL_PROFILE,
    "imaging": IMAGING_PROFILE,
    "lab": LAB_PROFILE,
    "bioprocess": BIOPROCESS_PROFILE,
    "sterile": STERILE_PROFILE,
    "food": FOOD_PROFILE,
    "agriculture": AGRICULTURE_PROFILE,
    "bio_food": BIO_FOOD_PROFILE,
}


# ---------------------------------------------------------------------------
# Curated archetype tables
# ---------------------------------------------------------------------------

def _archetype(
    archetype_id: str,
    name: str,
    aliases: tuple[str, ...],
    *,
    kind: str,
    category: str,
    profile: str,
    dependencies: Mapping[str, tuple[str, ...]],
    explanation: str,
    use_template: str,
    status: str,
    status_epistemic: str,
    status_basis: str,
    gaps: tuple[str, ...],
    focus: tuple[str, ...],
    downstream: tuple[str, ...],
    related: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "id": archetype_id,
        "name": name,
        "aliases": aliases,
        "kind": kind,
        "category": category,
        "profile": profile,
        "dependencies": dependencies,
        "explanation": explanation,
        "use_template": use_template,
        "status": status,
        "status_epistemic": status_epistemic,
        "status_basis": status_basis,
        "gaps": gaps,
        "focus": focus,
        "downstream": downstream,
        "related": related,
    }


MACHINE_ARCHETYPES = (
    _archetype(
        "3-axis-cnc-vmc", "3-axis CNC vertical machining center", ("VMC", "3-axis machining center"),
        kind="equipment", category="machine tools", profile="machine",
        dependencies={
            "design": ("capability:machine-tool-design", "capability:precision-machining"),
            "process": ("process:cnc-machining", "process:precision-grinding", "process:machine-alignment"),
            "material": ("material:cast-iron", "material:tool-steel", "material:lubricant"),
            "equipment": ("equipment:cnc-machining-center", "equipment:metrology-cmm"),
            "quality": ("capability:machine-qualification", "capability:metrology"),
        },
        explanation="A programmable subtractive machine that removes material while maintaining tool-path and geometric control.",
        use_template="Use {name} to produce repeatable prismatic parts, fixtures, and machine components.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Broad ontology status only; qualified envelope, yield, and scalable domestic depth are not adjudicated here.",
        gaps=("qualified geometric accuracy and thermal stability", "controller, spindle, guideway, and metrology depth", "supplier qualification and service network"),
        focus=("capability:precision-machining", "process:cnc-machining"),
        downstream=("capability:machine-tools", "capability:industrial-automation"),
        related=("5-axis-cnc-machining-center", "cnc-turning-center", "metrology-cmm"),
    ),
    _archetype(
        "5-axis-cnc-machining-center", "5-axis CNC machining center", ("5-axis CNC", "five-axis machining center"),
        kind="equipment", category="machine tools", profile="machine",
        dependencies={
            "design": ("capability:machine-tool-design", "capability:precision-motion", "capability:kinematic-calibration"),
            "process": ("process:cnc-machining", "process:precision-grinding", "process:machine-alignment", "process:thermal-stabilisation"),
            "material": ("material:cast-iron", "material:alloy-steel", "material:tool-steel"),
            "equipment": ("equipment:5-axis-cnc-machining-center", "equipment:precision-bearing", "equipment:metrology-cmm"),
            "quality": ("capability:metrology", "capability:machine-qualification", "capability:process-control"),
        },
        explanation="A multi-axis machine that coordinates tool orientation and part motion for complex geometry.",
        use_template="Use {name} where multi-face access, contouring, and setup reduction materially affect buildability.",
        status="INDIA_EMERGING_OR_LIMITED", status_epistemic="MODELLED",
        status_basis="Conservative modelled maturity label for a strategically deep machine-tool class; no capacity is asserted.",
        gaps=("multi-axis kinematic calibration and thermal error compensation", "high-end controls, rotary axes, and precision bearings", "customer qualification at sustained production duty"),
        focus=("capability:precision-machining", "capability:metrology"),
        downstream=("capability:aerospace-machining", "capability:robotics", "capability:machine-tools"),
        related=("3-axis-cnc-vmc", "cnc-grinding-machine", "machine-vision-system"),
    ),
    _archetype(
        "cnc-turning-center", "CNC turning center", ("CNC lathe", "turning center"),
        kind="equipment", category="machine tools", profile="machine",
        dependencies={
            "design": ("capability:machine-tool-design", "capability:precision-motion"),
            "process": ("process:cnc-turning", "process:precision-grinding", "process:machine-alignment"),
            "material": ("material:alloy-steel", "material:cast-iron", "material:cutting-tool-carbide"),
            "equipment": ("equipment:cnc-machining-center", "equipment:servo-drive", "equipment:metrology-cmm"),
            "quality": ("capability:metrology", "capability:machine-qualification"),
        },
        explanation="A numerically controlled lathe platform for rotational parts, turning, boring, threading, and live tooling.",
        use_template="Use {name} to manufacture shafts, hubs, housings, threaded parts, and rotational assemblies.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Broad presence is plausible, but local specification coverage and qualified output remain unknown.",
        gaps=("spindle and chuck repeatability", "cutting-tool life and coolant control", "inspection and acceptance-test depth"),
        focus=("capability:precision-machining", "process:cnc-turning"),
        downstream=("capability:rotating-equipment", "capability:machine-tools"),
        related=("3-axis-cnc-vmc", "swiss-turning-machine", "cnc-grinding-machine"),
    ),
    _archetype(
        "swiss-turning-machine", "CNC Swiss-type turning machine", ("Swiss lathe", "sliding-headstock lathe"),
        kind="equipment", category="machine tools", profile="machine",
        dependencies={
            "design": ("capability:machine-tool-design", "capability:precision-motion"),
            "process": ("process:cnc-turning", "process:bar-feeding", "process:precision-grinding"),
            "material": ("material:alloy-steel", "material:cutting-tool-carbide", "material:stainless-steel"),
            "equipment": ("equipment:cnc-machining-center", "equipment:bar-feeder", "equipment:metrology-cmm"),
            "quality": ("capability:micro-machining", "capability:metrology"),
        },
        explanation="A sliding-headstock platform that supports small, slender, and multi-operation precision parts.",
        use_template="Use {name} for high-repeatability small shafts, connectors, medical parts, and precision fittings.",
        status="INDIA_IMPORT_DEPENDENT_OR_QUALIFICATION_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Import exposure and qualified domestic depth need direct supplier and process evidence.",
        gaps=("small-part tooling and guide-bushing know-how", "bar-feed reliability and chip control", "verified high-volume yield"),
        focus=("capability:micro-machining", "process:cnc-turning"),
        downstream=("capability:medical-components", "capability:precision-instruments"),
        related=("cnc-turning-center", "5-axis-cnc-machining-center", "medical-device-assembly"),
    ),
    _archetype(
        "cnc-grinding-machine", "CNC precision grinding machine", ("CNC grinder", "precision grinder"),
        kind="equipment", category="machine tools", profile="machine",
        dependencies={
            "design": ("capability:machine-tool-design", "capability:precision-motion", "capability:thermal-control"),
            "process": ("process:precision-grinding", "process:wheel-dressing", "process:heat-treatment"),
            "material": ("material:tool-steel", "material:grinding-abrasive", "material:alloy-steel"),
            "equipment": ("equipment:precision-grinder", "equipment:metrology-cmm", "equipment:temperature-control"),
            "quality": ("capability:metrology", "capability:machine-qualification", "capability:surface-integrity"),
        },
        explanation="A controlled abrasive process platform for tight form, size, surface, and runout requirements.",
        use_template="Use {name} to finish bearings, guideways, shafts, gears, and precision machine-tool components.",
        status="INDIA_EMERGING_OR_LIMITED", status_epistemic="MODELLED",
        status_basis="Modelled as a depth-sensitive foundational capability; no domestic output or supplier is claimed.",
        gaps=("grinding-wheel, dressing, and thermal-error expertise", "abrasive and spindle supply", "closed-loop metrology and process qualification"),
        focus=("process:precision-grinding", "capability:metrology"),
        downstream=("capability:precision-motion", "capability:precision-bearings", "capability:machine-tools"),
        related=("gear-grinding-machine", "5-axis-cnc-machining-center", "metrology-cmm"),
    ),
    _archetype(
        "gear-hobbing-machine", "CNC gear hobbing machine", ("gear hobber", "hobbing machine"),
        kind="equipment", category="machine tools", profile="machine",
        dependencies={
            "design": ("capability:gear-design", "capability:precision-motion"),
            "process": ("process:gear-hobbing", "process:heat-treatment", "process:precision-grinding"),
            "material": ("material:alloy-steel", "material:tool-steel", "material:cutting-tool-carbide"),
            "equipment": ("equipment:cnc-machining-center", "equipment:metrology-gear-checker", "equipment:heat-treatment-furnace"),
            "quality": ("capability:gear-metrology", "capability:machine-qualification"),
        },
        explanation="A synchronized cutting machine for generating involute gear teeth before finishing and inspection.",
        use_template="Use {name} to produce gear blanks and tooth forms for reducers, drives, vehicles, and industrial machinery.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Generic domestic presence is not treated as qualified capability across gear classes.",
        gaps=("gear geometry, tooling, and process capability", "heat-treatment distortion control", "gear inspection and noise qualification"),
        focus=("capability:gear-manufacturing", "process:gear-hobbing"),
        downstream=("capability:industrial-reducers", "capability:robotics", "capability:vehicle-drives"),
        related=("gear-grinding-machine", "cnc-grinding-machine", "industrial-robot"),
    ),
    _archetype(
        "gear-grinding-machine", "CNC gear grinding machine", ("gear grinder", "profile gear grinder"),
        kind="equipment", category="machine tools", profile="machine",
        dependencies={
            "design": ("capability:gear-design", "capability:precision-motion", "capability:metrology"),
            "process": ("process:gear-grinding", "process:heat-treatment", "process:wheel-dressing"),
            "material": ("material:alloy-steel", "material:grinding-abrasive", "material:tool-steel"),
            "equipment": ("equipment:precision-grinder", "equipment:metrology-gear-checker", "equipment:controlled-atmosphere-furnace"),
            "quality": ("capability:gear-metrology", "capability:machine-qualification", "capability:surface-integrity"),
        },
        explanation="A finishing platform that corrects gear flank geometry, transmission error, and surface quality.",
        use_template="Use {name} when reducer noise, efficiency, life, and repeatability require controlled tooth finishing.",
        status="INDIA_IMPORT_DEPENDENT_OR_QUALIFICATION_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Qualified domestic depth is a decision-sensitive unknown; no import share is asserted.",
        gaps=("grinding and dressing know-how", "gear inspection correlation", "qualified process recipes for high-load reducers"),
        focus=("process:gear-grinding", "capability:gear-metrology"),
        downstream=("capability:robot-reducers", "capability:industrial-reducers"),
        related=("gear-hobbing-machine", "cnc-grinding-machine", "precision-bearing"),
    ),
    _archetype(
        "wire-edm-machine", "wire electrical-discharge machining machine", ("wire EDM", "wire-cut EDM"),
        kind="equipment", category="machine tools", profile="machine",
        dependencies={
            "design": ("capability:machine-tool-design", "capability:precision-motion"),
            "process": ("process:wire-edm", "process:dielectric-filtration", "process:machine-alignment"),
            "material": ("material:tool-steel", "material:conductive-alloy", "material:edm-wire"),
            "equipment": ("equipment:cnc-machining-center", "equipment:dielectric-system", "equipment:metrology-cmm"),
            "quality": ("capability:metrology", "capability:electrical-process-control"),
        },
        explanation="A controlled spark-erosion machine for conductive materials, fine profiles, and hard-to-cut features.",
        use_template="Use {name} for dies, molds, fine slots, hard alloys, and low-force precision features.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Presence of machine users is not evidence of domestic machine design or qualified manufacture.",
        gaps=("pulse-control and dielectric management", "wire and consumables quality", "surface integrity and post-process inspection"),
        focus=("process:wire-edm", "capability:toolmaking"),
        downstream=("capability:tooling", "capability:precision-molds"),
        related=("3-axis-cnc-vmc", "laser-cutting-machine", "press-brake"),
    ),
    _archetype(
        "laser-cutting-machine", "industrial laser cutting machine", ("laser cutter", "fiber laser cutting system"),
        kind="equipment", category="fabrication equipment", profile="machine",
        dependencies={
            "design": ("capability:machine-tool-design", "capability:laser-process-engineering"),
            "process": ("process:laser-cutting", "process:sheet-forming", "process:surface-treatment"),
            "material": ("material:stainless-steel", "material:carbon-steel", "material:aluminum"),
            "equipment": ("equipment:laser-source", "equipment:cnc-machining-center", "equipment:fume-extraction"),
            "quality": ("capability:metrology", "capability:laser-safety", "capability:process-control"),
        },
        explanation="A programmable thermal cutting platform for sheet, plate, tube, and profile fabrication.",
        use_template="Use {name} to cut repeatable profiles and nests before forming, welding, and assembly.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Broad fabrication use does not establish source, optical, motion, or qualified production depth.",
        gaps=("laser source and optical train", "assist-gas and thermal-distortion control", "cut-edge qualification across materials"),
        focus=("process:laser-cutting", "capability:fabrication"),
        downstream=("capability:sheet-metal-fabrication", "capability:industrial-enclosures"),
        related=("press-brake", "wire-edm-machine", "robotic-welding-cell"),
    ),
    _archetype(
        "press-brake", "CNC press brake", ("bending press", "sheet-metal press brake"),
        kind="equipment", category="fabrication equipment", profile="machine",
        dependencies={
            "design": ("capability:machine-tool-design", "capability:forming-process-engineering"),
            "process": ("process:sheet-bending", "process:tooling", "process:machine-alignment"),
            "material": ("material:tool-steel", "material:stainless-steel", "material:aluminum"),
            "equipment": ("equipment:hydraulic-power-unit", "equipment:servo-drive", "equipment:metrology-cmm"),
            "quality": ("capability:forming-quality", "capability:process-control"),
        },
        explanation="A controlled forming machine that bends sheet and plate into repeatable structural geometry.",
        use_template="Use {name} to form cabinets, frames, ducts, brackets, and fabricated machine structures.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="General fabrication availability is not treated as a complete domestic capability claim.",
        gaps=("bending-tooling and springback models", "force/position control", "repeatability across grades and thicknesses"),
        focus=("process:sheet-bending", "capability:toolmaking"),
        downstream=("capability:industrial-enclosures", "capability:machine-structures"),
        related=("laser-cutting-machine", "3-axis-cnc-vmc", "robotic-welding-cell"),
    ),
    _archetype(
        "industrial-motor", "industrial electric motor", ("AC motor", "industrial motor"),
        kind="equipment", category="electromechanical equipment", profile="motor",
        dependencies={
            "design": ("capability:motor-design", "capability:electromagnetic-analysis"),
            "process": ("process:electrical-steel-stamping", "process:motor-winding", "process:impregnation", "process:rotor-balancing"),
            "material": ("material:electrical-steel", "material:copper", "material:insulation-system", "material:alloy-steel"),
            "equipment": ("equipment:stator-winding-machine", "equipment:dynamic-balancer", "equipment:test-bench"),
            "quality": ("capability:motor-testing", "capability:thermal-classification", "capability:production-quality"),
        },
        explanation="A rotating electromechanical converter that turns electrical input into controlled shaft power.",
        use_template="Use {name} to drive pumps, fans, compressors, conveyors, machine tools, and industrial auxiliaries.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Industrial use is broad, while technology envelope, yield, and supplier depth remain unspecified.",
        gaps=("electrical steel and winding-process control", "thermal life and vibration qualification", "drive/motor system integration"),
        focus=("capability:motor-manufacturing", "process:motor-winding"),
        downstream=("capability:industrial-pumps", "capability:industrial-automation", "capability:compressors"),
        related=("induction-motor", "servo-motor", "motor-drive"),
    ),
    _archetype(
        "induction-motor", "squirrel-cage induction motor", ("induction motor", "asynchronous motor"),
        kind="equipment", category="electromechanical equipment", profile="motor",
        dependencies={
            "design": ("capability:motor-design", "capability:electromagnetic-analysis"),
            "process": ("process:electrical-steel-stamping", "process:rotor-casting", "process:motor-winding", "process:rotor-balancing"),
            "material": ("material:electrical-steel", "material:copper", "material:aluminum", "material:insulation-system"),
            "equipment": ("equipment:stator-winding-machine", "equipment:rotor-casting-cell", "equipment:dynamic-balancer"),
            "quality": ("capability:motor-testing", "capability:thermal-classification"),
        },
        explanation="A robust AC motor topology using an induced rotor current rather than permanent magnets.",
        use_template="Use {name} for pumps, fans, compressors, conveyors, and rugged variable-speed industrial drives.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Common topology does not prove a particular efficiency class, scale, or qualified local route.",
        gaps=("lamination, rotor-casting, and balancing yield", "efficiency and thermal testing", "high-performance variable-speed control"),
        focus=("capability:motor-manufacturing", "capability:power-electronics"),
        downstream=("capability:industrial-pumps", "capability:industrial-heat-pumps"),
        related=("industrial-motor", "synchronous-reluctance-motor", "motor-drive"),
    ),
    _archetype(
        "bldc-pmsm-motor", "BLDC/PMSM motor", ("permanent-magnet motor", "brushless motor"),
        kind="equipment", category="electromechanical equipment", profile="motor",
        dependencies={
            "design": ("capability:motor-design", "capability:electromagnetic-analysis", "capability:power-electronics"),
            "process": ("process:electrical-steel-stamping", "process:motor-winding", "process:magnet-insertion", "process:rotor-balancing"),
            "material": ("material:electrical-steel", "material:copper", "material:rare-earth-magnet", "material:insulation-system"),
            "equipment": ("equipment:stator-winding-machine", "equipment:magnetisation-system", "equipment:dynamic-balancer"),
            "quality": ("capability:motor-testing", "capability:position-feedback", "capability:thermal-classification"),
        },
        explanation="A high power-density permanent-magnet motor family for efficient, responsive motion.",
        use_template="Use {name} where power density, controllability, and efficiency justify magnet and inverter dependencies.",
        status="INDIA_IMPORT_DEPENDENT_OR_QUALIFICATION_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Rare-earth material, magnet processing, and qualified drive integration are decision-sensitive unknowns.",
        gaps=("magnet material and coating route", "rotor retention and high-speed safety", "inverter, encoder, and thermal qualification"),
        focus=("capability:motor-manufacturing", "material:rare-earth-magnet"),
        downstream=("capability:robotics", "capability:servo-motion", "capability:electric-vehicles"),
        related=("induction-motor", "synchronous-reluctance-motor", "servo-motor"),
    ),
    _archetype(
        "servo-motor", "industrial servo motor", ("servo motor", "motion-control motor"),
        kind="equipment", category="motion control", profile="motor",
        dependencies={
            "design": ("capability:motor-design", "capability:motion-control", "capability:electromagnetic-analysis"),
            "process": ("process:motor-winding", "process:rotor-balancing", "process:encoder-alignment", "process:thermal-stabilisation"),
            "material": ("material:electrical-steel", "material:copper", "material:rare-earth-magnet", "material:insulation-system"),
            "equipment": ("equipment:servo-drive", "equipment:dynamic-balancer", "equipment:test-bench", "equipment:encoder-tester"),
            "quality": ("capability:motion-qualification", "capability:metrology", "capability:position-feedback"),
        },
        explanation="A feedback-controlled motor designed for commanded position, speed, and torque response.",
        use_template="Use {name} in CNC axes, robots, packaging machines, textile machinery, and precision automation.",
        status="INDIA_EMERGING_OR_LIMITED", status_epistemic="MODELLED",
        status_basis="Modelled as an industrial depth-sensitive class; no domestic producer or capacity is asserted.",
        gaps=("encoder, drive, and tuning ecosystem", "thermal and dynamic response qualification", "repeatable low-volume-to-series ramp"),
        focus=("capability:precision-motion", "capability:power-electronics"),
        downstream=("capability:machine-tools", "capability:industrial-robotics", "capability:packaging-machinery"),
        related=("bldc-pmsm-motor", "motor-drive", "plc-controller"),
    ),
    _archetype(
        "motor-drive", "variable-frequency motor drive", ("VFD", "inverter drive"),
        kind="equipment", category="power electronics", profile="motor",
        dependencies={
            "design": ("capability:power-electronics", "capability:motor-control", "capability:embedded-control"),
            "process": ("process:electronics-assembly", "process:thermal-management", "process:firmware-validation"),
            "material": ("material:power-semiconductor", "material:copper", "material:insulation-system", "material:aluminum"),
            "equipment": ("equipment:power-electronics-test-bench", "equipment:thermal-cycling-chamber", "equipment:emc-test-system"),
            "quality": ("capability:power-electronics-qualification", "capability:emc-compliance", "capability:process-control"),
        },
        explanation="A power-electronic converter that controls motor speed, torque, and energy flow from an electrical supply.",
        use_template="Use {name} to control induction, synchronous, and other motors in energy-sensitive industrial systems.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Drive assembly and use do not establish component, firmware, or qualification autonomy.",
        gaps=("power-device, gate-drive, and thermal stack", "embedded software and EMC qualification", "field reliability and service diagnostics"),
        focus=("capability:power-electronics", "process:electronics-assembly"),
        downstream=("capability:industrial-motors", "capability:industrial-automation", "capability:industrial-heat-pumps"),
        related=("servo-drive", "induction-motor", "plc-controller"),
    ),
    _archetype(
        "servo-drive", "industrial servo drive", ("servo amplifier", "motion drive"),
        kind="equipment", category="power electronics", profile="motor",
        dependencies={
            "design": ("capability:motion-control", "capability:power-electronics", "capability:embedded-control"),
            "process": ("process:electronics-assembly", "process:firmware-validation", "process:thermal-management"),
            "material": ("material:power-semiconductor", "material:control-electronics", "material:copper"),
            "equipment": ("equipment:power-electronics-test-bench", "equipment:emc-test-system", "equipment:thermal-cycling-chamber"),
            "quality": ("capability:motion-qualification", "capability:emc-compliance", "capability:machine-qualification"),
        },
        explanation="A closed-loop drive that converts command trajectories into controlled motor current and motion.",
        use_template="Use {name} where coordinated axes, fast response, and feedback stability are required.",
        status="INDIA_EMERGING_OR_LIMITED", status_epistemic="MODELLED",
        status_basis="Strategic maturity label is modelled; product-family, control-stack, and qualified scale are not asserted.",
        gaps=("high-bandwidth control and encoder interfaces", "power-device sourcing and EMC testing", "motion tuning and application support"),
        focus=("capability:motion-control", "capability:power-electronics"),
        downstream=("capability:machine-tools", "capability:industrial-robotics", "capability:packaging-machinery"),
        related=("servo-motor", "motor-drive", "plc-controller"),
    ),
    _archetype(
        "plc-controller", "programmable logic controller", ("PLC", "industrial controller"),
        kind="equipment", category="industrial automation", profile="machine",
        dependencies={
            "design": ("capability:embedded-control", "capability:industrial-automation", "capability:control-software"),
            "process": ("process:electronics-assembly", "process:firmware-validation", "process:industrial-networking"),
            "material": ("material:control-electronics", "material:power-semiconductor", "material:engineering-polymer"),
            "equipment": ("equipment:electronics-test-bench", "equipment:emc-test-system", "equipment:thermal-cycling-chamber"),
            "quality": ("capability:industrial-cybersecurity", "capability:emc-compliance", "capability:automation-qualification"),
        },
        explanation="A rugged programmable controller that sequences machines and interoperates with sensors, drives, and safety systems.",
        use_template="Use {name} to coordinate discrete manufacturing, process units, machine cells, and safety interlocks.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Integration and use are not proof of local controller silicon, firmware, or certification depth.",
        gaps=("real-time firmware and industrial communication", "functional safety and cybersecurity qualification", "long-life supply and field support"),
        focus=("capability:industrial-automation", "capability:process-control"),
        downstream=("capability:packaging-machinery", "capability:textile-machinery", "capability:process-plants"),
        related=("servo-drive", "industrial-robot", "machine-vision-system"),
    ),
    _archetype(
        "industrial-robot", "six-axis articulated industrial robot", ("industrial robot", "articulated robot arm"),
        kind="equipment", category="robotics", profile="robot",
        dependencies={
            "design": ("capability:robotics-design", "capability:motion-control", "capability:robot-programming"),
            "process": ("process:precision-machining", "process:gear-grinding", "process:robot-calibration", "process:electronics-assembly"),
            "material": ("material:alloy-steel", "material:aluminum", "material:precision-bearing", "material:rare-earth-magnet"),
            "equipment": ("equipment:precision-bearing", "equipment:servo-motor", "equipment:servo-drive", "equipment:metrology-tracker"),
            "quality": ("capability:robot-qualification", "capability:metrology", "capability:force-sensing"),
        },
        explanation="A serial multi-joint manipulator that repeats programmed motion for handling, welding, assembly, and processing.",
        use_template="Use {name} for hazardous, repetitive, high-cycle, or geometrically coordinated industrial tasks.",
        status="INDIA_EMERGING_OR_LIMITED", status_epistemic="MODELLED",
        status_basis="Modelled as strategically important; robot-grade reducers, encoders, control, and qualified production remain unknown.",
        gaps=("precision reducers, bearings, encoders, and servo stack", "calibration and application engineering", "qualified high-cycle reliability"),
        focus=("capability:robotics", "capability:precision-motion"),
        downstream=("capability:robotic-welding", "capability:automated-assembly", "capability:packaging-machinery"),
        related=("scara-robot", "collaborative-robot", "robotic-welding-cell"),
    ),
    _archetype(
        "scara-robot", "SCARA industrial robot", ("SCARA", "selective-compliance assembly robot"),
        kind="equipment", category="robotics", profile="robot",
        dependencies={
            "design": ("capability:robotics-design", "capability:motion-control"),
            "process": ("process:precision-machining", "process:gear-grinding", "process:robot-calibration"),
            "material": ("material:aluminum", "material:alloy-steel", "material:precision-bearing"),
            "equipment": ("equipment:servo-motor", "equipment:servo-drive", "equipment:metrology-tracker"),
            "quality": ("capability:robot-qualification", "capability:metrology", "capability:machine-vision"),
        },
        explanation="A fast horizontal-arm robot architecture optimized for planar assembly, pick-and-place, and small-part handling.",
        use_template="Use {name} for high-cycle assembly, inspection, packaging, and electronics handling.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Use in automation does not establish locally qualified robot mechanisms or control electronics.",
        gaps=("arm rigidity and precision bearing supply", "cycle-life and repeatability evidence", "application-specific grippers and vision"),
        focus=("capability:robotics", "capability:precision-motion"),
        downstream=("capability:electronics-assembly", "capability:packaging-machinery"),
        related=("industrial-robot", "delta-robot", "packaging-machinery"),
    ),
    _archetype(
        "delta-robot", "delta pick-and-place robot", ("delta robot", "parallel robot"),
        kind="equipment", category="robotics", profile="robot",
        dependencies={
            "design": ("capability:robotics-design", "capability:motion-control"),
            "process": ("process:precision-machining", "process:robot-calibration", "process:electronics-assembly"),
            "material": ("material:aluminum", "material:carbon-fiber", "material:precision-bearing"),
            "equipment": ("equipment:servo-motor", "equipment:servo-drive", "equipment:machine-vision"),
            "quality": ("capability:robot-qualification", "capability:metrology", "capability:machine-vision"),
        },
        explanation="A lightweight parallel robot architecture for very fast pick, sort, and place operations.",
        use_template="Use {name} for food, pharmaceutical, packaging, and small-component high-cycle handling.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Application presence is not treated as evidence of local high-cycle robot production.",
        gaps=("lightweight linkage and bearing dynamics", "vision and gripper integration", "validated high-cycle operation"),
        focus=("capability:robotics", "capability:machine-vision"),
        downstream=("capability:packaging-machinery", "capability:food-processing"),
        related=("scara-robot", "industrial-robot", "packaging-machinery"),
    ),
    _archetype(
        "collaborative-robot", "collaborative robot", ("cobot", "human-safe robot"),
        kind="equipment", category="robotics", profile="robot",
        dependencies={
            "design": ("capability:robotics-design", "capability:force-control", "capability:robot-safety"),
            "process": ("process:precision-machining", "process:robot-calibration", "process:electronics-assembly"),
            "material": ("material:aluminum", "material:engineering-polymer", "material:precision-bearing"),
            "equipment": ("equipment:servo-motor", "equipment:servo-drive", "equipment:force-torque-sensor"),
            "quality": ("capability:robot-qualification", "capability:functional-safety", "capability:metrology"),
        },
        explanation="A force- and speed-limited robot intended to share a workspace with people under defined safeguards.",
        use_template="Use {name} for flexible assembly, machine tending, inspection, and low-to-medium-volume automation.",
        status="INDIA_EMERGING_OR_LIMITED", status_epistemic="MODELLED",
        status_basis="Modelled emerging status; safety certification, reliability, and ecosystem depth require evidence.",
        gaps=("force sensing and safety validation", "reliable low-volume deployment economics", "gripper, vision, and application ecosystem"),
        focus=("capability:robotics", "capability:functional-safety"),
        downstream=("capability:automated-assembly", "capability:machine-tending"),
        related=("industrial-robot", "scara-robot", "machine-vision-system"),
    ),
    _archetype(
        "cartesian-gantry-robot", "Cartesian gantry robot", ("gantry robot", "linear robot"),
        kind="equipment", category="robotics", profile="robot",
        dependencies={
            "design": ("capability:robotics-design", "capability:precision-motion"),
            "process": ("process:precision-machining", "process:linear-guide-installation", "process:robot-calibration"),
            "material": ("material:alloy-steel", "material:aluminum", "material:precision-bearing"),
            "equipment": ("equipment:linear-guide", "equipment:servo-motor", "equipment:servo-drive", "equipment:metrology-tracker"),
            "quality": ("capability:metrology", "capability:robot-qualification", "capability:machine-alignment"),
        },
        explanation="A rail-based multi-axis automation platform suited to large work envelopes and repeatable linear motion.",
        use_template="Use {name} for palletizing, large-part handling, machine tending, welding, and additive deposition.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Fabrication and integration availability are not equivalent to a qualified robot platform.",
        gaps=("long-axis guideway straightness", "load-bearing motion and calibration", "cell safety and serviceability"),
        focus=("capability:precision-motion", "capability:robotics"),
        downstream=("capability:large-part-automation", "capability:robotic-welding"),
        related=("industrial-robot", "robotic-welding-cell", "5-axis-cnc-machining-center"),
    ),
    _archetype(
        "autonomous-mobile-robot", "autonomous mobile robot", ("AMR", "factory mobile robot"),
        kind="equipment", category="intralogistics automation", profile="robot",
        dependencies={
            "design": ("capability:robotics-design", "capability:autonomous-navigation", "capability:industrial-automation"),
            "process": ("process:electronics-assembly", "process:firmware-validation", "process:robot-calibration"),
            "material": ("material:engineering-polymer", "material:aluminum", "material:battery-cell"),
            "equipment": ("equipment:servo-motor", "equipment:machine-vision", "equipment:lidar", "equipment:industrial-network"),
            "quality": ("capability:robot-safety", "capability:software-validation", "capability:warehouse-operations"),
        },
        explanation="A sensor-guided mobile platform that transports materials through changing industrial layouts.",
        use_template="Use {name} to move pallets, bins, components, and work-in-progress between process steps.",
        status="INDIA_EMERGING_OR_LIMITED", status_epistemic="MODELLED",
        status_basis="Emerging status is a broad model label; navigation, fleet uptime, and local service depth are unknown.",
        gaps=("mapping, navigation, and fleet orchestration", "battery, safety, and traffic management", "integration with production and warehouse systems"),
        focus=("capability:industrial-automation", "capability:robotics"),
        downstream=("capability:smart-factory", "capability:warehouse-automation"),
        related=("industrial-robot", "plc-controller", "machine-vision-system"),
    ),
    _archetype(
        "packaging-machinery", "industrial packaging machinery", ("packaging line", "packaging equipment"),
        kind="equipment", category="industrial automation", profile="machine",
        dependencies={
            "design": ("capability:packaging-machine-design", "capability:industrial-automation"),
            "process": ("process:forming", "process:sealing", "process:labeling", "process:machine-alignment"),
            "material": ("material:stainless-steel", "material:engineering-polymer", "material:packaging-film"),
            "equipment": ("equipment:servo-drive", "equipment:machine-vision", "equipment:plc-controller"),
            "quality": ("capability:hygienic-design", "capability:line-qualification", "capability:process-control"),
        },
        explanation="A coordinated machine or line that forms, fills, closes, labels, or inspects a product package.",
        use_template="Use {name} to convert bulk product into repeatable, protected, traceable saleable units.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Packaging use is broad, but line integration, hygienic qualification, and component depth are unknown.",
        gaps=("format changeover and servo synchronization", "hygienic design and seal inspection", "film, closure, and automation ecosystem"),
        focus=("capability:packaging-machinery", "capability:industrial-automation"),
        downstream=("capability:food-processing", "capability:pharma-manufacturing", "capability:consumer-goods"),
        related=("plc-controller", "servo-motor", "delta-robot"),
    ),
    _archetype(
        "textile-machinery", "industrial textile machinery", ("textile machine", "spinning/weaving machinery"),
        kind="equipment", category="industrial automation", profile="machine",
        dependencies={
            "design": ("capability:textile-machine-design", "capability:industrial-automation"),
            "process": ("process:spinning", "process:weaving", "process:knitting", "process:machine-alignment"),
            "material": ("material:alloy-steel", "material:engineering-polymer", "material:precision-bearing"),
            "equipment": ("equipment:servo-motor", "equipment:servo-drive", "equipment:plc-controller"),
            "quality": ("capability:textile-process-control", "capability:high-cycle-reliability", "capability:metrology"),
        },
        explanation="A high-cycle machine family for preparing, spinning, weaving, knitting, finishing, or inspecting textile products.",
        use_template="Use {name} to transform fibres or yarns into controlled textile structures and finished rolls.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Industrial use does not establish local control, precision-motion, or high-cycle machinery depth.",
        gaps=("high-speed dynamics and yarn-process control", "precision guides, bearings, and actuators", "yield, quality, and service ecosystem"),
        focus=("capability:textile-machinery", "capability:industrial-automation"),
        downstream=("capability:textile-production", "capability:technical-textiles"),
        related=("packaging-machinery", "servo-motor", "plc-controller"),
    ),
)


MATERIAL_ARCHETYPES = (
    _archetype(
        "stainless-steel-flat-products", "stainless steel flat products", ("stainless sheet", "stainless strip"),
        kind="material", category="metals", profile="material",
        dependencies={
            "design": ("capability:metallurgy", "capability:materials-characterisation"),
            "process": ("process:steelmaking", "process:rolling", "process:heat-treatment", "process:surface-treatment"),
            "material": ("material:iron-feedstock", "material:chromium", "material:nickel", "material:stainless-steel"),
            "equipment": ("equipment:melting-furnace", "equipment:rolling-mill", "equipment:heat-treatment-furnace"),
            "quality": ("capability:metallurgical-testing", "capability:surface-inspection", "capability:quality-system"),
        },
        explanation="Corrosion-resistant stainless flat stock used as a structural, hygienic, and process-equipment input.",
        use_template="Use {name} for process vessels, food/pharma equipment, enclosures, structures, and corrosion-prone service.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Broad material production/use is not a claim about every grade, finish, or qualified route.",
        gaps=("grade-specific alloying and inclusion control", "surface finish, flatness, and inspection", "nickel/chromium feedstock resilience"),
        focus=("capability:metallurgy", "process:rolling"),
        downstream=("capability:process-equipment", "capability:food-processing", "capability:medical-equipment"),
        related=("alloy-steel-bar", "engineering-glass", "industrial-heat-exchanger"),
    ),
    _archetype(
        "alloy-steel-bar", "alloy steel bar and billet", ("alloy steel", "engineering steel bar"),
        kind="material", category="metals", profile="material",
        dependencies={
            "design": ("capability:metallurgy", "capability:materials-characterisation"),
            "process": ("process:steelmaking", "process:forging", "process:heat-treatment", "process:precision-machining"),
            "material": ("material:iron-feedstock", "material:chromium", "material:molybdenum", "material:alloy-steel"),
            "equipment": ("equipment:melting-furnace", "equipment:forging-press", "equipment:heat-treatment-furnace"),
            "quality": ("capability:metallurgical-testing", "capability:non-destructive-testing", "capability:quality-system"),
        },
        explanation="A heat-treatable engineering-metal input for shafts, gears, machine structures, and high-load components.",
        use_template="Use {name} to make forgings, shafts, gears, fasteners, and load-bearing machine parts.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Common steelmaking does not prove alloy-specific cleanliness, heat treatment, or qualification.",
        gaps=("clean steel and chemistry control", "heat-treatment distortion and depth", "traceability and fatigue-performance evidence"),
        focus=("capability:metallurgy", "process:heat-treatment"),
        downstream=("capability:gear-manufacturing", "capability:machine-tools", "capability:industrial-motors"),
        related=("bearing-steel", "tool-steel", "stainless-steel-flat-products"),
    ),
    _archetype(
        "electrical-steel", "electrical steel sheet", ("electrical steel", "motor lamination steel"),
        kind="material", category="electrical materials", profile="material",
        dependencies={
            "design": ("capability:electromagnetic-materials", "capability:metallurgy"),
            "process": ("process:steelmaking", "process:rolling", "process:annealing", "process:electrical-steel-stamping"),
            "material": ("material:iron-feedstock", "material:silicon", "material:electrical-steel", "material:insulation-coating"),
            "equipment": ("equipment:rolling-mill", "equipment:annealing-furnace", "equipment:stamping-press"),
            "quality": ("capability:magnetic-loss-testing", "capability:metallurgical-testing", "capability:quality-system"),
        },
        explanation="A low-loss ferromagnetic sheet input for motor, generator, transformer, and power-electronic magnetic circuits.",
        use_template="Use {name} to reduce magnetic losses in motors, generators, transformers, and high-efficiency drives.",
        status="INDIA_IMPORT_DEPENDENT_OR_QUALIFICATION_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Magnetic-loss grade, coating, and qualified supply depth are decision-sensitive unknowns.",
        gaps=("grade-specific magnetic loss and texture control", "thin-gauge rolling and insulation coating", "lamination stamping yield"),
        focus=("capability:electromagnetic-materials", "process:electrical-steel-stamping"),
        downstream=("capability:industrial-motors", "capability:transformers", "capability:power-electronics"),
        related=("copper-rod", "alloy-steel-bar", "industrial-motor"),
    ),
    _archetype(
        "bearing-steel", "bearing steel and raceway stock", ("bearing steel", "52100-type steel"),
        kind="material", category="metals", profile="material",
        dependencies={
            "design": ("capability:metallurgy", "capability:precision-components"),
            "process": ("process:steelmaking", "process:forging", "process:heat-treatment", "process:precision-grinding"),
            "material": ("material:iron-feedstock", "material:chromium", "material:alloy-steel", "material:clean-steel"),
            "equipment": ("equipment:melting-furnace", "equipment:heat-treatment-furnace", "equipment:precision-grinder"),
            "quality": ("capability:metallurgical-testing", "capability:fatigue-testing", "capability:metrology"),
        },
        explanation="A clean, hardenable steel input for rolling elements, races, spindles, reducers, and precision bearings.",
        use_template="Use {name} to make long-life rolling contacts where cleanliness, hardness, and geometry interact.",
        status="INDIA_IMPORT_DEPENDENT_OR_QUALIFICATION_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Publicly visible steel production cannot resolve bearing-grade cleanliness and qualified life.",
        gaps=("oxide/inclusion control and vacuum processing", "heat-treatment and retained-austenite control", "life testing and precision finishing"),
        focus=("capability:precision-components", "process:precision-grinding"),
        downstream=("capability:precision-bearings", "capability:robot-reducers", "capability:spindles"),
        related=("alloy-steel-bar", "tool-steel", "cnc-grinding-machine"),
    ),
    _archetype(
        "tool-steel", "tool and die steel", ("tool steel", "mold steel"),
        kind="material", category="metals", profile="material",
        dependencies={
            "design": ("capability:metallurgy", "capability:tooling-design"),
            "process": ("process:steelmaking", "process:forging", "process:heat-treatment", "process:precision-grinding"),
            "material": ("material:iron-feedstock", "material:chromium", "material:tungsten", "material:tool-steel"),
            "equipment": ("equipment:melting-furnace", "equipment:vacuum-furnace", "equipment:precision-grinder"),
            "quality": ("capability:metallurgical-testing", "capability:tool-life-testing", "capability:metrology"),
        },
        explanation="A wear- and heat-resistant steel input for cutting tools, dies, molds, and high-load tooling.",
        use_template="Use {name} to build tooling that must retain hardness, shape, and surface integrity through repeated cycles.",
        status="INDIA_PRESENT_BUT_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Generic tool-steel availability does not prove grade-specific production or heat-treatment depth.",
        gaps=("powder/melt cleanliness and alloy control", "vacuum heat treatment and distortion", "tool-life evidence in target applications"),
        focus=("capability:toolmaking", "process:heat-treatment"),
        downstream=("capability:machine-tools", "capability:packaging-machinery", "capability:automotive-tooling"),
        related=("bearing-steel", "alloy-steel-bar", "cnc-grinding-machine"),
    ),
    _archetype(
        "nickel-superalloy", "nickel-base superalloy stock", ("nickel superalloy", "high-temperature alloy"),
        kind="material", category="advanced metals", profile="material",
        dependencies={
            "design": ("capability:high-temperature-metallurgy", "capability:materials-characterisation"),
            "process": ("process:vacuum-melting", "process:forging", "process:heat-treatment", "process:precision-machining"),
            "material": ("material:nickel", "material:chromium", "material:cobalt", "material:nickel-alloy"),
            "equipment": ("equipment:vacuum-induction-furnace", "equipment:forging-press", "equipment:vacuum-furnace"),
            "quality": ("capability:metallurgical-testing", "capability:non-destructive-testing", "capability:high-temperature-testing"),
        },
        explanation="A high-temperature, corrosion-resistant alloy input for hot-section, chemical, and energy equipment.",
        use_template="Use {name} where creep, oxidation, fatigue, and corrosion exceed ordinary steel or aluminum envelopes.",
        status="INDIA_IMPORT_DEPENDENT_OR_QUALIFICATION_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="High-temperature alloy chemistry, cleanliness, and qualified conversion routes are not adjudicated.",
        gaps=("vacuum melt and inclusion control", "forging/heat-treatment process window", "long-duration creep and fatigue evidence"),
        focus=("capability:high-temperature-metallurgy", "process:vacuum-melting"),
        downstream=("capability:power-equipment", "capability:aerospace-components", "capability:chemical-process-equipment"),
        related=("titanium-alloy", "tool-steel", "heat-exchanger"),
    ),
    _archetype(
        "aluminum-alloy", "aluminum alloy semi-finished product", ("aluminum alloy", "aluminium alloy"),
        kind="material", category="non-ferrous metals", profile="material",
        dependencies={
            "design": ("capability:lightweight-materials", "capability:metallurgy"),
            "process": ("process:casting", "process:rolling", "process:heat-treatment", "process:surface-treatment"),
            "material": ("material:aluminum", "material:magnesium", "material:silicon", "material:aluminum-alloy"),
            "equipment": ("equipment:melting-furnace", "equipment:rolling-mill", "equipment:heat-treatment-furnace"),
            "quality": ("capability:metallurgical-testing", "capability:surface-inspection", "capability:quality-system"),
        },
        explanation="A light structural metal family supplied as sheet, plate, extrusion, bar, or near-net shape.",
        use_template="Use {name} to reduce mass in structures, housings, vehicles, robots, heat exchangers, and equipment.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Material family is broad; grade, temper, cleanliness, and qualified application depth remain unknown.",
        gaps=("alloy/temper-specific consistency", "joining and galvanic-control routes", "recycled feedstock chemistry control"),
        focus=("capability:lightweight-materials", "process:casting"),
        downstream=("capability:robotics", "capability:industrial-enclosures", "capability:machine-tools"),
        related=("titanium-alloy", "stainless-steel-flat-products", "engineering-polymer"),
    ),
    _archetype(
        "titanium-alloy", "titanium alloy semi-finished product", ("titanium alloy", "titanium stock"),
        kind="material", category="advanced metals", profile="material",
        dependencies={
            "design": ("capability:lightweight-materials", "capability:metallurgy"),
            "process": ("process:vacuum-melting", "process:forging", "process:heat-treatment", "process:precision-machining"),
            "material": ("material:titanium", "material:aluminum", "material:vanadium", "material:titanium-alloy"),
            "equipment": ("equipment:vacuum-induction-furnace", "equipment:forging-press", "equipment:5-axis-cnc-machining-center"),
            "quality": ("capability:metallurgical-testing", "capability:non-destructive-testing", "capability:fatigue-testing"),
        },
        explanation="A high specific-strength and corrosion-resistant alloy input for demanding structures and process equipment.",
        use_template="Use {name} where mass, corrosion, or temperature constraints justify difficult conversion and machining.",
        status="INDIA_IMPORT_DEPENDENT_OR_QUALIFICATION_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Qualified grade, melt, forging, and machining depth require direct evidence.",
        gaps=("sponge/melt supply and chemistry control", "forging and machining process window", "application qualification and fatigue data"),
        focus=("capability:advanced-metallurgy", "capability:precision-machining"),
        downstream=("capability:aerospace-components", "capability:medical-components", "capability:chemical-process-equipment"),
        related=("nickel-superalloy", "aluminum-alloy", "5-axis-cnc-machining-center"),
    ),
    _archetype(
        "copper-rod", "copper rod and conductor stock", ("copper rod", "electrical copper"),
        kind="material", category="non-ferrous metals", profile="material",
        dependencies={
            "design": ("capability:electrical-materials", "capability:metallurgy"),
            "process": ("process:smelting", "process:casting", "process:rolling", "process:wire-drawing"),
            "material": ("material:copper", "material:copper-concentrate", "material:recycled-copper"),
            "equipment": ("equipment:melting-furnace", "equipment:continuous-caster", "equipment:wire-drawing-machine"),
            "quality": ("capability:conductivity-testing", "capability:metallurgical-testing", "capability:quality-system"),
        },
        explanation="A high-conductivity metal input for windings, cables, busbars, heat exchangers, and electrical interconnects.",
        use_template="Use {name} to make conductors, coils, wiring, busbars, motors, transformers, and thermal paths.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Trade or smelting activity does not establish feedstock, purity, and product-form resilience.",
        gaps=("refined supply and scrap collection", "conductivity and surface quality", "draw/anneal consistency for fine conductors"),
        focus=("capability:electrical-materials", "process:wire-drawing"),
        downstream=("capability:industrial-motors", "capability:power-electronics", "capability:electrical-equipment"),
        related=("electrical-steel", "aluminum-alloy", "industrial-motor"),
    ),
    _archetype(
        "engineering-glass", "engineering glass and ceramic material", ("technical glass", "engineering ceramic"),
        kind="material", category="glass and ceramics", profile="material",
        dependencies={
            "design": ("capability:ceramics-engineering", "capability:materials-characterisation"),
            "process": ("process:glass-melting", "process:ceramic-sintering", "process:precision-grinding", "process:surface-treatment"),
            "material": ("material:silica", "material:alumina", "material:borosilicate-glass", "material:ceramic"),
            "equipment": ("equipment:melting-furnace", "equipment:controlled-atmosphere-furnace", "equipment:precision-grinder"),
            "quality": ("capability:optical-inspection", "capability:thermal-shock-testing", "capability:metrology"),
        },
        explanation="A non-metallic material family used where thermal, chemical, electrical, optical, or wear properties matter.",
        use_template="Use {name} for insulators, windows, labware, seals, process liners, optics, and wear-resistant components.",
        status="INDIA_PRESENT_BUT_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Material-family presence is not evidence of grade-specific purity, forming, or qualification.",
        gaps=("purity and defect control", "forming, firing, and finishing yield", "thermal, optical, or chemical qualification"),
        focus=("capability:ceramics-engineering", "process:ceramic-sintering"),
        downstream=("capability:medical-equipment", "capability:chemical-process-equipment", "capability:scientific-instruments"),
        related=("stainless-steel-flat-products", "engineering-polymer", "vacuum-furnace"),
    ),
    _archetype(
        "lfp-cathode-material", "lithium iron phosphate cathode material", ("LFP cathode", "iron-phosphate cathode"),
        kind="material", category="battery materials", profile="chemical",
        dependencies={
            "design": ("capability:battery-materials", "capability:electrochemical-characterisation"),
            "process": ("process:precursor-synthesis", "process:calcination", "process:powder-processing", "process:coating"),
            "material": ("material:lithium-compound", "material:iron-phosphate", "material:carbon-coating", "material:process-water"),
            "equipment": ("equipment:calciner", "equipment:powder-mixer", "equipment:controlled-atmosphere-furnace"),
            "quality": ("capability:particle-size-control", "capability:electrochemical-testing", "capability:quality-system"),
        },
        explanation="A lithium-ion cathode chemistry that trades some energy density for reduced cobalt and nickel dependence.",
        use_template="Use {name} in batteries where safety, cycle life, cost, and material availability outweigh maximum energy density.",
        status="INDIA_EMERGING_OR_LIMITED", status_epistemic="MODELLED",
        status_basis="Strategic emerging label only; precursor, powder, cell, and qualified yield depth remain unknown.",
        gaps=("precursor purity and particle morphology", "calcination/coating uniformity", "cell-level qualification and recycling"),
        focus=("capability:battery-materials", "process:calcination"),
        downstream=("capability:battery-cells", "capability:energy-storage", "capability:electric-vehicles"),
        related=("hard-carbon-anode", "nmc-precursor", "battery-cell-assembly"),
    ),
    _archetype(
        "nmc-precursor", "nickel manganese cobalt cathode precursor", ("NMC precursor", "ternary cathode precursor"),
        kind="chemical", category="battery materials", profile="chemical",
        dependencies={
            "design": ("capability:battery-materials", "capability:electrochemical-characterisation"),
            "process": ("process:co-precipitation", "process:calcination", "process:powder-processing", "process:coating"),
            "material": ("material:lithium-compound", "material:nickel", "material:manganese", "material:cobalt"),
            "equipment": ("equipment:precipitation-reactor", "equipment:calciner", "equipment:powder-mixer"),
            "quality": ("capability:particle-size-control", "capability:electrochemical-testing", "capability:chemical-quality"),
        },
        explanation="A co-precipitated transition-metal precursor for high-energy lithium-ion cathodes.",
        use_template="Use {name} when cell architecture needs high energy density and controlled nickel/manganese/cobalt ratios.",
        status="INDIA_IMPORT_DEPENDENT_OR_QUALIFICATION_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Feedstock, purification, and qualified cathode performance are not resolved by this ontology card.",
        gaps=("nickel/cobalt feedstock and impurity control", "co-precipitation morphology", "cell qualification and supply resilience"),
        focus=("capability:battery-materials", "process:co-precipitation"),
        downstream=("capability:battery-cells", "capability:energy-storage"),
        related=("lfp-cathode-material", "hard-carbon-anode", "lithium-compound"),
    ),
    _archetype(
        "graphite-anode", "graphite anode material", ("graphite anode", "battery graphite"),
        kind="material", category="battery materials", profile="chemical",
        dependencies={
            "design": ("capability:battery-materials", "capability:electrochemical-characterisation"),
            "process": ("process:graphite-purification", "process:graphitisation", "process:powder-processing", "process:coating"),
            "material": ("material:natural-graphite", "material:synthetic-graphite", "material:carbon-coating"),
            "equipment": ("equipment:graphitisation-furnace", "equipment:powder-classifier", "equipment:controlled-atmosphere-furnace"),
            "quality": ("capability:particle-size-control", "capability:electrochemical-testing", "capability:chemical-quality"),
        },
        explanation="A carbon anode material that stores lithium through intercalation in a controlled particle structure.",
        use_template="Use {name} in lithium-ion cells where reversible capacity, rate performance, and manufacturability are required.",
        status="INDIA_IMPORT_DEPENDENT_OR_QUALIFICATION_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Graphite purification and battery-grade qualification are separate from mineral occurrence or trade.",
        gaps=("purity and morphology control", "graphitisation energy and furnace depth", "electrolyte compatibility and cell qualification"),
        focus=("capability:battery-materials", "process:graphitisation"),
        downstream=("capability:battery-cells", "capability:energy-storage"),
        related=("hard-carbon-anode", "lfp-cathode-material", "battery-cell-assembly"),
    ),
    _archetype(
        "hard-carbon-anode", "hard-carbon anode material", ("hard carbon", "sodium-ion anode"),
        kind="material", category="battery materials", profile="chemical",
        dependencies={
            "design": ("capability:battery-materials", "capability:electrochemical-characterisation"),
            "process": ("process:biomass-carbonisation", "process:pyrolysis", "process:powder-processing", "process:surface-treatment"),
            "material": ("material:biomass-feedstock", "material:carbon", "material:process-gas"),
            "equipment": ("equipment:pyrolysis-furnace", "equipment:powder-classifier", "equipment:controlled-atmosphere-furnace"),
            "quality": ("capability:particle-size-control", "capability:electrochemical-testing", "capability:chemical-quality"),
        },
        explanation="A disordered carbon anode candidate for sodium-ion or selected lithium-ion battery architectures.",
        use_template="Use {name} where abundant feedstocks and reduced graphite dependence are valued over maximum energy density.",
        status="INDIA_EMERGING_OR_LIMITED", status_epistemic="MODELLED",
        status_basis="Emerging label is a scenario-friendly ontology status, not a claim of commercial Indian production.",
        gaps=("feedstock consistency and pore-structure control", "carbonisation recipe and yield", "cell ageing and cycle-life qualification"),
        focus=("capability:battery-materials", "process:pyrolysis"),
        downstream=("capability:sodium-ion-battery", "capability:energy-storage"),
        related=("graphite-anode", "lfp-cathode-material", "biomass-processing"),
    ),
    _archetype(
        "lithium-compound", "battery-grade lithium compound", ("lithium carbonate", "lithium hydroxide"),
        kind="chemical", category="battery materials", profile="chemical",
        dependencies={
            "design": ("capability:chemical-process-design", "capability:electrochemical-characterisation"),
            "process": ("process:leaching", "process:solvent-extraction", "process:precipitation", "process:crystallisation"),
            "material": ("material:lithium-feedstock", "material:process-water", "material:process-chemicals"),
            "equipment": ("equipment:leach-reactor", "equipment:solvent-extraction-unit", "equipment:crystalliser"),
            "quality": ("capability:chemical-quality", "capability:trace-impurity-analysis", "capability:quality-system"),
        },
        explanation="A purified lithium chemical precursor used to make cathodes and other battery-active materials.",
        use_template="Use {name} when battery production requires controlled lithium concentration and low trace impurities.",
        status="INDIA_IMPORT_DEPENDENT_OR_QUALIFICATION_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Resource, trade, and project claims are not converted into usable battery-grade supply here.",
        gaps=("feedstock and conversion route", "trace impurity removal and crystallisation", "qualified battery-material customer acceptance"),
        focus=("capability:battery-materials", "process:crystallisation"),
        downstream=("capability:lfp-cathode", "capability:nmc-cathode", "capability:battery-cells"),
        related=("lfp-cathode-material", "nmc-precursor", "graphite-anode"),
    ),
    _archetype(
        "rare-earth-oxide", "rare-earth oxide and separated precursor", ("rare-earth oxide", "NdPr oxide"),
        kind="chemical", category="critical materials", profile="chemical",
        dependencies={
            "design": ("capability:rare-earth-processing", "capability:chemical-process-design"),
            "process": ("process:beneficiation", "process:leaching", "process:solvent-extraction", "process:precipitation"),
            "material": ("material:rare-earth-feedstock", "material:process-chemicals", "material:process-water"),
            "equipment": ("equipment:leach-reactor", "equipment:solvent-extraction-unit", "equipment:filter-press"),
            "quality": ("capability:trace-impurity-analysis", "capability:chemical-quality", "capability:environmental-control"),
        },
        explanation="A separated rare-earth chemical precursor upstream of magnets, phosphors, catalysts, and selected electronics.",
        use_template="Use {name} when downstream materials require controlled rare-earth composition and impurity levels.",
        status="INDIA_IMPORT_DEPENDENT_OR_QUALIFICATION_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Mineral occurrence and trade are not treated as separated, usable, or qualified industrial supply.",
        gaps=("separation chemistry and solvent management", "purity and trace-element control", "waste handling and qualified downstream conversion"),
        focus=("capability:rare-earth-processing", "process:solvent-extraction"),
        downstream=("capability:permanent-magnet-materials", "capability:industrial-motors", "capability:robotics"),
        related=("lithium-compound", "graphite-anode", "chemical-process-equipment"),
    ),
    _archetype(
        "chlor-alkali-plant", "chlor-alkali process plant", ("chlor-alkali", "caustic soda/chlorine plant"),
        kind="process_system", category="chemicals", profile="process",
        dependencies={
            "design": ("capability:chemical-process-design", "capability:process-safety"),
            "process": ("process:electrolysis", "process:chlorine-handling", "process:caustic-evaporation"),
            "material": ("material:salt", "material:stainless-steel", "material:process-water", "material:membrane"),
            "equipment": ("equipment:electrolyzer", "equipment:industrial-pump", "equipment:heat-exchanger", "equipment:gas-scrubber"),
            "quality": ("capability:process-safety", "capability:chemical-quality", "capability:environmental-control"),
        },
        explanation="An electrochemical process route for chlorine, caustic soda, hydrogen, and related chemical intermediates.",
        use_template="Use {name} to supply chlorine-alkali chemistry while managing electricity, brine, gas, and waste constraints.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Plant category is established; route-specific efficiency, membrane, safety, and operating depth are unknown.",
        gaps=("membrane/electrode life and power efficiency", "chlorine containment and safety systems", "brine quality and downstream integration"),
        focus=("capability:chemical-processes", "capability:process-safety"),
        downstream=("capability:solvents", "capability:water-treatment", "capability:polymer-production"),
        related=("pem-electrolyzer", "alkaline-electrolyzer", "industrial-heat-exchanger"),
    ),
    _archetype(
        "sulfuric-acid-plant", "sulfuric acid process plant", ("sulfuric acid plant", "contact-process plant"),
        kind="process_system", category="chemicals", profile="process",
        dependencies={
            "design": ("capability:chemical-process-design", "capability:process-safety"),
            "process": ("process:roasting", "process:catalytic-conversion", "process:gas-cleaning"),
            "material": ("material:sulfur-feedstock", "material:stainless-steel", "material:process-water", "material:catalyst"),
            "equipment": ("equipment:industrial-pump", "equipment:heat-exchanger", "equipment:gas-scrubber", "equipment:process-reactor"),
            "quality": ("capability:chemical-quality", "capability:corrosion-management", "capability:environmental-control"),
        },
        explanation="A catalytic oxidation and absorption route producing sulfuric acid for fertilizer, chemicals, and metallurgy.",
        use_template="Use {name} to convert sulfur-bearing feedstock into controlled acid for upstream and downstream industrial chemistry.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Plant class is broad; feedstock, corrosion, emissions, and effective operating depth are not asserted.",
        gaps=("corrosion-resistant process equipment", "catalyst and heat-recovery control", "emissions, acid strength, and safety qualification"),
        focus=("capability:chemical-processes", "process:gas-cleaning"),
        downstream=("capability:fertilizer-production", "capability:hydrometallurgy", "capability:battery-materials"),
        related=("nitric-acid-plant", "industrial-heat-exchanger", "centrifugal-pump"),
    ),
    _archetype(
        "nitric-acid-plant", "nitric acid process plant", ("nitric acid plant", "nitric oxidation plant"),
        kind="process_system", category="chemicals", profile="process",
        dependencies={
            "design": ("capability:chemical-process-design", "capability:process-safety"),
            "process": ("process:ammonia-oxidation", "process:absorption", "process:gas-cleaning"),
            "material": ("material:ammonia", "material:stainless-steel", "material:process-water", "material:catalyst"),
            "equipment": ("equipment:process-reactor", "equipment:industrial-pump", "equipment:heat-exchanger", "equipment:gas-scrubber"),
            "quality": ("capability:chemical-quality", "capability:process-safety", "capability:environmental-control"),
        },
        explanation="An ammonia oxidation and absorption route for nitric acid and nitrate intermediates.",
        use_template="Use {name} to supply nitrate chemistry while managing heat, emissions, corrosion, and safety.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Process class is known; plant-specific feedstock, emissions, and qualified route remain unknown.",
        gaps=("catalyst and gas-flow control", "corrosion and NOx abatement", "safe integration with downstream fertilizer or chemical units"),
        focus=("capability:chemical-processes", "capability:process-safety"),
        downstream=("capability:fertilizer-production", "capability:explosives-chemistry", "capability:chemical-process-equipment"),
        related=("ammonia-urea-plant", "sulfuric-acid-plant", "industrial-pump"),
    ),
    _archetype(
        "ammonia-urea-plant", "ammonia and urea process plant", ("ammonia plant", "urea plant"),
        kind="process_system", category="chemicals and fertilizers", profile="process",
        dependencies={
            "design": ("capability:chemical-process-design", "capability:process-safety", "capability:thermal-integration"),
            "process": ("process:ammonia-synthesis", "process:carbon-dioxide-capture", "process:urea-synthesis"),
            "material": ("material:natural-gas", "material:hydrogen", "material:nitrogen", "material:stainless-steel"),
            "equipment": ("equipment:process-reactor", "equipment:industrial-compressor", "equipment:heat-exchanger", "equipment:industrial-pump"),
            "quality": ("capability:process-safety", "capability:chemical-quality", "capability:environmental-control"),
        },
        explanation="An integrated high-pressure route for ammonia and nitrogen fertilizer intermediates.",
        use_template="Use {name} to make nitrogen products from hydrogen, nitrogen, and controlled high-pressure synthesis loops.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Plant category is established; feedstock, energy, process efficiency, and ramp depth are not asserted.",
        gaps=("high-pressure equipment and catalyst life", "hydrogen and natural-gas resilience", "heat integration, safety, and emissions control"),
        focus=("capability:chemical-processes", "capability:industrial-compressors"),
        downstream=("capability:fertilizer-production", "capability:industrial-hydrogen", "capability:chemical-logistics"),
        related=("pem-electrolyzer", "industrial-compressor", "industrial-heat-exchanger"),
    ),
    _archetype(
        "methanol-syngas-plant", "methanol and syngas process plant", ("methanol plant", "syngas plant"),
        kind="process_system", category="chemicals and fuels", profile="process",
        dependencies={
            "design": ("capability:chemical-process-design", "capability:thermal-integration"),
            "process": ("process:gasification", "process:reforming", "process:syngas-cleaning", "process:methanol-synthesis"),
            "material": ("material:natural-gas", "material:biomass-feedstock", "material:hydrogen", "material:catalyst"),
            "equipment": ("equipment:process-reactor", "equipment:industrial-compressor", "equipment:gas-scrubber", "equipment:heat-exchanger"),
            "quality": ("capability:chemical-quality", "capability:process-safety", "capability:emissions-control"),
        },
        explanation="A synthesis-gas conversion route for methanol, chemicals, fuels, and carbon-utilization pathways.",
        use_template="Use {name} to convert carbonaceous or hydrogen-rich feedstocks into controlled chemical intermediates.",
        status="INDIA_EMERGING_OR_LIMITED", status_epistemic="MODELLED",
        status_basis="Modelled as route-dependent; feedstock, catalyst, and qualified plant depth are unknown.",
        gaps=("feedstock cleanup and catalyst life", "heat/power integration", "carbon intensity and downstream offtake qualification"),
        focus=("capability:chemical-processes", "capability:thermal-integration"),
        downstream=("capability:solvents", "capability:polymer-production", "capability:sustainable-fuels"),
        related=("ammonia-urea-plant", "industrial-compressor", "biogas-upgrader"),
    ),
    _archetype(
        "industrial-gas-separation", "industrial gas separation and purification system", ("air separation unit", "industrial gas plant"),
        kind="process_system", category="process industries", profile="process",
        dependencies={
            "design": ("capability:chemical-process-design", "capability:cryogenic-engineering"),
            "process": ("process:compression", "process:distillation", "process:gas-purification", "process:cryogenic-separation"),
            "material": ("material:stainless-steel", "material:process-gas", "material:adsorbent", "material:process-water"),
            "equipment": ("equipment:industrial-compressor", "equipment:distillation-column", "equipment:heat-exchanger", "equipment:gas-scrubber"),
            "quality": ("capability:gas-purity-analysis", "capability:process-safety", "capability:utility-reliability"),
        },
        explanation="A separation and purification system producing oxygen, nitrogen, argon, hydrogen, or specialty gases.",
        use_template="Use {name} to supply process gases whose purity, pressure, and continuity govern downstream production.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Gas production category is broad; purity, uptime, and facility integration remain unspecified.",
        gaps=("low-temperature heat exchange and adsorbent life", "purity measurement and storage", "power continuity and safety"),
        focus=("capability:industrial-gases", "process:gas-purification"),
        downstream=("capability:steelmaking", "capability:medical-gases", "capability:semiconductor-processing"),
        related=("industrial-compressor", "distillation-column", "hydrogen-purification"),
    ),
    _archetype(
        "solvent-recovery-unit", "solvent recovery and purification unit", ("solvent recovery", "solvent distillation"),
        kind="process_system", category="chemicals", profile="chemical",
        dependencies={
            "design": ("capability:chemical-process-design", "capability:process-safety"),
            "process": ("process:distillation", "process:adsorption", "process:condensation", "process:waste-treatment"),
            "material": ("material:stainless-steel", "material:engineering-polymer", "material:solvent-feedstock", "material:adsorbent"),
            "equipment": ("equipment:distillation-column", "equipment:heat-exchanger", "equipment:industrial-pump", "equipment:vacuum-system"),
            "quality": ("capability:chemical-quality", "capability:environmental-control", "capability:process-safety"),
        },
        explanation="A separation unit that recovers and purifies solvents for reuse, emissions control, and process economics.",
        use_template="Use {name} to recover solvent from chemical, pharmaceutical, coating, and electronics process streams.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Equipment category is known; solvent-specific route, purity, and recovery performance are unknown.",
        gaps=("corrosion and compatibility control", "low-energy separation and purity", "safe handling of flammable or toxic streams"),
        focus=("capability:chemical-processes", "process:distillation"),
        downstream=("capability:pharmaceutical-equipment", "capability:coatings", "capability:electronics-processing"),
        related=("distillation-column", "chemical-reactor", "industrial-heat-exchanger"),
    ),
    _archetype(
        "engineering-polymer", "engineering polymer resin and compound", ("engineering plastic", "polymer compound"),
        kind="material", category="polymers", profile="chemical",
        dependencies={
            "design": ("capability:polymer-formulation", "capability:materials-characterisation"),
            "process": ("process:polymerisation", "process:compounding", "process:extrusion", "process:pelletising"),
            "material": ("material:polymer-feedstock", "material:glass-fibre", "material:carbon-filler", "material:additives"),
            "equipment": ("equipment:polymer-reactor", "equipment:extruder", "equipment:pelletiser"),
            "quality": ("capability:polymer-testing", "capability:chemical-quality", "capability:process-control"),
        },
        explanation="A polymer material engineered for structural, thermal, electrical, or chemical performance beyond commodity plastics.",
        use_template="Use {name} for housings, gears, seals, insulators, medical parts, and lightweight equipment structures.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Polymer production/use is broad; formulation, filler, purity, and application qualification remain unknown.",
        gaps=("feedstock and additive consistency", "compound dispersion and moisture control", "long-term mechanical/thermal qualification"),
        focus=("capability:polymer-formulation", "process:compounding"),
        downstream=("capability:industrial-enclosures", "capability:medical-equipment", "capability:packaging-machinery"),
        related=("stainless-steel-flat-products", "engineering-glass", "single-use-bioprocess-system"),
    ),
    _archetype(
        "centrifugal-pump", "industrial centrifugal pump", ("centrifugal pump", "process pump"),
        kind="equipment", category="process equipment", profile="process",
        dependencies={
            "design": ("capability:fluid-machinery-design", "capability:rotordynamics"),
            "process": ("process:casting", "process:precision-machining", "process:balancing", "process:surface-treatment"),
            "material": ("material:stainless-steel", "material:alloy-steel", "material:engineering-polymer", "material:seal-material"),
            "equipment": ("equipment:cnc-machining-center", "equipment:dynamic-balancer", "equipment:industrial-motor", "equipment:test-bench"),
            "quality": ("capability:pump-testing", "capability:hydraulic-performance", "capability:corrosion-management"),
        },
        explanation="A rotating fluid machine that converts shaft power into pressure and flow for industrial process services.",
        use_template="Use {name} to move water, chemicals, slurries, cooling fluids, and process streams with controlled duty.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Pump manufacturing/use is broad; duty envelope, materials, seals, and qualified efficiency remain unknown.",
        gaps=("hydraulic design and cavitation margin", "seal/material compatibility", "tested efficiency, vibration, and lifecycle evidence"),
        focus=("capability:fluid-machinery", "capability:precision-machining"),
        downstream=("capability:chemical-process-equipment", "capability:water-treatment", "capability:food-processing"),
        related=("industrial-motor", "industrial-heat-pump", "heat-exchanger"),
    ),
    _archetype(
        "industrial-heat-pump", "industrial heat pump", ("process heat pump", "high-temperature heat pump"),
        kind="equipment", category="thermal process equipment", profile="process",
        dependencies={
            "design": ("capability:thermal-systems-design", "capability:refrigeration-engineering"),
            "process": ("process:compression", "process:heat-exchange", "process:refrigerant-management", "process:thermal-integration"),
            "material": ("material:stainless-steel", "material:copper", "material:refrigerant", "material:engineering-polymer"),
            "equipment": ("equipment:industrial-compressor", "equipment:heat-exchanger", "equipment:industrial-motor", "equipment:control-system"),
            "quality": ("capability:thermal-performance-testing", "capability:refrigerant-safety", "capability:process-control"),
        },
        explanation="A thermodynamic system that upgrades low-grade heat to useful process heat through a refrigerant cycle.",
        use_template="Use {name} to decarbonise drying, evaporation, hot-water, and low-to-medium-temperature process duties.",
        status="INDIA_EMERGING_OR_LIMITED", status_epistemic="MODELLED",
        status_basis="Emerging strategic label only; high-temperature duty, refrigerant, and integration depth require evidence.",
        gaps=("compressor and refrigerant envelope", "heat-exchanger fouling and control", "site integration, uptime, and maintenance"),
        focus=("capability:thermal-systems", "capability:industrial-compressors"),
        downstream=("capability:food-processing", "capability:chemical-processes", "capability:industrial-decarbonisation"),
        related=("centrifugal-pump", "industrial-motor", "heat-exchanger"),
    ),
    _archetype(
        "pem-electrolyzer", "PEM water electrolyzer system", ("PEM electrolyzer", "proton-exchange membrane electrolyzer"),
        kind="equipment", category="hydrogen equipment", profile="process",
        dependencies={
            "design": ("capability:electrochemical-systems", "capability:hydrogen-systems", "capability:power-electronics"),
            "process": ("process:membrane-electrode-assembly", "process:stack-assembly", "process:gas-purification", "process:water-treatment"),
            "material": ("material:stainless-steel", "material:membrane", "material:platinum-group-catalyst", "material:process-water"),
            "equipment": ("equipment:electrolyzer", "equipment:power-electronics-test-bench", "equipment:gas-purification"),
            "quality": ("capability:hydrogen-purity-testing", "capability:electrochemical-testing", "capability:pressure-safety"),
        },
        explanation="An electrochemical stack and balance-of-plant that splits purified water into hydrogen and oxygen.",
        use_template="Use {name} where dynamic hydrogen production, purity, and compact modular deployment are important.",
        status="INDIA_EMERGING_OR_LIMITED", status_epistemic="MODELLED",
        status_basis="Strategic emerging label; stack life, catalyst supply, and qualified scale are unknown.",
        gaps=("membrane/electrode durability and catalyst loading", "stack sealing, power electronics, and gas purity", "water quality, safety, and operating data"),
        focus=("capability:hydrogen-systems", "process:electrolysis"),
        downstream=("capability:industrial-hydrogen", "capability:green-chemicals", "capability:energy-storage"),
        related=("alkaline-electrolyzer", "industrial-gas-separation", "industrial-heat-pump"),
    ),
    _archetype(
        "alkaline-electrolyzer", "alkaline water electrolyzer system", ("alkaline electrolyzer", "alkaline hydrogen system"),
        kind="equipment", category="hydrogen equipment", profile="process",
        dependencies={
            "design": ("capability:electrochemical-systems", "capability:hydrogen-systems", "capability:process-safety"),
            "process": ("process:electrolysis", "process:stack-assembly", "process:gas-purification", "process:water-treatment"),
            "material": ("material:stainless-steel", "material:alkaline-electrolyte", "material:nickel", "material:process-water"),
            "equipment": ("equipment:electrolyzer", "equipment:industrial-pump", "equipment:gas-purification", "equipment:power-electronics-test-bench"),
            "quality": ("capability:hydrogen-purity-testing", "capability:electrochemical-testing", "capability:pressure-safety"),
        },
        explanation="An alkaline electrochemical system that produces hydrogen and oxygen using a liquid electrolyte.",
        use_template="Use {name} for steady-duty hydrogen production where mature balance-of-plant and lower catalyst intensity are valued.",
        status="INDIA_EMERGING_OR_LIMITED", status_epistemic="MODELLED",
        status_basis="Emerging label only; stack, diaphragm, balance-of-plant, and qualification depth remain unknown.",
        gaps=("diaphragm/electrolyte management", "stack lifetime and gas crossover", "system integration, safety, and power quality"),
        focus=("capability:hydrogen-systems", "process:electrolysis"),
        downstream=("capability:industrial-hydrogen", "capability:ammonia-production", "capability:green-steel"),
        related=("pem-electrolyzer", "industrial-gas-separation", "industrial-compressor"),
    ),
    _archetype(
        "industrial-heat-exchanger", "industrial heat exchanger", ("heat exchanger", "process heat exchanger"),
        kind="equipment", category="process equipment", profile="process",
        dependencies={
            "design": ("capability:thermal-systems-design", "capability:fluid-machinery-design"),
            "process": ("process:rolling", "process:welding", "process:brazing", "process:pressure-testing"),
            "material": ("material:stainless-steel", "material:copper", "material:nickel-alloy", "material:seal-material"),
            "equipment": ("equipment:cnc-machining-center", "equipment:welding-system", "equipment:pressure-test-bench", "equipment:metrology-cmm"),
            "quality": ("capability:pressure-boundary-qualification", "capability:non-destructive-testing", "capability:thermal-performance-testing"),
        },
        explanation="A pressure-boundary device that transfers heat between process streams without mixing them.",
        use_template="Use {name} to heat, cool, condense, evaporate, recover, or integrate energy across industrial flows.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Equipment category is broad; material, weld, fouling, pressure, and thermal qualification remain unknown.",
        gaps=("material/geometry selection and fouling control", "pressure-boundary welding and NDT", "thermal performance under actual process conditions"),
        focus=("capability:thermal-systems", "process:pressure-testing"),
        downstream=("capability:chemical-process-equipment", "capability:industrial-heat-pumps", "capability:food-processing"),
        related=("centrifugal-pump", "industrial-heat-pump", "stainless-steel-flat-products"),
    ),
    _archetype(
        "thermal-vacuum-furnace", "vacuum and controlled-atmosphere furnace", ("vacuum furnace", "industrial heat-treatment furnace"),
        kind="equipment", category="thermal process equipment", profile="process",
        dependencies={
            "design": ("capability:thermal-process-design", "capability:metallurgy"),
            "process": ("process:heat-treatment", "process:vacuum-processing", "process:controlled-atmosphere-processing"),
            "material": ("material:tool-steel", "material:alloy-steel", "material:graphite", "material:refractory-ceramic"),
            "equipment": ("equipment:vacuum-system", "equipment:temperature-control", "equipment:gas-purification", "equipment:metrology-cmm"),
            "quality": ("capability:thermal-uniformity-testing", "capability:metallurgical-testing", "capability:process-qualification"),
        },
        explanation="A controlled thermal-processing system for hardening, annealing, sintering, brazing, or vacuum treatment.",
        use_template="Use {name} to alter material properties while limiting oxidation, contamination, distortion, or atmosphere variation.",
        status="INDIA_EMERGING_OR_LIMITED", status_epistemic="MODELLED",
        status_basis="Foundational equipment status is modelled; temperature uniformity, vacuum, and qualified recipe depth are unknown.",
        gaps=("thermal uniformity and atmosphere control", "vacuum seals, pumps, and graphite hot-zone", "recipe qualification and distortion/yield data"),
        focus=("capability:thermal-processing", "process:heat-treatment"),
        downstream=("capability:precision-bearings", "capability:machine-tools", "capability:advanced-metals"),
        related=("tool-steel", "bearing-steel", "industrial-heat-exchanger"),
    ),
)


MEDICAL_ARCHETYPES = (
    _archetype(
        "mri-system", "magnetic resonance imaging system", ("MRI", "MR scanner"),
        kind="instrument", category="medical imaging", profile="imaging",
        dependencies={
            "design": ("capability:medical-device-design", "capability:magnetic-resonance-engineering", "capability:clinical-protocols"),
            "process": ("process:superconducting-magnet-assembly", "process:electronics-assembly", "process:medical-device-assembly", "process:calibration"),
            "material": ("material:superconducting-wire", "material:stainless-steel", "material:engineering-polymer", "material:helium"),
            "equipment": ("equipment:magnet-test-system", "equipment:gradient-amplifier", "equipment:metrology-cmm", "equipment:thermal-cycling-chamber"),
            "quality": ("capability:medical-qualification", "capability:electrical-safety", "capability:clinical-validation", "capability:imaging-quality"),
        },
        explanation="A non-ionizing imaging system that maps tissue using magnetic fields, gradients, and radio-frequency signals.",
        use_template="Use {name} for soft-tissue imaging, neurological studies, musculoskeletal diagnosis, and research protocols.",
        status="INDIA_IMPORT_DEPENDENT_OR_QUALIFICATION_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Service/assembly activity is not evidence of magnet, gradient, RF, cryogenic, or qualified system autonomy.",
        gaps=("superconducting magnet and cryogenic subsystem", "gradient/RF chain and image reconstruction", "clinical qualification, service, and uptime"),
        focus=("capability:medical-imaging", "capability:medical-qualification"),
        downstream=("capability:clinical-diagnostics", "capability:medical-research"),
        related=("ct-scanner", "ultrasound-system", "medical-device-assembly"),
    ),
    _archetype(
        "ct-scanner", "computed tomography scanner", ("CT scanner", "computed tomography"),
        kind="instrument", category="medical imaging", profile="imaging",
        dependencies={
            "design": ("capability:medical-device-design", "capability:medical-imaging", "capability:clinical-protocols"),
            "process": ("process:precision-machining", "process:electronics-assembly", "process:medical-device-assembly", "process:calibration"),
            "material": ("material:aluminum", "material:stainless-steel", "material:semiconductor", "material:shielding-material"),
            "equipment": ("equipment:x-ray-tube", "equipment:detector-array", "equipment:motion-stage", "equipment:metrology-cmm"),
            "quality": ("capability:medical-qualification", "capability:radiation-safety", "capability:imaging-quality", "capability:clinical-validation"),
        },
        explanation="A rotating X-ray imaging system that reconstructs cross-sectional anatomy from measured attenuation.",
        use_template="Use {name} for rapid cross-sectional imaging, trauma, oncology, and interventional planning.",
        status="INDIA_IMPORT_DEPENDENT_OR_QUALIFICATION_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Assembly and service are not treated as proof of tube, detector, motion, or imaging-chain depth.",
        gaps=("X-ray tube, detector, and high-voltage generator", "gantry motion and dose control", "image-quality, radiation, and clinical qualification"),
        focus=("capability:medical-imaging", "capability:medical-qualification"),
        downstream=("capability:clinical-diagnostics", "capability:medical-research"),
        related=("mri-system", "x-ray-system", "ultrasound-system"),
    ),
    _archetype(
        "x-ray-system", "digital X-ray radiography system", ("X-ray system", "digital radiography"),
        kind="instrument", category="medical imaging", profile="imaging",
        dependencies={
            "design": ("capability:medical-device-design", "capability:medical-imaging"),
            "process": ("process:electronics-assembly", "process:medical-device-assembly", "process:calibration", "process:shielding-installation"),
            "material": ("material:aluminum", "material:stainless-steel", "material:semiconductor", "material:shielding-material"),
            "equipment": ("equipment:x-ray-tube", "equipment:flat-panel-detector", "equipment:high-voltage-generator"),
            "quality": ("capability:radiation-safety", "capability:imaging-quality", "capability:medical-qualification"),
        },
        explanation="A projection-imaging system that converts controlled X-rays into diagnostic digital images.",
        use_template="Use {name} for radiography where compact workflow, dose management, and repeatable image quality matter.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Broad use and assembly do not prove local detector, tube, high-voltage, or clinical qualification depth.",
        gaps=("detector, tube, and high-voltage chain", "dose/image-quality calibration", "radiation safety and service reliability"),
        focus=("capability:medical-imaging", "capability:medical-qualification"),
        downstream=("capability:clinical-diagnostics", "capability:medical-logistics"),
        related=("ct-scanner", "ultrasound-system", "mri-system"),
    ),
    _archetype(
        "ultrasound-system", "diagnostic ultrasound system", ("ultrasound", "sonography system"),
        kind="instrument", category="medical imaging", profile="imaging",
        dependencies={
            "design": ("capability:medical-device-design", "capability:medical-imaging", "capability:embedded-control"),
            "process": ("process:electronics-assembly", "process:transducer-assembly", "process:medical-device-assembly", "process:calibration"),
            "material": ("material:piezoelectric-ceramic", "material:engineering-polymer", "material:stainless-steel", "material:control-electronics"),
            "equipment": ("equipment:transducer-test-system", "equipment:electronics-test-bench", "equipment:metrology-cmm"),
            "quality": ("capability:imaging-quality", "capability:medical-qualification", "capability:electrical-safety"),
        },
        explanation="A non-ionizing imaging platform that uses acoustic transducers to visualize tissue and flow.",
        use_template="Use {name} for bedside, obstetric, cardiac, vascular, and point-of-care imaging workflows.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="System use does not establish transducer materials, beamforming electronics, or qualified image quality.",
        gaps=("transducer fabrication and matching layers", "beamforming and signal chain", "probe reliability, calibration, and clinical qualification"),
        focus=("capability:medical-imaging", "capability:medical-electronics"),
        downstream=("capability:clinical-diagnostics", "capability:point-of-care"),
        related=("mri-system", "x-ray-system", "patient-monitor"),
    ),
    _archetype(
        "pet-spect-system", "PET/SPECT nuclear imaging system", ("PET scanner", "SPECT scanner"),
        kind="instrument", category="medical imaging", profile="imaging",
        dependencies={
            "design": ("capability:medical-device-design", "capability:nuclear-imaging", "capability:clinical-protocols"),
            "process": ("process:detector-assembly", "process:electronics-assembly", "process:medical-device-assembly", "process:calibration"),
            "material": ("material:scintillator", "material:semiconductor", "material:shielding-material", "material:stainless-steel"),
            "equipment": ("equipment:detector-array", "equipment:coincidence-electronics", "equipment:metrology-cmm", "equipment:environmental-test-chamber"),
            "quality": ("capability:radiation-safety", "capability:imaging-quality", "capability:medical-qualification", "capability:clinical-validation"),
        },
        explanation="A detector system that maps radiotracer distribution for functional and metabolic imaging.",
        use_template="Use {name} for oncology, neurology, cardiology, and research applications requiring functional imaging.",
        status="INDIA_IMPORT_DEPENDENT_OR_QUALIFICATION_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Detector, scintillator, radiotracer, and clinical qualification depth are not resolved here.",
        gaps=("detector/scintillator and coincidence chain", "radiotracer logistics and radiation controls", "clinical image-quality and uptime evidence"),
        focus=("capability:nuclear-imaging", "capability:medical-qualification"),
        downstream=("capability:clinical-diagnostics", "capability:medical-research"),
        related=("mri-system", "ct-scanner", "radiotherapy-linac"),
    ),
    _archetype(
        "radiotherapy-linac", "medical linear accelerator", ("radiotherapy linac", "LINAC"),
        kind="equipment", category="radiotherapy", profile="imaging",
        dependencies={
            "design": ("capability:medical-device-design", "capability:accelerator-engineering", "capability:radiation-therapy"),
            "process": ("process:precision-machining", "process:vacuum-processing", "process:electronics-assembly", "process:calibration"),
            "material": ("material:copper", "material:tungsten", "material:stainless-steel", "material:shielding-material"),
            "equipment": ("equipment:rf-power-system", "equipment:vacuum-system", "equipment:beam-monitor", "equipment:metrology-cmm"),
            "quality": ("capability:radiation-safety", "capability:medical-qualification", "capability:dosimetry", "capability:clinical-validation"),
        },
        explanation="A high-energy accelerator that generates therapeutic radiation under tightly controlled dose and geometry.",
        use_template="Use {name} for external-beam radiation therapy with validated dose, targeting, and safety interlocks.",
        status="INDIA_IMPORT_DEPENDENT_OR_QUALIFICATION_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Installed clinical systems do not prove accelerator, RF, vacuum, dosimetry, or service autonomy.",
        gaps=("accelerator/RF/vacuum subsystem", "beam monitoring and dosimetry", "regulatory, clinical, and uptime qualification"),
        focus=("capability:medical-qualification", "capability:precision-machining"),
        downstream=("capability:cancer-care", "capability:medical-research"),
        related=("pet-spect-system", "x-ray-system", "mri-system"),
    ),
    _archetype(
        "surgical-robot", "robotic surgical system", ("surgical robot", "robot-assisted surgery system"),
        kind="equipment", category="medical robotics", profile="robot",
        dependencies={
            "design": ("capability:medical-device-design", "capability:robotics", "capability:clinical-protocols"),
            "process": ("process:precision-machining", "process:robot-calibration", "process:sterilisation", "process:medical-device-assembly"),
            "material": ("material:stainless-steel", "material:titanium", "material:engineering-polymer", "material:precision-bearing"),
            "equipment": ("equipment:servo-motor", "equipment:servo-drive", "equipment:force-torque-sensor", "equipment:metrology-tracker"),
            "quality": ("capability:medical-qualification", "capability:functional-safety", "capability:clinical-validation", "capability:sterile-barrier"),
        },
        explanation="A force- and motion-controlled surgical platform that translates clinician commands into precise instrument motion.",
        use_template="Use {name} where dexterity, tremor reduction, visualization, and repeatable instrument positioning matter.",
        status="INDIA_EMERGING_OR_LIMITED", status_epistemic="MODELLED",
        status_basis="Emerging strategic label; sterile interfaces, safety, clinical evidence, and qualified production remain unknown.",
        gaps=("medical-grade precision motion and sensing", "sterilizable instruments and safety architecture", "clinical, regulatory, and service qualification"),
        focus=("capability:medical-robotics", "capability:medical-qualification"),
        downstream=("capability:surgical-care", "capability:medical-instruments"),
        related=("industrial-robot", "mri-system", "sterile-fill-finish-line"),
    ),
    _archetype(
        "anesthesia-workstation", "anesthesia workstation", ("anesthesia machine", "anesthesia system"),
        kind="equipment", category="critical care equipment", profile="imaging",
        dependencies={
            "design": ("capability:medical-device-design", "capability:gas-systems", "capability:embedded-control"),
            "process": ("process:medical-device-assembly", "process:gas-path-cleaning", "process:calibration", "process:electronics-assembly"),
            "material": ("material:stainless-steel", "material:engineering-polymer", "material:seal-material", "material:medical-gas"),
            "equipment": ("equipment:gas-mixer", "equipment:flow-sensor", "equipment:electronics-test-bench", "equipment:pressure-test-bench"),
            "quality": ("capability:medical-qualification", "capability:gas-safety", "capability:electrical-safety", "capability:clinical-validation"),
        },
        explanation="A controlled gas delivery and monitoring system supporting anesthesia and ventilation during procedures.",
        use_template="Use {name} to blend, deliver, humidify, and monitor medical gases under clinician supervision.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Use/assembly is not treated as evidence of gas-path, sensor, software, or clinical qualification depth.",
        gaps=("flow/pressure sensing and gas-mixing accuracy", "cleanable gas path and alarm validation", "clinical, electrical, and service qualification"),
        focus=("capability:medical-equipment", "capability:gas-systems"),
        downstream=("capability:critical-care", "capability:surgical-care"),
        related=("ventilator", "patient-monitor", "medical-oxygen-concentrator"),
    ),
    _archetype(
        "ventilator", "mechanical ventilator", ("ventilator", "critical-care ventilator"),
        kind="equipment", category="critical care equipment", profile="imaging",
        dependencies={
            "design": ("capability:medical-device-design", "capability:fluid-control", "capability:embedded-control"),
            "process": ("process:medical-device-assembly", "process:gas-path-cleaning", "process:calibration", "process:electronics-assembly"),
            "material": ("material:engineering-polymer", "material:stainless-steel", "material:seal-material", "material:medical-gas"),
            "equipment": ("equipment:flow-sensor", "equipment:pressure-test-bench", "equipment:electronics-test-bench", "equipment:gas-mixer"),
            "quality": ("capability:medical-qualification", "capability:electrical-safety", "capability:clinical-validation", "capability:software-validation"),
        },
        explanation="A closed-loop gas-flow machine that supports or replaces spontaneous breathing under clinical protocols.",
        use_template="Use {name} for controlled ventilation where pressure, volume, oxygen, alarms, and patient safety must be validated.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Assembly and crisis supply are not proof of long-term clinical, sensor, software, or service qualification.",
        gaps=("flow/pressure control and alarm coverage", "gas-path cleanliness and sterilization", "clinical validation, reliability, and field service"),
        focus=("capability:medical-equipment", "capability:embedded-control"),
        downstream=("capability:critical-care", "capability:emergency-care"),
        related=("anesthesia-workstation", "patient-monitor", "medical-oxygen-concentrator"),
    ),
    _archetype(
        "patient-monitor", "multiparameter patient monitor", ("patient monitor", "bedside monitor"),
        kind="instrument", category="critical care equipment", profile="lab",
        dependencies={
            "design": ("capability:medical-device-design", "capability:biomedical-signal-processing", "capability:embedded-control"),
            "process": ("process:electronics-assembly", "process:medical-device-assembly", "process:calibration", "process:software-validation"),
            "material": ("material:control-electronics", "material:engineering-polymer", "material:stainless-steel", "material:medical-sensors"),
            "equipment": ("equipment:electronics-test-bench", "equipment:signal-simulator", "equipment:environmental-test-chamber"),
            "quality": ("capability:medical-qualification", "capability:electrical-safety", "capability:clinical-validation", "capability:software-validation"),
        },
        explanation="A bedside measurement platform that displays and alarms on physiological signals and vital signs.",
        use_template="Use {name} to observe, trend, and alarm on vital signs in wards, operating rooms, and intensive care.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="System assembly/use is not evidence of sensor, algorithm, software, or clinical qualification depth.",
        gaps=("sensor and signal-chain accuracy", "alarm logic and cybersecurity", "clinical validation, service, and consumables"),
        focus=("capability:medical-electronics", "capability:medical-qualification"),
        downstream=("capability:critical-care", "capability:remote-monitoring"),
        related=("ventilator", "infusion-pump", "ultrasound-system"),
    ),
    _archetype(
        "infusion-pump", "medical infusion pump", ("infusion pump", "syringe pump"),
        kind="equipment", category="drug delivery equipment", profile="lab",
        dependencies={
            "design": ("capability:medical-device-design", "capability:fluid-control", "capability:embedded-control"),
            "process": ("process:precision-machining", "process:medical-device-assembly", "process:calibration", "process:software-validation"),
            "material": ("material:engineering-polymer", "material:stainless-steel", "material:seal-material", "material:control-electronics"),
            "equipment": ("equipment:servo-motor", "equipment:flow-sensor", "equipment:electronics-test-bench", "equipment:pressure-test-bench"),
            "quality": ("capability:medical-qualification", "capability:electrical-safety", "capability:flow-accuracy-testing", "capability:software-validation"),
        },
        explanation="A metered fluid-delivery system that administers medicines or nutrition at controlled rates and volumes.",
        use_template="Use {name} where dose accuracy, alarm handling, occlusion detection, and traceability matter.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Product use/assembly does not establish actuator, sensor, software, or clinical qualification depth.",
        gaps=("flow accuracy and occlusion detection", "disposable set compatibility", "software, alarm, and clinical validation"),
        focus=("capability:medical-equipment", "capability:fluid-control"),
        downstream=("capability:critical-care", "capability:home-care"),
        related=("patient-monitor", "dialysis-machine", "sterile-fill-finish-line"),
    ),
    _archetype(
        "dialysis-machine", "hemodialysis machine", ("dialysis machine", "renal replacement system"),
        kind="equipment", category="renal care equipment", profile="process",
        dependencies={
            "design": ("capability:medical-device-design", "capability:fluid-control", "capability:water-treatment"),
            "process": ("process:medical-device-assembly", "process:water-purification", "process:calibration", "process:sterilisation"),
            "material": ("material:stainless-steel", "material:engineering-polymer", "material:membrane", "material:medical-water"),
            "equipment": ("equipment:industrial-pump", "equipment:flow-sensor", "equipment:water-purification-system", "equipment:electronics-test-bench"),
            "quality": ("capability:medical-qualification", "capability:water-quality", "capability:clinical-validation", "capability:electrical-safety"),
        },
        explanation="A controlled extracorporeal fluid and membrane system that removes waste and balances patient fluids.",
        use_template="Use {name} for renal replacement therapy where fluid, membrane, pressure, and disinfection controls must be validated.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Clinical availability is not evidence of domestic membrane, pump, sensor, water, or qualification depth.",
        gaps=("dialyzer and membrane supply", "ultrapure water, pump, and pressure control", "clinical, disinfection, and service qualification"),
        focus=("capability:medical-equipment", "capability:water-treatment"),
        downstream=("capability:renal-care", "capability:medical-consumables"),
        related=("infusion-pump", "centrifugal-pump", "water-purification-system"),
    ),
    _archetype(
        "autoclave", "steam sterilizer/autoclave", ("autoclave", "steam sterilizer"),
        kind="equipment", category="sterilization equipment", profile="sterile",
        dependencies={
            "design": ("capability:medical-device-design", "capability:sterilisation-engineering", "capability:pressure-systems"),
            "process": ("process:pressure-vessel-fabrication", "process:welding", "process:steam-sterilisation", "process:calibration"),
            "material": ("material:stainless-steel", "material:seal-material", "material:insulation-material", "material:process-water"),
            "equipment": ("equipment:steam-generator", "equipment:industrial-pump", "equipment:pressure-test-bench", "equipment:temperature-control"),
            "quality": ("capability:sterilisation-validation", "capability:pressure-boundary-qualification", "capability:medical-qualification", "capability:metrology"),
        },
        explanation="A validated pressure-steam system for sterilizing instruments, media, components, and laboratory loads.",
        use_template="Use {name} to deliver repeatable sterilization cycles with traceable temperature, pressure, and load records.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Equipment availability is not proof of pressure-boundary, cycle, or validation depth.",
        gaps=("pressure vessel and door-seal integrity", "load mapping and cycle validation", "steam quality, calibration, and service"),
        focus=("capability:sterilisation", "capability:pressure-systems"),
        downstream=("capability:medical-equipment", "capability:bioprocessing", "capability:pharma-manufacturing"),
        related=("freeze-dryer", "biosafety-cabinet", "sterile-fill-finish-line"),
    ),
    _archetype(
        "lab-centrifuge", "laboratory centrifuge", ("lab centrifuge", "centrifugal separator"),
        kind="instrument", category="laboratory equipment", profile="lab",
        dependencies={
            "design": ("capability:instrument-design", "capability:rotordynamics", "capability:lab-operations"),
            "process": ("process:precision-machining", "process:rotor-balancing", "process:electronics-assembly", "process:calibration"),
            "material": ("material:stainless-steel", "material:engineering-polymer", "material:precision-bearing", "material:control-electronics"),
            "equipment": ("equipment:dynamic-balancer", "equipment:servo-motor", "equipment:electronics-test-bench", "equipment:temperature-control"),
            "quality": ("capability:rotordynamics", "capability:lab-qualification", "capability:metrology", "capability:electrical-safety"),
        },
        explanation="A controlled rotating instrument that separates samples by density, sedimentation, or phase behavior.",
        use_template="Use {name} to prepare, separate, concentrate, or clarify biological, chemical, and diagnostic samples.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Laboratory use is broad; rotor, bearing, control, temperature, and qualified speed envelopes are unknown.",
        gaps=("rotor balance and containment", "speed/temperature control and safety interlocks", "life testing and service/consumables"),
        focus=("capability:lab-equipment", "capability:rotordynamics"),
        downstream=("capability:diagnostics", "capability:bioprocessing", "capability:pharma-research"),
        related=("bioreactor", "flow-cytometer", "freeze-dryer"),
    ),
    _archetype(
        "freeze-dryer", "pharmaceutical freeze dryer/lyophilizer", ("freeze dryer", "lyophilizer"),
        kind="equipment", category="pharma process equipment", profile="sterile",
        dependencies={
            "design": ("capability:pharma-process-design", "capability:vacuum-engineering", "capability:thermal-systems-design"),
            "process": ("process:freezing", "process:vacuum-drying", "process:sterile-filling", "process:clean-in-place"),
            "material": ("material:stainless-steel", "material:seal-material", "material:refrigerant", "material:process-water"),
            "equipment": ("equipment:vacuum-system", "equipment:industrial-compressor", "equipment:heat-exchanger", "equipment:temperature-control"),
            "quality": ("capability:aseptic-qualification", "capability:process-validation", "capability:thermal-uniformity-testing", "capability:quality-system"),
        },
        explanation="A vacuum and temperature-controlled dryer that removes ice from sensitive products while preserving structure.",
        use_template="Use {name} to stabilize vaccines, biologics, injectables, cultures, and temperature-sensitive formulations.",
        status="INDIA_IMPORT_DEPENDENT_OR_QUALIFICATION_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Equipment category is visible, but chamber, refrigeration, vacuum, recipe, and validation depth remain unknown.",
        gaps=("shelf/chamber thermal uniformity", "vacuum/refrigeration capacity and control", "aseptic loading, recipe validation, and service"),
        focus=("capability:pharma-equipment", "process:lyophilization"),
        downstream=("capability:biologics", "capability:vaccine-manufacturing", "capability:sterile-pharma"),
        related=("autoclave", "sterile-fill-finish-line", "bioreactor"),
    ),
    _archetype(
        "hplc-system", "high-performance liquid chromatography system", ("HPLC", "liquid chromatograph"),
        kind="instrument", category="analytical instruments", profile="lab",
        dependencies={
            "design": ("capability:analytical-instrument-design", "capability:separation-science"),
            "process": ("process:precision-machining", "process:electronics-assembly", "process:fluidic-assembly", "process:calibration"),
            "material": ("material:stainless-steel", "material:engineering-polymer", "material:glass", "material:seal-material"),
            "equipment": ("equipment:precision-pump", "equipment:detector-module", "equipment:electronics-test-bench", "equipment:temperature-control"),
            "quality": ("capability:analytical-validation", "capability:trace-impurity-analysis", "capability:metrology", "capability:software-validation"),
        },
        explanation="A pressure-driven separation and detection system for identifying and quantifying dissolved compounds.",
        use_template="Use {name} for pharmaceutical assay, impurity, food, chemical, and research measurements.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Laboratory use is not evidence of pump, detector, column, software, or validated analytical depth.",
        gaps=("low-pulsation pump and injector", "detector, column chemistry, and fluidic cleanliness", "method validation and traceable calibration"),
        focus=("capability:analytical-instruments", "capability:metrology"),
        downstream=("capability:pharma-quality", "capability:food-quality", "capability:chemical-quality"),
        related=("lc-ms-system", "gc-ms-system", "microplate-reader"),
    ),
    _archetype(
        "lc-ms-system", "liquid chromatography mass spectrometry system", ("LC-MS", "liquid chromatograph mass spectrometer"),
        kind="instrument", category="analytical instruments", profile="lab",
        dependencies={
            "design": ("capability:analytical-instrument-design", "capability:mass-spectrometry", "capability:separation-science"),
            "process": ("process:precision-machining", "process:vacuum-processing", "process:electronics-assembly", "process:calibration"),
            "material": ("material:stainless-steel", "material:engineering-polymer", "material:vacuum-material", "material:control-electronics"),
            "equipment": ("equipment:precision-pump", "equipment:mass-analyser", "equipment:vacuum-system", "equipment:electronics-test-bench"),
            "quality": ("capability:analytical-validation", "capability:mass-calibration", "capability:vacuum-engineering", "capability:software-validation"),
        },
        explanation="A coupled separation and mass-analysis platform for sensitive chemical and biomolecular identification.",
        use_template="Use {name} for trace analysis, biologics characterization, metabolomics, contaminants, and forensic chemistry.",
        status="INDIA_IMPORT_DEPENDENT_OR_QUALIFICATION_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Instrument use is not treated as evidence of mass analyzer, vacuum, source, or validated analytical depth.",
        gaps=("mass analyzer/source and vacuum stack", "ion optics, detector, and software", "calibration, method validation, and service"),
        focus=("capability:analytical-instruments", "capability:mass-spectrometry"),
        downstream=("capability:pharma-quality", "capability:biotech-research", "capability:food-quality"),
        related=("hplc-system", "gc-ms-system", "flow-cytometer"),
    ),
    _archetype(
        "gc-ms-system", "gas chromatography mass spectrometry system", ("GC-MS", "gas chromatograph mass spectrometer"),
        kind="instrument", category="analytical instruments", profile="lab",
        dependencies={
            "design": ("capability:analytical-instrument-design", "capability:mass-spectrometry", "capability:separation-science"),
            "process": ("process:precision-machining", "process:vacuum-processing", "process:electronics-assembly", "process:calibration"),
            "material": ("material:stainless-steel", "material:glass", "material:vacuum-material", "material:control-electronics"),
            "equipment": ("equipment:mass-analyser", "equipment:vacuum-system", "equipment:temperature-control", "equipment:electronics-test-bench"),
            "quality": ("capability:analytical-validation", "capability:mass-calibration", "capability:chemical-quality", "capability:software-validation"),
        },
        explanation="A vapor-phase separation and mass-analysis platform for volatile and semi-volatile compounds.",
        use_template="Use {name} for solvents, residues, fuels, flavors, environmental samples, and forensic measurements.",
        status="INDIA_IMPORT_DEPENDENT_OR_QUALIFICATION_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Laboratory availability is not evidence of column, source, vacuum, detector, or validated service depth.",
        gaps=("column and inlet control", "mass analyzer/vacuum stack", "method validation and calibration traceability"),
        focus=("capability:analytical-instruments", "capability:mass-spectrometry"),
        downstream=("capability:chemical-quality", "capability:food-quality", "capability:environmental-testing"),
        related=("hplc-system", "lc-ms-system", "microplate-reader"),
    ),
    _archetype(
        "prep-chromatography-skid", "preparative chromatography skid", ("prep chromatography", "chromatography skid"),
        kind="equipment", category="bioprocess equipment", profile="bioprocess",
        dependencies={
            "design": ("capability:bioprocess-engineering", "capability:separation-science"),
            "process": ("process:chromatography", "process:fluidic-assembly", "process:clean-in-place", "process:calibration"),
            "material": ("material:stainless-steel", "material:single-use-polymer", "material:chromatography-resin", "material:process-water"),
            "equipment": ("equipment:precision-pump", "equipment:valve-manifold", "equipment:uv-detector", "equipment:control-system"),
            "quality": ("capability:bioprocess-validation", "capability:aseptic-qualification", "capability:analytical-validation", "capability:quality-system"),
        },
        explanation="A skid-mounted separation system that purifies proteins, vaccines, enzymes, and other biologics.",
        use_template="Use {name} to capture, wash, elute, and monitor biologic products within a validated process train.",
        status="INDIA_IMPORT_DEPENDENT_OR_QUALIFICATION_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Bioprocess use does not establish resin, pump, sensor, single-use, or validated scale depth.",
        gaps=("resin and membrane supply", "low-shear flow and aseptic fluidics", "process validation and resin lifecycle"),
        focus=("capability:bioprocessing", "process:chromatography"),
        downstream=("capability:biologics", "capability:vaccine-manufacturing", "capability:pharma-quality"),
        related=("bioreactor", "single-use-bioprocess-system", "freeze-dryer"),
    ),
    _archetype(
        "pcr-system", "PCR/qPCR instrument", ("PCR machine", "qPCR system"),
        kind="instrument", category="molecular diagnostics", profile="lab",
        dependencies={
            "design": ("capability:medical-device-design", "capability:molecular-diagnostics", "capability:embedded-control"),
            "process": ("process:electronics-assembly", "process:thermal-cycling", "process:medical-device-assembly", "process:calibration"),
            "material": ("material:engineering-polymer", "material:semiconductor", "material:optical-material", "material:control-electronics"),
            "equipment": ("equipment:thermal-cycling-chamber", "equipment:optical-detector", "equipment:electronics-test-bench", "equipment:metrology-cmm"),
            "quality": ("capability:diagnostic-quality", "capability:analytical-validation", "capability:software-validation", "capability:medical-qualification"),
        },
        explanation="A temperature-cycling and fluorescence-detection instrument for amplifying and measuring nucleic-acid targets.",
        use_template="Use {name} for molecular diagnostics, pathogen testing, genetics, research, and quality-control assays.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Assembly/use is not proof of thermal uniformity, optics, software, reagent, or diagnostic qualification.",
        gaps=("thermal uniformity and optical detection", "software/algorithm and contamination control", "diagnostic validation and reagent ecosystem"),
        focus=("capability:molecular-diagnostics", "capability:medical-electronics"),
        downstream=("capability:clinical-diagnostics", "capability:biotech-research", "capability:food-safety"),
        related=("sequencing-instrument", "microplate-reader", "lab-centrifuge"),
    ),
    _archetype(
        "sequencing-instrument", "next-generation sequencing instrument", ("sequencer", "NGS instrument"),
        kind="instrument", category="molecular biology equipment", profile="lab",
        dependencies={
            "design": ("capability:genomics-instrumentation", "capability:molecular-diagnostics", "capability:optical-engineering"),
            "process": ("process:electronics-assembly", "process:fluidic-assembly", "process:precision-machining", "process:calibration"),
            "material": ("material:semiconductor", "material:optical-material", "material:engineering-polymer", "material:single-use-polymer"),
            "equipment": ("equipment:optical-detector", "equipment:precision-pump", "equipment:machine-vision", "equipment:electronics-test-bench"),
            "quality": ("capability:analytical-validation", "capability:diagnostic-quality", "capability:software-validation", "capability:sample-preparation"),
        },
        explanation="A high-throughput molecular instrument that reads nucleic-acid sequences through cyclic biochemical and optical steps.",
        use_template="Use {name} for genomics, pathogen surveillance, precision medicine, agriculture, and research.",
        status="INDIA_IMPORT_DEPENDENT_OR_QUALIFICATION_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Instrument and reagent ecosystem depth is unresolved; no local throughput or supplier claim is made.",
        gaps=("flow cell, optics, and fluidic control", "reagent and consumable qualification", "bioinformatics, service, and assay validation"),
        focus=("capability:genomics-instrumentation", "capability:biotech-research"),
        downstream=("capability:clinical-diagnostics", "capability:biotech-research", "capability:agri-biotechnology"),
        related=("pcr-system", "flow-cytometer", "microplate-reader"),
    ),
    _archetype(
        "flow-cytometer", "flow cytometer", ("flow cytometry system", "cell analyzer"),
        kind="instrument", category="cell analysis", profile="lab",
        dependencies={
            "design": ("capability:optical-engineering", "capability:biomedical-signal-processing", "capability:cell-analysis"),
            "process": ("process:fluidic-assembly", "process:electronics-assembly", "process:optical-alignment", "process:calibration"),
            "material": ("material:optical-material", "material:engineering-polymer", "material:stainless-steel", "material:control-electronics"),
            "equipment": ("equipment:laser-source", "equipment:optical-detector", "equipment:precision-pump", "equipment:electronics-test-bench"),
            "quality": ("capability:analytical-validation", "capability:optical-metrology", "capability:software-validation", "capability:lab-qualification"),
        },
        explanation="An optical and fluidic instrument that measures physical and fluorescent properties of individual cells or particles.",
        use_template="Use {name} for immunophenotyping, cell therapy development, hematology, and biological research.",
        status="INDIA_IMPORT_DEPENDENT_OR_QUALIFICATION_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Optical alignment, fluidics, detector, reagent, and assay qualification depth are unknown.",
        gaps=("laser/optics and detector chain", "fluidic focusing and contamination control", "assay validation, software, and service"),
        focus=("capability:cell-analysis", "capability:optical-engineering"),
        downstream=("capability:biotech-research", "capability:cell-therapy", "capability:clinical-diagnostics"),
        related=("sequencing-instrument", "pcr-system", "lab-centrifuge"),
    ),
    _archetype(
        "research-microscope", "research optical microscope", ("research microscope", "advanced microscope"),
        kind="instrument", category="scientific instruments", profile="lab",
        dependencies={
            "design": ("capability:optical-engineering", "capability:instrument-design", "capability:image-analysis"),
            "process": ("process:optical-polishing", "process:precision-machining", "process:optical-alignment", "process:electronics-assembly"),
            "material": ("material:optical-glass", "material:engineering-polymer", "material:alloy-steel", "material:semiconductor"),
            "equipment": ("equipment:optical-detector", "equipment:precision-stage", "equipment:machine-vision", "equipment:metrology-cmm"),
            "quality": ("capability:optical-metrology", "capability:image-quality", "capability:instrument-qualification", "capability:software-validation"),
        },
        explanation="A precision optical platform that resolves, measures, and records structures at microscopic scales.",
        use_template="Use {name} for materials, biology, pathology, semiconductor inspection, and scientific investigation.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Instrument use does not establish optical fabrication, coatings, stages, detectors, or validated resolution.",
        gaps=("optical glass, coatings, and aberration control", "precision stage and vibration isolation", "image quality, calibration, and application software"),
        focus=("capability:optical-engineering", "capability:metrology"),
        downstream=("capability:medical-research", "capability:materials-research", "capability:semiconductor-inspection"),
        related=("flow-cytometer", "microplate-reader", "machine-vision-system"),
    ),
    _archetype(
        "microplate-reader", "microplate reader", ("plate reader", "microplate assay reader"),
        kind="instrument", category="laboratory equipment", profile="lab",
        dependencies={
            "design": ("capability:optical-engineering", "capability:instrument-design", "capability:biomedical-signal-processing"),
            "process": ("process:optical-alignment", "process:electronics-assembly", "process:precision-machining", "process:calibration"),
            "material": ("material:optical-material", "material:engineering-polymer", "material:semiconductor", "material:control-electronics"),
            "equipment": ("equipment:optical-detector", "equipment:precision-stage", "equipment:electronics-test-bench", "equipment:temperature-control"),
            "quality": ("capability:analytical-validation", "capability:optical-metrology", "capability:software-validation", "capability:lab-qualification"),
        },
        explanation="A multiwell optical measurement instrument for absorbance, fluorescence, luminescence, or kinetic assays.",
        use_template="Use {name} to run parallel biochemical, cell-based, pharmaceutical, and food assays.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Laboratory use is not evidence of optical, motion, thermal, or assay-validation depth.",
        gaps=("optical channel uniformity", "plate motion and temperature control", "calibration, assay validation, and consumables"),
        focus=("capability:analytical-instruments", "capability:optical-engineering"),
        downstream=("capability:biotech-research", "capability:pharma-research", "capability:food-quality"),
        related=("pcr-system", "research-microscope", "flow-cytometer"),
    ),
    _archetype(
        "lab-incubator", "laboratory incubator", ("lab incubator", "CO2 incubator"),
        kind="equipment", category="laboratory equipment", profile="process",
        dependencies={
            "design": ("capability:thermal-systems-design", "capability:lab-equipment-design", "capability:environmental-control"),
            "process": ("process:sheet-metal-fabrication", "process:electronics-assembly", "process:thermal-control", "process:calibration"),
            "material": ("material:stainless-steel", "material:engineering-polymer", "material:insulation-material", "material:glass"),
            "equipment": ("equipment:temperature-control", "equipment:humidity-control", "equipment:gas-sensor", "equipment:electronics-test-bench"),
            "quality": ("capability:thermal-uniformity-testing", "capability:lab-qualification", "capability:contamination-control", "capability:metrology"),
        },
        explanation="A controlled chamber that maintains temperature, atmosphere, humidity, or other conditions for biological growth.",
        use_template="Use {name} to culture cells, microbes, tissues, seedlings, or controlled biological experiments.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Chamber availability does not establish uniformity, contamination, gas control, or validated operation.",
        gaps=("temperature/CO2/humidity uniformity", "cleanability and contamination control", "sensor calibration and long-duration reliability"),
        focus=("capability:environmental-control", "capability:lab-equipment"),
        downstream=("capability:biotech-research", "capability:cell-therapy", "capability:agri-biotechnology"),
        related=("bioreactor", "biosafety-cabinet", "freeze-dryer"),
    ),
    _archetype(
        "bioreactor", "stirred-tank bioreactor", ("bioreactor", "fermenter"),
        kind="equipment", category="bioprocess equipment", profile="bioprocess",
        dependencies={
            "design": ("capability:bioprocess-engineering", "capability:fluid-machinery-design", "capability:process-control"),
            "process": ("process:precision-machining", "process:welding", "process:sterilisation", "process:clean-in-place"),
            "material": ("material:stainless-steel", "material:single-use-polymer", "material:seal-material", "material:process-water"),
            "equipment": ("equipment:industrial-motor", "equipment:industrial-pump", "equipment:gas-mixer", "equipment:control-system"),
            "quality": ("capability:bioprocess-validation", "capability:aseptic-qualification", "capability:process-analytics", "capability:quality-system"),
        },
        explanation="A controlled vessel that grows cells or microbes while managing mixing, gas transfer, heat, and nutrient conditions.",
        use_template="Use {name} to make biologics, enzymes, vaccines, fermentation products, and research cultures.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Bioprocess equipment presence is not evidence of sterile fabrication, control, yield, or validated scale.",
        gaps=("mixing, oxygen transfer, and shear control", "sterile boundary, sensors, and cleanability", "scale-up, process validation, and service"),
        focus=("capability:bioprocessing", "capability:process-control"),
        downstream=("capability:biologics", "capability:vaccine-manufacturing", "capability:food-fermentation"),
        related=("single-use-bioprocess-system", "prep-chromatography-skid", "freeze-dryer"),
    ),
    _archetype(
        "single-use-bioprocess-system", "single-use bioprocess system", ("single-use bioreactor", "disposable bioprocess train"),
        kind="equipment", category="bioprocess equipment", profile="bioprocess",
        dependencies={
            "design": ("capability:bioprocess-engineering", "capability:single-use-systems", "capability:process-control"),
            "process": ("process:film-forming", "process:fluidic-assembly", "process:sterilisation", "process:clean-room-assembly"),
            "material": ("material:single-use-polymer", "material:medical-grade-polymer", "material:seal-material", "material:process-water"),
            "equipment": ("equipment:precision-pump", "equipment:control-system", "equipment:thermal-control", "equipment:integrity-test-system"),
            "quality": ("capability:single-use-validation", "capability:extractables-leachables-testing", "capability:aseptic-qualification", "capability:quality-system"),
        },
        explanation="A disposable or hybrid fluid path that reduces cleaning burden and supports flexible biologic production.",
        use_template="Use {name} for multiproduct, clinical, or contamination-sensitive bioprocessing where rapid changeover matters.",
        status="INDIA_IMPORT_DEPENDENT_OR_QUALIFICATION_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Polymer film, bag, connector, sensor, and extractables qualification depth are unknown.",
        gaps=("film/connector and sensor supply", "integrity, extractables, and leachables qualification", "aseptic assembly and disposal route"),
        focus=("capability:bioprocessing", "capability:single-use-systems"),
        downstream=("capability:biologics", "capability:cell-therapy", "capability:vaccine-manufacturing"),
        related=("bioreactor", "prep-chromatography-skid", "sterile-fill-finish-line"),
    ),
    _archetype(
        "cell-therapy-isolator", "cell-therapy processing isolator", ("cell therapy isolator", "aseptic isolator"),
        kind="equipment", category="advanced bioprocess equipment", profile="sterile",
        dependencies={
            "design": ("capability:cell-therapy-processing", "capability:aseptic-engineering", "capability:cleanroom-design"),
            "process": ("process:clean-room-assembly", "process:sterilisation", "process:fluidic-assembly", "process:calibration"),
            "material": ("material:stainless-steel", "material:medical-grade-polymer", "material:glove-material", "material:filter-media"),
            "equipment": ("equipment:isolator", "equipment:gas-purification", "equipment:precision-pump", "equipment:environmental-monitoring"),
            "quality": ("capability:aseptic-qualification", "capability:environmental-monitoring", "capability:cell-therapy-validation", "capability:quality-system"),
        },
        explanation="A controlled barrier enclosure for manipulating cells under aseptic, monitored, and reproducible conditions.",
        use_template="Use {name} to protect cell products and operators during closed or semi-closed advanced therapy workflows.",
        status="INDIA_EMERGING_OR_LIMITED", status_epistemic="MODELLED",
        status_basis="Emerging label reflects high qualification burden; no facility or product maturity is asserted.",
        gaps=("barrier integrity and decontamination", "environmental monitoring and aseptic process", "cell-product validation and operator training"),
        focus=("capability:cell-therapy", "capability:aseptic-processing"),
        downstream=("capability:advanced-therapies", "capability:biologics"),
        related=("single-use-bioprocess-system", "biosafety-cabinet", "sterile-fill-finish-line"),
    ),
    _archetype(
        "pharma-solid-dose-line", "pharmaceutical solid-dose processing line", ("tablet press line", "capsule filling line"),
        kind="equipment", category="pharma process equipment", profile="sterile",
        dependencies={
            "design": ("capability:pharma-process-design", "capability:powder-processing", "capability:process-control"),
            "process": ("process:granulation", "process:tablet-compression", "process:capsule-filling", "process:coating"),
            "material": ("material:stainless-steel", "material:tool-steel", "material:engineering-polymer", "material:pharma-excipients"),
            "equipment": ("equipment:tablet-press", "equipment:powder-mixer", "equipment:coating-pan", "equipment:metal-detector"),
            "quality": ("capability:good-manufacturing-practice", "capability:process-validation", "capability:content-uniformity-testing", "capability:quality-system"),
        },
        explanation="A coordinated powder-to-dose line for blending, granulating, compressing, encapsulating, coating, and inspecting medicines.",
        use_template="Use {name} to produce repeatable solid oral doses with controlled weight, uniformity, coating, and traceability.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Pharma manufacturing breadth is not evidence of equipment design, tooling, validation, or product qualification depth.",
        gaps=("powder flow, tooling wear, and dose uniformity", "cleanability and changeover", "validated process, inspection, and serialization"),
        focus=("capability:pharma-equipment", "process:tablet-compression"),
        downstream=("capability:pharmaceuticals", "capability:generic-drugs", "capability:packaging-machinery"),
        related=("sterile-fill-finish-line", "freeze-dryer", "packaging-machinery"),
    ),
    _archetype(
        "sterile-fill-finish-line", "sterile pharmaceutical fill-finish line", ("aseptic filling line", "sterile fill-finish"),
        kind="equipment", category="pharma process equipment", profile="sterile",
        dependencies={
            "design": ("capability:pharma-process-design", "capability:aseptic-engineering", "capability:process-control"),
            "process": ("process:sterile-filling", "process:container-closure", "process:sterilisation", "process:visual-inspection"),
            "material": ("material:stainless-steel", "material:medical-grade-polymer", "material:glass", "material:seal-material"),
            "equipment": ("equipment:isolator", "equipment:fill-pump", "equipment:machine-vision", "equipment:lyophilizer"),
            "quality": ("capability:aseptic-qualification", "capability:process-validation", "capability:visual-inspection", "capability:good-manufacturing-practice"),
        },
        explanation="A controlled line for sterile product filling, stoppering, sealing, inspection, and packaging.",
        use_template="Use {name} to convert sterile bulk product into validated injectable or biologic presentations.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Pharma production is not proof of line-level aseptic, isolator, inspection, or qualification autonomy.",
        gaps=("aseptic barrier and fill accuracy", "container closure and visual inspection", "media fills, process validation, and service"),
        focus=("capability:pharma-equipment", "process:sterile-filling"),
        downstream=("capability:injectables", "capability:vaccine-manufacturing", "capability:biologics"),
        related=("freeze-dryer", "autoclave", "cell-therapy-isolator"),
    ),
)


FOOD_ARCHETYPES = (
    _archetype(
        "grain-mill", "grain milling system", ("grain mill", "cereal milling line"),
        kind="equipment", category="food processing", profile="food",
        dependencies={
            "design": ("capability:food-process-engineering", "capability:mechanical-design"),
            "process": ("process:cleaning", "process:dehulling", "process:grinding", "process:sifting"),
            "material": ("material:stainless-steel", "material:food-grade-polymer", "material:tool-steel", "material:grain-feedstock"),
            "equipment": ("equipment:roller-mill", "equipment:centrifugal-pump", "equipment:conveyor", "equipment:food-sieve"),
            "quality": ("capability:food-safety", "capability:hygienic-design", "capability:particle-size-control"),
        },
        explanation="A process train that cleans, dehulls, grinds, classifies, and conveys cereal or grain products.",
        use_template="Use {name} to turn grain feedstock into controlled flour, meal, grits, or feed fractions.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Food-processing presence is broad; hygienic design, yield, and equipment depth are not adjudicated.",
        gaps=("wear and contamination control", "particle-size and moisture management", "validated food safety and throughput"),
        focus=("capability:food-processing", "process:grinding"),
        downstream=("capability:flour-products", "capability:animal-feed", "capability:food-packaging"),
        related=("rice-mill", "pulse-oilseed-mill", "feed-mill"),
    ),
    _archetype(
        "rice-mill", "rice milling system", ("rice mill", "paddy processing line"),
        kind="equipment", category="food processing", profile="food",
        dependencies={
            "design": ("capability:food-process-engineering", "capability:mechanical-design"),
            "process": ("process:cleaning", "process:dehulling", "process:polishing", "process:grading"),
            "material": ("material:stainless-steel", "material:food-grade-polymer", "material:abrasive-material", "material:rice-feedstock"),
            "equipment": ("equipment:dehusker", "equipment:polisher", "equipment:optical-sorter", "equipment:conveyor"),
            "quality": ("capability:food-safety", "capability:grain-quality", "capability:process-control"),
        },
        explanation="A coordinated line that removes husk, polishes, grades, and sorts rice with controlled breakage.",
        use_template="Use {name} to convert paddy into graded rice, bran, husk, and marketable by-products.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Industry activity is not proof of low-breakage design, optical sorting, or qualified local machinery depth.",
        gaps=("husk/bran separation and breakage control", "optical sorting and moisture control", "wear, hygiene, and service ecosystem"),
        focus=("capability:food-processing", "process:dehulling"),
        downstream=("capability:rice-products", "capability:food-packaging", "capability:animal-feed"),
        related=("grain-mill", "pulse-oilseed-mill", "grain-dryer"),
    ),
    _archetype(
        "pulse-oilseed-mill", "pulse and oilseed processing line", ("pulse mill", "oilseed mill"),
        kind="equipment", category="food processing", profile="food",
        dependencies={
            "design": ("capability:food-process-engineering", "capability:mechanical-design"),
            "process": ("process:cleaning", "process:dehulling", "process:flaking", "process:pressing"),
            "material": ("material:stainless-steel", "material:food-grade-polymer", "material:tool-steel", "material:oilseed-feedstock"),
            "equipment": ("equipment:roller-mill", "equipment:expeller", "equipment:conveyor", "equipment:food-sieve"),
            "quality": ("capability:food-safety", "capability:moisture-control", "capability:process-control"),
        },
        explanation="A family of cleaning, dehulling, splitting, flaking, and pressing equipment for pulses and oilseeds.",
        use_template="Use {name} to make edible pulse fractions, oil, meal, and controlled by-products from crop feedstock.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Common processing does not establish machine design, hygiene, yield, or service depth.",
        gaps=("feedstock variability and breakage/yield control", "wear surfaces and cleanability", "food-safety, oil quality, and process validation"),
        focus=("capability:food-processing", "process:pressing"),
        downstream=("capability:edible-oils", "capability:protein-foods", "capability:animal-feed"),
        related=("grain-mill", "edible-oil-refinery", "feed-mill"),
    ),
    _archetype(
        "edible-oil-refinery", "edible oil refining system", ("edible oil refinery", "vegetable oil refining"),
        kind="process_system", category="food process industries", profile="process",
        dependencies={
            "design": ("capability:food-process-engineering", "capability:chemical-process-design"),
            "process": ("process:degumming", "process:neutralisation", "process:bleaching", "process:deodorisation"),
            "material": ("material:stainless-steel", "material:food-grade-polymer", "material:adsorbent", "material:oilseed-feedstock"),
            "equipment": ("equipment:industrial-pump", "equipment:heat-exchanger", "equipment:vacuum-system", "equipment:filter-press"),
            "quality": ("capability:food-safety", "capability:chemical-quality", "capability:process-validation"),
        },
        explanation="A sequence of physical and chemical operations that purifies crude vegetable oils for food use.",
        use_template="Use {name} to remove gums, free fatty acids, pigments, odors, and contaminants from edible oils.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Plant category is known; feedstock, process controls, and food-grade qualification remain unknown.",
        gaps=("oil/feedstock quality variation", "vacuum, adsorbent, and deodorization control", "food safety, traceability, and effluent handling"),
        focus=("capability:food-processing", "process:food-refining"),
        downstream=("capability:edible-oils", "capability:food-packaging", "capability:oleochemicals"),
        related=("industrial-heat-exchanger", "centrifugal-pump", "food-dehydrator"),
    ),
    _archetype(
        "sugar-process-plant", "sugar process plant", ("sugar mill", "sugar refinery"),
        kind="process_system", category="food process industries", profile="process",
        dependencies={
            "design": ("capability:food-process-engineering", "capability:thermal-systems-design"),
            "process": ("process:juice-extraction", "process:clarification", "process:evaporation", "process:crystallisation"),
            "material": ("material:stainless-steel", "material:carbon-steel", "material:process-water", "material:sugarcane-feedstock"),
            "equipment": ("equipment:industrial-pump", "equipment:heat-exchanger", "equipment:evaporator", "equipment:centrifuge"),
            "quality": ("capability:food-safety", "capability:thermal-process-control", "capability:effluent-management"),
        },
        explanation="An integrated extraction, clarification, evaporation, crystallization, and separation route for sugar products.",
        use_template="Use {name} to turn cane or beet feedstock into sugar, molasses, bagasse, and process heat streams.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Established industry does not prove specific energy, recovery, equipment, or environmental performance.",
        gaps=("feedstock variability and extraction efficiency", "evaporation/heat integration", "crystal quality, water, and effluent control"),
        focus=("capability:food-processing", "capability:thermal-integration"),
        downstream=("capability:sugar-products", "capability:bioenergy", "capability:food-chemicals"),
        related=("industrial-heat-pump", "centrifugal-pump", "anaerobic-digester"),
    ),
    _archetype(
        "dairy-pasteurizer", "dairy pasteurization system", ("milk pasteurizer", "dairy pasteurizer"),
        kind="equipment", category="food process equipment", profile="food",
        dependencies={
            "design": ("capability:food-process-engineering", "capability:hygienic-design"),
            "process": ("process:heat-exchange", "process:pasteurisation", "process:clean-in-place", "process:fluidic-assembly"),
            "material": ("material:stainless-steel", "material:food-grade-polymer", "material:seal-material", "material:process-water"),
            "equipment": ("equipment:heat-exchanger", "equipment:centrifugal-pump", "equipment:temperature-control", "equipment:control-system"),
            "quality": ("capability:food-safety", "capability:thermal-process-validation", "capability:hygienic-design", "capability:metrology"),
        },
        explanation="A hygienic heat-treatment system that reduces microbial risk while preserving desired dairy properties.",
        use_template="Use {name} to pasteurize milk or dairy streams with controlled temperature, hold time, and cleanability.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Food use is broad; heat-transfer, hygienic, sensor, and validated thermal-process depth are unknown.",
        gaps=("temperature/hold-time uniformity", "CIP, seals, and hygienic drainage", "food-safety validation and maintenance"),
        focus=("capability:food-processing", "capability:hygienic-design"),
        downstream=("capability:dairy-products", "capability:food-packaging", "capability:food-safety"),
        related=("milk-homogenizer", "cheese-yogurt-vat", "industrial-heat-exchanger"),
    ),
    _archetype(
        "cheese-yogurt-vat", "cheese and yogurt processing vat", ("dairy vat", "cheese/yogurt vat"),
        kind="equipment", category="food process equipment", profile="food",
        dependencies={
            "design": ("capability:food-process-engineering", "capability:hygienic-design"),
            "process": ("process:mixing", "process:fermentation", "process:heat-exchange", "process:clean-in-place"),
            "material": ("material:stainless-steel", "material:food-grade-polymer", "material:seal-material", "material:starter-culture"),
            "equipment": ("equipment:industrial-motor", "equipment:heat-exchanger", "equipment:centrifugal-pump", "equipment:temperature-control"),
            "quality": ("capability:food-safety", "capability:fermentation-control", "capability:hygienic-design", "capability:process-validation"),
        },
        explanation="A jacketed, agitated hygienic vessel for coagulation, fermentation, culture growth, and dairy texture control.",
        use_template="Use {name} to make yogurt, cheese, cultured dairy, and related products with controlled thermal and biological steps.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Dairy processing is broad; vessel, agitation, culture, cleanability, and quality depth remain unknown.",
        gaps=("mixing and temperature uniformity", "culture control and contamination prevention", "CIP, drains, and product qualification"),
        focus=("capability:food-processing", "process:fermentation"),
        downstream=("capability:dairy-products", "capability:food-packaging"),
        related=("dairy-pasteurizer", "spray-dryer", "food-fermentation-system"),
    ),
    _archetype(
        "spray-dryer", "food and ingredient spray dryer", ("spray dryer", "ingredient dryer"),
        kind="equipment", category="food process equipment", profile="process",
        dependencies={
            "design": ("capability:food-process-engineering", "capability:thermal-systems-design"),
            "process": ("process:atomisation", "process:hot-air-drying", "process:cyclone-separation", "process:clean-in-place"),
            "material": ("material:stainless-steel", "material:food-grade-polymer", "material:process-air", "material:food-feedstock"),
            "equipment": ("equipment:air-heater", "equipment:centrifugal-pump", "equipment:cyclone-separator", "equipment:air-filter"),
            "quality": ("capability:food-safety", "capability:moisture-control", "capability:thermal-process-validation"),
        },
        explanation="A drying system that atomizes liquid feed into hot air to make stable powders and ingredients.",
        use_template="Use {name} to make milk powders, flavors, cultures, proteins, and other controlled food ingredients.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Drying equipment category is known; thermal, fouling, moisture, and hygiene depth are not adjudicated.",
        gaps=("atomization and residence-time control", "fouling, powder recovery, and moisture uniformity", "CIP and food-safety validation"),
        focus=("capability:food-processing", "process:food-drying"),
        downstream=("capability:milk-powders", "capability:food-ingredients", "capability:animal-feed"),
        related=("food-dehydrator", "food-freeze-dryer", "industrial-heat-pump"),
    ),
    _archetype(
        "food-freeze-dryer", "food freeze dryer", ("food lyophilizer", "freeze-drying system"),
        kind="equipment", category="food process equipment", profile="process",
        dependencies={
            "design": ("capability:food-process-engineering", "capability:vacuum-engineering", "capability:thermal-systems-design"),
            "process": ("process:freezing", "process:vacuum-drying", "process:clean-in-place", "process:packaging"),
            "material": ("material:stainless-steel", "material:food-grade-polymer", "material:refrigerant", "material:process-water"),
            "equipment": ("equipment:vacuum-system", "equipment:industrial-compressor", "equipment:heat-exchanger", "equipment:temperature-control"),
            "quality": ("capability:food-safety", "capability:moisture-control", "capability:thermal-uniformity-testing", "capability:process-validation"),
        },
        explanation="A low-temperature vacuum dryer that preserves food structure, aroma, and shelf life by removing ice.",
        use_template="Use {name} to stabilize fruits, vegetables, cultures, ingredients, and specialty foods for long storage.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Equipment existence is not evidence of chamber, vacuum, refrigeration, recipe, or food validation depth.",
        gaps=("shelf/chamber uniformity and vacuum control", "refrigeration and energy efficiency", "moisture, packaging, and shelf-life qualification"),
        focus=("capability:food-processing", "process:lyophilization"),
        downstream=("capability:specialty-foods", "capability:food-ingredients", "capability:biological-products"),
        related=("food-dehydrator", "spray-dryer", "industrial-heat-pump"),
    ),
    _archetype(
        "food-dehydrator", "industrial food dehydrator", ("food dehydrator", "hot-air food dryer"),
        kind="equipment", category="food process equipment", profile="food",
        dependencies={
            "design": ("capability:food-process-engineering", "capability:thermal-systems-design"),
            "process": ("process:cutting", "process:hot-air-drying", "process:air-handling", "process:packaging"),
            "material": ("material:stainless-steel", "material:food-grade-polymer", "material:process-air", "material:food-feedstock"),
            "equipment": ("equipment:air-heater", "equipment:centrifugal-fan", "equipment:temperature-control", "equipment:conveyor"),
            "quality": ("capability:food-safety", "capability:moisture-control", "capability:thermal-process-validation", "capability:hygienic-design"),
        },
        explanation="A controlled-air drying machine that removes moisture from food while managing color, texture, and microbial risk.",
        use_template="Use {name} to make dried fruits, vegetables, spices, herbs, snacks, and shelf-stable ingredients.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Food-drying use is broad; air distribution, moisture uniformity, hygiene, and validated performance are unknown.",
        gaps=("air-flow distribution and residence time", "moisture uniformity and product handling", "energy, hygiene, and shelf-life validation"),
        focus=("capability:food-processing", "process:food-drying"),
        downstream=("capability:shelf-stable-foods", "capability:food-ingredients", "capability:food-packaging"),
        related=("food-freeze-dryer", "spray-dryer", "industrial-heat-pump"),
    ),
    _archetype(
        "retort-canning-system", "retort and canning system", ("retort", "canning line"),
        kind="equipment", category="food process equipment", profile="food",
        dependencies={
            "design": ("capability:food-process-engineering", "capability:pressure-systems"),
            "process": ("process:thermal-sterilisation", "process:can-seaming", "process:pressure-testing", "process:packaging"),
            "material": ("material:stainless-steel", "material:packaging-metal", "material:seal-material", "material:food-feedstock"),
            "equipment": ("equipment:steam-generator", "equipment:pressure-vessel", "equipment:can-seamer", "equipment:temperature-control"),
            "quality": ("capability:food-safety", "capability:thermal-process-validation", "capability:container-closure", "capability:traceability"),
        },
        explanation="A pressure and heat processing system that makes sealed food packages shelf-stable.",
        use_template="Use {name} to preserve low-acid foods, ready meals, sauces, and protein products in sealed containers.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Processing category is broad; pressure, thermal, closure, and validated shelf-life depth are unknown.",
        gaps=("cold-spot and lethality validation", "container closure and seam integrity", "pressure vessel, traceability, and food-safety systems"),
        focus=("capability:food-processing", "process:thermal-sterilisation"),
        downstream=("capability:shelf-stable-foods", "capability:food-packaging", "capability:emergency-food"),
        related=("aseptic-packaging-line", "bottling-line", "food-dehydrator"),
    ),
    _archetype(
        "aseptic-packaging-line", "aseptic food packaging line", ("aseptic packaging", "aseptic filling line"),
        kind="equipment", category="food packaging", profile="food",
        dependencies={
            "design": ("capability:food-process-engineering", "capability:hygienic-design", "capability:packaging-machine-design"),
            "process": ("process:ultra-high-temperature-treatment", "process:aseptic-filling", "process:forming", "process:sealing"),
            "material": ("material:stainless-steel", "material:packaging-laminate", "material:seal-material", "material:food-feedstock"),
            "equipment": ("equipment:heat-exchanger", "equipment:fill-pump", "equipment:servo-drive", "equipment:machine-vision"),
            "quality": ("capability:food-safety", "capability:aseptic-qualification", "capability:container-closure", "capability:traceability"),
        },
        explanation="A hygienic line that sterilizes product and package pathways before filling shelf-stable foods.",
        use_template="Use {name} to package milk, beverages, sauces, and liquid foods without a cold chain after filling.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Food packaging use is not evidence of aseptic barrier, laminate, filler, or qualification depth.",
        gaps=("sterile zone and package decontamination", "filler/closure integrity and changeover", "food-safety validation and packaging-material supply"),
        focus=("capability:food-packaging", "capability:hygienic-design"),
        downstream=("capability:shelf-stable-foods", "capability:dairy-products", "capability:beverages"),
        related=("packaging-machinery", "retort-canning-system", "bottling-line"),
    ),
    _archetype(
        "form-fill-seal-line", "form-fill-seal packaging line", ("FFS machine", "form-fill-seal"),
        kind="equipment", category="food packaging", profile="machine",
        dependencies={
            "design": ("capability:packaging-machine-design", "capability:industrial-automation"),
            "process": ("process:film-forming", "process:forming", "process:filling", "process:sealing"),
            "material": ("material:packaging-film", "material:engineering-polymer", "material:stainless-steel", "material:food-feedstock"),
            "equipment": ("equipment:servo-drive", "equipment:plc-controller", "equipment:machine-vision", "equipment:heat-sealer"),
            "quality": ("capability:food-safety", "capability:seal-integrity", "capability:line-qualification", "capability:traceability"),
        },
        explanation="A synchronized machine that forms packaging from web or film, fills it, and seals it in one line.",
        use_template="Use {name} to package snacks, powders, liquids, sachets, pouches, and portioned foods.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Packaging deployment is not evidence of servo, film, sealing, inspection, or line-qualification depth.",
        gaps=("film forming and seal-window control", "servo synchronization and changeover", "seal inspection, hygiene, and packaging-material resilience"),
        focus=("capability:packaging-machinery", "process:sealing"),
        downstream=("capability:food-packaging", "capability:consumer-goods"),
        related=("packaging-machinery", "aseptic-packaging-line", "bottling-line"),
    ),
    _archetype(
        "bottling-line", "food and beverage bottling line", ("bottling line", "liquid filling line"),
        kind="equipment", category="food packaging", profile="food",
        dependencies={
            "design": ("capability:packaging-machine-design", "capability:hygienic-design"),
            "process": ("process:container-washing", "process:filling", "process:capping", "process:labeling"),
            "material": ("material:stainless-steel", "material:glass", "material:engineering-polymer", "material:food-feedstock"),
            "equipment": ("equipment:centrifugal-pump", "equipment:servo-drive", "equipment:plc-controller", "equipment:machine-vision"),
            "quality": ("capability:food-safety", "capability:fill-volume-control", "capability:container-closure", "capability:line-qualification"),
        },
        explanation="A coordinated line for washing, filling, closing, labeling, and inspecting food or beverage containers.",
        use_template="Use {name} to convert bulk liquids into traceable bottles or containers with repeatable fill and closure.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Line presence is not evidence of hygienic design, closure, fill accuracy, or scalable automation depth.",
        gaps=("hygienic fluid paths and changeover", "fill/cap control and leak inspection", "container supply, sanitation, and service"),
        focus=("capability:food-packaging", "capability:industrial-automation"),
        downstream=("capability:beverages", "capability:dairy-products", "capability:food-logistics"),
        related=("aseptic-packaging-line", "form-fill-seal-line", "packaging-machinery"),
    ),
    _archetype(
        "cold-storage-system", "industrial cold-storage system", ("cold store", "refrigerated warehouse"),
        kind="facility_system", category="cold chain", profile="process",
        dependencies={
            "design": ("capability:cold-chain-engineering", "capability:thermal-systems-design"),
            "process": ("process:refrigeration", "process:thermal-insulation", "process:material-handling", "process:temperature-monitoring"),
            "material": ("material:insulation-material", "material:stainless-steel", "material:refrigerant", "material:engineering-polymer"),
            "equipment": ("equipment:industrial-compressor", "equipment:heat-exchanger", "equipment:industrial-fan", "equipment:temperature-control"),
            "quality": ("capability:food-safety", "capability:temperature-traceability", "capability:refrigeration-maintenance", "capability:utility-reliability"),
        },
        explanation="A thermally insulated storage and handling system that maintains temperature-sensitive food and biological products.",
        use_template="Use {name} to buffer harvest, production, transport, and demand while preserving product quality.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Cold-store existence is not evidence of thermal uniformity, uptime, or resilient power and maintenance.",
        gaps=("insulation and temperature uniformity", "refrigeration uptime and backup power", "monitoring, handling, and food-loss evidence"),
        focus=("capability:cold-chain", "capability:thermal-systems"),
        downstream=("capability:food-logistics", "capability:dairy-products", "capability:biological-production"),
        related=("industrial-heat-pump", "industrial-refrigeration", "bottling-line"),
    ),
    _archetype(
        "industrial-refrigeration", "industrial refrigeration system", ("industrial refrigeration", "ammonia refrigeration system"),
        kind="equipment", category="thermal process equipment", profile="process",
        dependencies={
            "design": ("capability:refrigeration-engineering", "capability:thermal-systems-design"),
            "process": ("process:compression", "process:heat-exchange", "process:refrigerant-management", "process:thermal-integration"),
            "material": ("material:stainless-steel", "material:copper", "material:refrigerant", "material:insulation-material"),
            "equipment": ("equipment:industrial-compressor", "equipment:heat-exchanger", "equipment:industrial-motor", "equipment:control-system"),
            "quality": ("capability:refrigerant-safety", "capability:thermal-performance-testing", "capability:utility-reliability", "capability:maintenance"),
        },
        explanation="A refrigeration plant that removes heat from cold rooms, process loads, ice systems, or transport systems.",
        use_template="Use {name} to cool or freeze food, ingredients, biological products, and industrial process streams.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Refrigeration installations do not establish compressor, refrigerant, controls, or lifecycle depth.",
        gaps=("compressor, refrigerant, and heat-exchanger envelope", "leak/safety and load-following control", "maintenance, energy efficiency, and backup power"),
        focus=("capability:thermal-systems", "capability:cold-chain"),
        downstream=("capability:cold-storage", "capability:food-processing", "capability:pharma-logistics"),
        related=("industrial-heat-pump", "cold-storage-system", "centrifugal-pump"),
    ),
    _archetype(
        "grain-dryer", "industrial grain dryer", ("grain dryer", "cereal dryer"),
        kind="equipment", category="agricultural processing", profile="food",
        dependencies={
            "design": ("capability:food-process-engineering", "capability:thermal-systems-design"),
            "process": ("process:hot-air-drying", "process:conveying", "process:temperature-monitoring", "process:cleaning"),
            "material": ("material:stainless-steel", "material:carbon-steel", "material:insulation-material", "material:grain-feedstock"),
            "equipment": ("equipment:air-heater", "equipment:industrial-fan", "equipment:conveyor", "equipment:temperature-control"),
            "quality": ("capability:grain-quality", "capability:moisture-control", "capability:food-safety", "capability:process-validation"),
        },
        explanation="A controlled airflow and heat system that reduces grain moisture to a stable storage condition.",
        use_template="Use {name} to reduce post-harvest losses and stabilize grain before storage or milling.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Dryer category is broad; moisture uniformity, energy use, and grain-quality performance are unknown.",
        gaps=("air distribution and moisture uniformity", "energy efficiency and contamination control", "grain damage and safe operation"),
        focus=("capability:agri-processing", "process:food-drying"),
        downstream=("capability:grain-storage", "capability:grain-milling", "capability:food-logistics"),
        related=("grain-mill", "grain-silo", "food-dehydrator"),
    ),
    _archetype(
        "seed-cleaner-treater", "seed cleaning and treatment system", ("seed cleaner", "seed treater"),
        kind="equipment", category="agricultural equipment", profile="agriculture",
        dependencies={
            "design": ("capability:agri-equipment-design", "capability:seed-science"),
            "process": ("process:cleaning", "process:grading", "process:coating", "process:metering"),
            "material": ("material:stainless-steel", "material:engineering-polymer", "material:seed-feedstock", "material:seed-treatment-chemicals"),
            "equipment": ("equipment:optical-sorter", "equipment:conveyor", "equipment:powder-doser", "equipment:control-system"),
            "quality": ("capability:seed-quality", "capability:agri-safety", "capability:process-control", "capability:traceability"),
        },
        explanation="A machine system that cleans, sizes, treats, coats, and meters seed for planting or distribution.",
        use_template="Use {name} to improve seed uniformity, protection, traceability, and planting performance.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Agricultural use is broad; seed-quality, coating, dosing, and validated treatment depth are unknown.",
        gaps=("sorting and grading accuracy", "treatment dose uniformity and worker safety", "seed germination, traceability, and service"),
        focus=("capability:agri-equipment", "capability:seed-science"),
        downstream=("capability:crop-production", "capability:agri-logistics"),
        related=("grain-silo", "grain-mill", "greenhouse-system"),
    ),
    _archetype(
        "combine-harvester", "combine harvester", ("combine", "harvesting machine"),
        kind="equipment", category="agricultural machinery", profile="agriculture",
        dependencies={
            "design": ("capability:agri-equipment-design", "capability:vehicle-engineering", "capability:mechanical-design"),
            "process": ("process:casting", "process:precision-machining", "process:welding", "process:assembly"),
            "material": ("material:alloy-steel", "material:cast-iron", "material:rubber", "material:hydraulic-fluid"),
            "equipment": ("equipment:industrial-motor", "equipment:hydraulic-power-unit", "equipment:control-system", "equipment:machine-vision"),
            "quality": ("capability:field-reliability", "capability:agri-service", "capability:operator-training", "capability:machine-qualification"),
        },
        explanation="A mobile machine that cuts, threshes, separates, cleans, and collects grain in one field operation.",
        use_template="Use {name} to reduce harvest labor and losses while matching crop, terrain, and service conditions.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Machine availability does not establish local design, component, field reliability, or service depth.",
        gaps=("crop-specific cutting/threshing performance", "hydraulic, engine, and control integration", "field reliability and service network"),
        focus=("capability:agri-machinery", "capability:field-reliability"),
        downstream=("capability:grain-storage", "capability:grain-milling", "capability:agri-logistics"),
        related=("tractor-implement", "irrigation-pump", "seed-cleaner-treater"),
    ),
    _archetype(
        "tractor-implement", "tractor and agricultural implement system", ("tractor implement", "farm implement"),
        kind="equipment", category="agricultural machinery", profile="agriculture",
        dependencies={
            "design": ("capability:agri-equipment-design", "capability:vehicle-engineering"),
            "process": ("process:casting", "process:forging", "process:welding", "process:assembly"),
            "material": ("material:alloy-steel", "material:cast-iron", "material:rubber", "material:hydraulic-fluid"),
            "equipment": ("equipment:cnc-machining-center", "equipment:hydraulic-power-unit", "equipment:industrial-motor", "equipment:test-bench"),
            "quality": ("capability:field-reliability", "capability:agri-service", "capability:operator-training", "capability:machine-qualification"),
        },
        explanation="A tractor-mounted or self-powered platform for tillage, planting, spraying, harvesting, and material handling.",
        use_template="Use {name} to mechanize field operations while matching implement geometry, soil, crop, and service constraints.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Agricultural equipment presence does not establish specific implement, hydraulic, or field-reliability depth.",
        gaps=("soil/crop-specific working envelope", "hydraulic and power-takeoff reliability", "service, spares, and operator training"),
        focus=("capability:agri-machinery", "capability:field-reliability"),
        downstream=("capability:crop-production", "capability:agri-logistics"),
        related=("combine-harvester", "irrigation-pump", "seed-cleaner-treater"),
    ),
    _archetype(
        "irrigation-pump", "agricultural irrigation pump system", ("irrigation pump", "farm pump"),
        kind="equipment", category="agricultural infrastructure", profile="agriculture",
        dependencies={
            "design": ("capability:fluid-machinery-design", "capability:agri-infrastructure"),
            "process": ("process:casting", "process:precision-machining", "process:assembly", "process:pressure-testing"),
            "material": ("material:cast-iron", "material:stainless-steel", "material:engineering-polymer", "material:seal-material"),
            "equipment": ("equipment:centrifugal-pump", "equipment:industrial-motor", "equipment:solar-inverter", "equipment:test-bench"),
            "quality": ("capability:hydraulic-performance", "capability:field-reliability", "capability:water-quality", "capability:service-network"),
        },
        explanation="A pump and drive system that lifts or distributes water for crops, livestock, and protected agriculture.",
        use_template="Use {name} to deliver water at the required flow and pressure while respecting energy and source constraints.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Pump use is widespread; source, efficiency, durability, and field-service depth are not adjudicated.",
        gaps=("hydraulic efficiency and cavitation margin", "water quality, seal life, and corrosion", "power source, controls, and field service"),
        focus=("capability:agri-infrastructure", "capability:fluid-machinery"),
        downstream=("capability:crop-production", "capability:greenhouse-agriculture", "capability:water-management"),
        related=("centrifugal-pump", "industrial-motor", "greenhouse-system"),
    ),
    _archetype(
        "greenhouse-system", "controlled-environment greenhouse system", ("greenhouse", "protected agriculture system"),
        kind="facility_system", category="agricultural infrastructure", profile="agriculture",
        dependencies={
            "design": ("capability:controlled-environment-agriculture", "capability:thermal-systems-design", "capability:agri-data-systems"),
            "process": ("process:structural-assembly", "process:irrigation", "process:climate-control", "process:crop-management"),
            "material": ("material:steel", "material:engineering-polymer", "material:glass", "material:crop-feedstock"),
            "equipment": ("equipment:irrigation-pump", "equipment:industrial-fan", "equipment:temperature-control", "equipment:lighting-system"),
            "quality": ("capability:agri-operations", "capability:water-quality", "capability:crop-quality", "capability:environmental-monitoring"),
        },
        explanation="A protected growing environment that controls climate, water, light, and crop handling.",
        use_template="Use {name} to stabilize yield or quality where outdoor climate, water, or land constraints dominate.",
        status="INDIA_EMERGING_OR_LIMITED", status_epistemic="MODELLED",
        status_basis="Emerging label only; crop economics, utility reliability, and operating depth are unknown.",
        gaps=("climate control and water balance", "crop-specific recipes and labor", "energy, structure, and disease-management economics"),
        focus=("capability:controlled-environment-agriculture", "capability:agri-data-systems"),
        downstream=("capability:horticulture", "capability:seed-production", "capability:food-logistics"),
        related=("vertical-farm", "irrigation-pump", "cold-storage-system"),
    ),
    _archetype(
        "vertical-farm", "vertical farming system", ("vertical farm", "indoor farm"),
        kind="facility_system", category="agricultural infrastructure", profile="agriculture",
        dependencies={
            "design": ("capability:controlled-environment-agriculture", "capability:agri-data-systems", "capability:thermal-systems-design"),
            "process": ("process:hydroponics", "process:climate-control", "process:lighting-control", "process:crop-management"),
            "material": ("material:engineering-polymer", "material:aluminum", "material:stainless-steel", "material:crop-feedstock"),
            "equipment": ("equipment:irrigation-pump", "equipment:industrial-fan", "equipment:led-lighting", "equipment:control-system"),
            "quality": ("capability:crop-quality", "capability:water-quality", "capability:environmental-monitoring", "capability:agri-operations"),
        },
        explanation="A stacked or indoor production system using controlled light, water, nutrients, and environment.",
        use_template="Use {name} for high-value crops where land, water, proximity, and climate control justify energy input.",
        status="INDIA_EMERGING_OR_LIMITED", status_epistemic="MODELLED",
        status_basis="Emerging label only; crop-specific yield, energy, and operating economics remain unknown.",
        gaps=("energy and thermal load", "crop recipe, nutrient, and disease control", "water recycling and viable operating model"),
        focus=("capability:controlled-environment-agriculture", "capability:agri-data-systems"),
        downstream=("capability:horticulture", "capability:urban-food-systems", "capability:food-logistics"),
        related=("greenhouse-system", "irrigation-pump", "industrial-heat-pump"),
    ),
    _archetype(
        "poultry-hatchery", "poultry hatchery system", ("poultry hatchery", "incubation system"),
        kind="facility_system", category="biological production", profile="bio_food",
        dependencies={
            "design": ("capability:animal-production", "capability:environmental-control", "capability:biosecurity"),
            "process": ("process:incubation", "process:climate-control", "process:sanitation", "process:biological-monitoring"),
            "material": ("material:engineering-polymer", "material:stainless-steel", "material:feedstock", "material:disinfectant"),
            "equipment": ("equipment:temperature-control", "equipment:humidity-control", "equipment:environmental-monitoring", "equipment:material-handling"),
            "quality": ("capability:animal-health", "capability:biosecurity", "capability:biological-quality", "capability:traceability"),
        },
        explanation="A controlled incubation and early-life handling system for poultry production.",
        use_template="Use {name} to manage temperature, humidity, sanitation, hatch timing, and flock-health inputs.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Biological production presence is not evidence of equipment, biosecurity, or hatch-quality depth.",
        gaps=("uniformity and environmental control", "sanitation and disease prevention", "hatch-rate, genetics, and traceability evidence"),
        focus=("capability:biological-production", "capability:biosecurity"),
        downstream=("capability:poultry-production", "capability:animal-feed", "capability:food-logistics"),
        related=("feed-mill", "aquaculture-system", "greenhouse-system"),
    ),
    _archetype(
        "feed-mill", "animal feed milling and pelleting system", ("feed mill", "feed pelleting line"),
        kind="equipment", category="biological production", profile="food",
        dependencies={
            "design": ("capability:feed-process-engineering", "capability:food-process-engineering"),
            "process": ("process:grinding", "process:mixing", "process:pelletising", "process:conditioning"),
            "material": ("material:stainless-steel", "material:tool-steel", "material:grain-feedstock", "material:feed-additives"),
            "equipment": ("equipment:roller-mill", "equipment:powder-mixer", "equipment:pellet-mill", "equipment:conveyor"),
            "quality": ("capability:feed-quality", "capability:food-safety", "capability:particle-size-control", "capability:traceability"),
        },
        explanation="A line that grinds, mixes, conditions, pellets, and handles feed for livestock, poultry, or aquaculture.",
        use_template="Use {name} to convert grains, proteins, minerals, and additives into consistent feed products.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Feed production is broad; formulation, pellet quality, contamination, and equipment depth remain unknown.",
        gaps=("formulation and micro-dosing", "pellet durability and heat control", "mycotoxin/contamination control and traceability"),
        focus=("capability:biological-production", "process:pelletising"),
        downstream=("capability:poultry-production", "capability:aquaculture", "capability:livestock-production"),
        related=("grain-mill", "poultry-hatchery", "aquaculture-system"),
    ),
    _archetype(
        "anaerobic-digester", "anaerobic digestion and biogas system", ("anaerobic digester", "biogas plant"),
        kind="process_system", category="biological production", profile="bio_food",
        dependencies={
            "design": ("capability:bioprocess-engineering", "capability:waste-management", "capability:gas-systems"),
            "process": ("process:feedstock-preprocessing", "process:anaerobic-digestion", "process:gas-cleaning", "process:digestate-management"),
            "material": ("material:biomass-feedstock", "material:stainless-steel", "material:engineering-polymer", "material:process-water"),
            "equipment": ("equipment:industrial-pump", "equipment:gas-scrubber", "equipment:industrial-compressor", "equipment:process-reactor"),
            "quality": ("capability:gas-quality", "capability:process-safety", "capability:waste-quality", "capability:environmental-control"),
        },
        explanation="A biological conversion system that turns organic feedstock into biogas and nutrient-bearing digestate.",
        use_template="Use {name} to recover energy and nutrients from manure, crop residues, food waste, or wastewater solids.",
        status="INDIA_EMERGING_OR_LIMITED", status_epistemic="MODELLED",
        status_basis="Emerging label only; feedstock continuity, gas quality, and operating maturity are unknown.",
        gaps=("feedstock preprocessing and stable biology", "gas cleaning, storage, and safety", "digestate quality and viable offtake"),
        focus=("capability:biological-production", "capability:waste-management"),
        downstream=("capability:biogas-upgrading", "capability:renewable-heat", "capability:fertilizer-inputs"),
        related=("biogas-upgrader", "methanol-syngas-plant", "feed-mill"),
    ),
    _archetype(
        "aquaculture-system", "controlled aquaculture production system", ("aquaculture system", "recirculating aquaculture"),
        kind="facility_system", category="biological production", profile="bio_food",
        dependencies={
            "design": ("capability:aquaculture-engineering", "capability:water-treatment", "capability:animal-production"),
            "process": ("process:water-circulation", "process:biofiltration", "process:oxygenation", "process:stock-management"),
            "material": ("material:stainless-steel", "material:engineering-polymer", "material:water-treatment-media", "material:feedstock"),
            "equipment": ("equipment:centrifugal-pump", "equipment:oxygenation-system", "equipment:biofilter", "equipment:environmental-monitoring"),
            "quality": ("capability:water-quality", "capability:animal-health", "capability:biosecurity", "capability:traceability"),
        },
        explanation="A controlled water, oxygen, feed, and biological-monitoring system for fish or aquatic food production.",
        use_template="Use {name} to produce aquatic protein while managing water quality, disease, feed, and energy.",
        status="INDIA_EMERGING_OR_LIMITED", status_epistemic="MODELLED",
        status_basis="Emerging label only; species, water, feed, disease, and operating depth remain unknown.",
        gaps=("biofiltration and water-quality stability", "oxygen, pump, and backup-power resilience", "disease control, feed, and market qualification"),
        focus=("capability:biological-production", "capability:water-treatment"),
        downstream=("capability:aquaculture-products", "capability:food-logistics", "capability:animal-feed"),
        related=("feed-mill", "irrigation-pump", "anaerobic-digester"),
    ),
    _archetype(
        "food-fermentation-system", "food fermentation production system", ("food fermentation", "fermentation vessel"),
        kind="process_system", category="biological production", profile="bio_food",
        dependencies={
            "design": ("capability:food-process-engineering", "capability:bioprocess-engineering", "capability:hygienic-design"),
            "process": ("process:fermentation", "process:mixing", "process:heat-exchange", "process:clean-in-place"),
            "material": ("material:stainless-steel", "material:food-grade-polymer", "material:starter-culture", "material:process-water"),
            "equipment": ("equipment:industrial-motor", "equipment:industrial-pump", "equipment:heat-exchanger", "equipment:control-system"),
            "quality": ("capability:food-safety", "capability:fermentation-control", "capability:process-validation", "capability:quality-system"),
        },
        explanation="A controlled biological process for making foods, ingredients, cultures, acids, enzymes, or beverages.",
        use_template="Use {name} to convert substrate into a consistent fermented product with controlled culture and conditions.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Food fermentation is broad; culture control, vessel, contamination, and product qualification remain unknown.",
        gaps=("culture/recipe control and contamination prevention", "mixing, heat, and oxygen transfer", "food-safety, yield, and sensory qualification"),
        focus=("capability:food-processing", "capability:bioprocessing"),
        downstream=("capability:dairy-products", "capability:food-ingredients", "capability:beverages"),
        related=("cheese-yogurt-vat", "bioreactor", "spray-dryer"),
    ),
    _archetype(
        "bakery-extrusion-line", "bakery and food extrusion line", ("food extruder", "industrial bakery line"),
        kind="equipment", category="food processing", profile="food",
        dependencies={
            "design": ("capability:food-process-engineering", "capability:packaging-machine-design"),
            "process": ("process:mixing", "process:extrusion", "process:baking", "process:packaging"),
            "material": ("material:stainless-steel", "material:tool-steel", "material:food-grade-polymer", "material:grain-feedstock"),
            "equipment": ("equipment:industrial-motor", "equipment:extruder", "equipment:industrial-oven", "equipment:packaging-machinery"),
            "quality": ("capability:food-safety", "capability:thermal-process-validation", "capability:moisture-control", "capability:line-qualification"),
        },
        explanation="A continuous or batch line for mixing, shaping, cooking, baking, cooling, and packaging food products.",
        use_template="Use {name} to make snacks, cereals, bakery goods, pet foods, and textured food products.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Food manufacturing presence does not establish tooling, thermal profile, hygiene, or line qualification.",
        gaps=("dough/feed rheology and tooling", "thermal uniformity and moisture control", "changeover, hygiene, and packaging integration"),
        focus=("capability:food-processing", "process:extrusion"),
        downstream=("capability:snack-foods", "capability:animal-feed", "capability:food-packaging"),
        related=("feed-mill", "food-dehydrator", "packaging-machinery"),
    ),
    _archetype(
        "meat-fish-processing-line", "meat and fish processing line", ("meat processing", "fish processing line"),
        kind="equipment", category="food processing", profile="food",
        dependencies={
            "design": ("capability:food-process-engineering", "capability:hygienic-design", "capability:cold-chain-engineering"),
            "process": ("process:cutting", "process:deboning", "process:chilling", "process:packaging"),
            "material": ("material:stainless-steel", "material:food-grade-polymer", "material:seal-material", "material:animal-feedstock"),
            "equipment": ("equipment:industrial-refrigeration", "equipment:food-cutter", "equipment:conveyor", "equipment:packaging-machinery"),
            "quality": ("capability:food-safety", "capability:cold-chain", "capability:traceability", "capability:hygienic-design"),
        },
        explanation="A hygienic chilled line for receiving, cutting, portioning, processing, and packaging animal protein.",
        use_template="Use {name} to process protein products while controlling temperature, contamination, yield, and traceability.",
        status="INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN", status_epistemic="UNKNOWN",
        status_basis="Processing activity is not evidence of hygienic equipment, cold-chain, yield, or export-quality depth.",
        gaps=("temperature and microbial control", "cutting/yield and cleanability", "traceability, waste handling, and cold-chain resilience"),
        focus=("capability:food-processing", "capability:cold-chain"),
        downstream=("capability:protein-foods", "capability:food-logistics", "capability:animal-feed"),
        related=("industrial-refrigeration", "bottling-line", "packaging-machinery"),
    ),
)


DOMAIN_METADATA: dict[str, dict[str, Any]] = {
    "05": {
        "domain_id": "05",
        "domain": "Machines, Robotics, and Industrial Automation",
        "short_name": "machines_robotics_automation",
        "archetypes": MACHINE_ARCHETYPES,
        "variant_profile_count": 36,
        "record_count": len(MACHINE_ARCHETYPES) * 36,
        "coverage_note": "Machine tools, motion, robots, controls, packaging, and textile machinery; no fleet or capacity claims.",
    },
    "06": {
        "domain_id": "06",
        "domain": "Materials, Metals, Chemicals, and Process Industries",
        "short_name": "materials_metals_chemicals_process",
        "archetypes": MATERIAL_ARCHETYPES,
        "variant_profile_count": 36,
        "record_count": len(MATERIAL_ARCHETYPES) * 36,
        "coverage_note": "Materials, chemicals, process equipment, pumps, heat pumps, electrolyzers, and thermal/vacuum systems.",
    },
    "07": {
        "domain_id": "07",
        "domain": "Medical, Scientific, Pharma, and Biotech Equipment",
        "short_name": "medical_scientific_pharma_biotech_equipment",
        "archetypes": MEDICAL_ARCHETYPES,
        "variant_profile_count": 36,
        "record_count": len(MEDICAL_ARCHETYPES) * 36,
        "coverage_note": "Imaging, critical care, analytical instruments, bioprocessing, freeze drying, and sterile manufacturing.",
    },
    "08": {
        "domain_id": "08",
        "domain": "Food, Agriculture, and Biological Production Systems",
        "short_name": "food_agriculture_biological_production",
        "archetypes": FOOD_ARCHETYPES,
        "variant_profile_count": 36,
        "record_count": len(FOOD_ARCHETYPES) * 36,
        "coverage_note": "Food processing and packaging, cold chain, farm equipment, controlled environments, and biological production.",
    },
}


def _build_record(domain_meta: Mapping[str, Any], blueprint: Mapping[str, Any], combo: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    profile = PROFILES[str(blueprint["profile"])]
    axis_names = [name for name, _ in profile["axes"]]
    axis_keys = [str(option["key"]) for option in combo]
    axis_labels = [str(option["label"]) for option in combo]
    variant_key = "-".join(axis_keys)
    record_id = f"product:{domain_meta['domain_id']}:{blueprint['id']}:{variant_key}"
    variant_name = ", ".join(axis_labels)
    name = f"{blueprint['name']} ({variant_name})"

    groups: list[dict[str, Any]] = []
    for group, ids in blueprint["dependencies"].items():
        merged = _dedupe(ids)
        if merged:
            groups.append({"group": str(group), "ids": merged})
    # Axis-specific prerequisites are kept in their own group.  This prevents a
    # control dependency from being misrepresented as a material dependency (or
    # vice versa) while still making every selected variant auditable.
    variant_dependencies = _dedupe(
        dependency
        for option in combo
        for dependency in option.get("dependencies", ())
    )
    if variant_dependencies:
        groups.append({"group": "variant_configuration", "ids": variant_dependencies})
    dependency_ids = _dedupe(item for group in groups for item in group["ids"])

    # The read-only atlas schema used by the sibling packets keeps exactly five
    # stable groups.  Retain the richer internal group names above, then expose
    # a normalized mapping for loaders that need the common contract.
    dependency_group_map: dict[str, list[str]] = {
        "systems": [],
        "processes": [],
        "materials": [],
        "equipment": [],
        "capabilities": [],
    }
    for group in groups:
        source_group = str(group["group"])
        if source_group == "process":
            target_group = "processes"
        elif source_group == "material":
            target_group = "materials"
        elif source_group == "equipment":
            target_group = "equipment"
        elif source_group == "design" or source_group == "quality" or source_group == "variant_configuration":
            target_group = "capabilities"
        else:
            target_group = "systems"
        dependency_group_map[target_group].extend(str(item) for item in group["ids"])
    dependency_group_map = {
        group: _dedupe(values) for group, values in dependency_group_map.items()
    }

    gaps = [
        {"type": "capability_gap", "note": str(note), "epistemic_class": "UNKNOWN"}
        for note in blueprint["gaps"]
    ]
    gaps.append({
        "type": "import_note",
        "note": "Imported capital equipment, materials, or subcomponents may remain in the route; trade or assembly is not treated as domestic capability.",
        "epistemic_class": "ASSUMPTION",
    })
    for option in combo:
        if option.get("note"):
            gaps.append({"type": "variant_note", "note": str(option["note"]), "epistemic_class": "ASSUMPTION"})

    ladder_focus = _dedupe((*blueprint["focus"], *dependency_ids[:3]))
    making_ladder = [
        {"step": 1, "action": "DEFINE", "text": f"Freeze the product/process envelope for {name}; record target geography, duty, and acceptance tests."},
        {"step": 2, "action": "MAP", "text": "Map the grouped dependencies to canonical capabilities, processes, materials, equipment, utilities, skills, and qualification gates."},
        {"step": 3, "action": "AUDIT", "text": "Audit India-specific qualified depth and import exposure for the decision-sensitive nodes; retain UNKNOWN where evidence is missing."},
        {"step": 4, "action": "QUALIFY", "text": f"Define prototype, metrology, process-validation, and customer/regulatory qualification work for {', '.join(ladder_focus[:3])}."},
        {"step": 5, "action": "RAMP", "text": "Sequence build/buy/partner/supplier-development actions, then re-solve throughput, resilience, and substitution scenarios."},
    ]

    upstream_links = _dedupe((*dependency_ids[:10], *blueprint["focus"]))
    downstream_links = _dedupe((*blueprint["downstream"], f"capability:{domain_meta['short_name']}"))
    related_links = _dedupe((*blueprint["related"], *(f"product:{domain_meta['domain_id']}:{x}" for x in blueprint["related"])))

    status_map = {
        "INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN": "PARTIAL",
        "INDIA_EMERGING_OR_LIMITED": "SCALE_LIMITED",
        "INDIA_IMPORT_DEPENDENT_OR_QUALIFICATION_UNKNOWN": "IMPORT_DEPENDENT",
        "INDIA_ASSEMBLY_OR_SERVICE_BASE_UNKNOWN": "PARTIAL",
        "UNKNOWN": "UNKNOWN",
        "CONFLICTED": "CONFLICTED",
    }
    kind_map = {
        "equipment": "EQUIPMENT",
        "instrument": "EQUIPMENT",
        "material": "MATERIAL",
        "chemical": "MATERIAL",
        "process_system": "PRODUCT",
        "facility_system": "PRODUCT",
        "product": "PRODUCT",
        "capability": "CAPABILITY",
        "process": "PROCESS",
    }
    common_ladder = [
        {"sequence": 1, "action": "IMPORT", "purpose": f"Use an external bridge while the India route for {name} is investigated.", "condition": "Eligibility is not supply; residual dependence must remain explicit."},
        {"sequence": 2, "action": "DEVELOP", "purpose": "Freeze the duty, interfaces, process route, and acceptance basis.", "condition": "Requires a measurable specification and process owner."},
        {"sequence": 3, "action": "REDESIGN", "purpose": "Evaluate architecture and specification changes that remove avoidable choke points.", "condition": "Requires explicit performance, cost, time, and qualification trade-offs."},
        {"sequence": 4, "action": "BUILD", "purpose": "Prototype the route with tooling, metrology, work instructions, and utilities.", "condition": "Requires capex, workforce, process controls, and ramp time."},
        {"sequence": 5, "action": "R&D", "purpose": "Resolve process windows, yield, reliability, qualification, and unknowns.", "condition": "Unresolved evidence remains UNKNOWN."},
        {"sequence": 6, "action": "LICENSE", "purpose": "Use controlled technology transfer or partnership where domestic depth is not closed.", "condition": "Requires rights, export permission, transfer scope, and a domestic operating team."},
    ]
    common_gaps = [str(row["note"]) for row in gaps if row["type"] in {"capability_gap", "import_note"}]
    common_import_notes = [str(row["note"]) for row in gaps if row["type"] == "import_note"]
    common_kind = kind_map.get(str(blueprint["kind"]), "PRODUCT")
    common_status = status_map.get(str(blueprint["status"]), "UNKNOWN")

    return {
        "schema_version": SCHEMA_VERSION,
        "id": record_id,
        "record_id": record_id,
        "canonical_id": record_id,
        "domain_id": str(domain_meta["domain_id"]),
        "domain_code": str(domain_meta["domain_id"]),
        "domain_number": int(domain_meta["domain_id"]),
        "domain_key": str(domain_meta["short_name"]),
        "domain": str(domain_meta["domain"]),
        "archetype_id": str(blueprint["id"]),
        "kind": common_kind,
        "kind_detail": str(blueprint["kind"]),
        "category": str(blueprint["category"]),
        "name": name,
        "canonical_name": name,
        # Alias strings are variant-qualified so a registry can enforce global
        # alias uniqueness without losing the unqualified archetype aliases.
        "aliases": _dedupe(
            tuple(f"{alias} ({variant_key})" for alias in (*blueprint["aliases"], str(blueprint["name"])))
            + (f"{blueprint['id']}:{variant_key}",)
        ),
        "archetype_aliases": _dedupe((*blueprint["aliases"], str(blueprint["name"]))),
        "explanation": str(blueprint["explanation"]),
        "use": str(blueprint["use_template"].format(name=name, variant=variant_name)),
        "uses": [str(blueprint["use_template"].format(name=name, variant=variant_name))],
        "use_template": str(blueprint["use_template"].format(name=name, variant=variant_name)),
        "variant": {
            "axes": axis_names,
            "keys": axis_keys,
            "labels": axis_labels,
            "compatibility_note": str(profile["compatibility_note"]),
        },
        "india_status": str(blueprint["status"]),
        "india_status_epistemic": str(blueprint["status_epistemic"]),
        "india_status_basis": str(blueprint["status_basis"]),
        "status": common_status,
        "status_basis": str(blueprint["status_basis"]),
        "status_epistemic_class": str(blueprint["status_epistemic"]),
        "status_basis_epistemic_class": str(blueprint["status_epistemic"]),
        "epistemic_class": str(blueprint["status_epistemic"]),
        "epistemic_basis": str(blueprint["status_basis"]),
        "dependencies": dependency_group_map,
        "dependency_groups": groups,
        "dependency_ids": dependency_ids,
        "dependencies_internal": groups,
        "gaps": common_gaps,
        "import_notes": common_import_notes,
        "gap_import_notes": " ".join(common_gaps),
        "gaps_import_notes": gaps,
        "making_ladder": common_ladder,
        "making_ladder_detail": making_ladder,
        "upstream": upstream_links,
        "downstream": downstream_links,
        "related": related_links,
        "upstream_links": upstream_links,
        "downstream_links": downstream_links,
        "related_links": related_links,
        "upstream_ids": upstream_links,
        "downstream_ids": downstream_links,
        "related_ids": related_links,
        "provenance_note": "Curated ontology template for V1 breadth; no company directory, exact capacity, product specification, or research claim is asserted.",
        "source_basis": "ASSUMPTION: curated archetype taxonomy; no web research or company/facility claim.",
        "source_spec": "data.india_v1.domains_05_08",
    }


def _generate_domain_records(domain_meta: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    profile_count = int(domain_meta["variant_profile_count"])
    records: list[dict[str, Any]] = []
    for blueprint in domain_meta["archetypes"]:
        profile = PROFILES[str(blueprint["profile"])]
        axes = [options for _, options in profile["axes"]]
        combinations = tuple(product(*axes))
        if len(combinations) != profile_count:
            raise AssertionError(f"profile {blueprint['profile']} generated {len(combinations)} variants, expected {profile_count}")
        for combo in combinations:
            records.append(_build_record(domain_meta, blueprint, combo))
    records.sort(key=lambda record: str(record["id"]))
    return tuple(records)


DOMAIN_RECORDS_BY_DOMAIN: dict[str, tuple[dict[str, Any], ...]] = {
    domain_id: _generate_domain_records(DOMAIN_METADATA[domain_id]) for domain_id in DOMAIN_ORDER
}

ALL_RECORDS: tuple[dict[str, Any], ...] = tuple(
    record for domain_id in DOMAIN_ORDER for record in DOMAIN_RECORDS_BY_DOMAIN[domain_id]
)


# ``DOMAIN_SPECS`` follows the sibling packet contract: a list of compact
# domain/archetype declarations.  The generated record stream is exposed
# separately so callers can choose ontology expansion or ready-to-ingest rows.
DOMAIN_SPECS: list[dict[str, Any]] = [
    {
        "code": domain_id,
        "key": str(DOMAIN_METADATA[domain_id]["short_name"]),
        "name": str(DOMAIN_METADATA[domain_id]["domain"]),
        "purpose": str(DOMAIN_METADATA[domain_id]["coverage_note"]),
        "variant_group": f"domain_{domain_id}_compatible_axes",
        "archetypes": [
            {
                "slug": str(blueprint["id"]),
                "name": str(blueprint["name"]),
                "category": str(blueprint["category"]),
                "kind": str(blueprint["kind"]),
                "profile": str(blueprint["profile"]),
                "status": str(blueprint["status"]),
                "aliases": list(blueprint["aliases"]),
                "uses": [str(blueprint["use_template"])],
                "explanation": str(blueprint["explanation"]),
                "gap": " ".join(str(note) for note in blueprint["gaps"]),
                "variant_axes": [
                    {
                        "name": str(axis_name),
                        "values": [str(option["key"]) for option in options],
                        "labels": [str(option["label"]) for option in options],
                    }
                    for axis_name, options in PROFILES[str(blueprint["profile"])] ["axes"]
                ],
            }
            for blueprint in DOMAIN_METADATA[domain_id]["archetypes"]
        ],
        "records": DOMAIN_RECORDS_BY_DOMAIN[domain_id],
    }
    for domain_id in DOMAIN_ORDER
]

DOMAINS_05_08 = DOMAIN_SPECS
DOMAINS = {str(spec["key"]): spec for spec in DOMAIN_SPECS}
DOMAIN_RECORDS = {
    str(spec["key"]): DOMAIN_RECORDS_BY_DOMAIN[str(spec["code"])] for spec in DOMAIN_SPECS
}
DOMAIN_COUNTS = {domain_id: len(records) for domain_id, records in DOMAIN_RECORDS.items()}
RECORDS = ALL_RECORDS
DOMAIN_RECORDS_FLAT = ALL_RECORDS


def iter_records(domain_id: str | None = None):
    """Yield records in stable domain/id order for registry ingestion."""

    if domain_id is None:
        yield from ALL_RECORDS
        return
    key = str(domain_id)
    if key not in DOMAIN_RECORDS_BY_DOMAIN:
        raise KeyError(f"unknown India V1 domain: {domain_id}")
    yield from DOMAIN_RECORDS_BY_DOMAIN[key]


def generate_domain_records(domain_id: str | int) -> tuple[dict[str, Any], ...]:
    """Return one generated domain in stable order (code or short key accepted)."""

    key = str(domain_id)
    aliases = {
        str(meta["short_name"]): code for code, meta in DOMAIN_METADATA.items()
    }
    key = aliases.get(key, key.zfill(2) if key.isdigit() else key)
    if key not in DOMAIN_RECORDS_BY_DOMAIN:
        raise KeyError(f"unknown India V1 domain: {domain_id!r}")
    return DOMAIN_RECORDS_BY_DOMAIN[key]


def validate_records(records: Iterable[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    """Run local breadth-contract checks without mutating generated records."""

    rows = list(ALL_RECORDS if records is None else records)
    errors: list[str] = []
    ids: set[str] = set()
    counts: dict[str, int] = {}
    allowed_statuses = {"STRONG", "AVAILABLE", "PARTIAL", "SCALE_LIMITED", "IMPORT_DEPENDENT", "MISSING", "UNKNOWN", "CONFLICTED"}
    for index, row in enumerate(rows):
        record_id = str(row.get("id", ""))
        if not record_id:
            errors.append(f"row {index}: missing id")
        elif record_id in ids:
            errors.append(f"duplicate id: {record_id}")
        ids.add(record_id)
        domain_id = str(row.get("domain_id", ""))
        counts[domain_id] = counts.get(domain_id, 0) + 1
        for field in ("canonical_name", "aliases", "kind", "category", "explanation", "use", "india_status", "status_basis", "dependencies", "gaps", "import_notes", "making_ladder", "upstream", "downstream", "related"):
            if row.get(field) in (None, "", [], (), {}):
                errors.append(f"{record_id or index}: missing {field}")
        dependencies = row.get("dependencies", {})
        flat = [ref for values in dependencies.values() for ref in values] if isinstance(dependencies, Mapping) else []
        if not 5 <= len(set(flat)) <= 30:
            errors.append(f"{record_id}: dependency count outside 5..30 ({len(set(flat))})")
        if row.get("status") not in allowed_statuses:
            errors.append(f"{record_id}: invalid normalized status {row.get('status')!r}")
        if row.get("epistemic_class") not in {"MEASURED", "REPORTED", "DERIVED", "ESTIMATED", "MODELLED", "ASSUMPTION", "SCENARIO", "UNKNOWN", "CONFLICTED"}:
            errors.append(f"{record_id}: invalid epistemic class {row.get('epistemic_class')!r}")
        if len(row.get("making_ladder", ())) < 4:
            errors.append(f"{record_id}: making ladder too short")
    return {
        "ok": not errors,
        "record_count": len(rows),
        "domain_counts": dict(sorted(counts.items())),
        "expected_domain_counts": {code: int(meta["record_count"]) for code, meta in DOMAIN_METADATA.items()},
        "unique_ids": len(ids),
        "errors": errors,
    }


def assert_valid(records: Iterable[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    report = validate_records(records)
    if not report["ok"]:
        raise ValueError("India V1 domains 05-08 validation failed: " + "; ".join(report["errors"][:8]))
    return report


def domain_counts() -> dict[str, int]:
    """Return deterministic generated-record counts for validation and manifests."""

    return {domain_id: len(DOMAIN_RECORDS_BY_DOMAIN[domain_id]) for domain_id in DOMAIN_ORDER}


__all__ = [
    "SCHEMA_VERSION",
    "DOMAIN_ORDER",
    "DOMAIN_METADATA",
    "DOMAIN_SPECS",
    "DOMAINS_05_08",
    "DOMAINS",
    "DOMAIN_COUNTS",
    "DOMAIN_RECORDS_BY_DOMAIN",
    "DOMAIN_RECORDS",
    "DOMAIN_RECORDS_FLAT",
    "ALL_RECORDS",
    "RECORDS",
    "iter_records",
    "generate_domain_records",
    "validate_records",
    "assert_valid",
    "domain_counts",
]
