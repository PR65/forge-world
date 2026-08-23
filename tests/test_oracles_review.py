"""RT4 review oracles: the four independent-review findings.

Each oracle is written to FAIL on the pre-fix implementation:

1. test_rt1_aggregate_dva_not_per_item_localization — loc_cap = 1 - min_dva
   per-item cap manufactured artificial shortfall in a genuinely-90%-domestic
   world at theta=0.70.
2. test_rt2_eligibility_without_capacity_is_no_supply — fcap_frac=1.0 silently
   converted "no evidenced foreign capacity" into demand-sized import supply.
3. test_rt3_dva_repeatability_and_concurrency — module-global _noted_raw_shares
   leaked assumption state across runs; ProofGraph.derive was monkey-patched
   at class scope inside measure_dva.
4. test_rt4_dva_proof_lineage_is_real — dva_fraction emitted pg.derive([], ...)
   disconnected from every computational dependency.
"""
import os
import sys
import threading

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from forge.evidence import ProofGraph
from forge.explode import explode_variant
from forge.solve import ScenarioOptions, solve_objective
from forge.pack import build_pack


def _agg_world():
    """P = 9xD + 1xI; D domestic @10 USD, I fully imported @10 USD.

    True aggregate recursive DVA = 1 - 10/100 = 90%.
    I carries an evidenced ForeignSupplySegment so the run is adjudicable under
    strict foreign-supply epistemics (finding-2 semantics tested separately).
    """
    raw = {
        "pack_id": "rt_agg", "sources": [{"id": "s", "name": "n"}],
        "evidence": [{"claim_id": "e1", "subject": "a", "predicate": "b",
                      "epistemic_class": "ASSUMPTION", "source_ids": ["s"]}],
        "parts": [{"id": k} for k in ("P", "D", "I")],
        "recipes": [{
            "id": "rec_D", "output_part": "D", "output_quantity": [1, "pcs"],
            "steps": [{"id": "s", "yield_fraction": 1.0}], "inputs": [],
            "applicable_geographies": ["INDIA"],
        }],
        "capacity_segments": [{
            "id": "seg_D", "item_id": "D", "geography": "INDIA",
            "nameplate_annual": [10_000_000, "pcs/yr"],
            "epistemic_class": "ESTIMATED",
        }],
        "foreign_supply_segments": [{
            "id": "fss_I", "item_id": "I", "origin_country": "CHN",
            "nameplate_annual": [10_000_000, "pcs/yr"],
            "epistemic_class": "ASSUMPTION",
        }],
        "product_variants": [
            {"id": "PV", "bom": [{"part": "D", "qty": 9}, {"part": "I", "qty": 1}]},
        ],
    }
    return build_pack(raw).world


# ---------------------------------------------------------------- finding 1


def test_rt1_aggregate_dva_not_per_item_localization():
    """theta=.70: feasible, DVA-certified ~90%, ZERO per-item shortfall.
    theta=.95: INFEASIBLE_WRT_DVA (policy failure), not fake physical shortage."""
    w = _agg_world()
    ex = explode_variant(w, ProofGraph(), "PV", 100_000, [2030])
    opts = ScenarioOptions(min_domestic_share=0.70,
                           cost_domestic={"D": 10.0}, cost_import={"I": 10.0})
    sr = solve_objective(w, ProofGraph(), ex, [2030], opts)
    assert sr.result_class.name in ("FEASIBLE", "CONDITIONALLY_FEASIBLE"), (
        f"per-item localization leaked into import bounds: {sr.result_class}"
    )
    for g in sr.years[2030].allocations:
        assert g.shortfall <= 1e-6, \
            f"artificial shortfall on {g.item_id} from an item-level cap"
    cert = sr.dva_certificate or {}
    assert cert.get("status") == "satisfied"
    assert abs(cert.get("achieved_dva", 0.0) - 0.90) < 0.02

    # theta=.95 must fail DVA certification as POLICY failure:
    opts95 = ScenarioOptions(min_domestic_share=0.95,
                             cost_domestic={"D": 10.0}, cost_import={"I": 10.0})
    sr95 = solve_objective(w, ProofGraph(), ex, [2030], opts95)
    assert sr95.result_class.name == "INFEASIBLE_WRT_DVA", (
        f"expected INFEASIBLE_WRT_DVA, got {sr95.result_class} — tightening-induced "
        "shortfall must never be reported as INFEASIBLE_UNDER_MODEL"
    )
    # and its shortfall vector must be clean (the untightened world delivers):
    assert sr95.years[2030].shortfall_vector.is_zero()


def test_rt1_per_item_caps_only_when_explicit():
    """per_item_import_cap still works when EXPLICITLY requested."""
    w = _agg_world()
    ex = explode_variant(w, ProofGraph(), "PV", 100_000, [2030])
    capped = solve_objective(w, ProofGraph(), ex, [2030], ScenarioOptions(
        min_domestic_share=0.0,
        per_item_import_cap={"D": 0.5},
        foreign_supply_policy="unbounded_assumption"))
    gap_d = next(g for g in capped.years[2030].allocations if g.item_id == "D")
    assert gap_d.imports_used <= 0.5 * gap_d.demand + 1e-6


