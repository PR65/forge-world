from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional


class EpistemicClass(str, Enum):
    MEASURED = "MEASURED"
    REPORTED = "REPORTED"
    DERIVED = "DERIVED"
    ESTIMATED = "ESTIMATED"
    MODELLED = "MODELLED"
    ASSUMPTION = "ASSUMPTION"
    SCENARIO = "SCENARIO"
    UNKNOWN = "UNKNOWN"
    CONFLICTED = "CONFLICTED"


class ResultClass(str, Enum):
    FEASIBLE = "FEASIBLE"
    CONDITIONALLY_FEASIBLE = "CONDITIONALLY_FEASIBLE"
    INFEASIBLE_UNDER_MODEL = "INFEASIBLE_UNDER_MODEL"
    INFEASIBLE_WRT_DVA = "INFEASIBLE_WRT_DVA"
    NOT_ADJUDICABLE = "NOT_ADJUDICABLE"


CONFIDENCE_DIMENSIONS = (
    "authority",
    "directness",
    "corroboration",
    "recency",
    "geographic_specificity",
    "technical_specificity",
    "completeness",
)


@dataclass(frozen=True)
class Confidence:
    values: Dict[str, Optional[float]] = field(default_factory=dict)

    def __post_init__(self):
        for k, v in self.values.items():
            if k not in CONFIDENCE_DIMENSIONS:
                raise ValueError(f"unknown confidence dimension '{k}'")
            if v is not None and not (0.0 <= v <= 1.0):
                raise ValueError(f"confidence dimension '{k}' must be in [0,1] or None")

    def get(self, dim: str) -> Optional[float]:
        return self.values.get(dim)

    def to_json(self) -> Dict:
        return dict(self.values)


def confidence(**dims) -> Confidence:
    return Confidence(dict(dims))
