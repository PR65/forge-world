import os

import pytest

from forge.evidence import ProofGraph
from forge.explode import check_mass_balance, explode_variant, primary_recipe
from forge.pack import PackValidationError, build_pack, load_pack
from forge.solve import ScenarioOptions, solve_objective

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _pack(pid):
    return load_pack(os.path.join(ROOT, "packs", f"{pid}.yaml"))


@pytest.mark.parametrize(
    "pid",
    ["humanoid_india", "battery_gwh_india", "smallsat_india"],
)
def test_all_packs_load_and_validate(pid):
    pk = _pack(pid)
    s = pk.summary()
    assert s["entities"] > 20
    assert s["evidence"] > 3
    assert len(s["variants"]) >= 1


def test_every_variant_has_bom():
    for pid in ("humanoid_india", "battery_gwh_india", "smallsat_india"):
        pk = _pack(pid)
        for vid, vd in pk.variants.items():
            assert vd.get("bom"), vid


def test_entity_evidence_references_must_resolve():
    raw = {
        "pack_id": "bad_evidence_reference",
        "parts": [{"id": "part", "evidence_ids": ["missing_claim"]}],
        "product_variants": [{"id": "variant", "bom": [{"part": "part", "qty": 1}]}],
    }
    with pytest.raises(PackValidationError, match="references unknown evidence"):
        build_pack(raw)


def test_evidence_inherits_source_licenses_and_rejects_missing_license():
    pack = build_pack({
        "pack_id": "licensed_evidence",
        "sources": [
            {"id": "public", "license": "public"},
            {"id": "internal", "license": "supplied-for-project use only"},
        ],
        "evidence": [{
            "claim_id": "claim",
            "subject": "part",
            "predicate": "status",
            "epistemic_class": "REPORTED",
            "source_ids": ["public", "internal"],
        }],
    })
    assert pack.evidence["claim"].license.startswith("MULTIPLE LICENSES")
    assert "public" in pack.evidence["claim"].license
    assert "supplied-for-project use only" in pack.evidence["claim"].license

    with pytest.raises(PackValidationError, match="declared license"):
        build_pack({
            "pack_id": "missing_source_license",
            "sources": [{"id": "source"}],
            "evidence": [{
                "claim_id": "claim",
                "subject": "part",
                "predicate": "status",
                "epistemic_class": "REPORTED",
                "source_ids": ["source"],
            }],
        })


def test_pack_rejects_duplicate_and_dangling_evidence_lineage():
    with pytest.raises(PackValidationError, match="duplicate source"):
        build_pack({
            "pack_id": "duplicate_source",
            "sources": [{"id": "source"}, {"id": "source"}],
        })
    with pytest.raises(PackValidationError, match="supersedes unknown evidence"):
        build_pack({
            "pack_id": "bad_supersedes",
            "evidence": [{
                "claim_id": "new",
                "subject": "part",
                "predicate": "status",
                "epistemic_class": "ASSUMPTION",
                "supersedes": "missing",
            }],
        })


def test_substitution_contract_gate_rejects_incomplete():
    from forge.substitutions import validate_substitution

    pk = _pack("humanoid_india")
    bad = {
        "id": "bad_sub",
        "replaces_part": "bldc_servo_motor",
        "alternative_recipe": "rec_bldc_servo_synrm",
        "level": "component",
        "functional_envelope": {},
        "maturity": "",
        "transition_months": [12, 24],
        "evidence_ids": ["ev_synrm_tradeoff"],
    }
    check = validate_substitution(pk.world, bad, variant_id="hv2_industrial")
    assert not check.accepted
    assert any("envelope" in r for r in check.reasons)


def test_humanoid_benchmark_multiplication():
    """Benchmark fixture: 1M HV-2 units must imply exact BOM multiples (C22)."""
    pk = _pack("humanoid_india")
    pg = ProofGraph()
    ex = explode_variant(pk.world, pg, "hv2_industrial", 1_000_000, [2030])
    w = pk.world

    def bom_qty(part):
        for e in w.out_edges("hv2_industrial", "decomposes_into"):
            if e.dst == part:
                return float(e.meta.get("qty", 1))
        return None

    act = ex.get("actuator_rotary_body")
    hand_micro = ex.get("micro_actuator_hand")
    bearings = ex.get("crossed_roller_bearing")
    encoders = ex.get("absolute_encoder")

    assert act is not None and act.net_annual.value == 30 * 1_000_000
    assert hand_micro is not None and hand_micro.net_annual.value == 14 * 1_000_000

    expected_bearings = bom_qty("crossed_roller_bearing") * 1e6
    rec = primary_recipe(w, "actuator_rotary_body")
    yf_act = 1.0
    for st in rec.steps:
        yf_act *= st.yield_fraction * (1 - st.scrap_fraction)
    brg_rec = primary_recipe(w, "crossed_roller_bearing")
    byf = 1.0
    for st in brg_rec.steps:
        byf *= st.yield_fraction * (1 - st.scrap_fraction)
    expected_bearings_gross = (
        expected_bearings + (2.0 * 30 * 1e6) / yf_act
    ) / byf
    assert abs(bearings.gross_annual.value - expected_bearings_gross) / expected_bearings_gross < 1e-9

    assert encoders.net_annual.value >= 60 * 1_000_000


def test_yield_grossup_increases_upstream_demand():
    pk = _pack("humanoid_india")
    pg = ProofGraph()
    ex = explode_variant(pk.world, pg, "hv1_compact", 1_000_000, [2030])
    pack_small = ex.get("battery_pack_small")
    assert pack_small is not None
    assert pack_small.net_annual.value == 1_000_000
    assert pack_small.gross_annual.value > pack_small.net_annual.value
    assert pack_small.via_recipe != ""
    jmu = ex.get("joint_motor_unit_compact")
    assert jmu is not None and jmu.net_annual.value == 23_000_000


