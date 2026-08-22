from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import Dict, List, Optional, Sequence, Set, Tuple

from .evidence import ProofGraph
from .epistemics import ResultClass
from .explode import ExplosionResult
from .model import Project, ProjectState, World
from .shocks import apply_shocks
from .solve import ScenarioOptions, SolveResult, solve_objective
from .substitutions import apply_substitution


@dataclass
class Action:
    action_id: str
    kind: str  # FUND_PROJECT | SUBSTITUTE | QUALIFY | STOCKPILE | RESEARCH
    label: str
    capex_usd: float = 0.0
    lead_time_years: Tuple[float, float] = (0.0, 0.0)
    effect_projects: Set[str] = field(default_factory=set)
    effect_substitution: Optional[str] = None
    resolves_unknown: Optional[str] = None
    evidence_ids: Tuple[str, ...] = ()
    rationale: str = ""

    def to_json(self) -> Dict:
        return dict(
            action_id=self.action_id, kind=self.kind, label=self.label,
            capex_usd=self.capex_usd,
            lead_time_years=list(self.lead_time_years),
            effect_projects=sorted(self.effect_projects),
            effect_substitution=self.effect_substitution,
            resolves_unknown=self.resolves_unknown,
            rationale=self.rationale,
        )


@dataclass
class TransformationPlan:
    actions: List[Action]
    total_capex_usd: float
    verified_result_class: ResultClass
    remaining_shortfall: float
    timeline: List[Dict] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_json(self) -> Dict:
        return dict(
            actions=[a.to_json() for a in self.actions],
            total_capex_usd=self.total_capex_usd,
            verified_result_class=self.verified_result_class.value,
            remaining_shortfall=self.remaining_shortfall,
            timeline=self.timeline,
            notes=self.notes,
        )


def candidate_actions(
    w: World,
    pg: ProofGraph,
    base_opts: ScenarioOptions,
    sr: SolveResult,
    explosion: ExplosionResult,
    years: Sequence[int],
    sub_contracts: Optional[Dict[str, Dict]] = None,
) -> List[Action]:
    actions: List[Action] = []
    shortfall_items = {
        g.item_id for y in years for g in (sr.years.get(y).shortfalls if sr.years.get(y) else [])
    }

    for prj in sorted(w.entities.values(), key=lambda p: p.id):
        if not isinstance(prj, Project):
            continue
        if prj.id in base_opts.funded_project_ids:
            continue
        if prj.item_id not in shortfall_items:
            continue
        capex = 0.0
        if prj.capex is not None:
            capex = prj.capex.value if prj.capex.unit == "USD" else prj.capex.to("MUSD").value * 1e6
        actions.append(Action(
            action_id=f"fund:{prj.id}",
            kind="FUND_PROJECT",
            label=f"Fund {prj.name} ({prj.item_id})",
            capex_usd=capex,
            lead_time_years=prj.years_to_commission,
            effect_projects={prj.id},
            evidence_ids=prj.evidence_ids,
            rationale=f"adds qualified capacity for {prj.item_id}; current state={prj.state.value}",
        ))

    for sid, contract in sorted((sub_contracts or {}).items()):
        replaced = str(contract.get("replaces_part", ""))
        if replaced in shortfall_items or any(
            replaced in c.get("resolves", "") for c in [{}]
        ):
            tm = contract.get("transition_months", [12, 24])
            actions.append(Action(
                action_id=f"sub:{sid}",
                kind="SUBSTITUTE",
                label=f"Substitute {replaced} via {sid}",
                lead_time_years=(float(tm[0]) / 12.0, float(tm[1]) / 12.0),
                effect_substitution=sid,
                rationale=str(contract.get("notes", "validated alternative architecture")),
            ))

    for item in sorted(shortfall_items):
        ent = w.entities.get(item)
        if ent is None:
            continue
        has_unqualified_segments = any(
            getattr(s, "item_id", "") == item and getattr(s, "qualification_fraction", 1.0) < 1.0
            and getattr(s, "geography", "") in ("INDIA", "GLOBAL")
            for s in w.entities.values()
            if getattr(s, "kind", "") == "capacity_segment"
        )
        if has_unqualified_segments:
            actions.append(Action(
                action_id=f"qualify:{item}",
                kind="QUALIFY",
                label=f"Supplier-qualification programme: {item}",
                capex_usd=2e7,
                lead_time_years=(1.0, 2.0),
                resolves_unknown=item,
                rationale="turn adjacent installed capacity into qualified usable capacity",
            ))
        if getattr(ent, "kind", "") in ("part", "resource_class"):
            actions.append(Action(
                action_id=f"research:{item}",
                kind="RESEARCH",
                label=f"Audit suppliers/yields for {item}",
                capex_usd=5e6,
                lead_time_years=(0.25, 0.75),
                resolves_unknown=item,
                rationale="resolve decision-critical UNKNOWN before irreversible investment",
            ))

    return actions


