"""Truthfulness and arithmetic checks for the alpha CNC and nuclear packs."""

import os

import pytest

from forge.capacity import capacity_envelope
from forge.evidence import ProofGraph
from forge.explode import explode_variant
from forge.pack import load_pack
from forge.solve import ScenarioOptions, solve_objective


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _pack(pack_id):
    return load_pack(os.path.join(ROOT, "packs", f"{pack_id}.yaml"))


@pytest.mark.parametrize("pack_id", ["cnc_machining_india", "nuclear_buildout_india"])
def test_alpha_packs_load_with_licensed_sources_and_evidence(pack_id):
    pk = _pack(pack_id)
    assert len(pk.variants) == 1
    assert len(pk.world.entities) > 40
    assert pk.sources
    assert pk.evidence

    for source in pk.sources.values():
        assert source.license and source.license != "UNSPECIFIED"

    for evidence in pk.evidence.values():
        for source_id in evidence.source_ids:
            assert source_id in pk.sources
        if evidence.epistemic_class.value in {"MEASURED", "REPORTED"}:
            assert evidence.source_ids, evidence.claim_id
            assert evidence.license != "UNSPECIFIED", evidence.claim_id
            for source_id in evidence.source_ids:
                assert pk.sources[source_id].license in evidence.license

    for entity in pk.world.entities.values():
        for evidence_id in getattr(entity, "evidence_ids", ()):
            assert evidence_id in pk.evidence, f"{entity.id}: {evidence_id}"


@pytest.mark.parametrize(
    "pack_id,variant_id,annual_units,expected_net",
    [
        (
            "cnc_machining_india",
            "cnc_vmc_100_per_year",
            100,
            {
                "machine_bed_casting": 100.0,
                "ball_screw_set": 300.0,
                "linear_guide_set": 300.0,
                "servo_motor_axis": 300.0,
                "servo_drive": 300.0,
                "absolute_encoder_axis": 300.0,
                "cnc_controller": 100.0,
                "atc_magazine": 100.0,
                "metrology_acceptance_kit": 100.0,
            },
        ),
        (
            "nuclear_buildout_india",
            "reactor_island_1gw_annual",
            1,
            {
                "reactor_pressure_boundary": 1.0,
                "calandria_and_core": 1.0,
                "pressure_tube_set": 1.0,
                "steam_generator": 4.0,
                "primary_coolant_pump": 4.0,
                "reactor_shutdown_system": 2.0,
                "safety_injection_system": 1.0,
                "containment_liner": 1.0,
                "turbine_generator_set": 1.0,
                "site_civil_works_package": 1.0,
                "fuel_channel_inspection_kit": 1.0,
            },
        ),
    ],
)
def test_alpha_explosion_has_hand_derived_bom_multiples(
    pack_id, variant_id, annual_units, expected_net
):
    pk = _pack(pack_id)
    ex = explode_variant(pk.world, ProofGraph(), variant_id, annual_units, [2030], geography="INDIA")
    for item_id, expected in expected_net.items():
        line = ex.get(item_id)
        assert line is not None, item_id
        assert line.net_annual.value == pytest.approx(expected)
        assert line.net_annual.unit == "pcs"

    # Every expanded line has a proof node, keeping the pack useful to WHY views.
    assert set(ex.items()) == set(ex.proof_node_ids)


