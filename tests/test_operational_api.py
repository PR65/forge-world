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
    assert shock.json()["objective_reached_by_causal_path"] is True


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
    comtrade = next(
        row for row in ingestion.json()["pathways"] if row["id"] == "un_comtrade_api"
    )
    assert "never capability" in comtrade["model_role"]


def test_operational_endpoints_reject_unknown_variants():
    response = CLIENT.post(
        "/api/workbench/case",
        json={**CNC_OBJECTIVE, "variant_id": "does_not_exist"},
    )
    assert response.status_code == 400
