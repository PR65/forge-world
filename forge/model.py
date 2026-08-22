from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .units import Quantity


class ProjectState(str, Enum):
    CONCEPT = "concept"
    ANNOUNCED = "announced"
    ENGINEERING = "engineering"
    PERMITTING = "permitting"
    APPROVED = "approved"
    FINANCED = "financed"
    PROCUREMENT = "procurement"
    CONSTRUCTION = "construction"
    MECHANICAL_COMPLETION = "mechanical_completion"
    COMMISSIONING = "commissioning"
    PROCESS_QUALIFICATION = "process_qualification"
    CUSTOMER_QUALIFICATION = "customer_qualification"
    RAMPING = "ramping"
    MATURE = "mature"
    IMPAIRED = "impaired"
    RETIRED = "retired"


STATE_ORDER: List[ProjectState] = list(ProjectState)


class ProjectStateContribution(str, Enum):
    ZERO = "zero"
    RAMP = "ramp"


STATE_CONTRIBUTION: Dict[ProjectState, ProjectStateContribution] = {
    s: ProjectStateContribution.ZERO for s in ProjectState
}
for s in (ProjectState.RAMPING, ProjectState.MATURE):
    STATE_CONTRIBUTION[s] = ProjectStateContribution.RAMP
STATE_CONTRIBUTION[ProjectState.IMPAIRED] = ProjectStateContribution.ZERO


CAPABILITY_DIMENSIONS = (
    "technical_demonstration",
    "manufacturing_maturity",
    "qualified_effective_capacity",
    "yield_process_control",
    "scaleup_maturity",
    "design_ownership",
    "process_ownership",
    "tooling_autonomy",
    "capital_equipment_dependence",
    "precursor_dependence",
    "qualification_state",
    "metrology_test",
    "workforce_knowhow",
    "lead_time_to_additional_output",
    "cost_position",
    "geographic_redundancy",
    "supplier_concentration",
    "export_control_exposure",
)

OWNERSHIP_LEVELS = ("external", "licensed", "joint", "domestic")
MATURITY_LEVELS = ("none", "study", "rd", "prototype", "pilot", "low_rate", "series", "high_volume")


@dataclass
class CapabilityVector:
    dims: Dict[str, object] = field(default_factory=dict)

    def __post_init__(self):
        for k in self.dims:
            if k not in CAPABILITY_DIMENSIONS:
                raise ValueError(f"unknown capability dimension '{k}'")

    def get(self, key: str, default=None):
        return self.dims.get(key, default)

    def label(self) -> str:
        mm = self.get("manufacturing_maturity", "none")
        do = self.get("design_ownership", "external")
        cap = self.get("qualified_effective_capacity", None)
        if mm in ("none", "study"):
            return "No capability" if mm == "none" else "Emerging"
        if mm == "rd":
            return "R&D stage"
        if mm == "prototype":
            return "Demonstrated (prototype)"
        if mm in ("pilot", "low_rate"):
            return "Limited production (%s)" % ("own tech" if do == "domestic" else do)
        if mm in ("series", "high_volume"):
            if do == "licensed":
                return "Producing (licensed)"
            if do == "domestic":
                return "Producing (own tech)" + (" @scale" if mm == "high_volume" else "")
        return f"Maturity={mm}"

    def to_json(self) -> Dict:
        return dict(self.dims)


@dataclass
class Entity:
    id: str
    name: str
    kind: str
    notes: str = ""
    evidence_ids: Tuple[str, ...] = ()
    tags: Tuple[str, ...] = ()

    def to_json(self) -> Dict:
        return dict(id=self.id, name=self.name, kind=self.kind, notes=self.notes,
                    evidence_ids=list(self.evidence_ids), tags=list(self.tags))


@dataclass
class FunctionalRequirement(Entity):
    metric: str = ""
    envelope_min: Optional[float] = None
    envelope_max: Optional[float] = None
    unit: str = ""


