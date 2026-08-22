"""FlowGraph — typed, immutable requirement-flow core for FORGE WORLD V0.1.

Replaces the flat `ExplosionResult.lines` accumulation (V0 defects F3/N1) with an
explicit requirement DAG. Requirements propagate along edges as physical Quantities;
aggregates are computed by a single memoized traversal from the variant root, so each
edge contributes exactly once regardless of graph shape (linearity/oracle B holds by
construction) and results are invariant to traversal order.

Semantics
---------
- output_requirement(n): annual production/procurement requirement for n's OUTPUT,
  including n's own route yield losses (gross).
- input_requirement(n): annual amount of n consumed as an input by its consumers,
  i.e. sum over incoming edges of parent_output_requirement * edge.qty (net demand
  placed on n). A leaf material's reported requirement is its input_requirement;
  its output requirement additionally divides by its own route yield.
- Each recipe route's yield lives on that route's OUTGOING edges (inputs scale per
  good output unit) and on the node's own output gross-up — applied exactly once.

Nothing in this module mutates after construction.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .units import Quantity, UnitError

MAX_DEPTH = 12  # recipe-chain expansion budget (depth-honesty bound, oracle B2)


@dataclass(frozen=True)
class FlowEdge:
    """Directed requirement flow: consumer -> provider, qty per ONE unit of consumer output."""

    src: str                      # consumer node id (variant/part/recipe-tagged consumer)
    dst: str                      # provider node id (part/resource)
    qty: Quantity                 # physical amount of dst per one unit of src OUTPUT
    route: str = ""               # recipe id that generated this edge ("" = BOM edge)
    depth: int = 0


class FlowGraph:
    """Immutable requirement DAG over product/material nodes."""

    def __init__(
        self,
        variant_id: str,
        annual_units: float,
        nodes: Dict[str, str],                     # node_id -> kind (variant|part|resource)
        edges: Tuple[FlowEdge, ...],
        unit_by_node: Dict[str, Quantity],          # canonical unit for one unit of the node
        yield_by_node: Optional[Dict[str, float]] = None,   # own-route cumulative yield
        warnings: Tuple[str, ...] = (),
    ):
        self.variant_id = variant_id
        self.annual_units = float(annual_units)
        self.nodes: Dict[str, str] = dict(nodes)
        self.edges: Tuple[FlowEdge, ...] = tuple(edges)
        self.unit_by_node: Dict[str, Quantity] = dict(unit_by_node)
        self.yield_by_node: Dict[str, float] = dict(yield_by_node or {})
        self.warnings: Tuple[str, ...] = tuple(warnings)
        self._children: Dict[str, List[FlowEdge]] = {}
        self._parents: Dict[str, List[FlowEdge]] = {}
        for e in self.edges:
            self._children.setdefault(e.src, []).append(e)
            self._parents.setdefault(e.dst, []).append(e)
        self._out_memo: Dict[str, Quantity] = {}
        self._in_memo: Dict[str, Quantity] = {}

    # ---------------------------------------------------------------- structure
    def children(self, node_id: str) -> List[FlowEdge]:
        return list(self._children.get(node_id, ()))

    def parents(self, node_id: str) -> List[FlowEdge]:
        return list(self._parents.get(node_id, ()))

    def has_node(self, node_id: str) -> bool:
        return node_id in self.nodes

    def kind_of(self, node_id: str) -> str:
        return self.nodes.get(node_id, "?")

    def item_ids(self) -> List[str]:
        """All material nodes (parts/resources), sorted."""
        return sorted(n for n, k in self.nodes.items() if k in ("part", "resource"))

    def route_of(self, node_id: str) -> str:
        """Route id that expands this node ('' = raw leaf), from its outgoing edges."""
        outs = self._children.get(node_id, ())
        return outs[0].route if outs else ""

    # ---------------------------------------------------------------- aggregates
    def output_requirement(self, node_id: str) -> Quantity:
        """Annual gross output requirement (includes own-route yield loss).

        The variant root's output is the objective itself: annual_units, never
        yield-adjusted (its 'yield' slot is reserved and must stay unset).
        """
        if node_id == self.variant_id:
            return Quantity(self.annual_units, self.unit_by_node[node_id].unit)
        if node_id in self._out_memo:
            return self._out_memo[node_id]
        direct = self.input_requirement(node_id)
        y = self.yield_by_node.get(node_id, 1.0)
        val = direct.value / (y if y > 0 else 1e-9)
        self._out_memo[node_id] = Quantity(val, direct.unit)
        return self._out_memo[node_id]

    def input_requirement(self, node_id: str) -> Quantity:
        """Annual amount of node demanded by its consumers (each edge counted once)."""
        if node_id in self._in_memo:
            return self._in_memo[node_id]
        ins = self._parents.get(node_id, ())
        unit = self.unit_by_node[node_id]
        if not ins:
            self._in_memo[node_id] = Quantity(0.0, unit.unit)
            return self._in_memo[node_id]
        total: Optional[Quantity] = None
        for e in ins:
            parent_out = self.output_requirement(e.src)
            contrib = Quantity(parent_out.value * e.qty.value, e.qty.unit)
            total = contrib if total is None else _checked_add(total, contrib, node_id)
        self._in_memo[node_id] = total
        return total

    def annual_flows(self) -> Tuple[Dict[str, Quantity], Dict[str, Quantity]]:
        """(input_requirements, output_requirements) for every material node."""
        ins: Dict[str, Quantity] = {}
        outs: Dict[str, Quantity] = {}
        for nid in self.item_ids():
            ins[nid] = self.input_requirement(nid)
            outs[nid] = self.output_requirement(nid)
        return ins, outs


def _checked_add(a: Quantity, b: Quantity, ctx: str) -> Quantity:
    try:
        return a + b
    except UnitError as exc:
        raise UnitError(
            f"cannot merge heterogeneous requirement flows for '{ctx}' "
            f"({a.unit} vs {b.unit}); unit families must not be conflated"
        ) from exc
