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
    flip_behavior: str
    next_evidence: List[str] = field(default_factory=list)

    def to_json(self) -> Dict:
        return dict(
            unknown_id=self.unknown_id,
            description=self.description,
            decision_impact=self.decision_impact,
            flip_behavior=self.flip_behavior,
            next_evidence=self.next_evidence,
        )


def value_of_information(
    unknown_items: Sequence[str],
    evaluate: Callable[[Dict[str, Tuple[float, float]]], SolveResult],
    default_bounds: Tuple[float, float] = (0.0, 1e9),
    bounds_by_item: Optional[Dict[str, Tuple[float, float]]] = None,
) -> List[ResearchTask]:
    """Feasibility-flip detection over declared UNKNOWNs.

    For each unknown, re-solve under pessimistic and optimistic capacity assumptions
    while holding other unknowns at their base state. A flip between result classes
    (or a large shortfall swing) marks decision-critical evidence.
    """
    bounds_by_item = bounds_by_item or {}
    base = evaluate({})
    base_short = base.years[base.worst_year()].total_shortfall if base.worst_year() is not None and base.years else 0.0
    tasks: List[ResearchTask] = []

    for item in unknown_items:
        lo_b, hi_b = bounds_by_item.get(item, default_bounds)
        pessimistic = evaluate({item: (lo_b, lo_b)})
        optimistic = evaluate({item: (hi_b, hi_b)})

        def rank(r: SolveResult) -> Tuple[int, float]:
            order = {
                ResultClass.NOT_ADJUDICABLE: 0,
                ResultClass.INFEASIBLE_UNDER_MODEL: 1,
                ResultClass.CONDITIONALLY_FEASIBLE: 2,
                ResultClass.FEASIBLE: 3,
            }
            short = r.years[r.worst_year()].total_shortfall if r.worst_year() is not None and r.years else 0.0
            return (order[r.result_class], -short)

        r_p, r_o = rank(pessimistic), rank(optimistic)
        flip = r_p != r_o
        short_p = pessimistic.years[pessimistic.worst_year()].total_shortfall if pessimistic.worst_year() is not None and pessimistic.years else 0.0
        short_o = optimistic.years[optimistic.worst_year()].total_shortfall if optimistic.worst_year() is not None and optimistic.years else 0.0
        swing = abs(short_p - short_o)
        base_rank = rank(base)

        if flip:
            impact = "HIGH"
            behavior = (
                f"flips conclusion: pessimistic={pessimistic.result_class.value}, "
                f"optimistic={optimistic.result_class.value}"
            )
        elif swing > max(base_short * 0.25, 1.0):
            impact = "MEDIUM"
            behavior = f"shortfall swings {swing:,.0f} units/yr between bounds"
        else:
            impact = "LOW"
            behavior = "little effect on conclusion within plausible bounds"

        tasks.append(ResearchTask(
            unknown_id=item,
            description=f"Qualified domestic capacity of {item} is UNKNOWN",
            decision_impact=impact,
            flip_behavior=behavior,
            next_evidence=[
                "supplier audit: machine fleet, cycle times, yields",
                "customer qualification status and annual qualified output",
                "backlog/allocation and lead-time quotations",
            ],
        ))

    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    tasks.sort(key=lambda t: order[t.decision_impact])
    return tasks