# ---------------------------------------------------------------- finding 2


def test_rt2_eligibility_without_capacity_is_no_supply():
    """import eligible=true, NO ForeignSupplySegment, NO domestic capacity,
    positive demand => eligibility alone must NOT create evidenced supply.

    strict policy (default): NOT_ADJUDICABLE with a structured ledger entry.
    unbounded_assumption policy: CONDITIONAL with the named assumption recorded.
    Either way it can NOT come back plain FEASIBLE with zero shortfall silence."""
    raw = {
        "pack_id": "rt_elig", "sources": [{"id": "s", "name": "n"}],
        "evidence": [{"claim_id": "e1", "subject": "a", "predicate": "b",
                      "epistemic_class": "ASSUMPTION", "source_ids": ["s"]}],
        "parts": [{"id": "W", "supplied_by_countries": ["CHN"]}],
        "product_variants": [{"id": "PV", "bom": [{"part": "W", "qty": 1}]}],
    }
    w = build_pack(raw).world
    ex = explode_variant(w, pg := ProofGraph(), "PV", 100_000, [2030])

    strict = solve_objective(w, pg, ex, [2030], ScenarioOptions())
    assert strict.result_class.name == "NOT_ADJUDICABLE", \
        "eligibility-only supply silently accepted under strict policy"
    types = {e["type"] for e in strict.condition_ledger}
    assert "foreign_supply_capacity_unknown" in types
    assert any("UNKNOWN foreign capacity" in b for b in strict.blocking_unknowns)

    assumed = solve_objective(w, ProofGraph(), ex, [2030], ScenarioOptions(
        foreign_supply_policy="unbounded_assumption"))
    assert assumed.result_class.name == "CONDITIONALLY_FEASIBLE"
    assert any("ASSUMPTION" in c and "unbounded" in c
               for c in assumed.conditional_reasons)
    types2 = {e["type"] for e in assumed.condition_ledger}
    assert "foreign_supply_unbounded_assumed" in types2


def test_rt2_evidenced_foreign_capacity_still_bounded():
    """The separate D-oracle: evidenced foreign capacity of 10 supplies at most 10."""
    raw = {
        "pack_id": "rt_fss", "sources": [{"id": "s", "name": "n"}],
        "evidence": [{"claim_id": "e1", "subject": "a", "predicate": "b",
                      "epistemic_class": "ASSUMPTION", "source_ids": ["s"]}],
        "parts": [{"id": "W"}],
        "foreign_supply_segments": [{
            "id": "fss_w", "item_id": "W", "origin_country": "ABC",
            "nameplate_annual": [10, "pcs/yr"], "epistemic_class": "ASSUMPTION",
        }],
        "product_variants": [{"id": "PV", "bom": [{"part": "W", "qty": 1}]}],
    }
    w = build_pack(raw).world
    ex = explode_variant(w, ProofGraph(), "PV", 100, [2030])
    sr = solve_objective(w, ProofGraph(), ex, [2030], ScenarioOptions())
    gap = sr.years[2030].allocations[0]
    assert gap.imports_used <= 10 + 1e-6
    assert gap.shortfall >= 90 - 1e-6


# ---------------------------------------------------------------- finding 3


def test_rt3_dva_repeatability_across_runs():
    """Assumption collection must be per-run: identical runs return identical
    assumptions regardless of how many runs happened earlier in the process."""
    from forge.dva import dva_fraction
    w = _agg_world()
    results = []
    for _ in range(3):
        ex = explode_variant(w, ProofGraph(), "PV", 100_000, [2030])
        opts = ScenarioOptions(cost_import={"I": 10.0}, cost_domestic={"D": 10.0})
        allocs = [type("G", (), {
            "item_id": it,
            "domestic_used": ex.get(it).net_annual.value if it == "D" else 0.0,
            "imports_used": ex.get(it).net_annual.value if it != "D" else 0.0,
            "shortfall": 0.0})() for it in ex.items()]
        br = dva_fraction(w, ProofGraph(), ex, opts,
                          allocations_by_year={2030: allocs}, decision_year=2030)
        results.append((br.fraction, tuple(br.assumptions_used)))
    assert len(set(results)) == 1, \
        f"cross-run global state detected: {results}"


def test_rt3_measure_dva_does_not_monkeypatch():
    """measure_dva must not touch ProofGraph.derive at class scope."""
    import inspect
    import forge.dva as dva_mod
    src = inspect.getsource(dva_mod)
    assert "ProofGraph.derive =" not in src, \
        "class-scope monkey patch present in dva.py"
    # behavioral check: derive() keeps working during measure_dva
    from forge.dva import measure_dva
    w = _agg_world()
    ex = explode_variant(w, ProofGraph(), "PV", 100_000, [2030])
    opts = ScenarioOptions(cost_import={"I": 10.0}, cost_domestic={"D": 10.0})
    allocs = [type("G", (), {
        "item_id": it, "domestic_used": ex.get(it).net_annual.value,
        "imports_used": 0.0, "shortfall": 0.0})() for it in ex.items()]
    pg = ProofGraph()
    orig_derive = ProofGraph.derive
    measure_dva(w, pg, ex, opts, allocations_by_year={2030: allocs}, decision_year=2030)
    assert ProofGraph.derive is orig_derive
    # graph untouched by the pure path:
    assert len(pg.nodes) == 0


