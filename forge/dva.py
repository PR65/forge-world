"""V0.1 DVA: recursive domestic-value-addition over the delivered mix.

V0 defects corrected here (F2 class):
- Domesticity was decided by recipe geography flags only; an item allocated
  domestically by the solver whose route lacked an INDIA tag contributed ZERO value
  even when fully made domestically. V0.1 rule: domesticity of DELIVERY follows the
  solved allocation (domestic_used share); the recipe walk only computes EMBEDDED
  import content of that domestic production.
- Inputs without any recipe were silently "fully imported". V0.1 rule: a raw
  material with evidenced domestic supply capacity counts as domestically sourced;
  with NO evidence either way its origin is UNKNOWN and it is treated per the
  explicit scenario default (`raw_material_import_share`, ASSUMPTION — never silent).
- Processing value added defaults are emitted as named ASSUMPTIONs (kept).

Convention (C18): DVA = 1 − imported_content_cost / ex_works_cost over DELIVERED
units. Shortfall exits both numerator and denominator (P22) and is reported
separately so nobody reads delivered-mix DVA as economy-wide performance.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .capacity import capacity_envelope
from .evidence import ProofGraph
from .explode import ExplosionResult, primary_recipe
from .model import ProductionRecipe, World
from .solve import ScenarioOptions
from .units import Quantity


@dataclass
class DVABreakdown:
    fraction: float
    total_cost_usd: float
    imported_cost_usd: float
    convention: str = ("C18 recursive; delivery domesticity from solved allocation; "
                        "embedded imports counted once at first arrival")
    per_item: Dict[str, Dict] = field(default_factory=dict)
    assumptions_used: List[str] = field(default_factory=list)
    shortfall_note: str = ""


_noted_raw_shares: set = set()


def _has_domestic_supply(w: World, item_id: str, year: int, geography: str) -> bool:
    """Evidenced domestic production capability for a raw material."""
    env = capacity_envelope(w, item_id, year, geography=geography)
    if env.domestic.is_unknown():
        return False
    return (env.domestic.hi or 0.0) > 0.0


def _embedded_import_content(
    w: World,
    rec: ProductionRecipe,
    opts: ScenarioOptions,
    year: int,
    depth: int,
    seen: Tuple[str, ...],
    assumptions: List[str],
) -> Tuple[float, float]:
    """(input_cost_total, input_cost_imported) per ONE unit of recipe output.

    For each declared input:
      - if it has its own production route, recurse for embedded content and add
        processing value (declared or named-ASSUMPTION default);
      - if it is a raw material WITH evidenced domestic supply, price it at the
        domestic cost — zero embedded import by default;
      - otherwise its origin is UNKNOWN: apply opts.raw_material_import_share
        (explicit ASSUMPTION recorded once).
    """
    if depth > 8 or rec.id in seen:
        return (0.0, 0.0)
    total = 0.0
    imported = 0.0
    scale = 1.0 / (rec.output_quantity.value or 1.0)
    geo = opts.geography
    for iname, iq in rec.inputs:
        need = iq.value * scale
        sub_rec = primary_recipe(w, iname, geography=geo)
        unit_cost_dom = opts.cost_domestic.get(iname)
        unit_cost_imp = opts.cost_import.get(iname, unit_cost_dom if unit_cost_dom is not None else 1.0)
        if sub_rec is not None:
            t_sub, i_sub = _embedded_import_content(
                w, sub_rec, opts, year, depth + 1, seen + (rec.id,), assumptions
            )
            proc_key = f"processing:{iname}"
            if proc_key in opts.cost_domestic:
                proc = opts.cost_domestic[proc_key]
            else:
                proc = 0.35 * max(t_sub, 0.5)
                assumptions.append(f"processing cost for {iname} assumed at 35% of input cost")
            item_total = t_sub + proc
            item_imported = i_sub
            total += need * item_total
            imported += need * item_imported
        elif _has_domestic_supply(w, iname, year, geo):
            price = unit_cost_dom if unit_cost_dom is not None else unit_cost_imp
            total += need * price
            imported += 0.0
        else:
            share = opts.raw_material_import_share
            price = unit_cost_imp
            total += need * price
            imported += need * price * share
            key = f"raw_share:{iname}"
            if key not in _noted_raw_shares:
                _noted_raw_shares.add(key)
                assumptions.append(
                    f"origin UNKNOWN for {iname}; raw_material_import_share="
                    f"{share:.2f} applied (ASSUMPTION)"
                )
    return (total, imported)


def dva_fraction(
    w: World,
    pg: ProofGraph,
    explosion: ExplosionResult,
    opts: ScenarioOptions,
    allocations_by_year: Optional[Dict[int, list]] = None,
    decision_year: Optional[int] = None,
) -> DVABreakdown:
    br = DVABreakdown(fraction=0.0, total_cost_usd=0.0, imported_cost_usd=0.0)
    assumptions: List[str] = []
    alloc_map: Dict[str, Tuple[float, float]] = {}
    target_year: Optional[int] = None
    if allocations_by_year:
        target_year = decision_year
        if target_year is None or target_year not in allocations_by_year:
            target_year = max(allocations_by_year.keys())
        for g in allocations_by_year.get(target_year, []):
            denom = g.domestic_used + g.imports_used + g.shortfall
            if denom > 0:
                alloc_map[g.item_id] = (
                    g.domestic_used / denom,
                    g.imports_used / denom,
                )

    # ---- DVA BASIS: product structure, not process structure -----------------
    # Every physical part composing the final product counts ONCE at its ex-works
    # value; how that part is made (recipe chains) contributes only EMBEDDED import
    # content. Items demanded solely as recipe inputs are intermediates: excluded
    # from the delivered-value sum (V0 triple-counted them — F2). Kit-style
    # variants with no explicit BOM fall back to counting every exploded item.
    fg = explosion.flows
    bom_in = {e.dst for e in fg.edges if e.route == "" and e.src != fg.variant_id}
    bom_in |= {e.dst for e in fg.edges if e.src == fg.variant_id}
    bom_structured_items = {i for i in fg.item_ids()
                            if any(e.dst == i and e.route == "" for e in fg.edges)}
    bom_out = {e.src for e in fg.edges if e.route == ""}
    basis_items = {i for i in bom_structured_items if i not in bom_out}
    if not bom_structured_items:
        basis_items = set(fg.item_ids())

    grand_total = 0.0
    grand_imported = 0.0
    grand_shortfall_qty = 0.0

    for item in explosion.items():
        line = explosion.get(item)
        qty = line.net_annual.value if line else 0.0
        in_basis = item in basis_items
        dom_share, imp_share = alloc_map.get(item, (0.0, 1.0))
        shortfall_share = max(0.0, 1.0 - dom_share - imp_share)
        year = target_year or 2030

        rec = primary_recipe(w, item, geography=opts.geography)

        dom_unit_total: Optional[float] = None
        dom_unit_imported: Optional[float] = None
        if dom_share > 0:
            if rec is not None:
                t_in, i_in = _embedded_import_content(
                    w, rec, opts, year, 0, (), assumptions
                )
                proc_key = f"processing:{item}"
                if proc_key in opts.cost_domestic:
                    proc_cost = opts.cost_domestic[proc_key]
                else:
                    proc_cost = 0.35 * max(t_in, 0.5)
                    assumptions.append(
                        f"processing cost for {item} assumed at 35% of input cost"
                    )
                dom_unit_total = t_in + proc_cost
                dom_unit_imported = i_in
                dom_price = opts.cost_domestic.get(item)
                if dom_price is not None and dom_price > 0:
                    dom_unit_total = max(dom_unit_total, dom_price)
            else:
                # domestically DELIVERED but no production route modeled:
                # priced from scenario tables; embedded content unknown->share rule
                base_price = opts.cost_domestic.get(
                    item, opts.cost_import.get(item, 1.0)
                )
                dom_unit_total = base_price
                if _has_domestic_supply(w, item, year, opts.geography):
                    dom_unit_imported = 0.0
                else:
                    dom_unit_imported = base_price * opts.raw_material_import_share
                    assumptions.append(
                        f"embedded import share for route-less {item} set to "
                        f"raw_material_import_share={opts.raw_material_import_share:.2f} "
                        f"(ASSUMPTION)"
                    )
            if (opts.cost_domestic.get(item) is None
                    and opts.cost_import.get(item) is None
                    and rec is None):
                assumptions.append(f"unit cost for {item} defaulted to 1.0 USD (ASSUMPTION)")

        imp_unit = opts.cost_import.get(item, opts.cost_domestic.get(item, 1.0))
        if (opts.cost_import.get(item) is None
                and opts.cost_domestic.get(item) is None
                and imp_share > 0 and rec is None):
            assumptions.append(f"unit cost for {item} defaulted to 1.0 USD (ASSUMPTION)")

        item_total = 0.0
        item_imported = 0.0
        if in_basis:
            # product part: value enters the denominator once
            if dom_unit_total is not None:
                item_total += dom_share * qty * dom_unit_total
                item_imported += dom_share * qty * (dom_unit_imported or 0.0)
            item_total += imp_share * qty * imp_unit
            item_imported += imp_share * qty * imp_unit

        grand_total += item_total
        grand_imported += item_imported
        if in_basis:
            grand_shortfall_qty += shortfall_share * qty
        br.per_item[item] = {
            "qty": qty,
            "in_dva_basis": in_basis,
            "domestic_share_solved": round(dom_share, 4),
            "import_share_solved": round(imp_share, 4),
            "shortfall_share": round(shortfall_share, 4),
            "unit_cost_domestic": (round(dom_unit_total, 6)
                                    if dom_unit_total is not None else None),
            "unit_cost_embedded_import": (round(dom_unit_imported, 6)
                                            if dom_unit_imported is not None else None),
            "unit_cost_import_landed": round(imp_unit, 6),
        }

    br.total_cost_usd = grand_total
    br.imported_cost_usd = grand_imported
    br.fraction = 1.0 - (grand_imported / grand_total) if grand_total > 0 else 0.0
    if grand_shortfall_qty > 0:
        br.shortfall_note = (
            "DVA measured on DELIVERED units only; unmet demand excluded from "
            "numerator and denominator (reported separately)"
        )
    br.assumptions_used = sorted(set(assumptions))

    pg.derive(
        [],
        f"DVA = {br.fraction:.1%} of delivered ex-works value",
        {
            "total_cost_usd": grand_total,
            "imported_cost_usd": grand_imported,
            "convention": br.convention,
            "assumptions": br.assumptions_used,
            "shortfall_excluded": True,
        },
    )
    return br


def measure_dva(
    w: World,
    pg: ProofGraph,
    explosion: ExplosionResult,
    opts: ScenarioOptions,
    allocations_by_year: Optional[Dict[int, list]] = None,
    decision_year: Optional[int] = None,
) -> DVABreakdown:
    """Measure DVA without emitting a proof node (used inside the certified loop)."""
    saved = ProofGraph.derive

    def _silent(self, *a, **k):
        return ""

    ProofGraph.derive = _silent  # type: ignore[method-assign]
    try:
        return dva_fraction(w, pg, explosion, opts,
                            allocations_by_year=allocations_by_year,
                            decision_year=decision_year)
    finally:
        ProofGraph.derive = saved  # type: ignore[method-assign]
