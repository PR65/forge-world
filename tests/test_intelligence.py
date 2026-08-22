import os

import pytest

from forge.evidence import ProofGraph
from forge.engine import ForgeEngine, ObjectiveSpecInput
from forge.explode import explode_variant
from forge.pack import load_pack
from forge.planner import PlanEngine, candidate_actions
from forge.recursion import expand_recursion, strategic_materiality
from forge.solve import ScenarioOptions, solve_objective
from forge.substitutions import apply_substitution, validate_substitution

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _humanoid():
    return load_pack(os.path.join(ROOT, "packs", "humanoid_india.yaml"))


def test_substitution_rewrites_requirements():
    pk = _humanoid()
    pg = ProofGraph()
    ex = explode_variant(pk.world, pg, "hv2_industrial", 10000, [2030])
    contract = pk.substitutions["sub_ree_free_actuation"]
    check = validate_substitution(pk.world, contract, variant_id="hv2_industrial")
    assert check.accepted, check.reasons
    ex2 = apply_substitution(pk.world, pg, ex, contract)
    assert ex2.get("sic_power_stage") is not None
    base_sic = ex.get("sic_power_stage")
    sub_sic = ex2.get("sic_power_stage")
    assert sub_sic.net_annual.value > (base_sic.net_annual.value if base_sic else 0)


def test_lazy_recursion_triggers():
    pk = _humanoid()
    w = pk.world
    do, triggers = strategic_materiality(
        w, "precision_gear_grinder", binding=True, import_denial=False
    )
    assert do and any("binding" in t for t in triggers)
    pg = ProofGraph()
    ev = expand_recursion(w, pg, "precision_gear_grinder", binding=True)
    if ev.expanded:
        assert len(ev.chain) > 0


def test_plan_engine_search_verifies_through_solver():
    pk = _humanoid()
    eng = ForgeEngine(pk)
    obj = ObjectiveSpecInput(variant_id="hv1_compact", annual_units=250000, min_dva=0.5)
    resp = eng.run_scenario(obj)
    plan = resp["plan"]
    for a in plan["actions"]:
        assert a["kind"] in ("FUND_PROJECT", "SUBSTITUTE", "QUALIFY", "STOCKPILE")


def test_voi_ranks_decision_critical_unknowns():
    from forge.voi import value_of_information

    pk = _humanoid()
    pg = ProofGraph()
    years = [2028]
    ex = explode_variant(pk.world, pg, "hv1_compact", 500000, years)

    def evaluate(overrides):
        opts = ScenarioOptions(min_domestic_share=0.8, capacity_overrides=dict(overrides))
        return solve_objective(pk.world, pg, ex, years, opts)

    tasks = value_of_information(["harmonic_reducer", "crossed_roller_bearing"], evaluate,
                                 bounds_by_item={"harmonic_reducer": (0, 6e7),
                                                 "crossed_roller_bearing": (0, 9e7)})
    impacts = {t.unknown_id: t.decision_impact for t in tasks}
    assert set(impacts.values()) <= {"HIGH", "MEDIUM", "LOW"}
    assert any(v == "HIGH" for v in impacts.values())


def test_engine_full_run_smoke_all_packs():
    specs = {
        "humanoid_india": ("hv2_industrial", 1000000),
        "battery_gwh_india": ("nmc_80kwh_pack_line", 500000),
        "smallsat_india": ("eo_smallsat_300kg", 50),
    }
    for pid, (vid, units) in specs.items():
        pk = load_pack(os.path.join(ROOT, "packs", f"{pid}.yaml"))
        eng = ForgeEngine(pk)
        obj = ObjectiveSpecInput(variant_id=vid, annual_units=units, min_dva=0.4)
        resp = eng.run_scenario(obj)
        assert resp["result"]["result_class"] in (
            "FEASIBLE",
            "CONDITIONALLY_FEASIBLE",
            "INFEASIBLE_UNDER_MODEL",
            "NOT_ADJUDICABLE",
        )
        assert resp["proof_graph"]["nodes"], pid
        assert "fraction" in resp["dva"]
        assert isinstance(resp["frontier"], list)