def test_unknown_capacity_never_becomes_supply():
    """C2: UNKNOWN domestic capacity must not satisfy demand."""
    pk = _pack("humanoid_india")
    pg = ProofGraph()
    ex = explode_variant(pk.world, pg, "hv2_industrial", 10000, [2028])
    opts = ScenarioOptions(min_domestic_share=1.0)
    sr = solve_objective(pk.world, pg, ex, [2028], opts)
    assert sr.result_class.value in (
        "INFEASIBLE_UNDER_MODEL",
        "NOT_ADJUDICABLE",
        "CONDITIONALLY_FEASIBLE",
    )
    for gap in sr.years[2028].allocations:
        if gap.unknown:
            assert gap.domestic_used == 0.0


def test_recipe_without_capacity_never_becomes_domestic_supply():
    raw = {
        "pack_id": "recipe_without_capacity",
        "parts": [{"id": "input"}, {"id": "assembly"}],
        "recipes": [{
            "id": "rec_assembly",
            "output_part": "assembly",
            "output_quantity": [1, "pcs"],
            "inputs": [{"id": "input", "quantity": [1, "pcs"]}],
            "steps": [{"id": "assemble", "yield_fraction": 1.0}],
            "applicable_geographies": ["INDIA"],
        }],
        "product_variants": [{"id": "variant", "bom": [{"part": "assembly", "qty": 1}]}],
    }
    pk = build_pack(raw)
    ex = explode_variant(pk.world, ProofGraph(), "variant", 100, [2030])
    result = solve_objective(
        pk.world,
        ProofGraph(),
        ex,
        [2030],
        ScenarioOptions(foreign_supply_policy="unbounded_assumption"),
    )
    assembly = next(g for g in result.years[2030].allocations if g.item_id == "assembly")
    assert assembly.unknown is True
    assert assembly.domestic_used == 0.0


def test_not_adjudicable_when_imports_blocked_and_capacity_unknown():
    from forge.model import Part, World
    from forge.pack import build_pack

    raw = {
        "pack_id": "t_na",
        "sources": [{"id": "s", "name": "n"}],
        "evidence": [
            {
                "claim_id": "e1",
                "subject": "a",
                "predicate": "b",
                "epistemic_class": "ASSUMPTION",
                "source_ids": ["s"],
            }
        ],
        "parts": [
            {"id": "solo_part"},
        ],
        "product_variants": [
            {"id": "v1", "bom": [{"part": "solo_part", "qty": 1}]},
        ],
    }
    pk = build_pack(raw)
    w = pk.world
    p = w.get("solo_part")
    assert isinstance(p, Part)
    object.__setattr__(p, "import_eligible", False)
    pg = ProofGraph()
    ex = explode_variant(w, pg, "v1", 10, [2027])
    sr = solve_objective(w, pg, ex, [2027], ScenarioOptions())
    assert sr.result_class.value == "NOT_ADJUDICABLE"
    assert sr.blocking_unknowns


def test_min_domestic_share_binds_lp():
    """RT4-updated: min_domestic_share is AGGREGATE recursive DVA. It must never
    create per-item shortfall directly; an unattainable aggregate target must
    surface as a DVA certification failure (INFEASIBLE_WRT_DVA or an explicit
    uncertified-DVA ledger entry), not as artificial physical shortage."""
    pk = _pack("smallsat_india")
    pg = ProofGraph()
    ex = explode_variant(pk.world, pg, "eo_smallsat_300kg", 50, [2030])
    loose = solve_objective(pk.world, pg, ex, [2030],
                            ScenarioOptions(min_domestic_share=0.0,
                                            foreign_supply_policy="unbounded_assumption"))
    tight = solve_objective(pk.world, pg, ex, [2030],
                            ScenarioOptions(min_domestic_share=0.99,
                                            foreign_supply_policy="unbounded_assumption"))
    # no per-item artificial shortfall may appear purely from raising theta:
    tight_short = tight.years[2030].total_shortfall
    loose_short = loose.years[2030].total_shortfall
    if tight_short > 0:
        # shortfall only allowed if the DVA certificate says the constraint failed
        cert = tight.dva_certificate or {}
        assert cert.get("status") in ("infeasible_wrt_dva", "infeasible_no_tightening_leverage",
                                      "infeasible_delivery_shortfall"), cert
    assert tight.dva_certificate is not None
    assert tight.dva_certificate.get("target_dva") == 0.99


def test_dva_embedded_imports_count():
    from forge.dva import dva_fraction

    pk = _pack("humanoid_india")
    pg = ProofGraph()
    ex = explode_variant(pk.world, pg, "hv2_industrial", 1000, [2028])
    opts = ScenarioOptions()
    allocations = {
        2028: type(
            "G",
            (),
            {
                "item_id": item,
                "domestic_used": 0.0,
                "imports_used": ex.get(item).net_annual.value,
                "shortfall": 0.0,
            },
        )()
        for item in ex.items()
    }
    dva = dva_fraction(pk.world, pg, ex, opts, allocations_by_year={2028: list(allocations.values())})
    assert dva.fraction <= 0.05


def test_model_run_deterministic_hash():
    from forge.run import ModelRun

    a = ModelRun.create("p", "1", {"x": 1}, {}, data_snapshot_payload={"k": [1, 2]})
    b = ModelRun.create("p", "1", {"x": 1}, {}, data_snapshot_payload={"k": [1, 2]})
    c = ModelRun.create("p", "1", {"x": 2}, {}, data_snapshot_payload={"k": [1, 2]})
    assert a.input_hash == b.input_hash
    assert a.input_hash != c.input_hash
