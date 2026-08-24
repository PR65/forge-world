"""V0.1 solve: unit-safe LP allocation + certified aggregate-DVA constraint.

Replaces V0 semantics where (F5) heterogeneous physical shortfalls summed into one
scalar and (F1) min_dva imposed a per-item localization cap. V0.1 rules:

- Every item's demand/capacity/shortfall carries its unit family. Cross-item totals
  are `ShortfallVector` (per-family sums) plus an explicit normalized deficit
  (share of that item's demand) used ONLY for ranking — never a physical sum.
- `min_dva` means aggregate recursive DVA over delivered value. It is enforced by a
  certified outer loop: solve -> measure DVA on the delivered mix -> tighten per-item
  import caps where dual information says imports displace domestic value ->
  re-solve, until measured DVA >= target or the loop certifies infeasibility
  (certificate exposed on the result).
- Import bounds respect foreign supply caps when ForeignSupplySegment evidence exists;
  eligibility multiplies availability, never creates quantity (F6/F7).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set, Tuple

import numpy as np
from scipy.optimize import linprog

from .capacity import CapacityEnvelope, capacity_envelope
from .evidence import ProofGraph
from .epistemics import ResultClass
from .explode import ExplosionResult, primary_recipe
from .model import Project, ProjectState, World
from .units import Quantity, UnitError, annual_scalar

SHORTFALL_PENALTY = 1e6
DVA_LOOP_MAX_ITER = 24


# ------------------------------------------------------------------ deficit metrics


@dataclass
class ShortfallVector:
    """Per-unit-family shortfall sums. Physical families are NEVER merged."""

    by_unit: Dict[str, float] = field(default_factory=dict)

    def add(self, unit: str, amount: float) -> None:
        self.by_unit[unit] = self.by_unit.get(unit, 0.0) + amount

    def is_zero(self) -> bool:
        return all(abs(v) <= 1e-9 for v in self.by_unit.values())

    def to_json(self) -> Dict[str, float]:
        return {k: round(v, 3) for k, v in sorted(self.by_unit.items()) if abs(v) > 1e-9}

    @staticmethod
    def total_from_gaps(gaps: List["ItemGap"]) -> "ShortfallVector":
        sv = ShortfallVector()
        for g in gaps:
            sv.add(g.unit_family, g.shortfall)
        return sv


def normalized_service_deficit(gaps: List["ItemGap"]) -> float:
    """Dimensionless ranking metric: mean share of unmet demand across items.

    Each item contributes shortfall/demand ∈ [0,1]; items with zero demand are
    skipped. Invariant to pure unit-representation changes by construction
    (shares are ratios within one item's own units). Used for planner/VOI/reverse
    ranking where V0 used the invalid physical scalar.
    """
    if not gaps:
        return 0.0
    shares = []
    for g in gaps:
        denom = g.demand
        if denom > 1e-12:
            shares.append(min(max(g.shortfall / denom, 0.0), 1.0))
    return sum(shares) / len(shares) if shares else 0.0


def _unit_family(qty: Quantity) -> str:
    return qty.unit if qty.unit != "pcs" else "pcs"


@dataclass
class ItemGap:
    item_id: str
    year: int
    unit_family: str
    demand: float
    domestic_used: float
    imports_used: float
    shortfall: float
    cap_dom_lo: Optional[float]
    cap_dom_hi: Optional[float]
    binding: bool = False
    unknown: bool = False

    @property
    def service_deficit_share(self) -> float:
        return min(max(self.shortfall / self.demand, 0.0), 1.0) if self.demand > 1e-12 else 0.0


@dataclass
class YearResult:
    year: int
    demand_items: int
    shortfall_vector: ShortfallVector = field(default_factory=ShortfallVector)
    normalized_deficit: float = 0.0
    shortfalls: List[ItemGap] = field(default_factory=list)
    allocations: List[ItemGap] = field(default_factory=list)
    binding_constraints: List[str] = field(default_factory=list)
    import_value_usd: float = 0.0
    domestic_value_usd: float = 0.0
    # RT4/F2': items whose delivered imports leaned on UNKNOWN foreign capacity
    # (eligibility held, but no evidenced ForeignSupplySegment bounded supply).
    foreign_supply_unknown: List[str] = field(default_factory=list)

    @property
    def total_shortfall(self) -> float:
        """DEPRECATED compatibility view: pcs-family sum only.

        Retained so existing callers render *something*; every internal decision
        uses shortfall_vector / normalized_deficit. Displayed values must be read
        together with to_json() which exposes the full vector.
        """
        return self.shortfall_vector.by_unit.get("pcs", 0.0)

    def worst_metric(self) -> float:
        """Ranking metric for this year: normalized service deficit."""
        return self.normalized_deficit


@dataclass
class SolveResult:
    result_class: ResultClass
    years: Dict[int, YearResult] = field(default_factory=dict)
    blocking_unknowns: List[str] = field(default_factory=list)
    conditional_reasons: List[str] = field(default_factory=list)
    condition_ledger: List[Dict] = field(default_factory=list)
    binding_summary: List[str] = field(default_factory=list)
    required_relaxations: List[str] = field(default_factory=list)
    closure_candidates: List[str] = field(default_factory=list)
    proof_root: Optional[str] = None
    max_shortfall_item: str = ""
    max_shortfall_year: int = 0
    dva_report: Optional[Dict] = None
    dva_certificate: Optional[Dict] = None

    def worst_year(self) -> Optional[int]:
        """Year with the highest normalized service deficit (unit-safe ranking)."""
        if not self.years:
            return None
        return max(self.years.keys(), key=lambda y: self.years[y].worst_metric())

    # -- compatibility shims for legacy call sites (planner/voi/frontier read these) --
    def legacy_total_shortfall(self, year: Optional[int] = None) -> float:
        """Normalized-deficit-scaled scalar: dimensionless, unit-safe ordering."""
        y = year if year is not None else self.worst_year()
        if y is None or y not in self.years:
            return 0.0
        yr = self.years[y]
        total_demand = sum(g.demand for g in yr.allocations)
        return yr.normalized_deficit * total_demand if total_demand > 0 else 0.0


@dataclass
class ScenarioOptions:
    import_eligibility: Dict[str, float] = field(default_factory=dict)
    funded_project_ids: Set[str] = field(default_factory=set)
    capacity_overrides: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    cost_domestic: Dict[str, float] = field(default_factory=dict)
    cost_import: Dict[str, float] = field(default_factory=dict)
    assume_capacity_hi: bool = True
    count_unproven_projects: bool = True
    equipment_hour_limits: Dict[str, float] = field(default_factory=dict)
    equipment_hours_per_unit: Dict[str, Dict[str, float]] = field(default_factory=dict)
    geography: str = "INDIA"
    competing_demand_cuts: Dict[str, float] = field(default_factory=dict)
    min_domestic_share: float = 0.0
    qualification_boosts: Set[str] = field(default_factory=set)
    # W3.2/F11: item -> first year its completed qualification counts (latency-honored).
    qualification_online_year: Dict[str, int] = field(default_factory=dict)
    global_import_cost_mult: float = 1.0
    global_domestic_cost_mult: float = 1.0
    funded_pipeline: str = "optimistic"
    enforce_dva: bool = True          # V0.1: min_domestic_share interpreted as aggregate DVA
    per_item_import_cap: Dict[str, float] = field(default_factory=dict)
    raw_material_import_share: float = 0.0   # origin-UNKNOWN default; explicit ASSUMPTION
    # RT4/F2': how to treat imports whose absolute foreign capacity is UNKNOWN.
    #   "strict"     (default): delivery leaning on them => NOT_ADJUDICABLE.
    #   "unbounded_assumption": proceed CONDITIONALLY, recording a named ASSUMPTION
    #                that foreign supply is treated as unbounded. Never silent.
    foreign_supply_policy: str = "strict"
    action_active_years: Dict[str, Tuple[int, int]] = field(default_factory=dict)
    decision_year: int = 2030

    def clone(self) -> "ScenarioOptions":
        """FULL copy including every field (V0 clones dropped funded_pipeline etc.)."""
        return ScenarioOptions(
            import_eligibility=dict(self.import_eligibility),
            funded_project_ids=set(self.funded_project_ids),
            capacity_overrides={k: tuple(v) for k, v in self.capacity_overrides.items()},
            cost_domestic=dict(self.cost_domestic),
            cost_import=dict(self.cost_import),
            assume_capacity_hi=self.assume_capacity_hi,
            count_unproven_projects=self.count_unproven_projects,
            equipment_hour_limits=dict(self.equipment_hour_limits),
            equipment_hours_per_unit={k: dict(v) for k, v in self.equipment_hours_per_unit.items()},
            geography=self.geography,
            competing_demand_cuts=dict(self.competing_demand_cuts),
            min_domestic_share=self.min_domestic_share,
            qualification_boosts=set(self.qualification_boosts),
            qualification_online_year=dict(self.qualification_online_year),
            foreign_supply_policy=self.foreign_supply_policy,
            global_import_cost_mult=self.global_import_cost_mult,
            global_domestic_cost_mult=self.global_domestic_cost_mult,
            funded_pipeline=self.funded_pipeline,
            enforce_dva=self.enforce_dva,
            per_item_import_cap=dict(self.per_item_import_cap),
            raw_material_import_share=self.raw_material_import_share,
            action_active_years=dict(self.action_active_years),
            decision_year=self.decision_year,
        )

    def funded_arg(self) -> Optional[Set[str]]:
        """Project set passed to capacity_envelope.

        optimistic  -> None (every evidenced project counts, flagged conditional)
        selected    -> the funded set
        """
        if self.funded_pipeline == "selected_only":
            return set(self.funded_project_ids)
        return self.funded_project_ids or None


def _unit_cost(opts: ScenarioOptions, item: str) -> Tuple[float, float]:
    cd = opts.cost_domestic.get(item, 1.0) * opts.global_domestic_cost_mult
    ci_declared = opts.cost_import.get(item)
    if ci_declared is not None:
        ci = ci_declared * opts.global_import_cost_mult
    elif item in opts.cost_domestic:
        # RT4: a declared domestic price with an undeclared import price must not
        # silently offer a flat fictional $1.08 import — assume import parity.
        ci = cd * 1.08
    else:
        ci = 1.08 * opts.global_import_cost_mult
    return (cd, ci)


def _recipe_input_value(w: World, rec, opts: ScenarioOptions,
                        depth: int = 0) -> Tuple[float, float]:
    """(input_value_total, input_value_imported) per ONE unit of recipe output.

    Shallow valuation for LP pricing defaults: declared prices where present,
    recursive recipe input value otherwise (bounded depth).
    """
    if depth > 6:
        return (0.0, 0.0)
    total = 0.0
    imported = 0.0
    scale = 1.0 / (rec.output_quantity.value or 1.0)
    for iname, iq in rec.inputs:
        need = iq.value * scale
        sub_rec = primary_recipe(w, iname, geography=opts.geography)
        cd = opts.cost_domestic.get(iname)
        ci = opts.cost_import.get(iname)
        if sub_rec is not None and cd is None:
            t_sub, i_sub = _recipe_input_value(w, sub_rec, opts, depth + 1)
            proc_key = f"processing:{iname}"
            proc = opts.cost_domestic.get(proc_key, 0.35 * max(t_sub, 0.5))
            total += need * (t_sub + proc)
            imported += need * i_sub
        else:
            v_dom = cd if cd is not None else (ci if ci is not None else 1.0)
            total += need * v_dom
            if ci is not None and cd is None:
                imported += need * ci
    return (total, imported)


def _importable(w: World, item_id: str) -> bool:
    ent = w.entities.get(item_id)
    if ent is None:
        return True
    return bool(getattr(ent, "import_eligible", True))


def _foreign_supply_cap(w: World, item_id: str, year: int) -> Optional[float]:
    """Evidenced foreign supply ceiling across ALL origins (None = UNKNOWN/no evidence).

    Only ForeignSupplySegment entities create absolute import caps; eligibility never
    does (oracle D). Units assumed comparable within one item (they describe supply
    of that item).
    """
    from .model import ForeignSupplySegment  # local import avoids cycle at module load
    total = 0.0
    found = False
    for e in w.entities.values():
        if isinstance(e, ForeignSupplySegment) and e.item_id == item_id:
            eff = e.effective_annual(year)
            if eff is None:
                continue
            found = True
            total += annual_scalar(eff)
    return total if found else None


def _supplier_weights(w: World, item_id: str) -> List[Tuple[str, float]]:
    """Per-country weights for eligibility aggregation.

    Evidenced share weights if present on the entity (supplier_shares); otherwise
    concentration-weighted proxy: dominant country gets weight ∝ sqrt(HHI), others
    split the rest equally — always flagged as ASSUMPTION by the caller. Falls back
    to equal weights only when no structure exists at all.
    """
    ent = w.entities.get(item_id)
    countries = list(getattr(ent, "supplied_by_countries", ()) or ()) if ent else []
    if not countries:
        return []
    shares = getattr(ent, "supplier_shares", None)
    if shares:
        tot = sum(float(shares.get(c, 0.0)) for c in countries)
        if tot > 0:
            return [(c, float(shares.get(c, 0.0)) / tot) for c in countries]
    hhi = getattr(ent, "concentration_hhi", None) if ent else None
    if hhi and hhi > 0.5 and len(countries) >= 2:
        # concentration proxy: first-listed (dominant) country carries ~hhi weight
        w_dom = min(max(hhi, 0.0), 1.0)
        rest = 1.0 - w_dom
        per = rest / (len(countries) - 1)
        return [(countries[0], w_dom)] + [(c, per) for c in countries[1:]]
    return [(c, 1.0 / len(countries)) for c in countries]


def solve_year(
    w: World,
    pg: ProofGraph,
    explosion: ExplosionResult,
    year: int,
    opts: ScenarioOptions,
    dva_cap_tightening: Optional[Dict[str, float]] = None,
    provenance_notes: Optional[List[Dict]] = None,
) -> YearResult:
    items = list(explosion.items())
    n = len(items)
    yr = YearResult(year=year, demand_items=n)
    if n == 0:
        return yr

    tighten = dva_cap_tightening or {}
    demand = np.zeros(n)
    cap_hi = np.zeros(n)
    imp_frac = np.zeros(n)
    unknown_flags: List[str] = []
    envelopes: Dict[str, CapacityEnvelope] = {}

    for k, it in enumerate(items):
        line = explosion.get(it)
        d = line.gross_annual if line else Quantity(0.0, "pcs")
        fam = line.gross_annual.unit if line else "pcs"
        demand[k] = abs(annual_scalar(d))
        env = capacity_envelope(
            w, it, year,
            import_eligibility=opts.import_eligibility,
            funded_project_ids=opts.funded_arg(),
            geography=opts.geography,
            qualification_boost=(
                it in opts.qualification_boosts
                and year >= opts.qualification_online_year.get(it, 0)
            ),
            exclude_unproven_projects=not opts.count_unproven_projects,
        )
        envelopes[it] = env
        if it in opts.capacity_overrides:
            _, hi = opts.capacity_overrides[it]
            cap_hi[k] = hi
        elif env.domestic.is_unknown():
            unknown_flags.append(it)
            # A recipe proves only that the route is represented in the model. It
            # is not evidence of installed, effective, or qualified throughput.
            # UNKNOWN domestic capacity therefore contributes no admissible
            # supply unless the analyst supplied an explicit capacity override.
            cap_hi[k] = 0.0
        else:
            use = env.domestic.hi if opts.assume_capacity_hi else env.domestic.lo
            cap_hi[k] = use or 0.0
        cut = opts.competing_demand_cuts.get(it, 0.0)
        if cut > 0 and np.isfinite(cap_hi[k]):
            pool_base = 0.0
            for e2 in w.entities.values():
                if getattr(e2, "kind", "") == "demand_pool" and getattr(e2, "resource_id", "") == it:
                    base = getattr(e2, "baseline_annual", None)
                    cf = float(getattr(e2, "contestable_fraction", 0.15))
                    growth = float(getattr(e2, "growth_pa", 0.03))
                    if base is not None:
                        grown = annual_scalar(base) * ((1.0 + growth) ** max(year - 2026, 0))
                        pool_base = grown * cf
            if pool_base > 0:
                cap_hi[k] *= max(pool_base - cut, 0.0) / pool_base

        # --- import bound: eligibility × foreign supply reality ---
        weights = _supplier_weights(w, it)
        if weights:
            elig_frac = sum(fr * opts.import_eligibility.get(c, 1.0) for c, fr in weights)
        else:
            elig_frac = min(opts.import_eligibility.values()) if opts.import_eligibility else 1.0
            elig_frac = 1.0 if elig_frac > 1.0 else elig_frac
        fcap = _foreign_supply_cap(w, it, year)
        if fcap is None:
            # RT4/F2': no evidenced foreign capacity. Eligibility alone must NOT
            # manufacture supply: we explore the optimistic edge (imports allowed)
            # but the item is flagged; solve_objective refuses adjudication when
            # the DELIVERED mix leans on these unevidenced volumes (imports > 0).
            fcap_frac = 1.0
            if elig_frac > 0 and demand[k] > 1e-12:
                yr.foreign_supply_unknown.append(it)
        else:
            fcap_frac = min(fcap / demand[k], 1.0) if demand[k] > 1e-12 else 0.0
        # RT4/F1': min_domestic_share is AGGREGATE recursive DVA — it never caps
        # individual items here. Per-item localization exists only via the
        # explicit per_item_import_cap field (analyst policy) and the certified
        # DVA loop's tightening map (which pursues the aggregate target).
        tight_k = min(tighten.get(it, 1.0), opts.per_item_import_cap.get(it, 1.0), 1.0)
        imp_frac[k] = min(elig_frac, fcap_frac) * tight_k

    # RT4 (review follow-up): an item with a production recipe must not be
    # importable at a flat fictional default price — that lets the LP "import"
    # finished assemblies for ~$1 and bypass the whole domestic chain. If no
    # import price is declared, import cost defaults to the item's DOMESTIC
    # production basis: declared domestic price, else its recipe input value,
    # else the flat fallback.
    from .explode import primary_recipe as _primary_recipe
    for k, it in enumerate(items):
        if it in opts.cost_import:
            continue
        cd, _ci = _unit_cost(opts, it)
        rec = _primary_recipe(w, it, geography=opts.geography)
        if cd != 1.0 or rec is None:
            continue  # declared price, or genuinely unknown-cost raw material
        t_in, i_in = _recipe_input_value(w, rec, opts)
        if t_in > 0:
            opts.cost_import.setdefault(it, t_in * 1.08)

    A_eq = np.zeros((n, n * 3))
    b_eq = np.zeros(n)
    for k in range(n):
        A_eq[k, k] = 1.0
        A_eq[k, n + k] = 1.0
        A_eq[k, 2 * n + k] = 1.0
        b_eq[k] = demand[k]

    eq_rows = n
    ub_names: List[str] = []
    A_ub_rows: List[np.ndarray] = []
    b_ub_vals: List[float] = []
    for equip_id, limit in sorted(opts.equipment_hour_limits.items()):
        row = np.zeros(n * 3)
        hpu_map = opts.equipment_hours_per_unit.get(equip_id, {})
        for k, it in enumerate(items):
            h = hpu_map.get(it, 0.0)
            if h:
                row[k] = h
        A_ub_rows.append(row)
        b_ub_vals.append(limit)
        ub_names.append(f"equipment-hours:{equip_id}")

    c = np.zeros(n * 3)
    bounds: list = [None] * (n * 3)
    for k, it in enumerate(items):
        cd, ci = _unit_cost(opts, it)
        c[k] = cd
        c[n + k] = ci
        c[2 * n + k] = SHORTFALL_PENALTY * max(demand[k], 1.0)
        hi_cap = cap_hi[k]
        dom_b = min(hi_cap, demand[k]) if np.isfinite(hi_cap) else demand[k]
        bounds[k] = (0.0, dom_b)
        bounds[n + k] = (0.0, demand[k] * imp_frac[k])
        bounds[2 * n + k] = (0.0, demand[k])

    A_ub = np.vstack(A_ub_rows) if A_ub_rows else None
    b_ub = np.array(b_ub_vals) if b_ub_vals else None
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")
    if not res.success:
        yr.shortfall_vector.add("INFEASIBLE_LP", float("inf"))
        yr.binding_constraints.append("LP failed: " + str(res.message))
        return yr

    x = res.x
    tol = max(1e-6, 1e-9 * max(float(demand.max()), 1.0))
    for k, it in enumerate(items):
        dom_u, imp_u, short = float(x[k]), float(x[n + k]), float(x[2 * n + k])
        env = envelopes[it]
        fam = explosion.get(it).gross_annual.unit if explosion.get(it) else "pcs"
        gap = ItemGap(
            item_id=it,
            year=year,
            unit_family=fam,
            demand=float(demand[k]),
            domestic_used=dom_u,
            imports_used=imp_u,
            shortfall=short,
            cap_dom_lo=(env.domestic.lo if not env.domestic.is_unknown() else None),
            cap_dom_hi=env.domestic.hi,
            binding=bool(short > tol),
            unknown=(it in unknown_flags),
        )
        yr.allocations.append(gap)
        if short > tol:
            yr.shortfalls.append(gap)
            yr.shortfall_vector.add(fam, short)
        cd, ci = _unit_cost(opts, it)
        yr.import_value_usd += imp_u * ci
        yr.domestic_value_usd += dom_u * cd

    yr.normalized_deficit = normalized_service_deficit(yr.allocations)

    try:
        ineq_marginals = res.ineqlin.marginals if res.ineqlin is not None else []
    except AttributeError:
        ineq_marginals = []
    for idx, name in enumerate(ub_names):
        if idx < len(ineq_marginals) and abs(ineq_marginals[idx]) > 1e-6:
            yr.binding_constraints.append(name)

    yr.shortfalls.sort(key=lambda g: -g.service_deficit_share)
    return yr


def collect_unproven_funded(w: World, funded: Set[str], pipeline: str = "optimistic") -> List[str]:
    out = []
    for e in w.entities.values():
        if isinstance(e, Project) and not _is_operating(e):
            if pipeline == "selected_only":
                if e.id in funded:
                    out.append(e.id)
            else:
                # optimistic pipeline counts EVERY evidenced unproven project
                out.append(e.id)
    return sorted(out)


def _is_operating(prj_like) -> bool:
    st = str(getattr(prj_like, "state", ""))
    return ("RAMPING" in st.upper()) or ("MATURE" in st.upper())


def solve_objective(
    w: World,
    pg: ProofGraph,
    explosion: ExplosionResult,
    years: Sequence[int],
    opts: ScenarioOptions,
) -> SolveResult:
    """Multi-year feasibility classification under V0.1 semantics.

    With enforce_dva=True, min_domestic_share is treated as a REQUIRED AGGREGATE
    RECURSIVE DVA and enforced through the certified tightening loop below.
    """
    from .dva import measure_dva

    blocking: List[str] = []
    conditional: List[str] = []
    ledger: List[Dict] = []
    partially_known: Set[str] = set()

    probe_years = sorted(set(years))
    for it in explosion.items():
        blocked_everywhere = True
        for year in probe_years:
            env = capacity_envelope(
                w, it, year,
                import_eligibility=opts.import_eligibility,
                funded_project_ids=opts.funded_arg(),
                geography=opts.geography,
            )
            if not env.domestic.is_unknown():
                blocked_everywhere = False
                break
            if env.import_eligible_fraction > 0 and _importable(w, it):
                blocked_everywhere = False
                partially_known.add(it)
                break
        if blocked_everywhere:
            blocking.append(f"capacity UNKNOWN and no eligible supply route: {it}")

    adjudicable = len(blocking) == 0
    for it in sorted(partially_known):
        conditional.append(
            f"domestic capacity UNKNOWN for {it}; verdict relies on eligible imports "
            f"(decision-sensitive)"
        )
        ledger.append({"type": "unknown_import_dependent", "item": it})

    # ---- RT4/F2': unevidenced foreign supply must not silently back a verdict ----
    # If the delivered mix leans on imports whose absolute foreign capacity is
    # UNKNOWN (no ForeignSupplySegment), the verdict is CONDITIONAL at best and
    # NOT_ADJUDICABLE when those imports carry the delivery (no shortfall headroom
    # elsewhere would survive removing them). We re-examine after solving below.
    foreign_unknown_items: set = set()

    # ---- project conditionality ledger (F8/F9): structured, numeric-aware ----
    unproven = collect_unproven_funded(w, opts.funded_project_ids, opts.funded_pipeline)
    if opts.count_unproven_projects is False and opts.funded_pipeline == "optimistic":
        pass  # handled numerically below via funded_arg override
    for prj_id in unproven:
        prj = w.entities.get(prj_id)
        if isinstance(prj, Project):
            cy = prj.earliest_start_year + (prj.years_to_commission[0] if prj.years_to_commission else 0)
            entry = {
                "type": "unproven_project_in_optimistic_edge",
                "project": prj_id,
                "state": prj.state.value,
                "earliest_contribution": int(cy) + 1,
                "design_capacity": (str(prj.design_capacity_annual)
                                     if prj.design_capacity_annual else None),
                "counted": bool(opts.count_unproven_projects),
            }
            ledger.append(entry)
            conditional.append(
                f"{prj_id} ({prj.state.value}) counted on optimistic edge before "
                f"qualification; earliest contribution ≥ {int(cy) + 1}"
                if opts.count_unproven_projects else
                f"{prj_id} excluded from optimistic edge (count_unproven_projects=False)"
            )

    if opts.capacity_overrides:
        conditional.append(
            "analyst capacity assumptions applied for: "
            + ", ".join(sorted(opts.capacity_overrides))
        )
        ledger.append({"type": "analyst_override",
                        "items": sorted(opts.capacity_overrides)})

    # ---- certified DVA loop ----
    dva_certificate: Optional[Dict] = None
    results: Dict[int, YearResult] = {}
    tighten: Dict[str, float] = {}

    target_dva = opts.min_domestic_share if opts.enforce_dva else 0.0

    def run_pass(tighten_map: Dict[str, float]):
        yrs: Dict[int, YearResult] = {}
        for year in probe_years:
            yrs[year] = solve_year(w, pg, explosion, year, opts,
                                   dva_cap_tightening=tighten_map,
                                   provenance_notes=None)
        return yrs

    results = run_pass(tighten)
    iterations = 0

    # ---- RT4/F2' epistemic gate on unevidenced foreign supply -----------------
    # After the first pass, inspect which items actually DELIVERED on imports with
    # UNKNOWN absolute foreign capacity (flagged only when imports were possible;
    # here we keep only items whose solved mix actually used them).
    for yr in results.values():
        for g in yr.allocations:
            if g.imports_used > 1e-6 and g.item_id in yr.foreign_supply_unknown:
                foreign_unknown_items.add(g.item_id)
    for it in sorted(foreign_unknown_items):
        ledger.append({
            "type": "foreign_supply_capacity_unknown",
            "item": it,
            "imports_delivered_on_unknown": True,
            "note": ("eligibility held but no evidenced ForeignSupplySegment; "
                      "delivered import volume is unevidenced"),
        })
    if foreign_unknown_items:
        conditional.append(
            "import volumes delivered without evidenced foreign capacity for: "
            + ", ".join(sorted(foreign_unknown_items))
            + " — verdict leans on unevidenced supply"
        )
        # Decision-critical unknown: would the verdict survive capping those
        # imports at zero? If not, the result is NOT adjudicable from evidence.
        def _survives_without_unevidenced_imports(res_map) -> bool:
            for yr2 in res_map.values():
                for g in yr2.allocations:
                    if g.item_id in foreign_unknown_items and \
                            (g.shortfall > 1e-6 or g.imports_used <= 1e-6):
                        continue
                    if g.item_id in foreign_unknown_items and g.imports_used > 1e-6:
                        # imports carried demand: removing them creates shortfall
                        return False
            return True
        if not _survives_without_unevidenced_imports(results):
            if opts.foreign_supply_policy == "strict":
                adjudicable = False
                blocking.append(
                    "delivery depends on imports with UNKNOWN foreign capacity: "
                    + ", ".join(sorted(foreign_unknown_items))
                    + " — NOT_ADJUDICABLE until ForeignSupplySegments are evidenced"
                )
            else:
                conditional.append(
                    "ASSUMPTION: foreign supply treated as unbounded for "
                    + ", ".join(sorted(foreign_unknown_items))
                    + " (foreign_supply_policy=unbounded_assumption; no evidenced capacity)"
                )
                ledger.append({
                    "type": "foreign_supply_unbounded_assumed",
                    "items": sorted(foreign_unknown_items),
                })

    if adjudicable and target_dva > 0:
        while iterations < DVA_LOOP_MAX_ITER:
            iterations += 1
            allocs = {y: yr.allocations for y, yr in results.items()}
            br = measure_dva(w, pg, explosion, opts, allocations_by_year=allocs,
                             decision_year=max(probe_years))
            achieved = br.fraction
            if achieved >= target_dva - 1e-6:
                dva_certificate = {
                    "status": "satisfied",
                    "target_dva": target_dva,
                    "achieved_dva": round(achieved, 6),
                    "iterations": iterations,
                    "tightened_items": {k: round(v, 4) for k, v in tighten.items()},
                    "convention": br.convention,
                    "assumptions": sorted(set(br.assumptions_used)),
                }
                break
            # If the shortfall already blocks delivery, DVA cannot be certified by
            # tightening import caps — record and stop (infeasibility dominates).
            if any(not yr.shortfall_vector.is_zero() for yr in results.values()):
                # RT4/F1' honesty: distinguish shortfall that EXISTS PHYSICALLY
                # (present before any DVA tightening) from shortfall the loop
                # itself manufactured by capping imports. Only the former is
                # INFEASIBLE_UNDER_MODEL; the latter is a policy failure — the
                # aggregate DVA target is unattainable and forcing item caps
                # must not masquerade as a physical shortage.
                if tighten:
                    dva_certificate = {
                        "status": "infeasible_wrt_dva",
                        "target_dva": target_dva,
                        "achieved_dva_on_delivered": round(achieved, 6),
                        "iterations": iterations,
                        "tightened_items": {k: round(v, 4) for k, v in tighten.items()},
                        "convention": br.convention,
                        "assumptions": sorted(set(br.assumptions_used)),
                    }
                    break
                dva_certificate = {
                    "status": "infeasible_delivery_shortfall",
                    "target_dva": target_dva,
                    "achieved_dva_on_delivered": round(achieved, 6),
                    "iterations": iterations,
                    "tightened_items": {k: round(v, 4) for k, v in tighten.items()},
                    "convention": br.convention,
                    "assumptions": sorted(set(br.assumptions_used)),
                }
                break
            # tighten: reduce import allowance on items whose imported share of
            # delivered mix exceeds what the DVA budget can absorb
            slack = target_dva - achieved
            step = min(0.5, max(0.15, slack))
            changed = False
            ranked = sorted(br.per_item.items(),
                            key=lambda kv: -kv[1].get("import_share_solved", 0.0))
            for it, info in ranked:
                imp_share = info.get("import_share_solved", 0.0)
                if imp_share <= 1e-9:
                    continue
                cur = tighten.get(it, 1.0)
                new_val = max(cur - step * cur if cur > 0 else 0.0, 0.0)
                new_val = max(new_val, 0.02) if cur > 0.02 else 0.0
                if new_val < cur - 1e-9:
                    tighten[it] = new_val
                    changed = True
                    break   # one item per pass: keep certificates interpretable
            if not changed:
                dva_certificate = {
                    "status": "infeasible_no_tightening_leverage",
                    "target_dva": target_dva,
                    "achieved_dva": round(achieved, 6),
                    "iterations": iterations,
                    "convention": br.convention,
                    "assumptions": sorted(set(br.assumptions_used)),
                }
                break
            results = run_pass(tighten)
            if iterations == DVA_LOOP_MAX_ITER:
                dva_certificate = {
                    "status": "max_iterations",
                    "target_dva": target_dva,
                    "achieved_at_last_measure": None,
                    "iterations": iterations,
                    "tightened_items": {k: round(v, 4) for k, v in tighten.items()},
                }
    elif adjudicable:
        dva_certificate = {
            "status": "not_enforced" if target_dva == 0 else "n/a",
            "target_dva": target_dva,
            "iterations": 0,
        }

    if adjudicable and dva_certificate is not None and \
            dva_certificate.get("status") not in ("satisfied", "not_enforced", "n/a"):
        conditional.append(
            f"aggregate DVA target {target_dva:.0%} NOT certified "
            f"({dva_certificate.get('status')}); verdict reflects constraint failure"
        )
        ledger.append({"type": "dva_constraint_uncertified",
                        "target": target_dva,
                        "status": dva_certificate.get("status")})

    sr = _classify(results, blocking, conditional, adjudicable)
    sr.condition_ledger = ledger
    sr.dva_certificate = dva_certificate
    # RT4/F1' honesty: when the DVA loop manufactured shortfall by tightening item
    # caps (physical first pass was clean), the verdict is a DVA-policy failure,
    # not physical infeasibility. Reclassify so the two are never conflated.
    if (dva_certificate is not None
            and dva_certificate.get("status") == "infeasible_wrt_dva"
            and sr.result_class == ResultClass.INFEASIBLE_UNDER_MODEL):
        first_pass_clean = True  # recomputed below from the untightened state
        # Re-run one clean pass to verify the physical world delivers fully.
        clean = run_pass({})
        first_pass_clean = all(yr.shortfall_vector.is_zero() for yr in clean.values())
        if first_pass_clean:
            sr.result_class = ResultClass.INFEASIBLE_WRT_DVA
            sr.years = clean
    # Verdict derives from year-result nodes; each year node derives from the
    # item-level requirement/allocation nodes (no disconnected roots — G1).
    verdict_parents: List[str] = []
    for y in sorted(results.keys()):
        year_node = pg.add_node(
            "derived", f"YearResult {y}: deficit={results[y].normalized_deficit:.4f}",
            {"year": y,
             "shortfall_vector": results[y].shortfall_vector.to_json(),
             "normalized_deficit": results[y].normalized_deficit},
            node_id=f"derived.year.{explosion.variant_id}.{y}",
        )
        for g in results[y].allocations:
            line_node = explosion.proof_node_ids.get(g.item_id)
            if line_node and line_node in pg.nodes:
                pg.add_edge(line_node, year_node)
        verdict_parents.append(year_node)
    sr.proof_root = pg.output(
        verdict_parents,
        f"Solve {explosion.variant_id}: {sr.result_class.value}",
        {
            "result_class": sr.result_class.value,
            "worst_shortfall_item": sr.max_shortfall_item,
            "worst_year": sr.max_shortfall_year,
            "binding": sr.binding_summary,
            "dva_certificate": dva_certificate,
        },
    )
    return sr


def _format_shortfall(value: float) -> str:
    """Show a non-zero physical deficit without rounding it to a fake zero."""

    return f"{value:,.3f}".rstrip("0").rstrip(".")


def _classify(
    results: Dict[int, YearResult],
    blocking_unknowns: List[str],
    conditional_reasons: List[str],
    adjudicable: bool,
) -> SolveResult:
    sr = SolveResult(result_class=ResultClass.FEASIBLE)
    sr.blocking_unknowns = list(blocking_unknowns)
    sr.conditional_reasons = list(conditional_reasons)

    worst_item, worst_val, worst_year = "", -1.0, 0
    for y, yr in sorted(results.items()):
        sr.years[y] = yr
        v = yr.worst_metric()
        if v > worst_val:
            worst_val = v
            worst_item = (yr.shortfalls[0].item_id if yr.shortfalls else "")
            worst_year = y
        for bc in yr.binding_constraints:
            if bc not in sr.binding_summary:
                sr.binding_summary.append(bc)

    sr.max_shortfall_item = worst_item
    sr.max_shortfall_year = worst_year

    if not adjudicable:
        sr.result_class = ResultClass.NOT_ADJUDICABLE
        return sr

    has_shortfall = any(not yr.shortfall_vector.is_zero() for yr in results.values())

    if has_shortfall:
        sr.result_class = ResultClass.INFEASIBLE_UNDER_MODEL
        for y, yr in sorted(results.items()):
            for g in yr.shortfalls:
                relax = (
                    f"{g.item_id}@{y}: need {_format_shortfall(g.shortfall)} more {g.unit_family}/yr "
                    f"({g.service_deficit_share:.0%} of its demand)"
                )
                if relax not in sr.required_relaxations:
                    sr.required_relaxations.append(relax)
                if g.unknown:
                    cand = f"RESEARCH {g.item_id}: capacity UNKNOWN — audit suppliers/yields"
                else:
                    cand = (f"BUILD/QUALIFY {g.item_id}: add {_format_shortfall(g.shortfall)} "
                            f"{g.unit_family}/yr before {y}")
                if cand not in sr.closure_candidates:
                    sr.closure_candidates.append(cand)
        return sr

    if sr.conditional_reasons:
        sr.result_class = ResultClass.CONDITIONALLY_FEASIBLE
    else:
        sr.result_class = ResultClass.FEASIBLE
    return sr
