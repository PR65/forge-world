"""Durable public contracts for the India industrial-objective compiler.

These contracts are deliberately representation-neutral.  The India atlas may
describe broad industrial structure, while the quantitative core requires
dimensioned coefficients and evidenced capacity.  Optional fields therefore
stay optional: an absent coefficient or capacity is never converted to one or
zero merely to make a compilation complete.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence


OBJECTIVE_COMPILER_SCHEMA_VERSION = "forge-industrial-objective-compilation-v0"


class ArchitectureNodeKind(str, Enum):
    PRODUCT_SYSTEM = "PRODUCT_SYSTEM"
    PRODUCT_COMPONENT = "PRODUCT_COMPONENT"
    MANUFACTURING_PROCESS = "MANUFACTURING_PROCESS"
    MANUFACTURING_EQUIPMENT = "MANUFACTURING_EQUIPMENT"
    MANUFACTURING_CAPABILITY = "MANUFACTURING_CAPABILITY"
    MATERIAL = "MATERIAL"
    METROLOGY = "METROLOGY"
    QUALIFICATION = "QUALIFICATION"
    INDUSTRIAL_ENVIRONMENT = "INDUSTRIAL_ENVIRONMENT"
    EVIDENCE_ONLY = "EVIDENCE_ONLY"


class DerivationClass(str, Enum):
    EXPLICIT = "EXPLICIT"
    DERIVED = "DERIVED"
    FAMILY_LEVEL = "FAMILY_LEVEL"
    MODELLED = "MODELLED"


class CoefficientState(str, Enum):
    VERIFIED = "VERIFIED"
    SUPPORTED = "SUPPORTED"
    ASSUMPTION = "ASSUMPTION"
    UNKNOWN = "UNKNOWN"


class QuantityState(str, Enum):
    DERIVED = "DERIVED"
    OBJECTIVE = "OBJECTIVE"
    UNKNOWN = "QUANTITY_UNKNOWN"


class DependencyState(str, Enum):
    DOMESTIC = "DOMESTIC"
    PARTIAL = "PARTIAL"
    IMPORT_DEPENDENT = "IMPORT_DEPENDENT"
    CONSTRAINED = "CONSTRAINED"
    MISSING = "MISSING"
    UNKNOWN = "UNKNOWN"


class ClosureActionCategory(str, Enum):
    MAKE = "MAKE"
    SOURCE = "SOURCE"
    LOCALIZE = "LOCALIZE"
    JV = "JV"
    DEVELOP = "DEVELOP"
    VERIFY = "VERIFY"
    INTEGRATE = "INTEGRATE"


def _json(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {str(key): _json(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (list, tuple)):
        return [_json(item) for item in value]
    return value


@dataclass(frozen=True)
class QuantitativeCoefficient:
    """Destination quantity needed per one source output unit."""

    value: float | None
    unit: str
    state: CoefficientState
    source_record_ids: tuple[str, ...] = ()
    note: str = ""

    def __post_init__(self) -> None:
        if self.state is CoefficientState.UNKNOWN and self.value is not None:
            raise ValueError("UNKNOWN coefficient must not carry a numeric value")
        if self.state is not CoefficientState.UNKNOWN and self.value is None:
            raise ValueError("quantified coefficient requires a numeric value")
        if self.value is not None and self.value < 0:
            raise ValueError("coefficient must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return _json(asdict(self))


@dataclass(frozen=True)
class ArchitectureNode:
    id: str
    label: str
    kind: ArchitectureNodeKind
    source_record_ids: tuple[str, ...]
    derivation_class: DerivationClass
    status: str = "UNKNOWN"
    epistemic_class: str = "UNKNOWN"
    family_key: str = ""
    description: str = ""
    depth: int = 0

    def to_dict(self) -> dict[str, Any]:
        return _json(asdict(self))


@dataclass(frozen=True)
class ArchitectureEdge:
    source_id: str
    destination_id: str
    relation: str
    source_record_ids: tuple[str, ...]
    derivation_class: DerivationClass
    coefficient: QuantitativeCoefficient | None = None

    def to_dict(self) -> dict[str, Any]:
        return _json(asdict(self))


@dataclass(frozen=True)
class ProductArchitecture:
    product_record_id: str
    product_name: str
    family_key: str
    nodes: tuple[ArchitectureNode, ...]
    edges: tuple[ArchitectureEdge, ...]
    coverage_class: str
    requires_confirmation: bool = False
    diagnostics: tuple[str, ...] = ()

    def node(self, node_id: str) -> ArchitectureNode | None:
        return next((node for node in self.nodes if node.id == node_id), None)

    def to_dict(self) -> dict[str, Any]:
        return _json(asdict(self))


@dataclass(frozen=True)
class ObjectiveConstraint:
    kind: str
    value: str | float

    def to_dict(self) -> dict[str, Any]:
        return _json(asdict(self))


@dataclass(frozen=True)
class IndustrialObjective:
    objective_type: str
    product: str
    quantity: float
    output_unit: str
    period: str
    geography: str
    target_year: int
    constraints: tuple[ObjectiveConstraint, ...] = ()
    confirm_family: bool = False

    def __post_init__(self) -> None:
        if self.objective_type != "manufacture":
            raise ValueError("V0 supports only the bounded 'manufacture' objective")
        if not self.product.strip() or len(self.product) > 240:
            raise ValueError("product must contain 1-240 characters")
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.period not in {"year", "month", "week", "day"}:
            raise ValueError("period must be year, month, week, or day")
        if not 2026 <= self.target_year <= 2200:
            raise ValueError("target_year must be in [2026, 2200]")
        if len(self.constraints) > 12:
            raise ValueError("at most 12 bounded constraints are supported")

    @property
    def annual_quantity(self) -> float:
        factor = {"year": 1.0, "month": 12.0, "week": 52.0, "day": 365.0}[self.period]
        return self.quantity * factor

    def to_dict(self) -> dict[str, Any]:
        data = _json(asdict(self))
        data["annual_quantity"] = self.annual_quantity
        return data


@dataclass(frozen=True)
class IndustrialObjectiveCompilation:
    resolved_objective: Mapping[str, Any]
    architecture: ProductArchitecture
    demand_ledger: Sequence[Mapping[str, Any]]
    capability_ledger: Sequence[Mapping[str, Any]]
    capacity_ledger: Sequence[Mapping[str, Any]]
    dependency_ledger: Sequence[Mapping[str, Any]]
    gap_ledger: Sequence[Mapping[str, Any]]
    bottlenecks: Sequence[Mapping[str, Any]]
    closure_actions: Sequence[Mapping[str, Any]]
    staged_plan: Sequence[Mapping[str, Any]]
    verification_frontier: Sequence[Mapping[str, Any]]
    evidence_references: Sequence[Mapping[str, Any]]
    compiler_diagnostics: Sequence[str]
    result_class: str = "NOT_ADJUDICABLE"
    schema_version: str = OBJECTIVE_COMPILER_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _json(asdict(self))


__all__ = [
    "OBJECTIVE_COMPILER_SCHEMA_VERSION",
    "ArchitectureNodeKind",
    "DerivationClass",
    "CoefficientState",
    "QuantityState",
    "DependencyState",
    "ClosureActionCategory",
    "QuantitativeCoefficient",
    "ArchitectureNode",
    "ArchitectureEdge",
    "ProductArchitecture",
    "ObjectiveConstraint",
    "IndustrialObjective",
    "IndustrialObjectiveCompilation",
]
