from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .evidence import ProofGraph
from .model import CapacitySegment, Project, ProjectState, Shock, World
from .solve import ScenarioOptions
from .units import Quantity, annual_scalar


@dataclass
class ShockReport:
    shock_ids: List[str]
    applied_edits: List[Dict] = field(default_factory=list)
    rejected_edits: List[str] = field(default_factory=list)


def _find_segment_for_item(w: World, item_id: str) -> List[CapacitySegment]:
    return [
        e for e in w.entities.values()
        if isinstance(e, CapacitySegment) and e.item_id == item_id
    ]


def apply_shocks(
    base_world: World,
    pg: ProofGraph,
    shock_ids: List[str],
    opts: ScenarioOptions,
) -> Tuple[World, ScenarioOptions, ShockReport]:
    """Shocks edit constraints on a cloned world; nothing downstream is hand-multiplied (C10).

    Supported edit types:
      import_eligibility  {origin, fraction}
      capacity_multiplier {item, factor}
      project_impair      {project_id}          -> state becomes impaired
      project_accelerate  {project_id, years}   -> lead time shortened (policy/logistics)
      cost_multiplier     {item, factor, side: domestic|import|both}
      equipment_limit     {equipment_class, hours_per_year}
      demand_add          {item, quantity_per_year}  -> competing demand subtracts from supply
    """
    w2 = copy.deepcopy(base_world)
    o2 = opts.clone()   # FULL clone: every scenario field survives (F16/N4 fixed)
    report = ShockReport(shock_ids=list(shock_ids))

    demand_adds: Dict[str, float] = {}

    for sid in shock_ids:
        sh = w2.entities.get(sid)
        if not isinstance(sh, Shock):
            report.rejected_edits.append(f"unknown shock '{sid}'")
            continue
        for edit in sh.edits:
            et = edit.get("type")
            if et == "import_eligibility":
                o2.import_eligibility[str(edit["origin"])] = float(edit.get("fraction", 0.0))
                report.applied_edits.append(
                    {"shock": sid, "edit": "import_eligibility", "origin": edit["origin"],
                     "fraction": edit.get("fraction", 0.0)}
                )
            elif et == "capacity_multiplier":
                item = str(edit["item"])
                f = float(edit.get("factor", 1.0))
                segs = _find_segment_for_item(w2, item)
                if not segs:
                    report.rejected_edits.append(
                        f"{sid}: capacity_multiplier for '{item}' matched no segment"
                    )
                for seg in segs:
                    if seg.nameplate_annual is not None:
                        seg.nameplate_annual = seg.nameplate_annual * f
                for prj in w2.entities.values():
                    if isinstance(prj, Project) and prj.item_id == item and prj.design_capacity_annual is not None:
                        prj.design_capacity_annual = prj.design_capacity_annual * f
                report.applied_edits.append(
                    {"shock": sid, "edit": "capacity_multiplier", "item": item, "factor": f}
                )
            elif et == "project_impair":
                pid = str(edit["project_id"])
                prj = w2.entities.get(pid)
                if isinstance(prj, Project):
                    prj.state = ProjectState.IMPAIRED
                    report.applied_edits.append(
                        {"shock": sid, "edit": "project_impair", "project": pid}
                    )
                else:
                    report.rejected_edits.append(f"{sid}: unknown project '{pid}'")
            elif et == "project_accelerate":
                pid = str(edit["project_id"])
                years = float(edit.get("years", 0.5))
                prj = w2.entities.get(pid)
                if isinstance(prj, Project):
                    lo, hi = prj.years_to_commission
                    prj.years_to_commission = (max(lo - years, 0.0), max(hi - years, 0.0))
                    report.applied_edits.append(
                        {"shock": sid, "edit": "project_accelerate", "project": pid,
                         "years": years}
                    )
                else:
                    report.rejected_edits.append(f"{sid}: unknown project '{pid}'")
            elif et == "cost_multiplier":
                item = str(edit.get("item", "*"))
                f = float(edit.get("factor", 1.0))
                side = str(edit.get("side", "both"))
                if item == "*":
                    if side in ("import", "both"):
                        o2.global_import_cost_mult *= f
                    if side in ("domestic", "both"):
                        o2.global_domestic_cost_mult *= f
                else:
                    if side in ("import", "both"):
                        o2.cost_import[item] = o2.cost_import.get(item, 1.0) * f
                    if side in ("domestic", "both"):
                        o2.cost_domestic[item] = o2.cost_domestic.get(item, 1.0) * f
                report.applied_edits.append(
                    {"shock": sid, "edit": "cost_multiplier", "item": item, "factor": f,
                     "side": side}
                )
            elif et == "equipment_limit":
                ec = str(edit["equipment_class"])
                h = float(edit.get("hours_per_year", 0.0))
                o2.equipment_hour_limits[ec] = h
                report.applied_edits.append(
                    {"shock": sid, "edit": "equipment_limit", "equipment_class": ec,
                     "hours_per_year": h}
                )
            elif et == "demand_add":
                item = str(edit["item"])
                qty = edit.get("quantity_per_year")
                q = Quantity(float(qty[0]), str(qty[1])) if isinstance(qty, (list, tuple)) else None
                if q is None:
                    report.rejected_edits.append(f"{sid}: demand_add missing quantity")
                else:
                    demand_adds[item] = demand_adds.get(item, 0.0) + annual_scalar(q)
                    report.applied_edits.append(
                        {"shock": sid, "edit": "demand_add", "item": item,
                         "quantity_per_year": str(q)}
                    )
            else:
                report.rejected_edits.append(f"{sid}: unsupported edit type '{et}'")

    # demand_add MERGES onto pre-existing cuts (I3); never replaces them (F16).
    for item, add in demand_adds.items():
        o2.competing_demand_cuts[item] = o2.competing_demand_cuts.get(item, 0.0) + add

    pg.derive(
        [],
        f"Shocks applied: {', '.join(shock_ids) if shock_ids else 'none'}",
        {"applied": report.applied_edits, "rejected": report.rejected_edits},
    )
    return w2, o2, report
