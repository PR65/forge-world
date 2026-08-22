from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set, Tuple

import numpy as np
from scipy.optimize import linprog

from .capacity import CapacityEnvelope, capacity_envelope
from .evidence import ProofGraph
from .epistemics import ResultClass
from .explode import ExplosionResult
from .model import Project, ProjectState, World
from .units import Quantity, annual_scalar


@dataclass
class ItemGap:
    item_id: str
    year: int
    demand: float
    domestic_used: float
    imports_used: float
    shortfall: float
    cap_dom_lo: Optional[float]
    cap_dom_hi: Optional[float]
    binding: bool = False
    unknown: bool = False


@dataclass
class YearResult:
    year: int
    demand_items: int
    total_shortfall: float
    shortfalls: List[ItemGap] = field(default_factory=list)
    allocations: List[ItemGap] = field(default_factory=list)
    binding_constraints: List[str] = field(default_factory=list)
    import_value_usd: float = 0.0
    domestic_value_usd: float = 0.0


@dataclass
class SolveResult:
    result_class: ResultClass
    years: Dict[int, YearResult] = field(default_factory=dict)
    blocking_unknowns: List[str] = field(default_factory=list)
    conditional_reasons: List[str] = field(default_factory=list)
    binding_summary: List[str] = field(default_factory=list)
    required_relaxations: List[str] = field(default_factory=list)
    closure_candidates: List[str] = field(default_factory=list)
    proof_root: Optional[str] = None
    max_shortfall_item: str = ""
    max_shortfall_year: int = 0

    def worst_year(self) -> Optional[int]:
        if not self.years:
            return None
        return max(self.years.keys(), key=lambda y: self.years[y].total_shortfall)


SHORTFALL_PENALTY = 1e6


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
    global_import_cost_mult: float = 1.0
    global_domestic_cost_mult: float = 1.0
    funded_pipeline: str = "optimistic"

    def funded_arg(self) -> Optional[Set[str]]:
        """None = optimistic pipeline (all evidenced projects counted, flagged conditional);
        set = selected-only pipeline (only listed projects contribute)."""
        if self.funded_pipeline == "selected_only":
            return self.funded_project_ids
        return self.funded_project_ids or None


def _unit_cost(opts: ScenarioOptions, item: str) -> Tuple[float, float]:
    """Planning unit costs. Imports carry a landed-cost premium over domestic production
    (freight/duty/handling ASSUMPTION), which also breaks LP cost ties deterministically
    toward domestic supply wherever qualified capacity exists."""
    cd = opts.cost_domestic.get(item, 1.0) * opts.global_domestic_cost_mult
    ci = opts.cost_import.get(item, 1.08) * opts.global_import_cost_mult
    return (cd, ci)


def _importable(w: World, item_id: str) -> bool:
    ent = w.entities.get(item_id)
    if ent is None:
        return True
    return bool(getattr(ent, "import_eligible", True))


def _is_operating(prj_like) -> bool:
    st = str(getattr(prj_like, "state", ""))
    return ("RAMPING" in st.upper()) or ("MATURE" in st.upper())


