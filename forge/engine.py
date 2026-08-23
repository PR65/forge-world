from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .capacity import CapacityEnvelope, capacity_envelope
from .dva import DVABreakdown, dva_fraction
from .evidence import ProofGraph
from .epistemics import ResultClass
from .explode import ExplosionResult, explode_variant, check_mass_balance
from .frontier import FrontierPoint, closure_frontier
from .model import Project, World
from .optionvalue import (
    CapabilityInvestment,
    ObjectiveSpec,
    option_value_portfolio,
    reverse_buildability,
)
from .pack import KnowledgePack
from .planner import Action, PlanEngine, TransformationPlan, candidate_actions
from .recursion import expand_recursion
from .run import ModelRun
from .shocks import apply_shocks
from .solve import ScenarioOptions, SolveResult, solve_objective
from .substitutions import validate_substitution
from .units import Quantity


DEFAULT_YEARS = [2026, 2027, 2028, 2029, 2030]


@dataclass
class ObjectiveSpecInput:
    variant_id: str
    annual_units: float
    geography: str = "INDIA"
    deadline_year: int = 2030
    max_single_country_dependence: float = 1.0
    min_dva: float = 0.70
    budget_usd: Optional[float] = None
    funded_projects: List[str] = field(default_factory=list)
    allowed_substitutions: List[str] = field(default_factory=list)
    analyst_capacity_assumptions: Dict[str, Tuple[float, float]] = field(default_factory=dict)


def _variant_list(pk: KnowledgePack) -> List[Dict]:
    out = []
    for vid, vd in pk.variants.items():
        out.append({
            "id": vid,
            "name": vd.get("name", vid),
            "notes": vd.get("notes", ""),
            "anchor_evidence": vd.get("anchor_evidence", []),
            "mass_kg": vd.get("mass_kg"),
            "battery_kwh": vd.get("battery_kwh"),
        })
    return out


def build_explosion(w: World, pg: ProofGraph, variant_id: str, annual_units: float):
    return explode_variant(w, pg, variant_id, annual_units, DEFAULT_YEARS)


def _envelope_rows(
    w: World, ex: ExplosionResult, years: Sequence[int], opts: ScenarioOptions
) -> List[Dict]:
    rows = []
    for item in ex.items():
        line = ex.get(item)
        env_by_year = {}
        suppliers: Tuple[str, ...] = ()
        hhi = None
        epistemic = "UNKNOWN"
        for y in years:
            env = capacity_envelope(
                w, item, y,
                import_eligibility=opts.import_eligibility,
                funded_project_ids=opts.funded_arg(),
                geography=opts.geography,
            )
            env_by_year[str(y)] = {
                "lo": env.domestic.lo,
                "hi": env.domestic.hi,
                "unknown": env.domestic.is_unknown(),
                "projects_only": env.proven_by_projects_only,
                "epistemic": env.epistemic,
                "reasons": env.unknown_reasons[:2],
            }
            if env.suppliers:
                suppliers = env.suppliers
                hhi = env.concentration_hhi
            epistemic = env.epistemic
        ent = w.entities.get(item)
        rows.append({
            "item": item,
            "kind": getattr(ent, "kind", "?") if ent else "?",
            "demand_annual": line.net_annual.value if line else 0,
            "gross_demand_annual": line.gross_annual.to("pcs").value if line and line.gross_annual.unit == "pcs" else (line.gross_annual.value if line else 0),
            "unit": line.net_annual.unit if line else "pcs",
            "suppliers": list(suppliers),
            "concentration_hhi": hhi,
            "epistemic": epistemic,
            "by_year": env_by_year,
            "proof": ex.proof_node_ids.get(item),
        })
    return rows


