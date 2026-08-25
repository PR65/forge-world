import pytest
from fastapi.testclient import TestClient

from server.app import app


CLIENT = TestClient(app)
CNC_OBJECTIVE = {
    "pack_id": "cnc_machining_india",
    "variant_id": "cnc_vmc_100_per_year",
    "annual_units": 100,
    "geography": "INDIA",
    "deadline_year": 2030,
    "min_dva": 0.7,
    "funded_projects": ["__baseline_none__"],
    "include_deep": False,
}


def test_operational_case_api_projects_one_solver_run_into_action_surfaces():
    response = CLIENT.post("/api/workbench/case", json=CNC_OBJECTIVE)

    assert response.status_code == 200
    body = response.json()
    assert body["brief"]["result_class"] == "NOT_ADJUDICABLE"
    assert body["research"]["count"] >= 3
    assert body["execution"]["make_buy"]
    assert body["reverse_buildability"]["epistemic_class"] == "UNKNOWN"
    reverse_scenario = body["reverse_buildability"]["declared_scenarios"][0]
    assert reverse_scenario["epistemic_class"] == "SCENARIO"
    assert reverse_scenario["ceiling_range_units_per_year"] == [82, 98]
    assert reverse_scenario["assumption_boundary"]["baseline_world_mutated"] is False
    assert reverse_scenario["ranked_interventions"][0]["item_id"] == "machine_bed_casting"
    assert body["registry_snapshot_id"]


def test_design_and_shock_endpoints_return_causal_graph_deltas():
    design = CLIENT.post(
        "/api/design/compare",
        json={**CNC_OBJECTIVE, "substitution_id": "sub_servo_axis_synrm"},
    )
    assert design.status_code == 200
    assert "servo_motor_axis" in design.json()["graph_delta"]["removed_dependencies"]

    shock = CLIENT.post(
        "/api/shocks/impact",
        json={**CNC_OBJECTIVE, "shocks": ["shk_ball_screw_grinder_loss"]},
    )
    assert shock.status_code == 200
    impact = shock.json()
    assert impact["objective_reached_by_causal_path"] is True
    assert "baseline" in impact["deadline_shortfall_vectors"]
    assert "shocked" in impact["deadline_shortfall_vectors"]
    assert isinstance(impact["deadline_shortfall_delta_by_unit"], dict)
    assert len(impact["deadline_shortfall_delta_by_unit"]) >= 2
    assert isinstance(impact["deadline_normalized_deficit_delta"], float)
    assert impact["deadline_shortfall_delta"] is None
    assert impact["deadline_shortfall_delta_unit"] is None
    assert "mixed physical unit families" in impact["deadline_shortfall_delta_semantics"]


def test_discover_program_and_ingestion_endpoints_expose_epistemic_boundaries():
    discover = CLIENT.get("/api/discover/capabilities", params={"limit": 100})
    assert discover.status_code == 200
    assert len(discover.json()["capabilities"]) >= 30
    assert "investment return" in discover.json()["not_claimed"]

    program = CLIENT.get("/api/program/nuclear_buildout_india")
    assert program.status_code == 200
    assert program.json()["projection_type"] == "DECLARED_TRANCHE_SCENARIO"
    assert program.json()["objective"]["accounting"]["annual_production_flow"]["semantic_class"] == "FLOW"
    assert program.json()["objective"]["accounting"]["cumulative_installed_capacity"]["semantic_class"] == "STOCK"

    ingestion = CLIENT.get("/api/ingestion/status")
    assert ingestion.status_code == 200
    assert ingestion.json()["unresolved_world_subjects"] == []
    assert ingestion.json()["targeted_catalog_observations"] == 14
    assert ingestion.json()["targeted_resolved_world_subjects"] == 14
    comtrade = next(
        row for row in ingestion.json()["pathways"] if row["id"] == "un_comtrade_api"
    )
    assert "never capability" in comtrade["model_role"]

    targeted = CLIENT.get("/api/adapter/official/targeted")
    assert targeted.status_code == 200
    assert targeted.json()["pathway"] == "HOMI_TARGETED_PRIMARY_SOURCE_CATALOG"
    assert len(targeted.json()["results"]) == 14


def test_operational_endpoints_reject_unknown_variants():
    response = CLIENT.post(
        "/api/workbench/case",
        json={**CNC_OBJECTIVE, "variant_id": "does_not_exist"},
    )
    assert response.status_code == 400


@pytest.mark.parametrize(
    "invalid_patch",
    [
        {"min_dva": -0.01},
        {"min_dva": 1.01},
        {"budget_usd": -1},
        {"deadline_year": 2025},
        {"analyst_capacity_assumptions": {"motor": [10]}},
        {"analyst_capacity_assumptions": {"motor": [-1, 10]}},
        {"analyst_capacity_assumptions": {"motor": [10, 9]}},
        {"per_item_import_cap": {"motor": -0.01}},
        {"per_item_import_cap": {"motor": 1.01}},
    ],
)
def test_objective_api_rejects_invalid_physical_and_policy_ranges(invalid_patch):
    response = CLIENT.post("/api/solve", json={**CNC_OBJECTIVE, **invalid_patch})

    assert response.status_code == 422


def test_solve_api_applies_explicit_per_item_import_cap():
    response = CLIENT.post(
        "/api/solve",
        json={
            **CNC_OBJECTIVE,
            "min_dva": 0.0,
            "per_item_import_cap": {"machine_bed_casting": 0.0},
        },
    )

    assert response.status_code == 200
    deadline_gaps = response.json()["result"]["years"]["2030"]["shortfalls"]
    casting_gap = next(
        row for row in deadline_gaps if row["item"] == "machine_bed_casting"
    )
    assert casting_gap["imports_used"] == 0.0
    assert casting_gap["shortfall"] > 0.0
