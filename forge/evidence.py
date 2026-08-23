from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .epistemics import Confidence, EpistemicClass


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    publisher: str
    url: str = ""
    source_type: str = "document"
    license: str = "UNSPECIFIED"
    access_date: str = ""
    notes: str = ""

    def to_json(self) -> Dict:
        return dict(
            id=self.id, name=self.name, publisher=self.publisher, url=self.url,
            source_type=self.source_type, license=self.license,
            access_date=self.access_date, notes=self.notes,
        )


@dataclass(frozen=True)
class EvidenceRecord:
    """Immutable claim about the world. Corrections create new records (supersedes)."""

    claim_id: str
    subject: str
    predicate: str
    epistemic_class: EpistemicClass
    value_text: str = ""
    value_quantity: Optional[tuple] = None
    unit_note: str = ""
    source_ids: Tuple[str, ...] = ()
    publication_date: str = ""
    effective_date: str = ""
    retrieval_date: str = ""
    geographic_scope: str = "GLOBAL"
    technical_scope: str = ""
    extraction_method: str = "manual"
    confidence: Confidence = field(default_factory=Confidence)
    license: str = "UNSPECIFIED"
    derived_from: Tuple[str, ...] = ()
    supersedes: Optional[str] = None
    review_status: str = "unreviewed"
    quote_or_caveat: str = ""

    def to_json(self) -> Dict:
        return dict(
            claim_id=self.claim_id, subject=self.subject, predicate=self.predicate,
            epistemic_class=self.epistemic_class.value,
            value_text=self.value_text,
            value_quantity=(list(self.value_quantity) if self.value_quantity else None),
            unit_note=self.unit_note, source_ids=list(self.source_ids),
            publication_date=self.publication_date, effective_date=self.effective_date,
            retrieval_date=self.retrieval_date, geographic_scope=self.geographic_scope,
            technical_scope=self.technical_scope, extraction_method=self.extraction_method,
            confidence=self.confidence.to_json(), license=self.license,
            derived_from=list(self.derived_from), supersedes=self.supersedes,
            review_status=self.review_status, quote_or_caveat=self.quote_or_caveat,
        )


@dataclass
class ProofNode:
    node_id: str
    kind: str
    label: str
    detail: Dict = field(default_factory=dict)
    sources: Tuple[str, ...] = ()

    def to_json(self) -> Dict:
        return dict(node_id=self.node_id, kind=self.kind, label=self.label,
                    detail=self.detail, sources=list(self.sources))


@dataclass
class ProofEdge:
    from_id: str
    to_id: str
    relation: str

    def to_json(self) -> Dict:
        return dict(from_id=self.from_id, to_id=self.to_id, relation=self.relation)


