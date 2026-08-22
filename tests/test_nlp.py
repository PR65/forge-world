import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from forge.nlp import parse_objective


def test_full_objective_sentence():
    p = parse_objective("What would it take for India to manufacture 1 million humanoids a year by 2030?")
    assert p.objective is not None
    assert p.objective.annual_units == 1_000_000
    assert p.objective.deadline_year == 2030
    assert p.objective.variant_id == "hv2_industrial"
    assert not p.unresolved
    assert any("humanoids" in i for i in p.interpretations)


def test_shock_sentence_maps_preset_and_reports_unresolved():
    p = parse_objective("What if Chinese rare-earth magnet exports fell by 80%?")
    assert "shk_cn_ree_minus80" in p.shocks
    assert p.objective is None
    assert "annual output quantity" in p.unresolved


def test_dva_and_budget_extraction():
    p = parse_objective("Reach 85% domestic value addition for 500k robots by 2029 with $50 billion")
    assert p.objective is not None
    assert p.objective.min_dva == 0.85
    assert p.objective.annual_units == 500_000
    assert p.objective.deadline_year == 2029
    assert p.objective.budget_usd == 50e9


def test_satellite_domain_routing():
    p = parse_objective("India builds 50 satellites per year by 2030")
    assert p.objective is not None
    assert p.objective.variant_id == "eo_smallsat_300kg"
    assert p.objective.annual_units == 50
