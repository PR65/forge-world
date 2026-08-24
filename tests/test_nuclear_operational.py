"""Operational-depth and epistemic checks for the nuclear programme pack.

The pack remains an annual-flow recipe benchmark, but its ``program_model`` is a
structured multi-year input for generic program consumers.  These tests intentionally
check the raw program rows as well as the executable product/recipe graph.
"""

import os

import pytest

from forge.capacity import capacity_envelope
from forge.evidence import ProofGraph
from forge.explode import explode_variant
from forge.pack import load_pack
from forge.operations import program_timeline
from forge.shocks import apply_shocks
from forge.solve import ScenarioOptions


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _pack():
    return load_pack(os.path.join(ROOT, "packs", "nuclear_buildout_india.yaml"))


def test_program_model_preserves_policy_scenario_and_flow_stock_semantics():
    pk = _pack()
    model = pk.raw["program_model"]
    objective = model["objective"]

    assert objective["target_gw"] == pytest.approx(200.0)
    assert objective["start_year"] == 2026
    assert objective["target_year"] == 2047
    assert objective["epistemic_class"] == "SCENARIO"
    assert objective["existing_capacity_gw"] == pytest.approx(8.78)
    assert objective["existing_capacity_gw_metadata"]["epistemic_class"] == "REPORTED"
    assert objective["existing_capacity_gw_metadata"]["evidence_ids"] == [
        "ev_nuclear_current_capacity_878"
    ]
    assert objective["policy_comparator"]["target_gw"] == pytest.approx(100.0)
    assert objective["policy_comparator"]["target_year"] == 2047
    assert objective["policy_comparator"]["epistemic_class"] == "REPORTED"

    accounting = objective["accounting"]
    assert accounting["annual_production_flow"]["semantic_class"] == "FLOW"
    assert accounting["annual_production_flow"]["unit"] == "kits/yr"
    assert accounting["cumulative_installed_capacity"]["semantic_class"] == "STOCK"
    assert accounting["cumulative_installed_capacity"]["unit"] == "GWe"
    assert accounting["operational_generation"]["epistemic_class"] == "UNKNOWN"

    projection = program_timeline(pk)
    assert projection["available"] is True
    assert projection["projection_type"] == "DECLARED_TRANCHE_SCENARIO"
    assert projection["annual_projection"][0]["year"] == 2026
    assert projection["annual_projection"][-1]["year"] == 2047
    assert projection["annual_projection"][-1]["commissioned_gw_optimistic"] >= 8.78


def test_program_tranches_and_gates_form_a_temporal_connected_graph():
    pk = _pack()
    model = pk.raw["program_model"]
    tranches = model["tranches"]
    gates = model["system_gates"]
    world_ids = set(pk.world.entities)

    assert len(tranches) >= 3
    assert {t["reactor_family"] for t in tranches} >= {"PHWR_700", "LWR_VVER_1000"}
    assert model["capacity_unknowns"][0]["reactor_family"] == "MIXED_FLEET"
    for tranche in tranches:
        assert tranche["start_year"] >= model["objective"]["start_year"]
        assert tranche["construction_years"][0] <= tranche["construction_years"][1]
        assert tranche["commissioning_years"][0] <= tranche["commissioning_years"][1]
        assert tranche["evidence_ids"]
        assert set(tranche["entity_ids"]) <= world_ids

    gate_ids = {gate["id"] for gate in gates}
    assert len(gates) >= 10
    for gate in gates:
        assert gate["earliest_year"] >= model["objective"]["start_year"]
        assert gate["duration_years"][0] <= gate["duration_years"][1]
        assert set(gate["depends_on"]) <= gate_ids
        assert set(gate["entity_ids"]) <= world_ids
        assert gate["evidence_ids"]

    terminal = next(g for g in gates if g["id"] == "gate_integrated_commissioning_and_grid")
    assert len(terminal["depends_on"]) >= 5
    residual = next(
        t for t in model["capacity_unknowns"] if t["id"] == "tr_residual_200gw_scale_unknown"
    )
    assert residual["units"] == "UNKNOWN"
    assert residual["unit_capacity_gw"] == "UNKNOWN"


def test_fleet_architectures_and_recipe_graph_reach_upstream_fuel_cycle():
    pk = _pack()
    model = pk.raw["program_model"]
    architectures = model["fleet_architectures"]
    dependency_edges = model["industrial_dependency_edges"]
    world_ids = set(pk.world.entities)

    assert {a["id"] for a in architectures} >= {
        "arch_phwr_heavy_700mwe",
        "arch_mixed_phwr_lwr",
        "arch_smr_development_context",
    }
    for architecture in architectures:
        assert architecture["evidence_ids"]
        assert set(architecture["shared_entity_ids"]) <= world_ids
        assert set(architecture["distinctive_entity_ids"]) <= world_ids

    for edge in dependency_edges:
        assert edge["from_entity"] in world_ids
        assert edge["to_entity"] in world_ids

    ex = explode_variant(
        pk.world,
        ProofGraph(),
        "reactor_island_1gw_annual",
        1,
        [2035],
        geography="INDIA",
    )
    for item_id in (
        "phwr_fuel_bundle",
        "uranium_dioxide_powder",
        "mat_natural_uranium_concentrate",
        "zirconium_sponge",
        "spent_fuel_reprocessing",
        "vitrified_high_level_waste",
        "plant_electrical_system",
        "generator_step_up_transformer",
    ):
        assert ex.get(item_id) is not None, item_id
        assert ex.get(item_id).net_annual.value > 0
    assert max(line.depth for line in ex.lines.values()) >= 5


