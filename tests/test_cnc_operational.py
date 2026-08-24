"""Focused operational-depth checks for the India 100-CNC execution pack.

These tests intentionally check graph connectivity and evidence discipline rather
than claiming that the unresolved capacities are known.  The pack is an execution
model: it should tell a later generic layer what to procure, qualify, measure, and
research, while leaving unsupported effective capacity UNKNOWN.
"""

import os

import pytest

from forge.evidence import ProofGraph
from forge.explode import explode_variant, primary_recipe
from forge.pack import load_pack
from forge.shocks import apply_shocks
from forge.solve import ScenarioOptions
from forge.substitutions import apply_substitution, validate_substitution


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def cnc_pack():
    return load_pack(os.path.join(ROOT, "packs", "cnc_machining_india.yaml"))


def test_cnc_pack_has_operational_work_packages_and_exact_research_tasks(cnc_pack):
    model = cnc_pack.raw.get("execution_model")
    assert model and model["work_packages"] and model["research_tasks"]

    entity_ids = set(cnc_pack.world.entities)
    evidence_ids = set(cnc_pack.evidence)
    work_ids = {row["id"] for row in model["work_packages"]}
    assert len(work_ids) == len(model["work_packages"])
    assert {"wp_ball_screw_recursive_chain", "wp_final_metrology_and_customer_acceptance"} <= work_ids

    for row in model["work_packages"]:
        assert row["entity_ids"], row["id"]
        assert set(row["entity_ids"]) <= entity_ids, row["id"]
        assert row["acceptance_criteria"], row["id"]
        assert row["evidence_ids"], row["id"]
        assert set(row["evidence_ids"]) <= evidence_ids, row["id"]
        assert isinstance(row["human_approval_required"], bool)

    task_ids = {row["id"] for row in model["research_tasks"]}
    assert len(task_ids) == len(model["research_tasks"])
    assert {
        "rq_vmc_qualified_effective_capacity",
        "rq_ballscrew_grade_and_supplier",
        "rq_ballscrew_grinder_machine_hours",
        "rq_ballscrew_metrology_throughput",
        "rq_final_acceptance_service",
    } <= task_ids
    for task in model["research_tasks"]:
        assert task["target_entity_id"] in entity_ids, task["id"]
        assert task["question"].endswith("?")
        assert task["missing_variable"]
        assert task["decision"]
        assert task["suggested_source_types"]
        assert task["capture_fields"]