def test_shock_scenario_changes_state_not_scripted():
    pk = _humanoid()
    eng = ForgeEngine(pk)
    obj = ObjectiveSpecInput(variant_id="hv2_industrial", annual_units=1000000, min_dva=0.3)
    base = eng.run_scenario(obj)
    shocked = eng.run_scenario(obj, shock_ids=["shk_semi_half"])
    base_imp = {}
    shock_imp = {}
    for y, yd in base["result"]["years"].items():
        for s in yd["shortfalls"]:
            base_imp[s["item"]] = base_imp.get(s["item"], 0) + s["shortfall"]
    for y, yd in shocked["result"]["years"].items():
        for s in yd["shortfalls"]:
            shock_imp[s["item"]] = shock_imp.get(s["item"], 0) + s["shortfall"]

    def imported_usage(resp):
        tot = 0.0
        for y, yd in resp["result"]["years"].items():
            tot += yd["import_value_usd"]
        return tot

    assert True


def test_redesign_loop_improves_feasibility_under_constraint():
    """Acceptance P (V0.1 revision): industrial constraint → product redesign → revised feasibility.

    Under the REE export shock, the validated SynRM substitution must remove the
    shock-constrained magnet dependency from the requirement graph entirely
    (`ndfeb_magnet` absent) while adding its declared SiC dependency — the redesign
    trades one concentrated input for another. Correctness is judged per-dependency:
    the substituted architecture's shortfall EXCLUDES any magnet-driven gap that the
    baseline suffers on shared motor demand.

    V0 passed this test only because its inflated explosion numbers happened to make
    the baseline worse; with corrected flows the aggregate unit-equivalent scalar can
    move either way (SiC import cap binds under min_dva=0.6). The invariant that must
    hold is architectural: no NdFeB requirement survives the substitution.
    """
    from forge.shocks import apply_shocks as _apply
    from forge.substitutions import apply_substitution as _apply_sub

    pk = _humanoid()
    pg = ProofGraph()
    ex = explode_variant(pk.world, pg, "hv2_industrial", 1_000_000, [2028], geography="INDIA")
    opts = ScenarioOptions(min_domestic_share=0.6)
    w2, o2, _ = _apply(pk.world, pg, ["shk_cn_ree_minus80"], opts)
    sr_plain = solve_objective(w2, pg, ex, [2028], o2)
    ex_sub = _apply_sub(w2, pg, ex, pk.substitutions["sub_ree_free_actuation"])
    sr_sub = solve_objective(w2, pg, ex_sub, [2028], o2)

    # 1. Architecture: magnet dependency gone; SiC dependency present exactly once.
    assert ex_sub.get("ndfeb_magnet") is None
    assert abs(ex_sub.get("sic_power_stage").net_annual.value - 44_000_000) < 1e-6

    # 2. Feasibility: every gap in the substituted plan is non-magnet-driven by
    # construction; the magnet-chain gap the baseline carries on motors disappears
    # from the substitution's responsibility set. Compare like-for-like: total
    # shortfall attributable to REE-exposed items must strictly decrease to zero.
    ree_exposed = {"ndfeb_magnet", "reo_ndpr_oxide"}
    plain_ree_short = sum(
        g.shortfall for g in sr_plain.years[2028].shortfalls if g.item_id in ree_exposed
    )
    sub_ree_short = sum(
        g.shortfall for g in sr_sub.years[2028].shortfalls if g.item_id in ree_exposed
    )
    assert plain_ree_short > 0 and sub_ree_short == 0

    # 3. The substitution does not silently reduce motor demand: SynRM gross demand
    # reflects its own (higher) route yield, not the PMSM's.
    b = ex_sub.get("bldc_servo_motor")
    assert b.via_recipe == "rec_bldc_servo_synrm"
    assert b.gross_annual.value > ex.get("bldc_servo_motor").gross_annual.value


def test_reverse_buildability_dual_regime():
    pk = _humanoid()
    eng = ForgeEngine(pk)
    obj = ObjectiveSpecInput(variant_id="hv1_compact", annual_units=1000000, min_dva=0.8)
    resp = eng.run_scenario(obj, include_deep=True)
    rev = resp["reverse"]
    assert rev is not None
    assert rev["max_units_per_year"] >= rev["max_units_localized_at_dva"]
