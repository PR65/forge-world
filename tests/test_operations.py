from pathlib import Path

import pytest

from forge.engine import ForgeEngine, ObjectiveSpecInput
from forge.operations import (
    build_case_brief,
    build_execution_plan,
    build_research_queue,
    compare_design,
    reverse_buildability_report,
    shock_impact,
)
from forge.pack import load_pack
from forge.research import process_research_capture


ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def cnc_case():
    pack = load_pack(str(ROOT / "packs" / "cnc_machining_india.yaml"))
    objective = ObjectiveSpecInput(
        variant_id="cnc_vmc_100_per_year",
        annual_units=100,
        geography="INDIA",
        deadline_year=2030,
        min_dva=0.70,
        funded_projects=["__baseline_none__"],
    )
    response = ForgeEngine(pack).run_scenario(objective, include_deep=False)
    return pack, objective, response


def test_operational_case_exposes_conclusion_research_and_execution(cnc_case):
    pack, objective, response = cnc_case
    research = build_research_queue(pack, objective, response)
    execution = build_execution_plan(pack, objective, response, research)
    brief = build_case_brief(pack, objective, response, research)

    assert brief["result_class"] == "NOT_ADJUDICABLE"
    assert brief["top_bottlenecks"]
    assert brief["important_unknowns"]
    assert {task["id"] for task in research} >= {
        "rq_ballscrew_grade_and_supplier",
        "rq_ballscrew_grinder_machine_hours",
        "rq_ballscrew_metrology_throughput",
    }
    assert any(row["item_id"] == "ball_screw_set" for row in execution["make_buy"])
    assert any(row["recipe_id"] == "rec_ball_screw_set" for row in execution["process_routes"])
    assert any(
        row["equipment_id"] == "ball_screw_grinder"
        for row in execution["machinery_requirements"]
    )
    assert len(execution["work_packages"]) >= 6
    assert all(row["human_approval_required"] for row in execution["work_packages"])


def test_design_comparison_is_a_real_dependency_rewrite(cnc_case):
    pack, objective, _ = cnc_case
    comparison = compare_design(pack, objective, "sub_servo_axis_synrm")

    assert comparison["accepted"] is True
    assert "servo_motor_axis" in comparison["graph_delta"]["removed_dependencies"]
    magnet_delta = next(
        row
        for row in comparison["graph_delta"]["changed_demand"]
        if row["item_id"] == "permanent_magnet"
    )
    assert magnet_delta["delta"] < 0
    assert comparison["graph_delta"]["changed_demand"]
    assert comparison["approval_boundary"]


def test_reverse_buildability_keeps_unknown_as_unknown(cnc_case):
    pack, objective, _ = cnc_case
    report = reverse_buildability_report(pack, objective)

    assert report["max_units_per_year"] is None
    assert report["epistemic_class"] == "UNKNOWN"
    assert report["status"] == "NOT_ADJUDICABLE_AT_ONE_UNIT"
    assert report["interventions"]


def test_declared_reverse_scenario_derives_a_bounded_ceiling_without_mutating_unknown(cnc_case):
    pack, objective, _ = cnc_case
    report = reverse_buildability_report(pack, objective)

    # The evidence-bounded answer remains UNKNOWN. The numerical result lives
    # only inside an explicit, non-persistent scenario boundary.
    assert report["max_units_per_year"] is None
    scenario = report["declared_scenarios"][0]
    assert scenario["scenario_id"] == "cnc_declared_qualification_envelope"
    assert scenario["status"] == "SCENARIO_CEILING_DERIVED"
    assert scenario["epistemic_class"] == "SCENARIO"
    assert scenario["ceiling_range_units_per_year"] == [82, 98]
    assert scenario["assumption_boundary"]["persistent"] is False
    assert scenario["assumption_boundary"]["baseline_world_mutated"] is False
    assert scenario["assumption_boundary"]["import_policy"] == "DOMESTIC_ONLY"
    assert scenario["assumption_boundary"]["explicit_assumption_count"] == 4
    assert scenario["assumption_boundary"]["policy_generated_assumption_count"] > 0
    assert all(
        row["epistemic_class"] == "ASSUMPTION"
        for row in scenario["assumption_boundary"]["assumptions"]
    )
    assert scenario["binding_constraints"] == [
        "machine_bed_casting@2026: shortfall 0.336 pcs/yr"
    ]
    assert scenario["ranked_interventions"][0]["item_id"] == "machine_bed_casting"
    assert scenario["ranked_interventions"][0]["peak_shortfall"] > 0


def test_shock_impact_reaches_the_objective_through_real_edges(cnc_case):
    pack, objective, _ = cnc_case
    impact = shock_impact(pack, objective, ["shk_ball_screw_grinder_loss"])

    assert impact["objective_reached_by_causal_path"] is True
    assert impact["causal_paths"]
    assert impact["applied_edits"]
    assert impact["inventory_posture"].startswith("UNKNOWN")


def test_research_capture_promotes_then_uses_only_an_explicit_scenario_overlay(cnc_case):
    pack, objective, response = cnc_case
    task = next(
        row
        for row in build_research_queue(pack, objective, response)
        if row["target_entity_id"] == "ball_screw_set"
    )
    result = process_research_capture(
        pack,
        objective,
        task,
        {
            "source_id": "supplier-audit-001",
            "source_url": "https://example.invalid/controlled-audit-reference",
            "publisher": "Independent audit team",
            "license": "Confidential reference; metadata retention permitted",
            "source_type": "facility_audit",
            "document_date": "2026-08-20",
            "epistemic_class": "REPORTED",
            "predicate": "qualified_effective_capacity",
            "capacity_range": [250, 300],
            "unit": "pcs/year",
            "technical_scope": "C3/C5 ground ball-screw sets for the active VMC envelope",
            "caveat": "Single audited period; customer allocation and future validity require renewal.",
            "confidence": {"authority": 0.8, "directness": 0.9},
        },
        reviewer="test-reviewer",
        approve_for_scenario=True,
    )

    assert result["promotion"]["reviewer"] == "test-reviewer"
    assert result["scenario_overlay"]["type"] == "ANALYST_SCENARIO_CAPACITY_OVERRIDE"
    assert result["scenario_overlay"]["persistent"] is False
    assert result["rerun"] is not None
    assert result["persistent_world_update"]["status"] == "PENDING_REPOSITORY_REVIEW"


def test_engine_rejects_unknown_variant_instead_of_returning_empty_feasibility(cnc_case):
    pack, _, _ = cnc_case
    with pytest.raises(KeyError):
        ForgeEngine(pack).run_scenario(
            ObjectiveSpecInput("missing_variant", 100), include_deep=False
        )
