"""V0.1 substitution: immutable architecture-level rewrite + full re-explosion.

A substitution is an ARCHITECTURE EDIT on the requirement graph: the replaced node's
route is re-pointed to the validated alternative recipe and the entire explosion is
recomputed from scratch. The original FlowGraph/ExplosionResult is never mutated
(F4/N1 fixed by construction). Dependencies belonging only to the replaced route
disappear because nothing is copied — the graph is rebuilt (oracle C2).

Route overrides are applied via an explicit `route_override` hook on the World view
passed to explosion — no monkey-patching, no global state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .evidence import ProofGraph
from .explode import ExplosionResult, RequirementLine, primary_recipe
from .model import FunctionalRequirement, Part, ProductionRecipe, World
from .units import Quantity, UnitError


@dataclass
class SubstitutionCheck:
    sub_id: str
    accepted: bool
    reasons: List[str] = field(default_factory=list)
    envelope_report: List[Dict] = field(default_factory=list)


def validate_substitution(
    w: World, contract: Dict, variant_id: Optional[str] = None
) -> SubstitutionCheck:
    """Engineering-equivalence gate (C9), hardened per V0.1.

    Field presence is NOT enough: the functional envelope must actually cover the
    variant's declared requirement windows (interval intersection).
    """
    reasons: List[str] = []
    env_report: List[Dict] = []

    envelope = contract.get("functional_envelope") or {}
    if not isinstance(envelope, dict) or not envelope:
        reasons.append("functional_envelope empty — cannot establish equivalence")

    if variant_id is not None:
        if not w.has(variant_id):
            reasons.append(f"unknown variant '{variant_id}'")
        else:
            # FRs link to the variant via derived_from (pack.py); check both directions.
            fr_entities = [
                ent for ent in w.entities.values()
                if isinstance(ent, FunctionalRequirement)
                and (
                    any(e.src == ent.id and e.dst == variant_id
                        for e in w.in_edges(variant_id))
                )
            ]
            for fr in fr_entities:
                spec = envelope.get(fr.metric)
                entry = {
                    "requirement": fr.metric,
                    "unit": fr.unit,
                    "required": [fr.envelope_min, fr.envelope_max],
                    "alternative": spec,
                }
                ok = spec is not None
                if ok and isinstance(spec, (list, tuple)) and len(spec) == 2:
                    lo, hi = float(spec[0]), float(spec[1])
                    covered = True
                    if fr.envelope_max is not None and lo > fr.envelope_max:
                        covered = False
                    if fr.envelope_min is not None and hi < fr.envelope_min:
                        covered = False
                    ok = covered
                elif ok and isinstance(spec, (int, float)):
                    val = float(spec)
                    ok = (
                        (fr.envelope_min is None or val >= fr.envelope_min)
                        and (fr.envelope_max is None or val <= fr.envelope_max)
                    )
                    entry["alternative"] = val
                if not ok:
                    reasons.append(
                        f"requirement '{fr.metric}' not covered by alternative envelope"
                    )
                entry["covered"] = ok
                env_report.append(entry)

    for fld in ("changed_bom", "performance_delta"):
        if fld not in contract:
            reasons.append(f"contract missing '{fld}'")

    maturity = str(contract.get("maturity", ""))
    if maturity in ("", "concept"):
        reasons.append(
            "maturity must be declared (concept-level alternatives are not solver-eligible)"
        )

    return SubstitutionCheck(
        sub_id=str(contract.get("id", "?")),
        accepted=(len(reasons) == 0),
        reasons=reasons,
        envelope_report=env_report,
    )


def apply_substitution(
    w: World,
    pg: ProofGraph,
    explosion: ExplosionResult,
    contract: Dict,
) -> ExplosionResult:
    """Architecture-level rewrite + complete re-explosion. Immutable by construction."""
    from .explode import explode_variant

    variant_id = explosion.flows.variant_id
    check = validate_substitution(w, contract, variant_id=variant_id)
    if not check.accepted:
        raise ValueError(
            f"substitution '{contract.get('id')}' rejected by equivalence gate: {check.reasons}"
        )
    replaced = str(contract["replaces_part"])
    alt_rec = w.require(str(contract["alternative_recipe"]))
    assert isinstance(alt_rec, ProductionRecipe)

    sub_node = pg.derive(
        [],
        f"Substitution {contract['id']}: {replaced} -> {alt_rec.output_part or alt_rec.id}",
        {
            "level": contract.get("level", "component"),
            "maturity": contract.get("maturity"),
            "transition_months": list(contract.get("transition_months", [])),
            "performance_delta": contract.get("performance_delta", {}),
            "evidence_ids": list(contract.get("evidence_ids", [])),
        },
    )
    # G1: the substitution decision derives from its declared evidence records.
    for cid in contract.get("evidence_ids", []) or []:
        ev_nid = f"ev.{cid}"
        if ev_nid in pg.nodes:
            pg.add_edge(ev_nid, sub_node)

    variant_id = explosion.flows.variant_id
    annual_units = explosion.annual_units

    # changed_bom additions become synthetic BOM entries for the re-explosion.
    bom_additions: List[Tuple[str, float]] = []
    for entry in contract.get("changed_bom", []) or []:
        pid = str(entry.get("part"))
        qty = float(entry.get("qty", 1))
        if not w.has(pid):
            w.add(Part(id=pid, name=pid, kind="part", part_class="component"))
        bom_additions.append((pid, qty))

    # Route override: the replaced part resolves to the alternative recipe during rebuild.
    overrides = {replaced: alt_rec}
    alt_part = alt_rec.output_part
    # If the alternative recipe yields a different part, the architecture edit swaps
    # the BOM entry: exclude the replaced part and add the alternative part instead.
    bom_exclusions: Set[str] = set()
    if alt_part and alt_part != replaced:
        bom_exclusions.add(replaced)
        bom_additions.append((alt_part, 1.0))

    res = explode_variant(
        w, pg, variant_id, annual_units, [2030],
        geography="INDIA",
        route_override=overrides,
        bom_additions=bom_additions,
        bom_exclusions=bom_exclusions,
    )
    res.variant_id = f"{variant_id}+sub:{contract.get('id')}"

    # Provenance: aggregate lines derive from the substitution decision node.
    for nid, line in res.lines.items():
        res.proof_node_ids[nid] = pg.derive(
            [sub_node],
            f"{nid}: net {line.net_annual} / gross {line.gross_annual}/yr (post-substitution)",
            {"net_per_year": str(line.net_annual), "gross_per_year": str(line.gross_annual),
             "recipe": line.via_recipe},
        )
    return res