@dataclass
class Part(Entity):
    """Component or subassembly. kind='part', part_class in {component, subassembly}."""
    part_class: str = "component"
    mass: Optional[Quantity] = None
    spec: str = ""
    supplied_by_countries: Tuple[str, ...] = ()
    concentration_hhi: Optional[float] = None
    lead_time: Optional[Quantity] = None
    import_eligible: bool = True

    def to_json(self):
        base = super().to_json()
        base.update(part_class=self.part_class,
                    mass=(str(self.mass) if self.mass else None),
                    spec=self.spec,
                    supplied_by_countries=list(self.supplied_by_countries),
                    concentration_hhi=self.concentration_hhi)
        return base


@dataclass
class MaterialGrade(Entity):
    family: str = ""
    grade_spec: str = ""
    purity: Optional[float] = None
    form: str = ""


@dataclass
class ProcessStep(Entity):
    resource_classes: Tuple[str, ...] = ()
    equipment_classes: Tuple[str, ...] = ()
    cycle_time_per_unit: Optional[Quantity] = None
    energy_per_unit: Optional[Quantity] = None
    water_per_unit: Optional[Quantity] = None
    labor_skill: Tuple[str, ...] = ()
    environment: str = ""
    yield_fraction: float = 1.0
    scrap_fraction: float = 0.0


@dataclass
class ProductionRecipe(Entity):
    """Validated route: inputs -> output through process steps."""

    output_part: str = ""
    output_quantity: Quantity = Quantity(1.0, "pcs")
    inputs: Tuple[Tuple[str, Quantity], ...] = ()
    steps: Tuple[ProcessStep, ...] = ()
    route_type: str = "primary"
    maturity: str = "series"
    requires_qualification: Tuple[str, ...] = ()
    applicable_geographies: Tuple[str, ...] = ("GLOBAL",)
    capex_estimate: Optional[Quantity] = None
    unit_conversion_note: str = ""

    def to_json(self):
        base = Entity.to_json(self)
        base.update(
            output_part=self.output_part,
            output_quantity=str(self.output_quantity),
            inputs=[{"id": i, "quantity": str(qty)} for i, qty in self.inputs],
            steps=[
                {
                    "id": s.id, "name": s.name, "resource_classes": list(s.resource_classes),
                    "equipment_classes": list(s.equipment_classes),
                    "cycle_time": str(s.cycle_time_per_unit) if s.cycle_time_per_unit else None,
                    "energy": str(s.energy_per_unit) if s.energy_per_unit else None,
                    "yield_fraction": s.yield_fraction, "scrap_fraction": s.scrap_fraction,
                }
                for s in self.steps
            ],
            maturity=self.maturity,
            requires_qualification=list(self.requires_qualification),
        )
        return base


@dataclass
class ResourceClass(Entity):
    category: str = "material"
    unit: str = "pcs"
    substitutable_with: Tuple[str, ...] = ()
    supplied_by_countries: Tuple[str, ...] = ()
    concentration_hhi: Optional[float] = None
    lead_time: Optional[Quantity] = None
    import_eligible: bool = True


@dataclass
class EquipmentClass(Entity):
    machine_hours_per_year: Optional[Quantity] = None
    domestically_producible: Optional[bool] = None
    dominant_supplier_countries: Tuple[str, ...] = ()


@dataclass
class Facility(Entity):
    geo_id: str = "UNKNOWN"
    country: str = "UNKNOWN"
    lat: Optional[float] = None
    lon: Optional[float] = None
    owner_org: str = ""
    operator_org: str = ""
    status: str = "operating"


@dataclass
class CapacitySegment(Entity):
    """Temporal, inspectable capacity of one producer for one item."""

    item_id: str = ""
    facility_id: str = ""
    org_id: str = ""
    geography: str = "INDIA"
    nameplate_annual: Optional[Quantity] = None
    availability: float = 1.0
    utilization: float = 1.0
    yield_fraction: float = 1.0
    qualification_fraction: float = 1.0
    product_compat: Tuple[str, ...] = ()
    valid_from: int = 1900
    valid_to: int = 2100
    epistemic_class: str = "REPORTED"
    is_project_capacity: bool = False
    project_id: str = ""

    def effective_annual(self, year: int) -> Optional[Quantity]:
        if not (self.valid_from <= year <= self.valid_to):
            return None
        if self.nameplate_annual is None:
            return None
        f = self.availability * self.utilization * self.yield_fraction * self.qualification_fraction
        return self.nameplate_annual * f


