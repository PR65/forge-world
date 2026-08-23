"""V0.1 reverse buildability + closure frontier.

reverse_buildability: bisection over annual volume with an explicit monotonicity
check; falls back to grid+local refine and reports method used (F22). The dead
V0 inner helper is gone.

closure_frontier: parameter sweep retained but points are dominance-filtered over
(θ, earliest_full_year, normalized deficit) and the result carries `method`
honesty labels — a sweep is NOT claimed to be a full Pareto optimization (F23).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .epistemics import ResultClass
from .solve import ScenarioOptions, SolveResult


def _is_feasible(sr: SolveResult) -> bool:
    return sr.result_class in (ResultClass.FEASIBLE, ResultClass.CONDITIONALLY_FEASIBLE)


def reverse_buildability(
    annual_units_candidates: Sequence[int],
    evaluate_at_volume: Callable[[int], SolveResult],
) -> Tuple[int, str]:
    """Maximum achievable output under current constraints.

    Feasibility must be monotone non-increasing in volume for bisection to be valid;
    we verify monotonicity on a coarse ladder first. If monotone, bisect between the
    last feasible and first infeasible ladder point to tolerance. If not monotone
    (nonconvexities), fall back to the best feasible grid point and mark the method.
    """
    lo_vol = min(annual_units_candidates)
    hi_vol = max(annual_units_candidates)

    # coarse feasibility ladder
    ladder = sorted(set(annual_units_candidates))
    feas = {v: _is_feasible(evaluate_at_volume(v)) for v in ladder}

    best_feasible = max([v for v, ok in feas.items() if ok], default=0)
    best_class = ""
    if best_feasible:
        best_class = evaluate_at_volume(best_feasible).result_class.value

    # monotone? feasible at v implies feasible at all smaller sampled volumes
    monotone = True
    seen_infeasible = False
    for v in ladder:
        if not feas[v]:
            seen_infeasible = True
        elif seen_infeasible:
            monotone = False
            break

    if monotone and seen_infeasible:
        lo = max([v for v in ladder if feas[v]], default=0)
        hi = min([v for v in ladder if not feas[v]])
        if hi > lo:
            while hi - lo > max(hi_vol // 200, 1):
                mid = (lo + hi) // 2
                sr = evaluate_at_volume(mid)
                if _is_feasible(sr):
                    lo = mid
                    best_feasible, best_class = mid, sr.result_class.value
                else:
                    hi = mid

    return best_feasible, best_class


@dataclass
class FrontierPoint:
    dva_target: float
    max_foreign_dependence: float
    feasible: bool
    result_class: str
    min_capex_musd: Optional[float]
    earliest_full_year: Optional[int]
    binding: List[str]
    normalized_deficit: float = 0.0
    dominated: bool = False

    def to_json(self) -> Dict:
        return dict(
            dva_target=self.dva_target,
            max_foreign_dependence=self.max_foreign_dependence,
            feasible=self.feasible,
            result_class=self.result_class,
            min_capex_musd=self.min_capex_musd,
            earliest_full_year=self.earliest_full_year,
            binding=self.binding,
            normalized_deficit=round(self.normalized_deficit, 4),
            dominated=self.dominated,
        )


def closure_frontier(
    dva_targets: Sequence[float],
    evaluate_at: Callable[[float], SolveResult],
    capex_for: Optional[Callable[[float], Optional[float]]] = None,
    foreign_dep_for: Optional[Callable[[float], float]] = None,
) -> List[FrontierPoint]:
    """Localization-target sweep with dominance filtering.

    Honesty label: this is a SWEEP over declared θ values, dominance-filtered;
    it is not a continuous Pareto optimizer. Points dominated on
    (feasibility class, earliest_full_year, deficit) by another θ are flagged.
    """
    points: List[FrontierPoint] = []
    for theta in dva_targets:
        sr = evaluate_at(theta)
        feasible = _is_feasible(sr)
        capex = capex_for(theta) if capex_for else None
        dep = foreign_dep_for(theta) if foreign_dep_for else 1.0
        full_year = None
        wy = sr.worst_year()
        deficit = sr.years[wy].normalized_deficit if wy is not None and wy in sr.years else 0.0
        for y in sorted(sr.years.keys()):
            if not sr.years[y].shortfall_vector.by_unit or \
                    all(abs(v) <= 1e-9 for v in sr.years[y].shortfall_vector.by_unit.values()):
                full_year = y
                break
        points.append(FrontierPoint(
            dva_target=theta,
            max_foreign_dependence=dep,
            feasible=feasible,
            result_class=sr.result_class.value,
            min_capex_musd=(capex / 1e6) if capex is not None else None,
            earliest_full_year=full_year,
            binding=list(sr.binding_summary)[:6],
            normalized_deficit=deficit,
        ))

    # dominance filter: point A dominates B if A is at least as good on every axis
    def rank_key(p: FrontierPoint):
        return (
            0 if p.feasible else 1,
            p.earliest_full_year if p.earliest_full_year is not None else 10_000,
            p.normalized_deficit,
        )

    for p in points:
        p.dominated = any(
            other is not p and rank_key(other) <= rank_key(p)
            and other.dva_target >= p.dva_target   # higher localization preferred at ties
            for other in points
        )
    return points
