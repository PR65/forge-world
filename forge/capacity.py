from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .model import CapacitySegment, Project, ProjectState, ProjectStateContribution, World
from .units import Quantity, annual_scalar


@dataclass
class Interval:
    lo: Optional[float]
    hi: Optional[float]

    def is_unknown(self) -> bool:
        return self.lo is None and self.hi is None

    def __bool__(self) -> bool:
        return not self.is_unknown()


def ramp_fraction(ramp_points: Tuple[Tuple[float, float], ...], t_years: float) -> float:
    pts = sorted(ramp_points)
    if t_years <= 0:
        return 0.0 if not pts or pts[0][0] > 0 else float(pts[0][1])
    prev_t, prev_f = 0.0, 0.0
    for t, f in pts:
        if t_years <= t:
            span = t - prev_t
            frac = 0.0 if span <= 0 else (t_years - prev_t) / span
            return prev_f + frac * (f - prev_f)
        prev_t, prev_f = t, f
    return prev_f


CURRENT_YEAR = 2026
_OPERATING_STATES = (ProjectState.RAMPING, ProjectState.MATURE)


def _effective_start_year(prj: Project) -> int:
    if prj.state in _OPERATING_STATES:
        return prj.earliest_start_year
    return max(prj.earliest_start_year, CURRENT_YEAR)


def project_commission_year(prj: Project, funded: bool = True) -> Optional[int]:
    """Earliest year the project can begin contributing under its state machine (C7).

    Progress through pre-construction states earns schedule credit, but announced ≠
    operating: only completion of the remaining lead time plus ramp produces output.
    """
    if prj.state in (ProjectState.RETIRED, ProjectState.IMPAIRED):
        return None
    if not funded:
        return None
    lead_lo, lead_hi = prj.years_to_commission
    credit = {
        ProjectState.CONCEPT: 0.0,
        ProjectState.ANNOUNCED: 0.25,
        ProjectState.ENGINEERING: 0.5,
        ProjectState.PERMITTING: 0.75,
        ProjectState.APPROVED: 1.0,
        ProjectState.FINANCED: 1.25,
        ProjectState.PROCUREMENT: 1.5,
        ProjectState.CONSTRUCTION: 2.0,
        ProjectState.MECHANICAL_COMPLETION: 2.5,
        ProjectState.COMMISSIONING: 2.75,
        ProjectState.PROCESS_QUALIFICATION: 3.0,
        ProjectState.CUSTOMER_QUALIFICATION: 3.25,
        ProjectState.RAMPING: 3.5,
        ProjectState.MATURE: 4.0,
    }.get(prj.state, 0.0)
    remaining_optimistic = max(lead_lo - credit, 0.0)
    start = _effective_start_year(prj)
    if prj.commission_year_estimate is not None:
        return int(max(start + remaining_optimistic, min(prj.commission_year_estimate, start + remaining_optimistic)))
    return int(start + remaining_optimistic)


def project_contribution_range(prj: Project, year: int, funded: bool = True):
    """Return (pessimistic_qty, optimistic_qty) contributions for a given year."""
    if prj.design_capacity_annual is None:
        return None

    def zero():
        return Quantity(0.0, prj.design_capacity_annual.unit)

    if prj.state in (ProjectState.RETIRED, ProjectState.IMPAIRED):
        return (zero(), zero())
    if not funded:
        return (zero(), zero())
    lead_lo, lead_hi = prj.years_to_commission
    credit = {
        ProjectState.CONCEPT: 0.0,
        ProjectState.ANNOUNCED: 0.25,
        ProjectState.ENGINEERING: 0.5,
        ProjectState.PERMITTING: 0.75,
        ProjectState.APPROVED: 1.0,
        ProjectState.FINANCED: 1.25,
        ProjectState.PROCUREMENT: 1.5,
        ProjectState.CONSTRUCTION: 2.0,
        ProjectState.MECHANICAL_COMPLETION: 2.5,
        ProjectState.COMMISSIONING: 2.75,
        ProjectState.PROCESS_QUALIFICATION: 3.0,
        ProjectState.CUSTOMER_QUALIFICATION: 3.25,
        ProjectState.RAMPING: 3.5,
        ProjectState.MATURE: 4.0,
    }.get(prj.state, 0.0)
    rem_opt = max(lead_lo - credit, 0.0)
    rem_pess = max(lead_hi - credit, 0.0)
    start = _effective_start_year(prj)

    def contrib(remaining: float) -> float:
        cy = start + remaining
        t = float(year - cy)
        if t <= 0:
            return 0.0
        return ramp_fraction(prj.ramp_points, t)

    f_opt = contrib(rem_opt)
    f_pess = contrib(rem_pess)
    return (prj.design_capacity_annual * f_pess, prj.design_capacity_annual * f_opt)


def _cap_unit(prj: Project) -> str:
    assert prj.design_capacity_annual is not None
    return prj.design_capacity_annual.unit


