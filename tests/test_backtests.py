"""Historical mechanism backtests.

These replay stylized versions of documented disruptions through the same public
pipeline used by the product. They assert DIRECTIONAL model behavior, not exact
history — the point is that the machinery would have flagged the known bottleneck.
"""
import os

import pytest

from forge.capacity import capacity_envelope, ramp_fraction
from forge.evidence import ProofGraph
from forge.explode import explode_variant
from forge.model import CapacitySegment, Part, Project, ProjectState
from forge.pack import build_pack, load_pack
from forge.shocks import apply_shocks
from forge.solve import ScenarioOptions, solve_objective
from forge.units import Quantity

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _mini_two_supplier_world():
    raw = {
        "pack_id": "bt_2011",
        "sources": [{"id": "s", "name": "backtest fixture"}],
        "evidence": [
            {
                "claim_id": "e1",
                "subject": "fixture",
                "predicate": "cap",
                "epistemic_class": "ASSUMPTION",
                "value_quantity": [100000, "pcs/yr"],
                "source_ids": ["s"],
            }
        ],
        "parts": [
            {"id": "auto_ecu", "name": "Specialty MCU", "supplied_by_countries": ["JPN"]},
            {"id": "car", "name": "Car"},
        ],
        "recipes": [
            {
                "id": "rec_car",
                "output_part": "car",
                "output_quantity": [1, "pcs"],
                "steps": [{"id": "asm", "name": "assembly", "yield_fraction": 0.99}],
                "inputs": [{"id": "auto_ecu", "quantity": [1, "pcs"]}],
            }
        ],
        "capacity_segments": [
            {
                "id": "seg_jpn_mcu",
                "item_id": "auto_ecu",
                "geography": "JPN",
                "nameplate_annual": [3000000, "pcs/yr"],
                "epistemic_class": "ASSUMPTION",
                "evidence_ids": ["e1"],
            }
        ],
    }
    return build_pack(raw)


def test_backtest_japan_2011_single_source_outage():
    """Stylized Tōhoku: a concentrated specialty-part region goes offline.

    Model expectation: imports from the affected origin drop to zero, final output is
    capped by remaining qualified supply — i.e., the mechanism identifies the SPOF.
    """
    pk = _mini_two_supplier_world()
    pg = ProofGraph()
    ex = explode_variant(pk.world, pg, "car", 500000, [2011])

    normal = ScenarioOptions()
    sr_normal = solve_objective(pk.world, pg, ex, [2011], normal)
    assert sr_normal.years[2011].total_shortfall == pytest.approx(0, abs=1)

    disrupted = ScenarioOptions(import_eligibility={"JPN": 0.0})
    w2, o2, rep = apply_shocks(pk.world, pg, [], disrupted)
    o2.import_eligibility = {"JPN": 0.0}
    sr_outage = solve_objective(pk.world, pg, ex, [2011], o2)
    assert sr_outage.years[2011].total_shortfall > 400000
    worst = sr_outage.years[2011].shortfalls[0]
    assert worst.item_id == "auto_ecu"


def test_backtest_red_sea_style_corridor_cost_shock():
    """Corridor disruption raises landed import cost; allocation shifts toward domestic."""
    pk = load_pack(os.path.join(ROOT, "packs", "humanoid_india.yaml"))
    pg = ProofGraph()
    ex = explode_variant(pk.world, pg, "hv2_industrial", 20000, [2028])
    opts = ScenarioOptions(min_domestic_share=0.0)
    base = solve_objective(pk.world, pg, ex, [2028], opts)
    shocked_opts = ScenarioOptions(min_domestic_share=0.0)
    w2, o2, _ = apply_shocks(pk.world, pg, ["shk_oil_150"], shocked_opts)
    shock = solve_objective(w2, pg, ex, [2028], o2)
    assert shock.years[2028].import_value_usd >= base.years[2028].import_value_usd * 1.2


def test_backtest_semiconductor_shortage_allocation_regime():
    """2020-23 style: eligible advanced-chip capacity halves; shortfall appears on chips."""
    pk = load_pack(os.path.join(ROOT, "packs", "humanoid_india.yaml"))
    pg = ProofGraph()
    ex = explode_variant(pk.world, pg, "hv1_compact", 300000, [2028])
    opts = ScenarioOptions(min_domestic_share=0.95, funded_project_ids=set())
    w2, o2, _ = apply_shocks(pk.world, pg, ["shk_semi_half"], opts)
    sr = solve_objective(w2, pg, ex, [2028], o2)
    items_with_shortfall = {g.item_id for g in sr.years[2028].shortfalls}
    assert any("soc" in i or "edge_compute" in i for i in items_with_shortfall)


def test_ramp_behavior_matches_documented_pattern_direction():
    """Figure-style disclosure: fast initial ramp then plateau (company REPORTED)."""
    pts = ((0, 0.25), (1, 0.7), (2, 0.9), (4, 1.0))
    early, mid, late = ramp_fraction(pts, 0.5), ramp_fraction(pts, 1.5), ramp_fraction(pts, 3.5)
    assert early < mid < late <= 1.0