def solve_year(
    w: World,
    pg: ProofGraph,
    explosion: ExplosionResult,
    year: int,
    opts: ScenarioOptions,
) -> YearResult:
    items = list(explosion.items())
    n = len(items)
    yr = YearResult(year=year, demand_items=n, total_shortfall=0.0)
    if n == 0:
        return yr

    demand = np.zeros(n)
    cap_hi = np.zeros(n)
    imp_frac = np.ones(n)
    unknown_flags: List[str] = []
    envelopes: Dict[str, CapacityEnvelope] = {}

    for k, it in enumerate(items):
        line = explosion.get(it)
        d = line.gross_annual if line else Quantity(0.0, "pcs")
        demand[k] = abs(annual_scalar(d))
        env = capacity_envelope(
            w, it, year,
            import_eligibility=opts.import_eligibility,
            funded_project_ids=opts.funded_arg(),
            geography=opts.geography,
            qualification_boost=(it in opts.qualification_boosts),
        )
        envelopes[it] = env
        if it in opts.capacity_overrides:
            _, hi = opts.capacity_overrides[it]
            cap_hi[k] = hi
        elif env.domestic.is_unknown():
            # C2: UNKNOWN capacity never becomes supply. With no evidence of domestic
            # production the domestic bound is zero; imports (if eligible) may serve,
            # otherwise the item becomes a blocking unknown in solve_objective.
            unknown_flags.append(it)
            cap_hi[k] = 0.0
        else:
            use = env.domestic.hi if opts.assume_capacity_hi else env.domestic.lo
            cap_hi[k] = use or 0.0
        cut = opts.competing_demand_cuts.get(it, 0.0)
        if cut > 0 and np.isfinite(cap_hi[k]):
            pool_base = 0.0
            for e2 in w.entities.values():
                if getattr(e2, "kind", "") == "demand_pool" and getattr(e2, "resource_id", "") == it:
                    from .units import annual_scalar as _as
                    base = getattr(e2, "baseline_annual", None)
                    cf = float(getattr(e2, "contestable_fraction", 0.15))
                    if base is not None:
                        pool_base = _as(base) * cf
            if pool_base > 0:
                cap_hi[k] *= max(pool_base - cut, 0.0) / pool_base
        imp_frac[k] = min(imp_frac[k], env.import_eligible_fraction)

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
        import_share_cap = max(1.0 - opts.min_domestic_share, 0.0)
        bounds[n + k] = (0.0, demand[k] * imp_frac[k] * import_share_cap)
        bounds[2 * n + k] = (0.0, demand[k])

    A_ub = np.vstack(A_ub_rows) if A_ub_rows else None
    b_ub = np.array(b_ub_vals) if b_ub_vals else None
    res = linprog(
        c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs"
    )
    if not res.success:
        yr.total_shortfall = float("inf")
        yr.binding_constraints.append("LP failed: " + str(res.message))
        return yr

    x = res.x
    tol = max(1e-6, 1e-9 * max(float(demand.max()), 1.0))
    for k, it in enumerate(items):
        dom_u, imp_u, short = float(x[k]), float(x[n + k]), float(x[2 * n + k])
        env = envelopes[it]
        gap = ItemGap(
            item_id=it,
            year=year,
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
        yr.total_shortfall += short
        cd, ci = _unit_cost(opts, it)
        yr.import_value_usd += imp_u * ci
        yr.domestic_value_usd += dom_u * cd

    try:
        ineq_marginals = res.ineqlin.marginals if res.ineqlin is not None else []
    except AttributeError:
        ineq_marginals = []
    for idx, name in enumerate(ub_names):
        if idx < len(ineq_marginals) and abs(ineq_marginals[idx]) > 1e-6:
            yr.binding_constraints.append(name)

    yr.shortfalls.sort(key=lambda g: -g.shortfall)
    return yr


def collect_unproven_funded(w: World, funded: Set[str]) -> List[str]:
    out = []
    for e in w.entities.values():
        if isinstance(e, Project) and e.id in funded and not _is_operating(e):
            out.append(e.id)
    return out


def solve_objective(
    w: World,
    pg: ProofGraph,
    explosion: ExplosionResult,
    years: Sequence[int],
    opts: ScenarioOptions,
) -> SolveResult:
    """Multi-year feasibility classification per MODEL_CONTRACT C16."""
    blocking: List[str] = []
    conditional: List[str] = []
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

    unproven_funded = collect_unproven_funded(w, opts.funded_project_ids or set())
    if unproven_funded and opts.count_unproven_projects:
        conditional.append(
            "verdict counts unproven projects before qualification: "
            + ", ".join(sorted(unproven_funded))
        )
    if opts.capacity_overrides:
        conditional.append(
            "analyst capacity assumptions applied for: " + ", ".join(sorted(opts.capacity_overrides))
        )

    results: Dict[int, YearResult] = {}
    for year in probe_years:
        results[year] = solve_year(w, pg, explosion, year, opts)

    sr = _classify(results, blocking, conditional, adjudicable)
    sr.proof_root = pg.output(
        [],
        f"Solve {explosion.variant_id}: {sr.result_class.value}",
        {
            "result_class": sr.result_class.value,
            "worst_shortfall_item": sr.max_shortfall_item,
            "worst_year": sr.max_shortfall_year,
            "binding": sr.binding_summary,
        },
    )
    return sr


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
        v = yr.total_shortfall
        if v == float("inf"):
            v = float("inf")
        if v > worst_val:
            worst_val, worst_item, worst_year = (
                v,
                (yr.shortfalls[0].item_id if yr.shortfalls else ""),
                y,
            )
        for bc in yr.binding_constraints:
            if bc not in sr.binding_summary:
                sr.binding_summary.append(bc)

    sr.max_shortfall_item = worst_item
    sr.max_shortfall_year = worst_year

    if not adjudicable:
        sr.result_class = ResultClass.NOT_ADJUDICABLE
        return sr

    if worst_val > 0:
        sr.result_class = ResultClass.INFEASIBLE_UNDER_MODEL
        for y, yr in sorted(results.items()):
            for g in yr.shortfalls:
                relax = f"{g.item_id}@{y}: need {g.shortfall:,.0f} more qualified units/yr"
                if relax not in sr.required_relaxations:
                    sr.required_relaxations.append(relax)
                if g.unknown:
                    cand = f"RESEARCH {g.item_id}: capacity UNKNOWN — audit suppliers/yields"
                else:
                    cand = f"BUILD/QUALIFY {g.item_id}: add {g.shortfall:,.0f}/yr before {y}"
                if cand not in sr.closure_candidates:
                    sr.closure_candidates.append(cand)
        return sr

    if sr.conditional_reasons:
        sr.result_class = ResultClass.CONDITIONALLY_FEASIBLE
    else:
        sr.result_class = ResultClass.FEASIBLE
    return sr