def test_qualification_chain_covers_pressure_boundary_materials_and_backend():
    pk = _pack()
    qualifications = {q.id: q for q in pk.world.of_kind("qualification")}
    required = {
        "qual_large_forging",
        "qual_pressure_boundary",
        "qual_zirconium_material",
        "qual_front_end_fuel",
        "qual_fuel_bundle",
        "qual_reprocessing",
        "qual_electrical_system",
    }
    assert required <= set(qualifications)

    recipes = {r.id: r for r in pk.world.of_kind("recipe")}
    for recipe_id in (
        "rec_large_forged_shell",
        "rec_reactor_pressure_boundary",
        "rec_zirconium_alloy_tube",
        "rec_phwr_fuel_bundle",
        "rec_spent_fuel_reprocessing",
        "rec_plant_electrical_system",
    ):
        recipe = recipes[recipe_id]
        assert recipe.requires_qualification
        assert set(recipe.requires_qualification) <= set(qualifications)
        assert recipe.evidence_ids

    assert "ev_aerb_qa_gates" in qualifications["qual_pressure_boundary"].evidence_ids
    assert "ev_barc_reprocessing_scope" in qualifications["qual_reprocessing"].evidence_ids
    assert qualifications["qual_reprocessing"].latency_months[1] >= 60


def test_official_facilities_are_evidence_backed_without_fabricated_capacity():
    pk = _pack()
    facilities = {f.id: f for f in pk.world.of_kind("facility")}
    assert {
        "fac_nfc_hyderabad",
        "fac_nfc_zirconium_tuticorin",
        "fac_ucil_jaduguda",
        "fac_hwb_network",
        "fac_barc_tarapur_prefre",
        "fac_barc_kalpakkam_karp",
    } <= set(facilities)
    for facility in facilities.values():
        assert facility.evidence_ids
        assert facility.owner_org in pk.world.entities
        assert facility.operator_org in pk.world.entities

    claims = {c.capability_item: c for c in pk.world.of_kind("capability_claim")}
    for item_id in (
        "large_forged_shell",
        "reactor_pressure_boundary",
        "phwr_fuel_bundle",
        "mat_natural_uranium_concentrate",
        "heavy_water_inventory",
        "spent_fuel_reprocessing",
    ):
        assert claims[item_id].vector.get("qualified_effective_capacity") == "UNKNOWN"
        assert claims[item_id].evidence_ids

    assert not pk.world.of_kind("capacity_segment")
    assert capacity_envelope(pk.world, "large_forged_shell", 2035, geography="INDIA").domestic.is_unknown()
    assert capacity_envelope(pk.world, "phwr_fuel_bundle", 2035, geography="INDIA").domestic.is_unknown()


def test_facility_material_and_project_shocks_edit_causal_constraints():
    pk = _pack()
    pg = ProofGraph()
    opts = ScenarioOptions(geography="INDIA", min_domestic_share=0.0)
    raw_shocks = {row["id"]: row for row in pk.raw["shocks"]}
    assert raw_shocks["shk_nuclear_forging_facility_outage"]["facility_ids"] == ["fac_nfc_hyderabad"]
    assert raw_shocks["shk_nuclear_heavy_water_material_disruption"]["material_ids"] == [
        "heavy_water_inventory",
        "mat_heavy_water_feedstock",
    ]
    assert raw_shocks["shk_nuclear_project_qualification_delay"]["project_ids"] == [
        "prj_heavy_forging_qualification_scenario"
    ]

    w_forge, o_forge, report_forge = apply_shocks(
        pk.world, pg, ["shk_nuclear_forging_facility_outage"], opts
    )
    assert report_forge.rejected_edits == []
    assert o_forge.equipment_hour_limits["heavy_forging_press"] == 0
    assert any(e["edit"] == "equipment_limit" for e in report_forge.applied_edits)
    assert w_forge is not pk.world

    _w_material, o_material, report_material = apply_shocks(
        pk.world, pg, ["shk_nuclear_heavy_water_material_disruption"], opts
    )
    assert report_material.rejected_edits == []
    assert o_material.competing_demand_cuts["heavy_water_inventory"] > 0

    base_project_window = pk.world.get("prj_heavy_forging_qualification_scenario").years_to_commission
    base_qualification_window = pk.world.get("qual_large_forging").latency_months
    w_delay, _o_delay, report_delay = apply_shocks(
        pk.world, pg, ["shk_nuclear_project_qualification_delay"], opts
    )
    assert report_delay.rejected_edits == []
    assert w_delay.get("prj_heavy_forging_qualification_scenario").years_to_commission == (
        base_project_window[0] + 2,
        base_project_window[1] + 2,
    )
    assert w_delay.get("qual_large_forging").latency_months == (
        base_qualification_window[0] + 24,
        base_qualification_window[1] + 24,
    )
    assert any(e["edit"] == "project_delay" for e in report_delay.applied_edits)
    assert any(e["edit"] == "qualification_delay" for e in report_delay.applied_edits)