class ProofGraph:
    """Derivation DAG. Evidence nodes are roots; output nodes are leaves."""

    def __init__(self):
        self.nodes: Dict[str, ProofNode] = {}
        self.edges: List[ProofEdge] = []
        self._counter = 0

    def add_node(self, kind: str, label: str, detail: Optional[Dict] = None,
                 sources: Tuple[str, ...] = (), node_id: Optional[str] = None) -> str:
        if node_id is None:
            self._counter += 1
            node_id = f"{kind}.{self._counter}"
        if node_id not in self.nodes:
            self.nodes[node_id] = ProofNode(node_id, kind, label, dict(detail or {}), tuple(sources))
        else:
            existing = self.nodes[node_id]
            merged = dict(existing.detail)
            for k, v in (detail or {}).items():
                merged.setdefault(k, v)
            allsrc = set(existing.sources) | set(sources or ())
            self.nodes[node_id] = ProofNode(node_id, existing.kind, existing.label, merged, tuple(sorted(allsrc)))
        return node_id

    def add_edge(self, from_id: str, to_id: str, relation: str = "derived_from"):
        if from_id not in self.nodes or to_id not in self.nodes:
            raise KeyError(f"proof edge references unknown node: {from_id} -> {to_id}")
        e = ProofEdge(from_id, to_id, relation)
        if not any(x.from_id == from_id and x.to_id == to_id and x.relation == relation
                   for x in self.edges):
            self.edges.append(e)

    def evidence_node(self, rec: EvidenceRecord) -> str:
        nid = f"ev.{rec.claim_id}"
        self.add_node("evidence", f"{rec.subject} {rec.predicate} = {rec.value_text}",
                      rec.to_json(), rec.source_ids, node_id=nid)
        return nid

    def derive(self, inputs: List[str], label: str, detail: Optional[Dict] = None,
               relation: str = "derived_from") -> str:
        nid = self.add_node("derived", label, detail)
        for i in inputs:
            self.add_edge(i, nid, relation)
        return nid

    def assumption(self, label: str, detail: Optional[Dict] = None) -> str:
        return self.add_node("assumption", label, detail)

    def scenario_node(self, label: str, detail: Optional[Dict] = None) -> str:
        return self.add_node("scenario", label, detail)

    def output(self, inputs: List[str], label: str, detail: Optional[Dict] = None) -> str:
        nid = self.add_node("output", label, detail)
        for i in inputs:
            self.add_edge(i, nid)
        return nid

    def upstream_evidence(self, node_id: str) -> List[ProofNode]:
        seen, stack, out = set(), [node_id], []
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            n = self.nodes.get(cur)
            if n is None:
                continue
            if n.kind == "evidence":
                out.append(n)
            for e in self.edges:
                if e.to_id == cur:
                    stack.append(e.from_id)
        return out

    def subgraph(self, node_id: str, max_depth: int = 64) -> Tuple[List[Dict], List[Dict]]:
        keep, frontier, depth = {node_id}, {node_id}, 0
        while frontier and depth < max_depth:
            nxt = set()
            for nid in frontier:
                for e in self.edges:
                    if e.to_id == nid and e.from_id not in keep:
                        keep.add(e.from_id)
                        nxt.add(e.from_id)
            frontier = nxt
            depth += 1
        nodes = [self.nodes[n].to_json() for n in self.nodes if n in keep]
        edges = [e.to_json() for e in self.edges if e.from_id in keep and e.to_id in keep]
        return nodes, edges

    def to_json(self) -> Dict:
        return dict(
            nodes=[n.to_json() for n in self.nodes.values()],
            edges=[e.to_json() for e in self.edges],
        )


def world_snapshot(w: World) -> Dict:
    """Canonicalized, hashable snapshot of solver-relevant world state.

    Captures every entity's dataclass fields (numeric values included) plus the
    typed edge list. Order-independent (sorted); excludes nothing that can change
    a solve. Used by ModelRun identity — V0 hashed only pack summary counts, so a
    100,000x capacity change left the run hash byte-identical (F21/P7b).
    """
    ents: Dict[str, Dict] = {}
    for eid in sorted(w.entities.keys()):
        e = w.entities[eid]
        d: Dict = {"kind": e.kind}
        for f in e.__dataclass_fields__:
            if f in ("id", "kind"):
                continue
            v = getattr(e, f)
            if hasattr(v, "to_json"):
                v = v.to_json()
            elif hasattr(v, "value") and hasattr(v, "unit"):
                v = [v.value, v.unit]
            elif isinstance(v, tuple):
                v = [_tup_item(x) for x in v]
            elif isinstance(v, list):
                v = [_tup_item(x) for x in v]
            elif isinstance(v, dict):
                v = {k: _tup_item(x) for k, x in sorted(v.items())}
            d[f] = v
        ents[eid] = d
    edges = sorted((e.src, e.relation, e.dst) for e in w.edges)
    return {"entities": ents, "edges": edges}


def _tup_item(x):
    if hasattr(x, "value") and hasattr(x, "unit"):
        return [x.value, x.unit]
    if hasattr(x, "to_json"):
        return x.to_json()
    if isinstance(x, (tuple, list)):
        return [_tup_item(i) for i in x]
    if isinstance(x, dict):
        return {k: _tup_item(v) for k, v in sorted(x.items())}
    return x


def snapshot_hash(payload) -> str:
    blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()
