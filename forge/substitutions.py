from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .evidence import ProofGraph
from .explode import ExplosionResult, RequirementLine
from .model import FunctionalRequirement, Part, ProductionRecipe, World
from .units import Quantity


@dataclass
class SubstitutionCheck:
    sub_id: str
    accepted: bool
    reasons: List[str] = field(default_factory=list)
    envelope_report: List[Dict] = field(default_factory=list)


def validate_substitution(
    w: World, contract: Dict, variant_id: Optional[str] = None
) -> SubstitutionCheck:
    """Engineering-equivalence gate (MODEL_CONTRACT C9).

    A substitution may enter the solver only with a complete contract: functional
    envelope coverage of the variant's requirements, declared BOM/BOP changes,
    maturity/transition facts, and evidence.
    """
    reasons: List[str] = []
    env_report: List[Dict] = []

    envelope = contract.get("functional_envelope") or {}
    if not isinstance(envelope, dict) or not envelope:
        reasons.append("functional_envelope empty — cannot establish equivalence")

    if variant_id is not None:
        v = w.get(variant_id)
        for e in w.out_edges(variant_id):
            fr = w.entities.get(e.dst)
            if isinstance(fr, FunctionalRequirement):
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
                    if fr.envelope_min is not None and hi < fr.envelope_min:
                        ok = False
                    if fr.envelope_max is not None and lo > fr.envelope_max:
                        ok = False
                elif ok and isinstance(spec, (int, float)):
                    val = float(spec)
                    ok = (
                        (fr.envelope_min is None or val >= fr.envelope_min)
                        and (fr.envelope_max is None or val <= fr.envelope_max)
                    )
                    entry["alternative"] = val
                if not ok:
                    reasons.append(f"requirement '{fr.metric}' not covered by alternative envelope")
                entry["covered"] = ok
                env_report.append(entry)

    for fld in ("changed_bom", "performance_delta"):
        if fld not in contract:
            reasons.append(f"contract missing '{fld}'")

    maturity = str(contract.get("maturity", ""))
    if maturity in ("", "concept"):
        reasons.append("maturity must be declared (concept-level alternatives are not solver-eligible)")

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
    """Rewrite requirements per a validated substitution contract.

    Removes/reduces the replaced part line; adds the alternative recipe's input lines
    plus any changed_bom additions. Returns a NEW ExplosionResult (original untouched).
    """
    check = validate_substitution(w, contract)
    if not check.accepted:
        raise ValueError(
            f"substitution '{contract.get('id')}' rejected by equivalence gate: {check.reasons}"
        )
    replaced = str(contract["replaces_part"])
    alt_rec = w.require(str(contract["alternative_recipe"]))
    assert isinstance(alt_rec, ProductionRecipe)

    new_lines: Dict[str, RequirementLine] = dict(explosion.lines)
    new_proof = dict(explosion.proof_node_ids)

    removed_line = new_lines.pop(replaced, None)
    sub_node = pg.derive(
        [],
        f"Substitution {contract['id']}: {replaced} -> {alt_rec.output_part or alt_rec.id}",
        {
            "level": contract.get("level", "component"),
            "maturity": contract.get("maturity"),
            "transition_months": list(contract.get("transition_months", [])),
            "performance_delta": contract.get("performance_delta", {}),
        },
    )

    if alt_rec.output_part and alt_rec.output_part != replaced:
        qty_ratio = 1.0
        existing = new_lines.get(alt_rec.output_part)
        add = RequirementLine(
            item_id=alt_rec.output_part,
            kind="part",
            net_annual=Quantity(qty_ratio * (explosion.annual_units), "pcs"),
            gross_annual=Quantity(qty_ratio * (explosion.annual_units), "pcs"),
            depth=2,
            via_recipe=alt_rec.id,
        )
        if existing is not None:
            add.net_annual = existing.net_annual + add.net_annual
            add.gross_annual = existing.gross_annual + add.gross_annual
        new_lines[alt_rec.output_part] = add
        new_proof[alt_rec.output_part] = pg.derive(
            [sub_node],
            f"{alt_rec.output_part}: {add.net_annual}/yr (substituted assembly)",
            {"net_per_year": str(add.net_annual)},
        )

    scale = (removed_line.gross_annual.value if removed_line else explosion.annual_units) / (
        alt_rec.output_quantity.value or 1.0
    )
    for iname, iq in alt_rec.inputs:
        need = Quantity(iq.value * scale, iq.unit)
        existing = new_lines.get(iname)
        if existing is not None:
            existing.net_annual = existing.net_annual + need
            existing.gross_annual = existing.gross_annual + need
        else:
            new_lines[iname] = RequirementLine(
                item_id=iname,
                kind="material_or_resource",
                net_annual=need,
                gross_annual=need,
                depth=3,
            )
        new_proof[iname] = pg.derive(
            [sub_node],
            f"{iname}: {new_lines[iname].net_annual}/yr (substitution input)",
            {"net_per_year": str(new_lines[iname].net_annual)},
        )

    for entry in contract.get("changed_bom", []) or []:
        pid = str(entry.get("part"))
        q = float(entry.get("qty", 1))
        need = Quantity(q * explosion.annual_units, "pcs")
        existing = new_lines.get(pid)
        if existing is not None:
            if existing.net_annual.dim == need.dim:
                existing.net_annual = existing.net_annual + need
                existing.gross_annual = existing.gross_annual + need
            else:
                pg.add_node(
                    "derived",
                    f"substitution {contract.get('id')}: changed_bom '{pid}' unit mismatch "
                    f"({need.unit} vs {existing.net_annual.unit}); added as separate line",
                )
                new_lines[f"{pid}@{contract.get('id')}"] = RequirementLine(
                    item_id=f"{pid}@{contract.get('id')}",
                    kind="part",
                    net_annual=need,
                    gross_annual=need,
                    depth=2,
                )
        else:
            if not w.has(pid):
                from .model import Part as _Part
                w.add(_Part(id=pid, name=pid, kind="part", part_class="component"))
            new_lines[pid] = RequirementLine(
                item_id=pid, kind="part", net_annual=need, gross_annual=need, depth=2
            )

    return ExplosionResult(
        variant_id=explosion.variant_id + "+sub:" + str(contract.get("id")),
        annual_units=explosion.annual_units,
        lines=new_lines,
        mass_balance_warnings=list(explosion.mass_balance_warnings),
        proof_node_ids=new_proof,
    )