@dataclass
class ForeignSupplySegment(Entity):
    """Evidenced ABSOLUTE supply capacity available for import from an origin.

    Import eligibility (policy) is a separate multiplier; this entity is the physical
    ceiling. Without it, imports are eligibility-bounded only and the solve reports
    that limitation in its conditionality ledger. V0 had no such concept, so any
    eligible supplier implicitly offered demand-sized supply (F6).
    """

    item_id: str = ""
    origin_country: str = ""
    nameplate_annual: Optional[Quantity] = None
    availability: float = 1.0
    export_availability_fraction: float = 1.0   # share of capacity exported vs domestic use
    valid_from: int = 1900
    valid_to: int = 2100
    epistemic_class: str = "REPORTED"

    def effective_annual(self, year: int) -> Optional[Quantity]:
        if not (self.valid_from <= year <= self.valid_to):
            return None
        if self.nameplate_annual is None:
            return None
        f = self.availability * self.export_availability_fraction
        return self.nameplate_annual * f


@dataclass
class Project(Entity):
    item_id: str = ""
    geography: str = "INDIA"
    state: ProjectState = ProjectState.CONCEPT
    state_date: str = ""
    earliest_start_year: int = 2026
    years_to_commission: Tuple[float, float] = (0.0, 0.0)
    commission_year_estimate: Optional[int] = None
    design_capacity_annual: Optional[Quantity] = None
    ramp_points: Tuple[Tuple[float, float], ...] = ((0.0, 0.5), (2.0, 0.9), (4.0, 1.0))
    expected_yield_curve: Optional[Tuple[Tuple[float, float], ...]] = None
    qualification_gate: Tuple[str, ...] = ()
    required_capital_goods: Tuple[str, ...] = ()
    capex: Optional[Quantity] = None
    owner_org: str = ""
    probability_if_unfunded: float = 0.0

    def to_json(self):
        base = Entity.to_json(self)
        base.update(
            item_id=self.item_id, geography=self.geography, state=self.state.value,
            state_date=self.state_date, earliest_start_year=self.earliest_start_year,
            years_to_commission=list(self.years_to_commission),
            commission_year_estimate=self.commission_year_estimate,
            design_capacity_annual=str(self.design_capacity_annual) if self.design_capacity_annual else None,
            ramp_points=[list(p) for p in self.ramp_points],
            qualification_gate=list(self.qualification_gate),
            capex=str(self.capex) if self.capex else None,
            owner_org=self.owner_org,
        )
        return base


@dataclass
class Organization(Entity):
    org_type: str = "company"
    countries: Tuple[str, ...] = ()


@dataclass
class CapabilityClaim(Entity):
    capability_item: str = ""
    org_id: str = ""
    geography: str = "INDIA"
    vector: CapabilityVector = field(default_factory=CapabilityVector)
    claim_vs_assessment: str = "assessment"

    def to_json(self):
        base = Entity.to_json(self)
        base.update(capability_item=self.capability_item, org_id=self.org_id,
                    geography=self.geography, vector=self.vector.to_json(),
                    claim_vs_assessment=self.claim_vs_assessment)
        return base


@dataclass
class Qualification(Entity):
    item_id: str = ""
    qualifier: str = "customer"
    standard_ref: str = ""
    status: str = "not_started"
    latency_months: Tuple[float, float] = (6.0, 24.0)
    evidence_ids: Tuple[str, ...] = ()


@dataclass
class StandardRef(Entity):
    body: str = ""
    identifier: str = ""
    scope: str = ""


@dataclass
class TechnologyRight(Entity):
    holder: str = ""
    coverage: str = ""
    exclusivity: str = ""


@dataclass
class Skill(Entity):
    scarcity: str = "unknown"
    training_lead_months: Tuple[float, float] = (6.0, 18.0)


