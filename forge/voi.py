"""V0.1 VOI: ResultClass flips are the only HIGH trigger; magnitude is separate.

V0 defects corrected: (F14) any shortfall swing flipped the rank tuple and got
labeled "flips conclusion" even when both classes were identical; (F15) the engine's
counterfactual evaluator dropped active scenario fields. The evaluator contract is
now "clone the full ScenarioOptions, apply only the override" — see
engine.eval_with which uses ScenarioOptions.clone().
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .epistemics import ResultClass
from .solve import ScenarioOptions, SolveResult


@dataclass
class ResearchTask:
    unknown_id: str
    description: str
    decision_impact: str  # HIGH | MEDIUM | LOW
    flip_behavior: str    # class-flip description OR magnitude description
    shortfall_swing: float = 0.0
    class_pessimistic: str = ""
    class_optimistic: str = ""
    next_evidence: List[str] = field(default_factory=list)

    def to_json(self) -> Dict:
        return dict(
            unknown_id=self.unknown_id,
            description=self.description,
            decision_impact=self.decision_impact,
            flip_behavior=self.flip_behavior,
            shortfall_swing=round(self.shortfall_swing, 3),
            class_pessimistic=self.class_pessimistic,
            class_optimistic=self.class_optimistic,
            next_evidence=self.next_evidence,
        )


_CLASS_ORDER = {
    ResultClass.NOT_ADJUDICABLE: 0,
    ResultClass.INFEASIBLE_UNDER_MODEL: 1,
    ResultClass.INFEASIBLE_WRT_DVA: 1,
    ResultClass.CONDITIONALLY_FEASIBLE: 2,
    ResultClass.FEASIBLE: 3,
}


def _worst_shortfall(sr: SolveResult) -> float:
    """Normalized service deficit of the worst year — dimensionless ranking basis."""
    wy = sr.worst_year()
    if wy is None or wy not in sr.years:
        return 0.0
    return sr.years[wy].normalized_deficit


def value_of_information(
    unknown_items: Sequence[str],
    evaluate: Callable[[Dict[str, Tuple[float, float]]], SolveResult],
    default_bounds: Tuple[float, float] = (0.0, 1e9),
    bounds_by_item: Optional[Dict[str, Tuple[float, float]]] = None,
) -> List[ResearchTask]:
    """Feasibility-flip detection over declared UNKNOWNs.

    For each unknown, re-solve under pessimistic and optimistic capacity assumptions
    while holding other unknowns at their base state AND preserving the full active
    scenario (the caller's evaluate() must clone its base options).

    Semantics (V0.1):
      HIGH   = pessimistic and optimistic land in DIFFERENT ResultClasses.
      MEDIUM = same class but normalized deficit swings materially (>25% absolute).
      LOW    = little effect within plausible bounds.
    """
    bounds_by_item = bounds_by_item or {}
    base = evaluate({})
    base_short = _worst_shortfall(base)
    tasks: List[ResearchTask] = []

    for item in unknown_items:
        lo_b, hi_b = bounds_by_item.get(item, default_bounds)
        pessimistic = evaluate({item: (lo_b, lo_b)})
        optimistic = evaluate({item: (hi_b, hi_b)})

        r_p = pessimistic.result_class
        r_o = optimistic.result_class
        short_p = _worst_shortfall(pessimistic)
        short_o = _worst_shortfall(optimistic)
        swing = abs(short_o - short_p)

        if r_p != r_o:
            impact = "HIGH"
            behavior = (
                f"flips conclusion: {r_p.value} at pessimistic bound vs "
                f"{r_o.value} at optimistic bound"
            )
        elif swing > max(base_short * 0.25, 0.05):
            impact = "MEDIUM"
            behavior = (
                f"no class flip; normalized deficit swings "
                f"{short_p:.2f} -> {short_o:.2f} between bounds"
            )
        else:
            impact = "LOW"
            behavior = "little effect on conclusion within plausible bounds"

        tasks.append(ResearchTask(
            unknown_id=item,
            description=f"Qualified domestic capacity of {item} is UNKNOWN",
            decision_impact=impact,
            flip_behavior=behavior,
            shortfall_swing=swing,
            class_pessimistic=r_p.value,
            class_optimistic=r_o.value,
            next_evidence=[
                "supplier audit: machine fleet, cycle times, yields",
                "customer qualification status and annual qualified output",
                "backlog/allocation and lead-time quotations",
            ],
        ))

    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    tasks.sort(key=lambda t: (order[t.decision_impact], -t.shortfall_swing))
    return tasks