def test_ball_screw_grade_process_grinder_metrology_supplier_chain_is_connected(cnc_pack):
    world = cnc_pack.world
    entity_ids = set(world.entities)
    evidence_ids = set(cnc_pack.evidence)
    ex = explode_variant(
        world,
        ProofGraph(),
        "cnc_vmc_100_per_year",
        100,
        [2030],
        geography="INDIA",
    )

    # The 100/year BOM still has the original three axis-set multiple, while
    # recursive requirements now expose grade/specification, fixtures, grinding
    # and metrology artifacts instead of stopping at a generic ball-screw label.
    assert ex.get("ball_screw_set").net_annual.value == pytest.approx(300.0)
    for item in (
        "ball_screw_shaft_blank",
        "ball_screw_grade_spec",
        "ball_screw_grinding_fixture",
        "ball_screw_lead_error_artifact",
    ):
        assert ex.get(item) is not None and ex.get(item).net_annual.value > 0, item

    screw_route = primary_recipe(world, "ball_screw_set", geography="INDIA")
    shaft_route = primary_recipe(world, "ball_screw_shaft_blank", geography="INDIA")
    grinder_route = primary_recipe(world, "ball_screw_grinder", geography="INDIA")
    metrology_route = primary_recipe(world, "ball_screw_metrology_station", geography="INDIA")
    assert screw_route and shaft_route and grinder_route and metrology_route
    assert "ball_screw_grinder" in screw_route.steps[0].equipment_classes
    assert "ball_screw_metrology_station" in shaft_route.steps[-1].equipment_classes
    assert "ball_screw_metrology_station" in grinder_route.steps[-1].equipment_classes

    # Machine-builds-machine edge: the equipment dependency used by the shaft
    # route itself has a bounded recipe, and that route cites metrology/fixture
    # inputs. This is deliberately a graph relation, not prose in a notes field.
    produced = {
        (edge.src, edge.relation, edge.dst)
        for edge in world.edges
        if edge.src == "ball_screw_grinder"
    }
    assert ("ball_screw_grinder", "produced_via", "rec_ball_screw_grinder_machine") in produced
    grinder_inputs = {
        edge.dst
        for edge in world.edges
        if edge.src == "rec_ball_screw_grinder_machine" and edge.relation == "requires_input"
    }
    assert {"ball_screw_grinding_fixture", "ball_screw_lead_error_artifact"} <= grinder_inputs

    # Supplier/facility/capability context has official evidence, but no capacity
    # segment is promoted from it.
    assert not world.of_kind("capacity_segment")
    assert {"fac_micromatic_ghaziabad", "fac_micromatic_bengaluru", "fac_jyoti_rajkot_1"} <= {
        f.id for f in world.of_kind("facility")
    }
    assert cnc_pack.evidence["ev_micromatic_grinding_supplier"].source_ids == (
        "src_micromatic_grinding_official",
    )
    assert cnc_pack.evidence["ev_thk_ball_screw_grade"].epistemic_class.value == "REPORTED"
    assert any(
        claim.org_id == "org_micromatic_official"
        and claim.capability_item == "precision_surface_grinder"
        and claim.vector.get("qualified_effective_capacity") == "UNKNOWN"
        for claim in world.of_kind("capability_claim")
    )
    supplier_links = cnc_pack.raw.get("supplier_links", ())
    assert supplier_links
    for link in supplier_links:
        assert link["item_id"] in entity_ids
        assert link["organization_id"] in entity_ids
        if link.get("facility_id"):
            assert link["facility_id"] in entity_ids
        assert link["capability_claim_id"] in entity_ids
        assert link["status"] == "RESEARCH_REQUIRED"
        assert set(link["evidence_ids"]) <= evidence_ids
    grinder_link = next(row for row in supplier_links if row["item_id"] == "ball_screw_grinder")
    assert grinder_link["facility_id"] == "fac_micromatic_bengaluru"


def test_cnc_alternative_is_a_valid_graph_rewrite_and_reduces_only_declared_dependency(cnc_pack):
    world = cnc_pack.world
    contract = cnc_pack.substitutions["sub_servo_axis_synrm"]
    check = validate_substitution(world, contract, variant_id="cnc_vmc_100_per_year")
    assert check.accepted, check.reasons

    baseline_pg = ProofGraph()
    baseline = explode_variant(world, baseline_pg, "cnc_vmc_100_per_year", 100, [2030], geography="INDIA")
    alt_pg = ProofGraph()
    alternative = apply_substitution(world, alt_pg, baseline, contract)

    assert alternative.get("servo_motor_axis") is None
    assert alternative.get("servo_motor_axis_synrm") is not None
    assert alternative.get("servo_motor_axis_synrm").net_annual.value == pytest.approx(300.0)
    assert alternative.get("permanent_magnet").net_annual.value < baseline.get("permanent_magnet").net_annual.value
    # Spindle permanent magnets remain: the contract only rewrites axis motors.
    assert alternative.get("permanent_magnet").net_annual.value > 0
    assert alternative.variant_id.endswith("+sub:sub_servo_axis_synrm")


def test_cnc_shock_targets_grinder_and_import_policy_without_inventing_capacity(cnc_pack):
    opts = ScenarioOptions(geography="INDIA", foreign_supply_policy="strict")
    pg = ProofGraph()
    shocked_world, shocked_opts, report = apply_shocks(
        cnc_pack.world, pg, ["shk_ball_screw_grinder_loss"], opts
    )

    assert shocked_opts.equipment_hour_limits["ball_screw_grinder"] == 0.0
    assert shocked_opts.import_eligibility["JPN"] == 0.0
    assert len(report.applied_edits) == 2
    assert {edit["edit"] for edit in report.applied_edits} == {
        "equipment_limit",
        "import_eligibility",
    }
    # Shock cloning must not mutate the baseline world or create phantom supply.
    assert not cnc_pack.world.of_kind("capacity_segment")
    assert not shocked_world.of_kind("capacity_segment")