@dataclass
class GeoNode(Entity):
    level: str = "country"
    iso: str = ""


@dataclass
class TransportCorridor(Entity):
    from_geo: str = ""
    to_geo: str = ""
    mode: str = "maritime"
    transit_days: Tuple[float, float] = (10.0, 40.0)
    capacity_te_per_year: Optional[Quantity] = None
    disruption_exposure: Tuple[str, ...] = ()


@dataclass
class DemandPool(Entity):
    resource_id: str = ""
    baseline_annual: Optional[Quantity] = None
    contestable_fraction: float = 0.15
    geography: str = "GLOBAL"
    growth_pa: float = 0.03
    note: str = ""


@dataclass
class PolicyAction(Entity):
    instrument: str = "subsidy"
    targets: Tuple[str, ...] = ()
    effect: str = ""


@dataclass
class Restriction(Entity):
    scope: str = "export_control"
    origin: str = ""
    targets_items: Tuple[str, ...] = ()
    severity: str = "licensing"


@dataclass
class Substitution(Entity):
    replaces_part: str = ""
    alternative_recipe: str = ""
    level: str = "component"
    status: str = "candidate"


@dataclass
class Shock(Entity):
    shock_id: str = ""
    description: str = ""
    edits: Tuple[Dict, ...] = ()

    def to_json(self):
        base = Entity.to_json(self)
        base.update(shock_id=self.shock_id, description=self.description,
                    edits=[dict(e) for e in self.edits])
        return base


ALLOWED_EDGES = {
    "decomposes_into", "satisfies_function", "produced_via", "requires_input",
    "consumes_energy", "consumes_water", "requires_capability", "requires_equipment",
    "requires_tool", "requires_qualification", "has_capacity", "located_at", "owned_by",
    "operated_by", "licensed_from", "supplied_by", "transported_via", "competes_for",
    "substitutable_with", "gated_by", "enabled_by_project", "affected_by_shock",
    "supports", "contradicts", "supersedes", "derived_from", "recurses_into",
}


@dataclass
class Edge:
    src: str
    relation: str
    dst: str
    meta: Dict = field(default_factory=dict)


class World:
    """Typed container + graph over all pack entities."""

    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.edges: List[Edge] = []
        self._out: Dict[str, List[Edge]] = {}
        self._in: Dict[str, List[Edge]] = {}

    def add(self, e: Entity) -> Entity:
        if e.id in self.entities:
            raise ValueError(f"duplicate entity id '{e.id}'")
        self.entities[e.id] = e
        return e

    def get(self, eid: str) -> Entity:
        return self.entities[eid]

    def require(self, eid: str) -> Entity:
        if eid not in self.entities:
            raise KeyError(f"entity '{eid}' not found")
        return self.entities[eid]

    def has(self, eid: str) -> bool:
        return eid in self.entities

    def of_kind(self, kind: str) -> List[Entity]:
        return [e for e in self.entities.values() if e.kind == kind]

    def link(self, src: str, relation: str, dst: str, **meta):
        if relation not in ALLOWED_EDGES:
            raise ValueError(f"edge relation '{relation}' not allowed (typed edges only)")
        if src not in self.entities or dst not in self.entities:
            raise KeyError(f"edge endpoint missing: {src} -[{relation}]-> {dst}")
        e = Edge(src, relation, dst, dict(meta))
        self.edges.append(e)
        self._out.setdefault(src, []).append(e)
        self._in.setdefault(dst, []).append(e)

    def out_edges(self, eid: str, relation: Optional[str] = None) -> List[Edge]:
        return [e for e in self._out.get(eid, []) if relation is None or e.relation == relation]

    def in_edges(self, eid: str, relation: Optional[str] = None) -> List[Edge]:
        return [e for e in self._in.get(eid, []) if relation is None or e.relation == relation]

    def neighbors_out(self, eid: str, relation: Optional[str] = None) -> List[str]:
        return [e.dst for e in self.out_edges(eid, relation)]

    def neighbors_in(self, eid: str, relation: Optional[str] = None) -> List[str]:
        return [e.src for e in self.in_edges(eid, relation)]
