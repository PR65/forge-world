from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .epistemics import ResultClass
from .solve import ScenarioOptions, SolveResult


@dataclass
class FrontierPoint:
    dva_target: float
    max_foreign_dependence: float
    feasible: bool
    result_class: str
    min_capex_musd: Optional[float]
    earliest_full_year: Optional[int]
    binding: List[str]

    def to_json(self) -> Dict:
        return dict(
            dva_target=self.dva_target,
            max_foreign_dependence=self.max_foreign_dependence,
            feasible=self.feasible,
            result_class=self.result_class,
            min_capex_musd=self.min_capex_musd,
            earliest_full_year=self.earliest_full_year,
            binding=self.binding,
        )


def closure_frontier(
    dva_targets: Sequence[float],
    evaluate_at: Callable[[float], SolveResult],
    capex_for: Optional[Callable[[float], Optional[float]]] = None,
    foreign_dep_for: Optional[Callable[[float], float]] = None,
) -> List[FrontierPoint]:
    """Industrial closure frontier: sweep localization targets, record cost/time tradeoffs.

    `evaluate_at(theta)` must run the full pipeline under DVA >= theta and return a
    SolveResult; `capex_for`/`foreign_dep_for` extract portfolio cost and dependence.
    """
    points: List[FrontierPoint] = []
    for theta in dva_targets:
        sr = evaluate_at(theta)
        feasible = sr.result_class in (
            ResultClass.FEASIBLE,
            ResultClass.CONDITIONALLY_FEASIBLE,
        )
        capex = capex_for(theta) if capex_for else None
        dep = foreign_dep_for(theta) if foreign_dep_for else 1.0
        full_year = None
        for y in sorted(sr.years.keys()):
            if sr.years[y].total_shortfall <= 0:
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
        ))
    return points