def test_rt3_concurrent_measure_dva_is_isolated():
    """Concurrent measure_dva calls must not interfere (same result as serial)."""
    from forge.dva import measure_dva
    w = _agg_world()
    serial_results = []
    for _ in range(4):
        ex = explode_variant(w, ProofGraph(), "PV", 100_000, [2030])
        opts = ScenarioOptions(raw_material_import_share=0.5,
                               cost_import={"I": 10.0}, cost_domestic={"D": 10.0})
        allocs = [type("G", (), {
            "item_id": it, "domestic_used": ex.get(it).net_annual.value,
            "imports_used": 0.0, "shortfall": 0.0})() for it in ex.items()]
        br = measure_dva(w, ProofGraph(), ex, opts,
                         allocations_by_year={2030: allocs}, decision_year=2030)
        serial_results.append((br.fraction, tuple(sorted(br.assumptions_used))))

    concurrent_results = [None] * 8
    def worker(i):
        ex = explode_variant(w, ProofGraph(), "PV", 100_000, [2030])
        opts = ScenarioOptions(raw_material_import_share=0.5,
                               cost_import={"I": 10.0}, cost_domestic={"D": 10.0})
        allocs = [type("G", (), {
            "item_id": it, "domestic_used": ex.get(it).net_annual.value,
            "imports_used": 0.0, "shortfall": 0.0})() for it in ex.items()]
        br = measure_dva(w, ProofGraph(), ex, opts,
                         allocations_by_year={2030: allocs}, decision_year=2030)
        concurrent_results[i] = (br.fraction, tuple(sorted(br.assumptions_used)))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert None not in concurrent_results
    assert len(set(concurrent_results)) == 1, \
        f"concurrent runs disagree: {set(concurrent_results)}"
    assert set(concurrent_results) == set(serial_results)


# ---------------------------------------------------------------- finding 4


def test_rt4_dva_proof_lineage_is_real():
    """From the DVA output node there must be a path through the computational
    dependency nodes (allocation/basis/embedded/prices/origin) to evidence-bearing
    line nodes — not merely 'some' evidence node anywhere in the graph."""
    from forge.dva import dva_fraction
    w = _agg_world()
    pg = ProofGraph()
    ex = explode_variant(w, pg, "PV", 100_000, [2030])
    opts = ScenarioOptions(cost_import={"I": 10.0}, cost_domestic={"D": 10.0})
    allocs = [type("G", (), {
        "item_id": it,
        "domestic_used": ex.get(it).net_annual.value if it == "D" else 0.0,
        "imports_used": ex.get(it).net_annual.value if it == "I" else 0.0,
        "shortfall": 0.0})() for it in ex.items()]
    dva_fraction(w, pg, ex, opts, allocations_by_year={2030: allocs},
                 decision_year=2030)

    # find the DVA output node
    dva_nodes = [nid for nid, n in pg.nodes.items()
                 if n.kind == "derived" and n.label.startswith("DVA =")]
    assert len(dva_nodes) == 1, "expected exactly one DVA output node"
    out = dva_nodes[0]

    parents = {}
    for e in pg.edges:
        parents.setdefault(e.to_id, []).append(e.from_id)

    # 1) output's DIRECT parents must be the five input families — no [] root:
    direct = set(parents.get(out, []))
    required_kinds = {"dva.in.alloc.", "dva.in.basis.", "dva.in.embedded.",
                      "dva.in.prices.", "dva.in.origin.", "dva.in.year."}
    matched = {p for p in direct for pref in required_kinds if pref in p}
    assert len(matched) >= 5, f"DVA node under-derived: parents={direct}"

    # 2) allocation input must connect back to explosion LINE nodes (which carry
    #    pack evidence upstream in engine runs):
    alloc_node = next(p for p in direct if "dva.in.alloc." in p)
    line_parents = [p for p in parents.get(alloc_node, [])
                    if p.startswith("derived.") and "dva.in." not in p]
    assert line_parents, "allocation input not linked to requirement lines"

    # 3) origin-assumption input must expose its assumption detail (epistemic trail):
    origin_node = next(p for p in direct if "dva.in.origin." in p)
    assert "raw_material_import_share" in pg.nodes[origin_node].detail
    # 4) no unrelated shortcut edges: evidence nodes may only feed via lines
    ev_direct = [p for p in direct if p.startswith("ev.")]
    assert not ev_direct, "evidence attached directly to DVA node (decorative)"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
