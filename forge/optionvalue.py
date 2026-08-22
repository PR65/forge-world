from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .epistemics import ResultClass
from .solve import ScenarioOptions, SolveResult


@dataclass
class CapabilityInvestment:
    capability_id: str
    label: str
    capex_musd: float
    lead_time_years: Tuple[float, float]
    objectives_unlocked: List[str] = field(default_factory=list)
    option_score: float = 0.0
    explanation: str = ""

    def to_json(self) -> Dict:
        return dict(
            capability_id=self.capability_id,
            label=self.label,
            capex_musd=self.capex_musd,
            lead_time_years=list(self.lead_time_years),
            objectives_unlocked=self.objectives_unlocked,
            option_score=round(self.option_score, 4),
            explanation=self.explanation,
        )


@dataclass
class ObjectiveSpec:
    objective_id: str
    weight: float
    evaluate: Callable[[ScenarioOptions, Sequence[str]], SolveResult]
    shortfall_of: Optional[Callable[[SolveResult], float]] = None


def _shortfall(sr: SolveResult) -> float:
    wy = sr.worst_year()
    if wy is None or not sr.years:
        return 0.0
    return sr.years[wy].total_shortfall


def option_value_portfolio(
    investments: Sequence[CapabilityInvestment],
    objectives: Sequence[ObjectiveSpec],
    base_opts: ScenarioOptions,
    budget_count: int = 5,
) -> List[CapabilityInvestment]:
    """Score enabling capabilities by the feasible production space they unlock.

    For each candidate investment and each strategic objective we measure the
    normalized reduction in infeasibility it produces. The score is the
    weight-summed coverage across objectives minus a mild cost/time penalty.
    Explanations are derived from measured deltas, not asserted.
    """
    results: List[CapabilityInvestment] = []
    for inv in investments:
        total_gain = 0.0
        unlocked: List[str] = []
        details: List[str] = []
        for obj in objectives:
            sr_base = obj.evaluate(base_opts, [])
            base_short = (
                obj.shortfall_of(sr_base) if obj.shortfall_of else _shortfall(sr_base)
            )
            opts = ScenarioOptions(
                funded_project_ids=set(base_opts.funded_project_ids) | {inv.capability_id},
                geography=base_opts.geography,
                assume_capacity_hi=base_opts.assume_capacity_hi,
            )
            sr_with = obj.evaluate(opts, [])
            with_short = (
                obj.shortfall_of(sr_with) if obj.shortfall_of else _shortfall(sr_with)
            )
            denom = max(base_short, 1e-9)
            gain = max((base_short - with_short) / denom, 0.0) if base_short > 0 else (
                1.0 if sr_base.result_class == ResultClass.INFEASIBLE_UNDER_MODEL else 0.0
            )
            weighted = gain * obj.weight
            total_gain += weighted
            if gain > 0.05:
                unlocked.append(obj.objective_id)
                details.append(
                    f"{obj.objective_id}: shortfall {base_short:,.0f} -> {with_short:,.0f}"
                )
        time_pen = 0.02 * (inv.lead_time_years[0])
        score = total_gain - time_pen
        inv.option_score = score
        inv.objectives_unlocked = unlocked
        inv.explanation = (
            f"unlocks {len(unlocked)} of {len(list(objectives))} strategic objectives; "
            + ("; ".join(details[:3]) if details else "no measurable feasibility delta")
        )
        results.append(inv)

    results.sort(key=lambda i: -i.option_score)
    return results[:budget_count]


def reverse_buildability(
    annual_units_candidates: Sequence[int],
    evaluate_at_volume: Callable[[int], SolveResult],
) -> Tuple[int, str]:
    """Dual problem: maximum achievable output under current constraints (C-reverse).

    Binary search over candidate volumes using the real pipeline.
    """
    best_feasible = 0
    best_class = ""
    lo, hi = 0, max(annual_units_candidates)

    def ok(v: int) -> bool:
        sr = evaluate_at_volume(v)
        return sr.result_class in (ResultClass.FEASIBLE, ResultClass.CONDITIONALLY_FEASIBLE)

    sorted_candidates = sorted(annual_units_candidates)
    for v in sorted_candidates:
        sr = evaluate_at_volume(v)
        best_class = sr.result_class.value
        if sr.result_class in (ResultClass.FEASIBLE, ResultClass.CONDITIONALLY_FEASIBLE):
            best_feasible = v
        else:
            break

    return best_feasible, best_class
