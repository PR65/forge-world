"""Focused operational depth checks for the humanoid benchmark pack.

These tests intentionally inspect the pack's industrial graph rather than assert a
headline feasibility result.  The benchmark remains scenario- and evidence-limited:
official product scope is not promoted to qualified capacity, and modelled upstream
coefficients are labelled assumptions in the pack.
"""

from __future__ import annotations

import os

import pytest

from forge.capacity import capacity_envelope
from forge.evidence import ProofGraph
from forge.explode import explode_variant
from forge.pack import load_pack
from forge.shocks import apply_shocks
from forge.solve import ScenarioOptions
from forge.substitutions import apply_substitution


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _humanoid():
    return load_pack(os.path.join(ROOT, "packs", "humanoid_india.yaml"))


def test_hv2_component_scale_demand_is_explicit():
    """One million units expands to tens of millions of motion components."""
    pk = _humanoid()
    ex = explode_variant(
        pk.world, ProofGraph(), "hv2_industrial", 1_000_000, [2030], geography="INDIA"
    )

    assert ex.get("actuator_rotary_body").net_annual.value == pytest.approx(30_000_000)
    assert ex.get("micro_actuator_hand").net_annual.value == pytest.approx(14_000_000)
    assert ex.get("crossed_roller_bearing").net_annual.value >= 60_000_000
    assert ex.get("absolute_encoder").net_annual.value >= 60_000_000
    assert ex.get("motor_driver_inverter").net_annual.value >= 44_000_000
    assert ex.get("battery_cell_liion").net_annual.value >= 100_000_000
    assert ex.get("power_distribution_unit").net_annual.value == pytest.approx(1_000_000)
    assert ex.get("safety_controller").net_annual.value == pytest.approx(1_000_000)


def test_upstream_material_chain_and_process_equipment_are_traversable():
    """Magnet and battery demand recurse through explicit upstream/process nodes."""
    pk = _humanoid()
    ex = explode_variant(
        pk.world, ProofGraph(), "hv2_industrial", 1_000_000, [2030], geography="INDIA"
    )

    # NdFeB chain: magnet -> oxide -> carbonate -> concentrate -> mineral feed -> raw ore.
    for item in (
        "ndfeb_magnet",
        "reo_ndpr_oxide",
        "ndpr_mixed_carbonate",
        "mat_rare_earth_concentrate",
        "monazite_mineral_feed",
        "monazite_ore_raw",
    ):
        assert ex.get(item) is not None, item
        assert ex.get(item).net_annual.value > 0, item

    # Battery chain is present too, and it is not silently a cell-only BOM.
    for item in ("battery_cell_liion", "lithium_carbonate", "mat_lithium_brine_intermediate", "lithium_mineral_feed", "iron_phosphate", "mat_phosphate_rock"):
        assert ex.get(item) is not None, item

    rv = pk.world.require("rec_rv_reducer")
    rv_equipment = {
        equipment
        for step in rv.steps
        for equipment in step.equipment_classes
    }
    assert {"precision_gear_grinder", "vacuum_furnace", "metrology_cmm"} <= rv_equipment
    oxide = pk.world.require("rec_ndpr_oxide_grade")
    oxide_equipment = {equipment for step in oxide.steps for equipment in step.equipment_classes}
    assert {"hydrometallurgy_leach_line", "solvent_extraction_line", "calcination_furnace"} <= oxide_equipment


def test_rv_reducer_substitution_rewrites_dependencies_and_is_immutable():
    """The reducer-family alternative changes the graph, not just a displayed number."""
    pk = _humanoid()
    pg = ProofGraph()
    baseline = explode_variant(
        pk.world, pg, "hv2_industrial", 100_000, [2030], geography="INDIA"
    )
    snapshot = {
        item: (line.net_annual.value, line.gross_annual.value, line.via_recipe)
        for item, line in baseline.lines.items()
    }

    rewritten = apply_substitution(
        pk.world, pg, baseline, pk.substitutions["sub_body_actuator_rv_reducer"]
    )

    assert rewritten.get("actuator_rotary_body").via_recipe == "rec_joint_actuator_rv"
    assert rewritten.get("rv_reducer") is not None
    assert rewritten.get("rv_pin_steel") is not None
    assert rewritten.get("rv_case_steel") is not None
    assert baseline.get("rv_reducer") is None
    assert baseline.get("rv_pin_steel") is None
    assert baseline.get("rv_case_steel") is None
    assert rewritten.get("harmonic_reducer").net_annual.value < baseline.get("harmonic_reducer").net_annual.value

    # The original graph/result remains unchanged after the rewrite.
    after = {
        item: (line.net_annual.value, line.gross_annual.value, line.via_recipe)
        for item, line in baseline.lines.items()
    }
    assert after == snapshot
    assert any(
        edge.src == "actuator_rotary_body"
        and edge.dst == "rv_reducer"
        and edge.route == "rec_joint_actuator_rv"
        for edge in rewritten.flows.edges
    )
    assert not any(
        edge.src == "actuator_rotary_body"
        and edge.dst == "harmonic_reducer"
        and edge.route == "rec_joint_actuator_rv"
        for edge in rewritten.flows.edges
    )


