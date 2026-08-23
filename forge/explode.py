"""V0.1 explosion: build a FlowGraph from the pack world, then derive aggregates.

Replaces the V0 cumulative-accumulator recursion (F3: shared upstreams double-counted;
N8: silent depth truncation). Construction is deterministic and order-invariant.

Single edge convention (the V0.1 invariant): every FlowEdge.qty is the physical amount
of the destination needed per ONE unit of the source's gross output. Annual amounts
are derived exclusively by FlowGraph aggregation, so no quantity is ever scaled twice.

Precedence rule: if a node declares explicit product structure (`decomposes_into`),
that BOM is the authoritative architecture for its composition and its recipe-input
expansion is skipped (a note records the suppressed recipe). Cycles are rejected.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .evidence import ProofGraph
from .flows import FlowEdge, FlowGraph, MAX_DEPTH
from .model import Part, ProductionRecipe, World
from .units import Quantity, UnitError

MASS_BALANCE_TOL = 0.05


def primary_recipe(w: World, part_id: str, geography: Optional[str] = None) -> Optional[ProductionRecipe]:
    """Route selection for producing part_id.

    Policy (oracle M): prefer routes applicable to the solve geography; among those,
    prefer primary route_type. Geography beats route_type because a domestic-capable
    secondary route is more decision-relevant for INDIA buildability than a GLOBAL
    primary that cannot be domestic. Falls back to any applicable route, then any
    route at all.
    """
    candidates = []
    for e in w.out_edges(part_id, "produced_via"):
        r = w.require(e.dst)
        if isinstance(r, ProductionRecipe):
            candidates.append(r)
    if not candidates:
        return None
    if geography:
        geo = [r for r in candidates if geography in r.applicable_geographies]
        if geo:
            pool = geo
        else:
            pool = [r for r in candidates if "GLOBAL" in r.applicable_geographies] or candidates
    else:
        pool = candidates
    primaries = [r for r in pool if r.route_type == "primary"]
    return (primaries or pool)[0]


@dataclass
class RequirementLine:
    item_id: str
    kind: str
    net_annual: Quantity          # input requirement (what consumers demand of this item)
    gross_annual: Quantity        # output requirement incl. own-route yield losses
    depth: int
    via_recipe: str = ""
    yield_factor: float = 1.0


@dataclass
class ExplosionResult:
    """Compatibility view over the FlowGraph plus derived annual aggregates."""

    variant_id: str
    annual_units: float
    flows: FlowGraph
    lines: Dict[str, RequirementLine] = field(default_factory=dict)
    mass_balance_warnings: List[str] = field(default_factory=list)
    proof_node_ids: Dict[str, str] = field(default_factory=dict)

    def items(self) -> List[str]:
        return sorted(self.lines.keys())

    def get(self, item_id: str) -> Optional[RequirementLine]:
        return self.lines.get(item_id)


def _yield_of(rec: Optional[ProductionRecipe]) -> float:
    if rec is None:
        return 1.0
    yf = 1.0
    for st in rec.steps:
        yf *= st.yield_fraction * (1.0 - st.scrap_fraction)
    return max(yf, 1e-9)


def _unit_of(w: World, item_id: str) -> str:
    ent = w.entities.get(item_id)
    unit = getattr(ent, "unit", None) if ent is not None else None
    if isinstance(unit, str) and unit:
        return unit
    return "pcs"


def _collect_bom_edges(w: World, node_id: str, depth: int,
                       out: List[FlowEdge], visiting: Set[str]):
    """Recursively collect decomposes_into edges; qty per ONE unit of consumer output."""
    if node_id in visiting:
        raise UnitError(f"cyclic BOM structure at '{node_id}'")
    children = w.out_edges(node_id, "decomposes_into")
    next_visiting = visiting | {node_id}
    for e in children:
        dst = e.dst
        qty = float(e.meta.get("qty", 1.0))
        out.append(FlowEdge(src=node_id, dst=dst,
                            qty=Quantity(qty, _unit_of(w, dst)), route="", depth=depth + 1))
    for e in children:
        _collect_bom_edges(w, e.dst, depth + 1, out, next_visiting)


def explode_variant(w: World, pg: ProofGraph, variant_id: str, annual_units: float,
                    years: List[int], geography: Optional[str] = None,
                    route_override: Optional[Dict[str, ProductionRecipe]] = None,
                    bom_additions: Optional[List[Tuple[str, float]]] = None,
                    bom_exclusions: Optional[Set[str]] = None) -> ExplosionResult:
    """Expand variant BOM + recipe chains into an immutable FlowGraph and aggregate lines.

    `route_override` maps part_id -> recipe used instead of route selection
    (architecture edits; substitutions). `bom_additions` appends synthetic BOM edges
    (variant -> part, qty pcs per unit) before expansion. `bom_exclusions` drops
    declared BOM parts (architecture edits where the replacement part differs).
    Emits proof nodes for every computed line (C15 legacy behavior preserved).
    Raises UnitError on dimensionally invalid merges or cycles.
    """
    overrides = dict(route_override or {})
    root_unit = "pcs"
    nodes: Dict[str, str] = {variant_id: "variant"}
    unit_by_node: Dict[str, Quantity] = {variant_id: Quantity(1.0, root_unit)}
    yield_by_node: Dict[str, float] = {}
    edges: List[FlowEdge] = []
    notes: List[str] = []

    base_node = pg.add_node(
        "derived",
        f"Target: {annual_units:g} units/yr of {variant_id}",
        {"annual_units": annual_units, "variant": variant_id},
    )

    # --- Phase A: full BOM structure (product decomposition), per-unit edge qtys ---
    bom: List[FlowEdge] = []
    _collect_bom_edges(w, variant_id, 0, bom, set())
    excl = set(bom_exclusions or set())
    if excl:
        bom = [e for e in bom if e.dst not in excl]
        notes.append(f"BOM parts excluded by architecture edit: {sorted(excl)}")
    for pid, qty in (bom_additions or []):
        if not w.has(pid):
            w.add(Part(id=pid, name=pid, kind="part", part_class="component"))
        bom.append(FlowEdge(src=variant_id, dst=pid,
                            qty=Quantity(float(qty), "pcs"), route="", depth=1))
    edges.extend(bom)
    bom_structured: Set[str] = {e.src for e in bom}
    for e in bom:
        nodes.setdefault(e.dst, "part" if isinstance(w.entities.get(e.dst), Part) else "resource")
        existing_unit = unit_by_node.get(e.dst)
        if existing_unit is not None and e.dst != variant_id and existing_unit.unit != e.qty.unit:
            raise UnitError(
                f"item '{e.dst}' demanded in incompatible units "
                f"({existing_unit.unit} vs {e.qty.unit})"
            )
        unit_by_node.setdefault(e.dst, Quantity(1.0, e.qty.unit))

    depth_by_node: Dict[str, int] = {}
    for e in bom:
        depth_by_node[e.dst] = max(depth_by_node.get(e.dst, 0), e.depth)

    # --- Phase B: recipe-input expansion over a BFS frontier ---
    # Kit-style variants (empty BOM, recipe-defined) seed the frontier with the
    # variant root itself so its production route expands (japan-2011 backtest).
    if bom:
        frontier: List[str] = sorted({e.dst for e in bom},
                                     key=lambda x: (depth_by_node.get(x, 0), x))
    else:
        root_rec = overrides.get(variant_id) or primary_recipe(w, variant_id, geography=geography)
        if root_rec is None:
            frontier = []
            notes.append(f"variant '{variant_id}' declares neither BOM nor recipe")
        else:
            frontier = [variant_id]
            depth_by_node[variant_id] = 0
    expanded_routes: set = set()
    truncated: bool = False

    while frontier:
        nid = frontier.pop(0)
        d = depth_by_node.get(nid, 0)
        rec = overrides.get(nid) or primary_recipe(w, nid, geography=geography)
        yield_by_node[nid] = _yield_of(rec)
        if rec is None:
            continue
        if nid in bom_structured:
            notes.append(
                f"'{nid}' has explicit BOM structure; recipe '{rec.id}' inputs are "
                f"suppressed in favor of the declared architecture"
            )
            continue
        if d >= MAX_DEPTH:
            warnings_msg = (
                f"recipe-chain expansion stopped at MAX_DEPTH={MAX_DEPTH} for '{nid}'; "
                f"deeper inputs are NOT counted"
            )
            notes.append(warnings_msg)
            truncated = True
            continue
        key = (nid, rec.id)
        if key in expanded_routes:
            continue
        expanded_routes.add(key)
        out_per_unit = rec.output_quantity.value or 1.0
        for iname, iq in rec.inputs:
            per_out = Quantity(iq.value / out_per_unit, iq.unit)   # per ONE output unit
            edges.append(FlowEdge(src=nid, dst=iname, qty=per_out, route=rec.id, depth=d + 1))
            existing_unit = unit_by_node.get(iname)
            if existing_unit is not None and existing_unit.unit != per_out.unit:
                raise UnitError(
                    f"item '{iname}' demanded in incompatible units "
                    f"({existing_unit.unit} vs {per_out.unit})"
                )
            nodes.setdefault(iname, "part" if isinstance(w.entities.get(iname), Part) else "resource")
            unit_by_node.setdefault(iname, Quantity(1.0, per_out.unit))
            if iname not in depth_by_node or depth_by_node[iname] < d + 1:
                depth_by_node[iname] = d + 1
            if iname not in expanded_routes and all(i[0] != iname for i in frontier):
                frontier.append(iname)
    frontier = [n for n in frontier]  # keep reference; loop consumed copies above
    if truncated:
        notes.append("explosion depth budget exhausted; see per-node notes")

    fg = FlowGraph(variant_id=variant_id, annual_units=float(annual_units), nodes=nodes,
                   edges=tuple(edges), unit_by_node=unit_by_node,
                   yield_by_node=yield_by_node, warnings=tuple(notes))

    # --- Aggregates + proof nodes ---
    ins, outs = fg.annual_flows()
    res = ExplosionResult(variant_id=variant_id, annual_units=float(annual_units), flows=fg)
    for nid in fg.item_ids():
        # route provenance must match the route actually used for expansion
        rec_route = fg.route_of(nid)
        rec = None
        if overrides.get(nid) is not None:
            rec = overrides[nid]
        elif rec_route:
            rec = primary_recipe(w, nid, geography=geography)
        line = RequirementLine(
            item_id=nid,
            kind=getattr(w.entities.get(nid), "kind", "material_or_resource"),
            net_annual=ins[nid],
            gross_annual=outs[nid],
            depth=depth_by_node.get(nid, 0),
            via_recipe=fg.route_of(nid),
            yield_factor=yield_by_node.get(nid, 1.0),
        )
        res.lines[nid] = line
        lbl = f"{nid}: net {line.net_annual} / gross {line.gross_annual}/yr" + (
            f" via {line.via_recipe}" if line.via_recipe else "")
        detail = {
            "net_per_year": str(line.net_annual), "gross_per_year": str(line.gross_annual),
            "depth": line.depth, "recipe": line.via_recipe,
            "cumulative_yield": round(line.yield_factor, 6), "years": years,
        }
        res.proof_node_ids[nid] = pg.derive([base_node], lbl, detail)

    res.mass_balance_warnings = check_mass_balance(w, res)
    return res


def check_mass_balance(w: World, res: ExplosionResult, tol: float = MASS_BALANCE_TOL) -> List[str]:
    """Inputs must cover outputs across recipes within declared tolerance.

    Pure function: returns warnings; does not mutate the result's list (N7 fixed).
    Flags both deficits AND unexplained surplus (inputs >> outputs).
    """
    warnings: List[str] = []
    fg = res.flows
    for pid in fg.item_ids():
        if not fg.children(pid):
            continue
        rec = primary_recipe(w, pid)
        if rec is None:
            continue
        part = w.get(pid)
        out_mass = getattr(part, "mass", None)
        if out_mass is None:
            continue
        total_in = None
        for iname, iq in rec.inputs:
            ine = w.get(iname)
            im = getattr(ine, "mass", None)
            if im is None:
                total_in = None
                break
            scaled = im * (iq.value / (rec.output_quantity.value or 1.0))
            total_in = scaled if total_in is None else total_in + scaled
        if total_in is None:
            continue
        if out_mass.dim != total_in.dim:
            warnings.append(
                f"{pid}: input/output mass dimension mismatch ({total_in.unit} vs {out_mass.unit}); "
                f"unit families must not be conflated"
            )
            continue
        if total_in.canonical() < out_mass.canonical() * (1 - tol):
            warnings.append(f"{pid}: mass not conserved: inputs {total_in} < output {out_mass}")
        elif total_in.canonical() > out_mass.canonical() * (1 + 10 * max(tol, 0.05)):
            warnings.append(f"{pid}: input mass surplus: inputs {total_in} >> output {out_mass}")
    return warnings
