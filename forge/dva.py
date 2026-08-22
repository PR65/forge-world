from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

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
    per_item: Dict[str, Dict] = field(default_factory=dict)
    assumptions_used: List[str] = field(default_factory=list)


def _domestic_input_import_share(
    w: World,
    rec: ProductionRecipe,
    opts: ScenarioOptions,
    depth: int,
    seen: Tuple[str, ...],
) -> Tuple[float, float]:
    """(input_cost_total, input_cost_imported) per one unit of recipe output.

    Recursion follows domestic recipes only; inputs without a domestic route count as
    fully imported at landed cost (C18). Depth-capped; cycles guarded.
    """
    if depth > 6 or rec.id in seen:
        return (0.0, 0.0)
    total = 0.0
    imported = 0.0
    scale = 1.0 / (rec.output_quantity.value or 1.0)
    for iname, iq in rec.inputs:
        need = iq.value * scale
        sub_rec = primary_recipe(w, iname)
        domestic_route = (
            sub_rec is not None and "INDIA" in sub_rec.applicable_geographies
        )
        if domestic_route and sub_rec is not None:
            t_sub, i_sub = _domestic_input_import_share(
                w, sub_rec, opts, depth + 1, seen + (rec.id,)
            )
            proc = opts.cost_domestic.get(f"processing:{iname}", 0.35 * max(t_sub, 0.5))
            item_total = t_sub + proc
            item_imported = i_sub
        else:
            unit_cost = opts.cost_import.get(iname, opts.cost_domestic.get(iname, 1.0))
            item_total = need * unit_cost
            item_imported = item_total
        total += item_total
        imported += item_imported
    return (total, imported)


def dva_fraction(
    w: World,
    pg: ProofGraph,
    explosion: ExplosionResult,
    opts: ScenarioOptions,
    allocations_by_year: Optional[Dict[int, list]] = None,
    decision_year: Optional[int] = None,
) -> DVABreakdown:
    """Recursive domestic-value-addition accounting (MODEL_CONTRACT C18).

    DVA of delivered output = 1 - imported_cost / total_cost, where domestically
    produced items carry their recursive embedded-import content and imported items
    count fully as imported at landed cost. Uses the solver's actual allocation for
    the decision year (or the worst year).
    """
    br = DVABreakdown(fraction=0.0, total_cost_usd=0.0, imported_cost_usd=0.0)
    alloc_map: Dict[str, Tuple[float, float]] = {}
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

    grand_total = 0.0
    grand_imported = 0.0

    for item in explosion.items():
        line = explosion.get(item)
        qty = line.net_annual.value if line else 0.0
        dom_share, imp_share = alloc_map.get(item, (0.0, 1.0))
        shortfall_share = max(0.0, 1.0 - dom_share - imp_share)

        rec = primary_recipe(w, item)
        domestic_route = rec is not None and "INDIA" in rec.applicable_geographies

        if domestic_route and rec is not None:
            t_in, i_in = _domestic_input_import_share(w, rec, opts, 0, ())
            proc_cost = opts.cost_domestic.get(
                f"processing:{item}", 0.35 * max(t_in, 0.5)
            )
            if f"processing:{item}" not in opts.cost_domestic:
                br.assumptions_used.append(
                    f"processing cost for {item} assumed at 35% of input cost"
                )
            dom_unit_total = t_in + proc_cost
            dom_unit_imported = i_in
        else:
            dom_unit_total = None
            dom_unit_imported = None

        imp_unit = opts.cost_import.get(item, opts.cost_domestic.get(item, 1.0))
        if opts.cost_import.get(item) is None and opts.cost_domestic.get(item) is None and not domestic_route:
            br.assumptions_used.append(
                f"unit cost for {item} defaulted to 1.0 USD (ASSUMPTION)"
            )

        item_total = 0.0
        item_imported = 0.0
        if dom_unit_total is not None:
            item_total += dom_share * qty * dom_unit_total
            item_imported += dom_share * qty * dom_unit_imported
        item_total += imp_share * qty * imp_unit
        item_imported += imp_share * qty * imp_unit

        grand_total += item_total
        grand_imported += item_imported
        br.per_item[item] = {
            "qty": qty,
            "domestic_share_solved": round(dom_share, 4),
            "import_share_solved": round(imp_share, 4),
            "shortfall_share": round(shortfall_share, 4),
        }

    br.total_cost_usd = grand_total
    br.imported_cost_usd = grand_imported
    br.fraction = 1.0 - (grand_imported / grand_total) if grand_total > 0 else 0.0

    pg.derive(
        [],
        f"DVA = {br.fraction:.1%} of ex-works value",
        {
            "total_cost_usd": grand_total,
            "imported_cost_usd": grand_imported,
            "convention": "C18 recursive; imports at landed cost; embedded imports count",
            "assumptions": sorted(set(br.assumptions_used)),
        },
    )
    return br