def _result_to_json(sr: SolveResult, ex: ExplosionResult) -> Dict:
    return {
        "result_class": sr.result_class.value,
        "blocking_unknowns": sr.blocking_unknowns,
        "conditional_reasons": sr.conditional_reasons,
        "binding_summary": sr.binding_summary,
        "required_relaxations": sr.required_relaxations[:12],
        "closure_candidates": sr.closure_candidates[:12],
        "max_shortfall_item": sr.max_shortfall_item,
        "max_shortfall_year": sr.max_shortfall_year,
        "years": {
            str(y): {
                "total_shortfall": yr.total_shortfall,
                "shortfalls": [
                    {
                        "item": g.item_id, "demand": g.demand,
                        "domestic_used": g.domestic_used, "imports_used": g.imports_used,
                        "shortfall": g.shortfall, "unknown": g.unknown,
                    }
                    for g in yr.shortfalls[:20]
                ],
                "import_value_usd": yr.import_value_usd,
                "domestic_value_usd": yr.domestic_value_usd,
            }
            for y, yr in sorted(sr.years.items())
        },
    }


class ForgeEngine:
    def __init__(self, pack: KnowledgePack):
        self.pk = pack
        self.w = pack.world

    def run_scenario(self, obj: ObjectiveSpecInput, shock_ids: Optional[List[str]] = None,
                     include_deep: bool = True) -> Dict[str, Any]:
        pg = ProofGraph()
        years = [y for y in DEFAULT_YEARS if y <= obj.deadline_year]
        if obj.deadline_year not in years:
            years.append(obj.deadline_year)

        # ---- W4.1: evidence nodes enter the runtime proof graph ----------------
        # Every EvidenceRecord in the pack becomes an evidence node; parameter
        # derivations link to the records behind the entities they consumed
        # (via each entity's evidence_ids). C15 becomes mechanically true.
        evidence_node_ids = {}
        for rec in self.pk.evidence.values():
            evidence_node_ids[rec.claim_id] = pg.evidence_node(rec)

        scenario_node = pg.scenario_node(
            f"Objective: {obj.annual_units:g}/yr {obj.variant_id} in {obj.geography} "
            f"by {obj.deadline_year}, DVA>={obj.min_dva:.0%}",
            {"objective": obj.__dict__ | {"funded_projects": list(obj.funded_projects)},
             "shocks": shock_ids or []},
        )

        opts = ScenarioOptions(
            import_eligibility={},
            funded_project_ids=set(obj.funded_projects),
            capacity_overrides=dict(obj.analyst_capacity_assumptions),
            geography=obj.geography,
            min_domestic_share=obj.min_dva,
            funded_pipeline=("selected_only" if obj.funded_projects else "optimistic"),
        )
        opts_node = pg.derive([scenario_node], "ScenarioOptions assembled",
                              {"geography": obj.geography,
                               "min_domestic_share": obj.min_dva,
                               "funded_pipeline": opts.funded_pipeline})

        ex = explode_variant(self.w, pg, obj.variant_id, obj.annual_units, years)
        mass_warn = check_mass_balance(self.w, ex)

        # Link explosion lines to the evidence behind their recipes/BOM parts.
        for item in ex.items():
            line = ex.lines[item]
            src_ids = []
            ent = self.w.entities.get(item)
            if ent is not None:
                src_ids.extend(getattr(ent, "evidence_ids", ()) or ())
            if line.via_recipe:
                rec_ent = self.w.entities.get(line.via_recipe)
                if rec_ent is not None:
                    src_ids.extend(getattr(rec_ent, "evidence_ids", ()) or ())
            node = ex.proof_node_ids.get(item)
            if node and src_ids:
                for cid in sorted(set(src_ids)):
                    ev_nid = evidence_node_ids.get(cid)
                    if ev_nid:
                        pg.add_edge(ev_nid, node)

        if shock_ids:
            w_eff, opts_eff, shock_report = apply_shocks(self.w, pg, shock_ids, opts)
        else:
            w_eff, opts_eff, shock_report = self.w, opts, None

        sr = solve_objective(w_eff, pg, ex, years, opts_eff)

        dva = dva_fraction(
            w_eff, pg, ex, opts_eff,
            allocations_by_year={y: yr.allocations for y, yr in sr.years.items()},
            decision_year=obj.deadline_year,
        )

        def _plan_explosion(ww, pgg, v, u):
            exx = explode_variant(ww, pgg, v, u, years)
            # G1: plan re-explosion line nodes link to pack evidence + scenario node,
            # so planner/portfolio verdicts remain evidence-connected (no new roots).
            for item in exx.items():
                node = exx.proof_node_ids.get(item)
                if not node:
                    continue
                pg.add_edge(opts_node, node)
                src_ids = []
                ent = ww.entities.get(item)
                if ent is not None:
                    src_ids.extend(getattr(ent, "evidence_ids", ()) or ())
                via = exx.lines[item].via_recipe if exx.get(item) else ""
                if via:
                    rec_ent = ww.entities.get(via)
                    if rec_ent is not None:
                        src_ids.extend(getattr(rec_ent, "evidence_ids", ()) or ())
                for cid in sorted(set(src_ids)):
                    ev_nid = evidence_node_ids.get(cid)
                    if ev_nid:
                        pg.add_edge(ev_nid, node)
            return exx

        plan_engine = PlanEngine(
            w_eff, pg, _plan_explosion,
            obj.variant_id, obj.annual_units, years, opts_eff, shock_ids=None,
            provenance_root=opts_node,
        )
        plan_engine.set_substitution_contracts(self.pk.substitutions)

        base_for_plan_sr = sr
        actions = candidate_actions(
            self.w, pg, opts_eff, base_for_plan_sr, ex, years,
            sub_contracts=self.pk.substitutions,
        )
        plan = plan_engine.search_portfolio(actions, budget_usd=obj.budget_usd)

        unknown_items = sorted(
            set(sr.blocking_unknowns)
            | {
                it
                for it in ex.items()
                if capacity_envelope(self.w, it, min(years), geography=obj.geography).domestic.is_unknown()
            }
        )

        def eval_with(overrides: Dict[str, Tuple[float, float]]) -> SolveResult:
            o2 = ScenarioOptions(
                funded_project_ids=set(opts_eff.funded_project_ids),
                capacity_overrides={**opts_eff.capacity_overrides, **overrides},
                geography=opts_eff.geography,
                min_domestic_share=opts_eff.min_domestic_share,
                qualification_boosts=set(opts_eff.qualification_boosts),
            )
            return solve_objective(w_eff, pg, ex, years, o2)

        voi_tasks = []
        if unknown_items:
            from .voi import value_of_information
            bounds_by_item = {}
            for it in unknown_items:
                line = ex.get(it)
                hi = (line.gross_annual.value * 1.5) if line else 1e9
                bounds_by_item[it] = (0.0, hi)
            voi_tasks = value_of_information(
                unknown_items, eval_with, bounds_by_item=bounds_by_item
            )

        frontier_points: List[FrontierPoint] = []
        reverse_result: Optional[Tuple[int, str]] = None

        if include_deep:
            def eval_dva(theta: float) -> SolveResult:
                o2 = ScenarioOptions(
                    funded_project_ids=set(opts_eff.funded_project_ids),
                    capacity_overrides=dict(opts_eff.capacity_overrides),
                    geography=opts_eff.geography,
                    min_domestic_share=theta,
                )
                return solve_objective(w_eff, pg, ex, years, o2)

            frontier_points = closure_frontier([0.0, 0.5, 0.7, 0.85, 0.95], evaluate_at=eval_dva)
            reverse_result = reverse_buildability(
                [250000, 500000, 750000, 1000000],
                lambda v: self._reverse_eval(v, obj, shock_ids, min_domestic_share=0.0),
            )
            reverse_localized = reverse_buildability(
                [250000, 500000, 750000, 1000000],
                lambda v: self._reverse_eval(
                    v, obj, shock_ids, min_domestic_share=obj.min_dva
                ),
            )

        run = ModelRun.create(
            pack_id=self.pk.pack_id,
            pack_version=self.pk.version,
            objective={
                "variant": obj.variant_id,
                "annual_units": obj.annual_units,
                "geography": obj.geography,
                "deadline_year": obj.deadline_year,
                "min_dva": obj.min_dva,
                "budget_usd": obj.budget_usd,
            },
            scenario={"shocks": shock_ids or [], "funded_projects": obj.funded_projects},
            data_snapshot_payload=self.pk.summary(),
            assumptions=sorted(set(dva.assumptions_used)),
            world=self.w,                       # FULL snapshot hash (F21/G3)
            scenario_opts=opts_eff,
        )
        # W0.3/G3-4: outputs recorded on the run (finish() semantics made real).
        run.finish(
            {
                "result_class": sr.result_class.value,
                "worst_year": sr.max_shortfall_year,
                "dva_fraction": dva.fraction,
                "dva_certificate": sr.dva_certificate,
                "plan_actions": [a.action_id for a in plan.actions],
            },
            warnings=list(mass_warn) + [
                f"explosion note: {w}" for w in ex.flows.warnings
            ],
        )

        response: Dict[str, Any] = {
            "run": run.to_json(),
            "pack": self.pk.summary(),
            "variants": _variant_list(self.pk),
            "selected_variant": obj.variant_id,
            "annual_units": obj.annual_units,
            "years": years,
            "explosion": {
                "items": [
                    {
                        "item": i,
                        "net": ex.lines[i].net_annual.value,
                        "gross": ex.lines[i].gross_annual.value,
                        "unit": ex.lines[i].net_annual.unit,
                        "depth": ex.lines[i].depth,
                        "recipe": ex.lines[i].via_recipe,
                    }
                    for i in ex.items()
                ],
                "mass_balance_warnings": mass_warn,
            },
            "capacity_envelopes": _envelope_rows(self.w, ex, years, opts_eff),
            "result": _result_to_json(sr, ex),
            "dva": {
                "fraction": dva.fraction,
                "total_cost_usd": dva.total_cost_usd,
                "imported_cost_usd": dva.imported_cost_usd,
                "assumptions": dva.assumptions_used,
                "per_item_top": dict(list(sorted(dva.per_item.items()))[:24]),
                "certificate": sr.dva_certificate,
            },
            "actions": [a.to_json() for a in actions],
            "plan": plan.to_json(),
            "voi": [t.to_json() for t in voi_tasks],
            "shock_report": {
                "applied": shock_report.applied_edits if shock_report else [],
                "rejected": shock_report.rejected_edits if shock_report else [],
            },
            "frontier": [p.to_json() for p in frontier_points],
            "reverse": (
                {
                    "max_units_per_year": reverse_result[0],
                    "class_at_max": reverse_result[1],
                    "max_units_localized_at_dva": reverse_localized[0],
                    "class_localized": reverse_localized[1],
                    "dva_reference": obj.min_dva,
                }
                if reverse_result
                else None
            ),
            "proof_graph": pg.to_json(),
            "crosswalks": self.pk.crosswalks,
        }
        return response

    def _reverse_eval(self, volume: int, obj: ObjectiveSpecInput, shock_ids: Optional[List[str]],
                      min_domestic_share: float = 0.0):
        pg2 = ProofGraph()
        years = [2026, 2028, 2030]
        opts = ScenarioOptions(
            funded_project_ids=set(obj.funded_projects),
            min_domestic_share=min_domestic_share,
            funded_pipeline=("selected_only" if obj.funded_projects else "optimistic"),
        )
        ex = explode_variant(self.w, pg2, obj.variant_id, volume, years)
        w2, o2, _ = (
            apply_shocks(self.w, pg2, shock_ids, opts) if shock_ids else (self.w, opts, None)
        )
        return solve_objective(w2, pg2, ex, years, o2)