@pytest.mark.parametrize(
    "pack_id,variant_id,annual_units,critical_items",
    [
        (
            "cnc_machining_india",
            "cnc_vmc_100_per_year",
            100,
            ["machine_bed_casting", "spindle_bearing", "ball_screw_set", "metrology_acceptance_kit", "cbn_grinding_wheel"],
        ),
        (
            "nuclear_buildout_india",
            "reactor_island_1gw_annual",
            1,
            ["reactor_pressure_boundary", "large_forged_shell", "steam_generator", "heavy_water_inventory", "ultrasonic_ndt_service"],
        ),
    ],
)
def test_alpha_explosion_is_linear_and_reaches_recursive_dependencies(
    pack_id, variant_id, annual_units, critical_items
):
    pk = _pack(pack_id)
    ex_one = explode_variant(pk.world, ProofGraph(), variant_id, annual_units, [2030], geography="INDIA")
    ex_two = explode_variant(pk.world, ProofGraph(), variant_id, annual_units * 2, [2030], geography="INDIA")

    for item_id in critical_items:
        one = ex_one.get(item_id)
        two = ex_two.get(item_id)
        assert one is not None, item_id
        assert two is not None, item_id
        assert two.net_annual.value == pytest.approx(2 * one.net_annual.value)
        assert two.gross_annual.value == pytest.approx(2 * one.gross_annual.value)

    if pack_id == "cnc_machining_india":
        # A single bed route reaches both the grinding wheel and acceptance metrology.
        assert ex_one.get("cbn_grinding_wheel").net_annual.value > 0
        assert ex_one.get("granite_reference_artifact").net_annual.value > 0
        equipment = {e.id for e in pk.world.of_kind("equipment_class")}
        assert {"precision_surface_grinder", "ball_screw_grinder", "metrology_cmm", "laser_interferometer_station"} <= equipment
    else:
        # Pressure tubes and heavy water are recipe descendants, not hidden constants.
        tubes = ex_one.get("pressure_tube_set")
        zirconium = ex_one.get("zirconium_alloy_tube")
        calandria = ex_one.get("calandria_and_core")
        heavy_water = ex_one.get("heavy_water_inventory")
        assert tubes and zirconium and calandria and heavy_water
        assert zirconium.net_annual.value == pytest.approx(tubes.gross_annual.value * 392.0)
        assert heavy_water.net_annual.value == pytest.approx(calandria.gross_annual.value * 500.0)
        equipment = {e.id for e in pk.world.of_kind("equipment_class")}
        assert {"heavy_forging_press", "vacuum_heat_treatment_furnace", "ultrasonic_ndt_station", "large_metrology_lab", "nuclear_calibration_lab"} <= equipment


@pytest.mark.parametrize("pack_id,variant_id,annual_units,unknown_item", [
    ("cnc_machining_india", "cnc_vmc_100_per_year", 100, "spindle_bearing"),
    ("nuclear_buildout_india", "reactor_island_1gw_annual", 1, "large_forged_shell"),
])
def test_alpha_packs_do_not_turn_unknown_capacity_into_supply(
    pack_id, variant_id, annual_units, unknown_item
):
    pk = _pack(pack_id)
    ex = explode_variant(pk.world, ProofGraph(), variant_id, annual_units, [2030], geography="INDIA")
    env = capacity_envelope(pk.world, unknown_item, 2030, geography="INDIA")
    assert env.domestic.is_unknown()

    # There are intentionally no unsupported operating capacity observations.
    for segment in pk.world.of_kind("capacity_segment"):
        assert segment.evidence_ids or segment.epistemic_class not in {"MEASURED", "REPORTED"}

    opts = ScenarioOptions(
        geography="INDIA",
        min_domestic_share=0.0,
        foreign_supply_policy="strict",
    )
    result = solve_objective(pk.world, ProofGraph(), ex, [2030], opts)
    assert result.result_class.value == "NOT_ADJUDICABLE"
    assert result.blocking_unknowns


def test_nuclear_project_capacity_is_explicit_scenario_or_context_only():
    pk = _pack("nuclear_buildout_india")
    projects = pk.world.of_kind("project")
    assert len(projects) >= 3

    for project in projects:
        if project.design_capacity_annual is None:
            # Real programme/order context deliberately has no annual capacity.
            continue
        assert project.evidence_ids
        classes = {pk.evidence[e].epistemic_class.value for e in project.evidence_ids}
        assert classes & {"ASSUMPTION", "SCENARIO"}
        assert "not a government project" in project.notes.lower() or "scenario" in project.notes.lower()


def test_cnc_item_specific_qualification_schedules_are_explicit_assumptions():
    pk = _pack("cnc_machining_india")
    qualifications = pk.world.of_kind("qualification")
    assert qualifications

    for qualification in qualifications:
        classes = {pk.evidence[e].epistemic_class.value for e in qualification.evidence_ids}
        assert "ASSUMPTION" in classes, qualification.id
