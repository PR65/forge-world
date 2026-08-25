"""Cross-objective option-value reporting (V0).

Measures, through real re-solves, how much each evidenced investment relieves total
modeled infeasibility across the loaded domain objectives. Explanations are derived
from measured deltas — never asserted.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from forge.engine import ForgeEngine, ObjectiveSpecInput
from forge.epistemics import ResultClass
from forge.model import Project
from forge.pack import KnowledgePack


@dataclass
class OptionRow:
    investment_id: str
    label: str
    kind: str
    capex_musd: float | None
    lead_years: Tuple[float, float]
    per_objective: Dict[str, float] = field(default_factory=dict)
    total_relief: float = 0.0
    explanation: str = ""

    def to_json(self) -> dict:
        return dict(
            investment_id=self.investment_id,
            label=self.label,
            kind=self.kind,
            capex_musd=self.capex_musd,
            lead_years=list(self.lead_years),
            per_objective={k: round(v, 4) for k, v in self.per_objective.items()},
            total_relief=round(self.total_relief, 4),
            explanation=self.explanation,
        )


def _normalized_infeasibility(sr) -> float:
    """Map a SolveResult to [0,1]-ish infeasibility score for aggregation."""
    if sr.result_class == ResultClass.FEASIBLE:
        return 0.0
    if sr.result_class == ResultClass.NOT_ADJUDICABLE:
        return 1.5
    wy = sr.worst_year()
    demand_total = sum(g.demand for g in sr.years[wy].allocations) if wy is not None else 1.0
    short = sr.years[wy].total_shortfall if wy is not None else 0.0
    frac = min(short / max(demand_total, 1.0), 2.0)
    base = 0.25 if sr.result_class == ResultClass.CONDITIONALLY_FEASIBLE and short <= 0 else 0.0
    return frac + base


def option_value_report(
    packs: List[Tuple[str, KnowledgePack]],
    units_by_pack: Dict[str, float],
    dva_by_pack: Dict[str, float],
) -> List[dict]:
    # Foundational world packs intentionally have no product objective.  They
    # enrich the canonical substrate but must not be coerced into an arbitrary
    # solver benchmark merely because the registry loads them.
    objective_packs = [(pid, pk) for pid, pk in packs if pk.variants]
    engines: Dict[str, ForgeEngine] = {}
    baselines: Dict[str, float] = {}
    objectives: Dict[str, ObjectiveSpecInput] = {}

    for pid, pk in objective_packs:
        eng = ForgeEngine(pk)
        vid = sorted(pk.variants.keys())[0]
        spec = ObjectiveSpecInput(
            variant_id=vid,
            annual_units=units_by_pack.get(pid, 100000),
            min_dva=dva_by_pack.get(pid, 0.6),
            funded_projects=["__baseline_none__"],
        )
        engines[pid] = eng
        objectives[pid] = spec
        resp = eng.run_scenario(spec, include_deep=False)
        baselines[pid] = _normalized_infeasibility_score(resp)

    rows: Dict[str, OptionRow] = {}

    for pid, pk in objective_packs:
        eng = engines[pid]
        spec = objectives[pid]
        for prj in pk.world.of_kind("project"):
            if not isinstance(prj, Project):
                continue
            key = f"{pid}:{prj.id}"
            if key in rows:
                continue
            resp = eng.run_scenario(
                ObjectiveSpecInput(
                    variant_id=spec.variant_id,
                    annual_units=spec.annual_units,
                    min_dva=spec.min_dva,
                    deadline_year=spec.deadline_year,
                    funded_projects=[prj.id],
                ),
                include_deep=False,
            )
            after = _normalized_infeasibility_score(resp)
            relief = max(baselines[pid] - after, 0.0)
            capex_musd = None
            if prj.capex is not None:
                capex_musd = (
                    prj.capex.value / 1e6
                    if prj.capex.unit == "USD"
                    else prj.capex.to("MUSD").value
                )
            rows[key] = OptionRow(
                investment_id=key,
                label=prj.name,
                kind="project",
                capex_musd=capex_musd,
                lead_years=prj.years_to_commission,
                per_objective={pid: relief},
                total_relief=relief,
                explanation=(
                    f"reduces modeled infeasibility of [{pid}] objective by "
                    f"{relief:.1%} of normalized gap"
                    if relief > 0
                    else f"no measurable relief for [{pid}] objective under current constraints"
                ),
            )

    ranked = sorted(rows.values(), key=lambda r: -r.total_relief)
    return [r.to_json() for r in ranked]


def _normalized_infeasibility_score(resp) -> float:
    if resp["result"]["result_class"] == "FEASIBLE":
        return 0.0
    if resp["result"]["result_class"] == "NOT_ADJUDICABLE":
        return 1.5
    years = resp["result"]["years"]
    worst = max(years.keys(), key=lambda y: int(y))
    yr = years[worst]
    demand_total = sum(
        float(it["gross"]) for it in resp.get("explosion", {}).get("items", [])
    )
    short = yr["total_shortfall"]
    frac = min(short / max(demand_total, 1.0), 2.0)
    cond = 0.25 if resp["result"]["result_class"] == "CONDITIONALLY_FEASIBLE" and short <= 0 else 0.0
    return frac + cond
