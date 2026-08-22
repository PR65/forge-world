import dataclasses

import pytest

from forge.evidence import EvidenceRecord, ProofGraph, Source
from forge.epistemics import Confidence, EpistemicClass


def _src():
    return Source(id="s1", name="S", publisher="P", license="public")


def _rec(**kw):
    base = dict(
        claim_id="c1",
        subject="x",
        predicate="y",
        epistemic_class=EpistemicClass.REPORTED,
        source_ids=("s1",),
    )
    base.update(kw)
    return EvidenceRecord(**base)


def test_evidence_record_is_immutable():
    r = _rec()
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.value_text = "tampered"


def test_reported_requires_source():
    from forge.pack import PackValidationError, _build_evidence

    d = {
        "claim_id": "z",
        "subject": "a",
        "predicate": "b",
        "epistemic_class": "REPORTED",
        "source_ids": [],
    }
    with pytest.raises(PackValidationError):
        _build_evidence(d, {"s1": _src()})


def test_confidence_dimensions_validated():
    with pytest.raises(ValueError):
        Confidence({"magic_score": 0.5})
    c = Confidence({"authority": 0.8})
    assert c.get("authority") == 0.8
    assert c.get("directness") is None
    with pytest.raises(ValueError):
        Confidence({"authority": 2.0})


def test_proof_graph_lineage_and_upstream():
    pg = ProofGraph()
    ev = pg.add_node("evidence", "claim", {}, ("s1",), node_id="ev.c1")
    mid = pg.derive([ev], "step1")
    out = pg.output([mid], "final")
    ups = pg.upstream_evidence(out)
    assert any(n.node_id == "ev.c1" for n in ups)
    nodes, edges = pg.subgraph(out)
    assert len(nodes) == 3 and len(edges) == 2


def test_conflicted_is_first_class_enum_member():
    assert EpistemicClass.CONFLICTED.value == "CONFLICTED"
    assert EpistemicClass.UNKNOWN.value == "UNKNOWN"
