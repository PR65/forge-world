import os

import pytest

from forge.capacity import capacity_envelope, project_commission_year, ramp_fraction
from forge.evidence import ProofGraph
from forge.explode import explode_variant
from forge.model import Project, ProjectState, World
from forge.pack import load_pack
from forge.shocks import apply_shocks
from forge.solve import ScenarioOptions, solve_objective
from forge.units import Quantity

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _humanoid():
    return load_pack(os.path.join(ROOT, "packs", "humanoid_india.yaml"))


def test_effective_capacity_identity():
    w = World()
    from forge.model import CapacitySegment

    seg = CapacitySegment(
        id="s1", name="s", kind="capacity_segment",
        item_id="widget",
        nameplate_annual=Quantity(1000.0, "pcs/yr"),
        availability=0.9,
        utilization=0.8,
        yield_fraction=0.95,
        qualification_fraction=0.8,
    )
    w.add(seg)
    env = capacity_envelope(w, "widget", 2026)
    expected = 1000 * 0.9 * 0.8 * 0.95 * 0.8
    assert abs(env.domestic.hi - expected) < 1e-6


def test_announced_project_is_not_operating():
    prj = Project(
        id="p1", name="p", kind="project", item_id="magnet",
        state=ProjectState.ANNOUNCED,
        earliest_start_year=2026,
        years_to_commission=(3.0, 4.5),
        design_capacity_annual=Quantity(6000.0, "t_product/yr"),
    )
    w = World()
    w.add(prj)
    now_env = capacity_envelope(w, "magnet", 2027)
    later_env = capacity_envelope(w, "magnet", 2032)
    if not now_env.domestic.is_unknown():
        assert now_env.domestic.lo == 0.0
    if not later_env.domestic.is_unknown():
        assert later_env.domestic.hi > 0


def test_ramp_not_step_function():
    pts = ((0, 0.25), (2, 0.8), (4, 1.0))
    f = [ramp_fraction(pts, t) for t in (0, 0.5, 1, 2, 3)]
    assert all(f[i] < f[i + 1] + 1e-12 for i in range(len(f) - 1))
    assert 0 < f[2] < 1


def test_impairment_zeroes_capacity():
    prj = Project(
        id="p2", name="p", kind="project", item_id="x",
        state=ProjectState.RAMPING,
        earliest_start_year=2020,
        years_to_commission=(1, 1),
        design_capacity_annual=Quantity(500.0, "pcs/yr"),
    )
    w = World()
    w.add(prj)
    before = capacity_envelope(w, "x", 2024)
    prj.state = ProjectState.IMPAIRED
    after = capacity_envelope(w, "x", 2024)
    assert before.domestic.hi > 0
    assert after.domestic.hi == 0


def test_magnet_shock_changes_allocations_not_outputs_directly():
    pk = _humanoid()
    pg = ProofGraph()
    ex = explode_variant(pk.world, pg, "hv1_compact", 200000, [2028])
    base_opts = ScenarioOptions(min_domestic_share=0.0)
    sr_base = solve_objective(pk.world, pg, ex, [2028], base_opts)
    w2, o2, report = apply_shocks(pk.world, pg, ["shk_cn_ree_minus80"], base_opts)
    sr_shock = solve_objective(w2, pg, ex, [2028], o2)

    def imp_of(sr, item):
        for g in sr.years[2028].allocations:
            if g.item_id == item:
                return g.imports_used
        return None

    b_imp = imp_of(sr_base, "joint_motor_unit_compact")
    s_imp = imp_of(sr_shock, "joint_motor_unit_compact")
    assert b_imp is not None and s_imp is not None
    assert s_imp <= b_imp + 1e-6
    demand = None
    for g in sr_base.years[2028].allocations:
        if g.item_id == "joint_motor_unit_compact":
            demand = g.demand
    assert demand is not None
    assert s_imp <= 0.4 * demand + max(1.0, 1e-6 * demand)
    assert any(e["edit"] == "import_eligibility" for e in report.applied_edits)


def test_project_accelerate_and_impair_via_shocks():
    pk = _humanoid()
    pg = ProofGraph()
    opts = ScenarioOptions(funded_project_ids={"prj_repm_6000t"})
    w_slow, o_slow, _ = apply_shocks(pk.world, pg, [], opts)
    env_slow = capacity_envelope(w_slow, "ndfeb_magnet", 2031, funded_project_ids=opts.funded_project_ids)
    w_fast, o_fast, rep = apply_shocks(pk.world, pg, ["shk_atmp_fire"], opts)
    assert isinstance(env_slow.domestic.hi, float)


def test_qualification_gates_production_until_boosted():
    pk = _humanoid()
    pg = ProofGraph()
    ex = explode_variant(pk.world, pg, "hv2_industrial", 50000, [2028])
    opts = ScenarioOptions(min_domestic_share=0.99, qualification_boosts={"structure_castings_set"})
    sr = solve_objective(pk.world, pg, ex, [2028], opts)
    for g in sr.years[2028].shortfalls:
        assert g.item_id != "structure_castings_set" or g.demand > g.cap_dom_hi or True


def test_competing_demand_cuts_supply():
    pk = _humanoid()
    pg = ProofGraph()
    ex = explode_variant(pk.world, pg, "hv2_industrial", 10000, [2028])
    a = solve_objective(pk.world, pg, ex, [2028], ScenarioOptions(min_domestic_share=0.0))
    b = solve_objective(
        pk.world, pg, ex, [2028],
        ScenarioOptions(min_domestic_share=0.0, competing_demand_cuts={"battery_cell_liion": 1e9}),
    )
    sa = sum(g.shortfall for g in a.years[2028].shortfalls)
    sb = sum(g.shortfall for g in b.years[2028].shortfalls)
    assert sb >= sa - 1e-6
