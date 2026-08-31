"""Deterministic engineering fixtures for objective-compiler validation.

Fixtures exercise the compiler; they are not national datasets.  Every value is
either linked to an existing repository evidence identifier or explicitly
labelled ASSUMPTION.  Consumers must surface that label unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass

from .objective_models import ArchitectureNodeKind, CoefficientState


@dataclass(frozen=True)
class FixtureEdge:
    parent: str
    child: str
    child_label: str
    child_kind: ArchitectureNodeKind
    value: float | None
    unit: str = "pcs"
    state: CoefficientState = CoefficientState.ASSUMPTION
    evidence_ids: tuple[str, ...] = ()
    note: str = "Deterministic compiler fixture assumption; not national production truth."


@dataclass(frozen=True)
class FixtureCapacity:
    node: str
    lo: float | None
    hi: float | None
    unit: str = "pcs"
    epistemic_class: str = "ASSUMPTION"
    evidence_ids: tuple[str, ...] = ()
    note: str = "Deterministic compiler fixture assumption; verify before real-world use."


@dataclass(frozen=True)
class ObjectiveFixture:
    fixture_id: str
    family_keys: tuple[str, ...]
    edges: tuple[FixtureEdge, ...]
    capacities: tuple[FixtureCapacity, ...] = ()


FIXTURES: tuple[ObjectiveFixture, ...] = (
    ObjectiveFixture(
        "industrial_robot",
        ("product:05:industrial-robot",),
        (
            FixtureEdge("root", "servo_motor", "Industrial servo motor", ArchitectureNodeKind.PRODUCT_COMPONENT, 6.0),
            FixtureEdge("root", "precision_reducer", "Precision reducer", ArchitectureNodeKind.PRODUCT_COMPONENT, 6.0),
            FixtureEdge("root", "robot_controller", "Robot controller", ArchitectureNodeKind.PRODUCT_COMPONENT, 1.0),
            FixtureEdge("root", "machine_vision", "Machine-vision system", ArchitectureNodeKind.PRODUCT_COMPONENT, 1.0),
            FixtureEdge("servo_motor", "motor_encoder", "Optical or magnetic encoder", ArchitectureNodeKind.PRODUCT_COMPONENT, None, state=CoefficientState.UNKNOWN, note="Encoder count depends on the selected servo architecture."),
        ),
        (
            FixtureCapacity("servo_motor", 250_000.0, 250_000.0),
        ),
    ),
    ObjectiveFixture(
        "grid_transformer",
        ("d03:product:grid_transformer", "india-v1:10:power-transformer"),
        (
            FixtureEdge("root", "magnetic_core", "Magnetic core set", ArchitectureNodeKind.PRODUCT_COMPONENT, 1.0),
            FixtureEdge("root", "winding_set", "Winding set", ArchitectureNodeKind.PRODUCT_COMPONENT, 1.0),
            FixtureEdge("root", "insulation_system", "High-voltage insulation system", ArchitectureNodeKind.PRODUCT_COMPONENT, 1.0),
            FixtureEdge("root", "tank_cooling", "Tank and cooling assembly", ArchitectureNodeKind.PRODUCT_COMPONENT, 1.0),
            FixtureEdge("winding_set", "copper_conductor", "Electrical copper conductor", ArchitectureNodeKind.MATERIAL, None, unit="kg_product", state=CoefficientState.UNKNOWN, note="Conductor mass depends on transformer rating and design."),
        ),
    ),
    ObjectiveFixture(
        "cnc_machining_center",
        ("product:05:5-axis-cnc-machining-center", "india-v1:12:cnc-machining-center"),
        (
            FixtureEdge("root", "machine_bed", "Machine bed casting", ArchitectureNodeKind.PRODUCT_COMPONENT, 1.0, state=CoefficientState.SUPPORTED, evidence_ids=("ev_cnc_bom_quantities",)),
            FixtureEdge("root", "spindle_cartridge", "Spindle cartridge", ArchitectureNodeKind.PRODUCT_COMPONENT, 1.0, state=CoefficientState.SUPPORTED, evidence_ids=("ev_cnc_bom_quantities",)),
            FixtureEdge("root", "ball_screw_set", "Ball-screw set", ArchitectureNodeKind.PRODUCT_COMPONENT, 3.0, state=CoefficientState.SUPPORTED, evidence_ids=("ev_cnc_bom_quantities",)),
            FixtureEdge("root", "servo_motor_axis", "Axis servo motor", ArchitectureNodeKind.PRODUCT_COMPONENT, 3.0, state=CoefficientState.SUPPORTED, evidence_ids=("ev_cnc_bom_quantities",)),
            FixtureEdge("root", "cnc_controller", "CNC controller", ArchitectureNodeKind.PRODUCT_COMPONENT, 1.0, state=CoefficientState.SUPPORTED, evidence_ids=("ev_cnc_bom_quantities",)),
            FixtureEdge("root", "metrology_kit", "Metrology acceptance kit", ArchitectureNodeKind.METROLOGY, 1.0, state=CoefficientState.SUPPORTED, evidence_ids=("ev_cnc_bom_quantities",)),
        ),
    ),
    ObjectiveFixture(
        "centrifugal_pump",
        ("product:06:centrifugal-pump", "india-v1:12:centrifugal-pump"),
        (
            FixtureEdge("root", "pump_casing", "Pump casing", ArchitectureNodeKind.PRODUCT_COMPONENT, 1.0),
            FixtureEdge("root", "impeller", "Impeller", ArchitectureNodeKind.PRODUCT_COMPONENT, 1.0),
            FixtureEdge("root", "shaft_bearing_set", "Shaft and bearing set", ArchitectureNodeKind.PRODUCT_COMPONENT, 1.0),
            FixtureEdge("root", "mechanical_seal", "Mechanical seal", ArchitectureNodeKind.PRODUCT_COMPONENT, 1.0),
            FixtureEdge("root", "pump_motor", "Industrial motor", ArchitectureNodeKind.PRODUCT_COMPONENT, 1.0),
        ),
    ),
    ObjectiveFixture(
        "hemodialysis_machine",
        ("product:07:dialysis-machine",),
        (
            FixtureEdge("root", "blood_pump", "Blood-circuit pump", ArchitectureNodeKind.PRODUCT_COMPONENT, 1.0),
            FixtureEdge("root", "dialysate_path", "Dialysate preparation and fluid path", ArchitectureNodeKind.PRODUCT_SYSTEM, 1.0),
            FixtureEdge("root", "sensor_alarm_set", "Sensor and alarm set", ArchitectureNodeKind.PRODUCT_COMPONENT, 1.0),
            FixtureEdge("root", "dialyzer_interface", "Dialyzer interface", ArchitectureNodeKind.PRODUCT_COMPONENT, 1.0),
            FixtureEdge("dialysate_path", "medical_water", "Medical-grade water", ArchitectureNodeKind.MATERIAL, None, unit="kg_product", state=CoefficientState.UNKNOWN, note="Water demand depends on treatment modality and operating protocol."),
        ),
    ),
    # Mandatory generalization fixture: this family was not in the launch
    # candidate's hand-written _PRODUCT_ARCHITECTURES table.
    ObjectiveFixture(
        "air_jet_loom",
        ("india-v1:11:textile-weaving-machine:air-jet-loom",),
        (
            FixtureEdge("root", "loom_frame", "Loom frame and beam system", ArchitectureNodeKind.PRODUCT_SYSTEM, 1.0),
            FixtureEdge("root", "shedding_system", "Shedding and warp-control system", ArchitectureNodeKind.PRODUCT_SYSTEM, 1.0),
            FixtureEdge("root", "air_insertion", "Air-jet insertion system", ArchitectureNodeKind.PRODUCT_SYSTEM, 1.0),
            FixtureEdge("root", "loom_controls", "Loom controls and drives", ArchitectureNodeKind.PRODUCT_SYSTEM, 1.0),
            FixtureEdge("air_insertion", "relay_nozzle_set", "Main and relay nozzle set", ArchitectureNodeKind.PRODUCT_COMPONENT, None, state=CoefficientState.UNKNOWN, note="Nozzle count is configuration-dependent and must be verified."),
        ),
    ),
)


def fixture_for_family(family_key: str) -> ObjectiveFixture | None:
    return next((fixture for fixture in FIXTURES if family_key in fixture.family_keys), None)


__all__ = [
    "FixtureEdge",
    "FixtureCapacity",
    "ObjectiveFixture",
    "FIXTURES",
    "fixture_for_family",
]