def test_country_and_material_shocks_edit_the_world_not_the_output():
    pk = _humanoid()
    pg = ProofGraph()
    before_project = pk.world.require("prj_repm_6000t").design_capacity_annual.value
    opts = ScenarioOptions(min_domestic_share=0.7)

    shocked_world, shocked_opts, report = apply_shocks(
        pk.world,
        pg,
        ["shk_exclude_china", "shk_ndfeb_material_cut"],
        opts,
    )

    assert shocked_opts.import_eligibility["CHN"] == 0.0
    assert any(e["edit"] == "import_eligibility" and e["origin"] == "CHN" for e in report.applied_edits)
    assert any(e["edit"] == "capacity_multiplier" and e["item"] == "ndfeb_magnet" for e in report.applied_edits)
    assert shocked_world.require("prj_repm_6000t").design_capacity_annual.value == pytest.approx(
        before_project * 0.2
    )
    # Shock cloning does not mutate the baseline project or options.
    assert pk.world.require("prj_repm_6000t").design_capacity_annual.value == before_project
    assert "CHN" not in opts.import_eligibility


def test_scenario_presets_and_structured_unknowns_are_explicit():
    pk = _humanoid()
    presets = {row["id"]: row for row in pk.raw["scenario_presets"]}
    assert {
        "sc_world_hv2_1m_2030",
        "sc_india_dva70_hv2_1m_2030",
        "sc_exclude_china_hv2_1m_2030",
        "sc_no_chinese_magnets_hv2_1m_2030",
    } <= set(presets)
    assert presets["sc_world_hv2_1m_2030"]["geography"] == "GLOBAL"
    assert presets["sc_india_dva70_hv2_1m_2030"]["min_dva"] == pytest.approx(0.7)
    assert presets["sc_exclude_china_hv2_1m_2030"]["shock_ids"] == ["shk_exclude_china"]
    assert set(presets["sc_no_chinese_magnets_hv2_1m_2030"]["substitution_ids"]) == {
        "sub_ree_free_actuation",
        "sub_ree_free_hand_actuation",
    }

    required = {
        "id",
        "title",
        "question",
        "target_entity_id",
        "missing_variable",
        "decision",
        "priority",
        "suggested_source_types",
        "capture_fields",
    }
    tasks = pk.raw["research_tasks"]
    assert len(tasks) >= 10
    assert all(required <= set(task) for task in tasks)
    assert all(task.get("status") == "UNKNOWN" for task in tasks)
    assert {task["target_entity_id"] for task in tasks} >= {
        "harmonic_reducer",
        "rv_reducer",
        "crossed_roller_bearing",
        "absolute_encoder",
        "battery_cell_liion",
        "edge_compute_module",
    }


def test_official_product_scope_never_becomes_capacity():
    """Supplier identity/product scope links are present while exact capacities stay UNKNOWN."""
    pk = _humanoid()
    for item, facility, evidence in (
        ("harmonic_reducer", "fac_harmonicdrive_scope_unknown", "ev_harmonicdrive_scope"),
        ("rv_reducer", "fac_nabtesco_rv_scope_unknown", "ev_nabtesco_rv_scope"),
        ("crossed_roller_bearing", "fac_nsk_crossroller_scope_unknown", "ev_nsk_crossroller_scope"),
        ("absolute_encoder", "fac_renishaw_encoder_scope_unknown", "ev_renishaw_encoder_scope"),
    ):
        segment = next(
            seg for seg in pk.world.of_kind("capacity_segment") if seg.item_id == item
        )
        assert segment.facility_id == facility
        assert segment.nameplate_annual is None
        assert segment.epistemic_class == "UNKNOWN"
        assert evidence in segment.evidence_ids or "ev_precision_motion_capacity_unknown" in segment.evidence_ids
        env = capacity_envelope(pk.world, item, 2030, geography="INDIA")
        assert env.domestic.is_unknown()

    # Official scope is still visible in canonical entities and evidence records.
    assert pk.world.require("org_nabtesco").evidence_ids == ("ev_nabtesco_rv_scope",)
    assert pk.world.require("org_renishaw").evidence_ids == ("ev_renishaw_encoder_scope",)
    assert pk.evidence["ev_precision_motion_capacity_unknown"].epistemic_class.value == "UNKNOWN"