@dataclass
class CapacityEnvelope:
    item_id: str
    geography: str
    domestic: Interval
    import_eligible_fraction: float
    suppliers: Tuple[str, ...] = ()
    concentration_hhi: Optional[float] = None
    unknown_reasons: List[str] = field(default_factory=list)
    conflicted: bool = False
    contributing_projects: List[str] = field(default_factory=list)
    segment_ids: List[str] = field(default_factory=list)
    proven_by_projects_only: bool = False
    epistemic: str = "UNKNOWN"

    @property
    def adjudicable(self) -> bool:
        return not self.domestic.is_unknown()


def capacity_envelope(
    w: World,
    item_id: str,
    year: int,
    import_eligibility: Optional[Dict[str, float]] = None,
    funded_project_ids: Optional[set] = None,
    geography: str = "INDIA",
    count_unproven_projects: bool = True,
    qualification_boost: bool = False,
) -> CapacityEnvelope:
    """Assemble effective-capacity envelope for one item/year (C6).

    UNKNOWN when no evidence-bearing segment/claim/project defines capacity.
    Unproven projects contribute only to the optimistic edge of the interval and flag
    the result as conditional (C7: announced != operating).
    `qualification_boost` models a completed QUALIFY action: existing segments count at
    full qualification for this item (it does NOT create capacity that has no evidence).
    """
    funded = funded_project_ids or set()
    elig_map = import_eligibility or {}
    reasons: List[str] = []
    conflicted = False
    lo_vals: List[float] = []
    hi_vals: List[float] = []
    unit: Optional[str] = None
    seg_ids: List[str] = []
    proj_ids: List[str] = []
    proven_only = True

    for ent in w.entities.values():
        if not isinstance(ent, CapacitySegment):
            continue
        seg = ent
        if seg.item_id != item_id:
            continue
        if seg.geography not in (geography, "GLOBAL"):
            continue
        eff_frac = 1.0 if qualification_boost else seg.qualification_fraction
        f = seg.availability * seg.utilization * seg.yield_fraction * eff_frac
        if seg.nameplate_annual is None:
            continue
        v = annual_scalar(seg.nameplate_annual) * f
        if not (seg.valid_from <= year <= seg.valid_to):
            continue
        seg_ids.append(seg.id)
        lo_vals.append(v)
        hi_vals.append(v)
        unit = seg.nameplate_annual.unit

    for ent in w.entities.values():
        if not isinstance(ent, Project):
            continue
        prj = ent
        if prj.item_id != item_id:
            continue
        if prj.geography not in (geography, "GLOBAL"):
            continue
        rng = project_contribution_range(
            prj, year, funded=(prj.id in funded) if funded_project_ids is not None else True
        )
        if rng is None:
            reasons.append(f"project {prj.id}: design capacity unknown")
            continue
        pess, opt = rng
        proj_ids.append(prj.id)
        if prj.state in (ProjectState.RAMPING, ProjectState.MATURE):
            lo_vals.append(annual_scalar(pess))
            hi_vals.append(annual_scalar(opt))
        else:
            proven_only = False
            hi_vals.append(annual_scalar(opt))
        unit = prj.design_capacity_annual.unit

    if unit is None:
        dom = Interval(None, None)
        reasons.append(f"no qualified-capacity evidence found for {item_id} @ {geography} {year}")
    else:
        lo = min(lo_vals) if lo_vals else 0.0
        hi = sum(hi_vals) if hi_vals else 0.0
        if len(seg_ids) == 0 and proj_ids:
            lo = 0.0
        elif lo_vals:
            lo = sum(lo_vals)
        dom = Interval(min(lo, hi), hi)

    ent_item = w.entities.get(item_id)
    countries: Tuple[str, ...] = ()
    hhi = None
    if ent_item is not None:
        countries = tuple(getattr(ent_item, "supplied_by_countries", ()) or ())
        hhi = getattr(ent_item, "concentration_hhi", None)
    if countries:
        fracs = [elig_map.get(c, 1.0) for c in countries]
        elig_frac = sum(fracs) / len(fracs)
    else:
        elig_frac = 1.0

    seg_classes = {
        getattr(w.entities.get(s), "epistemic_class", "REPORTED") for s in seg_ids
    }
    if unit is None:
        epistemic = "UNKNOWN"
    elif seg_ids and not proj_ids:
        epistemic = "/".join(sorted(seg_classes))
    elif seg_ids and proj_ids:
        epistemic = "mixed:" + "+projects"
    elif proj_ids:
        epistemic = "projects_only"
    else:
        epistemic = "UNKNOWN"

    return CapacityEnvelope(
        item_id=item_id,
        geography=geography,
        domestic=dom,
        import_eligible_fraction=elig_frac,
        suppliers=countries,
        concentration_hhi=hhi,
        unknown_reasons=reasons,
        conflicted=conflicted,
        contributing_projects=proj_ids,
        segment_ids=seg_ids,
        proven_by_projects_only=(len(seg_ids) == 0 and len(proj_ids) > 0),
        epistemic=epistemic,
    )
