from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .evidence import ProofGraph
from .model import Part, ProductionRecipe, World
from .units import Quantity


def primary_recipe(w: World, part_id: str) -> Optional[ProductionRecipe]:
    """Return the primary route producing part_id, preferring domestic-applicable primary."""
    candidates = []
    for e in w.out_edges(part_id, "produced_via"):
        r = w.require(e.dst)
        if isinstance(r, ProductionRecipe):
            candidates.append(r)
    primaries = [r for r in candidates if r.route_type == "primary"]
    pool = primaries or candidates
    if not pool:
        return None
    india = [r for r in pool if "INDIA" in r.applicable_geographies]
    return (india or pool)[0]


@dataclass
class RequirementLine:
    item_id: str
    kind: str
    net_annual: Quantity
    gross_annual: Quantity
    depth: int
    via_recipe: str = ""
    yield_factor: float = 1.0


@dataclass
class ExplosionResult:
    variant_id: str
    annual_units: float
    lines: Dict[str, RequirementLine] = field(default_factory=dict)
    mass_balance_warnings: List[str] = field(default_factory=list)
    proof_node_ids: Dict[str, str] = field(default_factory=dict)
    input_accumulator: Dict[str, Quantity] = field(default_factory=dict)
    input_provenance: Dict[str, tuple] = field(default_factory=dict)

    def items(self) -> List[str]:
        return sorted(self.lines.keys())

    def get(self, item_id: str) -> Optional[RequirementLine]:
        return self.lines.get(item_id)


def _bom_leaves(w: World, node_id: str, qty_per_parent: float, depth: int,
                out: List[Tuple[str, float, int]]):
    children = w.out_edges(node_id, "decomposes_into")
    if not children:
        out.append((node_id, qty_per_parent, depth))
        return
    for e in children:
        child_qty = qty_per_parent * float(e.meta.get("qty", 1.0))
        _bom_leaves(w, e.dst, child_qty, depth + 1, out)


def explode_variant(w: World, pg: ProofGraph, variant_id: str, annual_units: float,
                    years: List[int], pack_title: str = "") -> ExplosionResult:
    """Expand variant BOM into annual net+gross requirements for each year.

    Gross-up applies each recipe's process yield/scrap so upstream demand reflects losses.
    Emits proof nodes for every computed line (C15).
    """
    leaves: List[Tuple[str, float, int]] = []
    _bom_leaves(w, variant_id, 1.0, 0, leaves)

    res = ExplosionResult(variant_id=variant_id, annual_units=annual_units)

    base_node = pg.add_node(
        "derived",
        f"Target: {annual_units:g} units/yr of {variant_id}",
        {"annual_units": annual_units, "variant": variant_id},
    )

    counts: Dict[str, Tuple[float, int]] = {}
    for pid, per_unit, depth in leaves:
        ent = w.require(pid)
        prev = counts.get(pid, (0.0, depth))
        counts[pid] = (prev[0] + per_unit, max(prev[1], depth))

    for pid, (per_unit, depth) in sorted(counts.items()):
        ent = w.require(pid)
        unit_dim = "pcs"
        net = Quantity(per_unit * annual_units, unit_dim)
        rec = primary_recipe(w, pid)
        yf = 1.0
        via = ""
        if rec is not None:
            yf = 1.0
            for st in rec.steps:
                yf *= st.yield_fraction * (1.0 - st.scrap_fraction)
            yf = max(yf, 1e-9)
            via = rec.id
        gross = net * (1.0 / yf)
        label = f"{pid}: net {net} / gross {gross}/yr" + (f" via {via}" if via else "")
        detail = {
            "net_per_year": str(net), "gross_per_year": str(gross),
            "depth": depth, "recipe": via, "cumulative_yield": round(yf, 6),
            "years": years,
        }
        nid = pg.derive([base_node], label, detail)
        res.lines[pid] = RequirementLine(
            item_id=pid,
            kind=getattr(ent, "part_class", ent.kind),
            net_annual=net,
            gross_annual=gross,
            depth=depth,
            via_recipe=via,
            yield_factor=yf,
        )
        res.proof_node_ids[pid] = nid

    _expand_input_chains(w, pg, res)
    return res