class PlanEngine:
    """Synthesizes and verifies transformation portfolios against the same solver."""

    def __init__(
        self,
        world: World,
        pg: ProofGraph,
        explosion_builder,
        variant_id: str,
        annual_units: float,
        years: Sequence[int],
        base_opts: ScenarioOptions,
        shock_ids: Optional[List[str]] = None,
    ):
        self.world = world
        self.pg = pg
        self.explosion_builder = explosion_builder
        self.variant_id = variant_id
        self.annual_units = annual_units
        self.years = list(years)
        self.base_opts = base_opts
        self.shock_ids = shock_ids or []

    def evaluate(self, opts: ScenarioOptions, active_substitutions: List[str]) -> SolveResult:
        w = self.world
        ex = self.explosion_builder(w, self.pg, self.variant_id, self.annual_units)
        for sid in active_substitutions:
            contract = self._contract(sid)
            if contract is not None:
                ex = apply_substitution(w, self.pg, ex, contract)
        if self.shock_ids:
            w2, o2, rep = apply_shocks(w, self.pg, self.shock_ids, opts)
            return solve_objective(w2, self.pg, ex, self.years, o2)
        return solve_objective(w, self.pg, ex, self.years, opts)

    def _contract(self, sub_id: str) -> Optional[Dict]:
        contracts = getattr(self, "_sub_contracts", {}) or {}
        return contracts.get(sub_id)

    def set_substitution_contracts(self, contracts: Dict[str, Dict]):
        self._sub_contracts = contracts

    def baseline(self) -> SolveResult:
        return self.evaluate(self.base_opts, [])

    def with_actions(
        self, actions: Sequence[Action], active_substitutions: Optional[List[str]] = None
    ) -> Tuple[SolveResult, ScenarioOptions]:
        opts = ScenarioOptions(
            import_eligibility=dict(self.base_opts.import_eligibility),
            funded_project_ids=set(self.base_opts.funded_project_ids),
            capacity_overrides=dict(self.base_opts.capacity_overrides),
            cost_domestic=dict(self.base_opts.cost_domestic),
            cost_import=dict(self.base_opts.cost_import),
            assume_capacity_hi=self.base_opts.assume_capacity_hi,
            count_unproven_projects=self.base_opts.count_unproven_projects,
            equipment_hour_limits=dict(self.base_opts.equipment_hour_limits),
            equipment_hours_per_unit={
                k: dict(v) for k, v in self.base_opts.equipment_hours_per_unit.items()
            },
            geography=self.base_opts.geography,
            min_domestic_share=self.base_opts.min_domestic_share,
            per_item_import_cap=dict(self.base_opts.per_item_import_cap),
            qualification_boosts=set(self.base_opts.qualification_boosts),
            competing_demand_cuts=dict(self.base_opts.competing_demand_cuts),
            enforce_dva=self.base_opts.enforce_dva,
            # N4/N6: preserve the base pipeline mode across clones.
            funded_pipeline=self.base_opts.funded_pipeline,
        )
        subs = list(active_substitutions or [])
        fund_added: Set[str] = set()
        for a in actions:
            opts.funded_project_ids |= a.effect_projects
            if a.action_id.startswith("fund:") or a.kind == "FUND_PROJECT":
                pid = a.action_id.split(":", 1)[1] if ":" in a.action_id else None
                for pid2 in ({pid} if pid else set()) | a.effect_projects:
                    if pid2:
                        opts.funded_project_ids.add(pid2)
                        fund_added.add(pid2)
            if a.kind == "SUBSTITUTE" and a.effect_substitution:
                subs.append(a.effect_substitution)
            if a.kind == "QUALIFY" and a.resolves_unknown:
                opts.qualification_boosts.add(a.resolves_unknown)
        # N6: FUND actions must be numerically meaningful. Under the optimistic
        # pipeline every evidenced project already counts, so adding an id is a
        # no-op; a plan that funds projects therefore evaluates the
        # selected-only pipeline containing exactly the chosen portfolio.
        if fund_added and opts.funded_pipeline == "optimistic":
            opts.funded_pipeline = "selected_only"
        sr = self.evaluate(opts, subs)
        return sr, opts

    def search_portfolio(
        self,
        actions: Sequence[Action],
        budget_usd: Optional[float] = None,
        max_actions: int = 8,
    ) -> TransformationPlan:
        """Greedy coverage search + verification; exact enumeration when tractable.

        Objective: eliminate shortfall; secondary: minimize capex. Every candidate
        portfolio is re-verified through the real solver — no scripted outcomes.
        """
        base_sr = self.baseline()
        if base_sr.result_class == ResultClass.FEASIBLE:
            return TransformationPlan([], 0.0, base_sr.result_class, 0.0,
                                      notes=["Already feasible without transformation."])

        pool = [a for a in actions if a.kind != "RESEARCH"]
        chosen: List[Action] = []
        best_plan = None

        if len(pool) <= max_actions and len(pool) > 0:
            best_key, best_combo = None, []
            for r in range(1, len(pool) + 1):
                for combo in combinations(pool, r):
                    capex = sum(a.capex_usd for a in combo)
                    if budget_usd is not None and capex > budget_usd:
                        continue
                    sr, _ = self.with_actions(combo)
                    key = (
                        0 if sr.result_class in (ResultClass.FEASIBLE, ResultClass.CONDITIONALLY_FEASIBLE) else 1,
                        round(sr.years[sr.worst_year()].total_shortfall if sr.worst_year() is not None and sr.years else 0.0, 3),
                        capex,
                    )
                    if best_key is None or key < best_key:
                        best_key, best_combo = key, list(combo)
                    if key[0] == 0 and (budget_usd is None or capex <= (budget_usd or 0)):
                        break
                else:
                    continue
                if best_key is not None and best_key[0] == 0:
                    break
            chosen = best_combo
        elif pool:
            remaining = list(pool)
            while remaining and len(chosen) < max_actions:
                scored = []
                for a in remaining:
                    trial = chosen + [a]
                    capex = sum(x.capex_usd for x in trial)
                    if budget_usd is not None and capex > budget_usd:
                        continue
                    sr, _ = self.with_actions(trial)
                    short = sr.years[sr.worst_year()].total_shortfall if sr.worst_year() is not None and sr.years else 0.0
                    scored.append((short, capex, a))
                if not scored:
                    break
                scored.sort(key=lambda t: (round(t[0], 3), t[1]))
                best = scored[0]
                chosen.append(best[2])
                remaining.remove(best[2])
                if best[0] <= 0:
                    break

        sr, _ = self.with_actions(chosen)
        total_capex = sum(a.capex_usd for a in chosen)
        timeline = self._sequence(chosen)
        plan = TransformationPlan(
            actions=chosen,
            total_capex_usd=total_capex,
            verified_result_class=sr.result_class,
            remaining_shortfall=(sr.years[sr.worst_year()].total_shortfall if sr.worst_year() is not None and sr.years else 0.0),
            timeline=timeline,
        )
        if sr.result_class not in (ResultClass.FEASIBLE, ResultClass.CONDITIONALLY_FEASIBLE):
            plan.notes.append(
                "Portfolio does not fully close under model; see remaining shortfall and "
                "value-of-information panel."
            )
        self.pg.derive(
            [],
            f"Transformation portfolio: {len(chosen)} actions, capex ${total_capex/1e6:,.0f}M "
            f"-> {sr.result_class.value}",
            {"actions": [a.action_id for a in chosen]},
        )
        best_plan = plan
        return best_plan

    def _sequence(self, actions: Sequence[Action]) -> List[Dict]:
        rows = []
        for a in actions:
            start = min(self.years) if self.years else 2026
            lo, hi = a.lead_time_years
            rows.append({
                "action": a.label,
                "kind": a.kind,
                "start_year": start,
                "online_earliest": int(start + lo),
                "online_latest": int(start + hi),
                "capex_musd": round(a.capex_usd / 1e6, 1),
            })
        rows.sort(key=lambda r: (r["online_earliest"], -r["capex_musd"]))
        return rows