def _expand_input_chains(w: World, pg: ProofGraph, res: ExplosionResult):
    """Phase B: accumulate recipe-input demand chains with per-route yield gross-up."""
    leaf_gross = {
        pid: line.gross_annual.value
        for pid, line in res.lines.items()
    }
    for pid, gv in sorted(leaf_gross.items()):
        _accumulate_inputs(w, pg, res, pid, gv, 0, ())

    for iname, qty in sorted(res.input_accumulator.items()):
        yf = _yield_of(w, iname)
        gross = Quantity(qty.value, qty.unit)
        net = Quantity(qty.value * yf, qty.unit)
        src_part = res.input_provenance.get(iname, ("?", 9))[0]
        existing_leaf = res.lines.get(iname)
        if existing_leaf is not None:
            merged_gross = existing_leaf.gross_annual + gross
            merged_net = existing_leaf.net_annual + net
            res.lines[iname] = RequirementLine(
                item_id=iname,
                kind=existing_leaf.kind,
                net_annual=merged_net,
                gross_annual=merged_gross,
                depth=existing_leaf.depth,
                via_recipe=existing_leaf.via_recipe,
                yield_factor=existing_leaf.yield_factor,
            )
        else:
            ent = w.entities.get(iname)
            res.lines[iname] = RequirementLine(
                item_id=iname,
                kind=(getattr(ent, "part_class", None) or getattr(ent, "kind", "material_or_resource")) if ent is not None else "material_or_resource",
                net_annual=net,
                gross_annual=gross,
                depth=res.input_provenance.get(iname, ("?", 9))[1],
                via_recipe="",
                yield_factor=yf,
            )
        parent_node = res.proof_node_ids.get(src_part) or pg.add_node(
            "derived", f"{src_part} requirements"
        )
        lbl = f"{iname}: gross {gross}/yr (input chain via {src_part})"
        det = {"gross_per_year": str(gross), "source_part": src_part}
        res.proof_node_ids[iname] = pg.derive([parent_node], lbl, det)


def _accumulate_inputs(
    w: World,
    pg: ProofGraph,
    res: ExplosionResult,
    item_id: str,
    gross_qty_value: float,
    depth: int,
    seen: Tuple[str, ...],
):
    if depth > 8 or item_id in seen:
        return
    rec = primary_recipe(w, item_id)
    if rec is None:
        return
    out_per_unit = rec.output_quantity.value or 1.0
    for iname, iq in rec.inputs:
        raw_need = iq.value * (gross_qty_value / out_per_unit)
        need_gross = raw_need / _yield_of(w, iname)
        acc = res.input_accumulator.get(iname)
        if acc is not None and acc.dim != iq.dim:
            key = f"{iname}@via:{item_id}"
            cur = res.input_accumulator.get(key)
            res.input_accumulator[key] = Quantity((cur.value if cur else 0.0) + need_gross, iq.unit)
            res.input_provenance.setdefault(key, (item_id, depth + 1))
            _accumulate_inputs(w, pg, res, key, res.input_accumulator[key].value, depth + 1, seen + (item_id,))
            continue
        res.input_accumulator[iname] = Quantity(
            (acc.value if acc else 0.0) + need_gross, iq.unit
        )
        if iname not in res.input_provenance:
            res.input_provenance[iname] = (item_id, depth + 1)
        _accumulate_inputs(w, pg, res, iname, res.input_accumulator[iname].value, depth + 1, seen + (item_id,))


def _yield_of(w: World, item_id: str) -> float:
    rec = primary_recipe(w, item_id)
    if rec is None:
        return 1.0
    yf = 1.0
    for st in rec.steps:
        yf *= st.yield_fraction * (1.0 - st.scrap_fraction)
    return max(yf, 1e-9)


def check_mass_balance(w: World, res: ExplosionResult, tol: float = 0.05) -> List[str]:
    warnings: List[str] = []
    for pid in list(res.lines.keys()):
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
            res.mass_balance_warnings.append(
                f"{pid}: input/output mass dimension mismatch ({total_in.unit} vs {out_mass.unit}); "
                f"unit families must not be conflated"
            )
            continue
        if total_in.canonical() < out_mass.canonical() * (1 - tol):
            warnings.append(f"{pid}: mass not conserved: inputs {total_in} < output {out_mass}")
    res.mass_balance_warnings.extend(warnings)
    return warnings
