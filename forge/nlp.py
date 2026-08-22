"""Deterministic natural-language objective parsing.

Rule-based only (MODEL_CONTRACT C20): parses common phrasings into an inspectable
structured objective. Every interpreted field is returned for user inspection and edit;
nothing here touches solver coefficients.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .engine import ObjectiveSpecInput

NUMBER_WORDS = {
    "thousand": 1e3, "k": 1e3, "million": 1e6, "mn": 1e6, "m": 1e6,
    "billion": 1e9, "bn": 1e9, "b": 1e9,
}

PACK_HINTS = {
    "humanoid": "humanoid_india",
    "robot": "humanoid_india",
    "battery": "battery_gwh_india",
    "gwh": "battery_gwh_india",
    "satellite": "smallsat_india",
}


@dataclass
class ParsedObjective:
    objective: Optional[ObjectiveSpecInput]
    shocks: List[str] = field(default_factory=list)
    interpretations: List[str] = field(default_factory=list)
    unresolved: List[str] = field(default_factory=list)

    def to_json(self) -> Dict:
        o = self.objective
        obj_json = (
            {
                "variant_id": o.variant_id,
                "annual_units": o.annual_units,
                "geography": o.geography,
                "deadline_year": o.deadline_year,
                "min_dva": o.min_dva,
                "budget_usd": o.budget_usd,
                "funded_projects": o.funded_projects,
            }
            if o
            else None
        )
        return dict(
            objective=obj_json,
            shocks=self.shocks,
            interpretations=self.interpretations,
            unresolved=self.unresolved,
        )


def _num(tok: str) -> float:
    tok = tok.replace(",", "").strip().lower()
    m = re.fullmatch(r"([\d.]+)\s*([a-z]*)", tok)
    if not m:
        return float(tok)
    val = float(m.group(1))
    mult = NUMBER_WORDS.get(m.group(2), 1.0)
    return val * mult


def parse_objective(text: str) -> ParsedObjective:
    t = text.lower().strip()
    interp: List[str] = []
    unresolved: List[str] = []

    pack_id = None
    for hint, pid in PACK_HINTS.items():
        if hint in t:
            pack_id = pid
            break

    units = None
    m = re.search(
        r"([\d][\d,.]*\s*(?:thousand|million|billion|mn|bn|k|m|b)?)\s*"
        r"(humanoid(?:s)?|robots?|packs?|vehicles?|satellites?)",
        t,
    )
    if m:
        units = _num(m.group(1))
        noun = m.group(2)
        interp.append(f"target output = {units:,.0f} {noun}/yr")

    year = None
    my = re.search(r"by\s+(20\d\d)", t)
    if my:
        year = int(my.group(1))
        interp.append(f"deadline = {year}")

    dva = None
    md = re.search(r"(\d{2})\s*%\s*(?:domestic|local)", t)
    if md:
        dva = int(md.group(1)) / 100.0
        interp.append(f"minimum domestic value addition = {int(md.group(1))}%")
    elif "sovereign" in t or "domestic" in t or "localization" in t:
        dva = 0.7
        interp.append("localization intent detected; default ≥70% DVA applied (editable)")

    shocks: List[str] = []
    if re.search(r"(rare[\s-]?earth|magnet).{0,40}(fell|drop|cut|reduc)|(-?\d+)\s*%.{0,20}magnet", t):
        shocks.append("shk_cn_ree_minus80")
        interp.append("shock mapped: Chinese REE/magnet exports −80% (preset)")
    if "oil" in t and re.search(r"\$?\s*150", t):
        shocks.append("shk_oil_150")
        interp.append("shock mapped: oil at $150/bbl")
    if re.search(r"copper.{0,30}(double|\d+x)", t):
        shocks.append("shk_cu_double")
        interp.append("shock mapped: copper price doubles")
    if re.search(r"semiconductor.{0,40}(-\s*\d+%|halv)", t):
        shocks.append("shk_semi_half")
        interp.append("shock mapped: advanced semiconductor availability −50%")

    budget = None
    mb = re.search(r"\$\s*([\d.,]+\s*(?:billion|b|million|m)?)", t)
    if mb:
        budget = _num(mb.group(1))
        interp.append(f"budget = ${budget:,.0f}")

    variant = None
    if pack_id == "humanoid_india":
        variant = "hv2_industrial"
        if "compact" in t or "g1" in t or "small" in t:
            variant = "hv1_compact"
        interp.append(f"reference architecture = {variant} (inspectable; switchable)")
    elif pack_id == "battery_gwh_india":
        variant = "nmc_80kwh_pack_line"
    elif pack_id == "smallsat_india":
        variant = "eo_smallsat_300kg"

    missing = []
    if units is None:
        missing.append("annual output quantity")
    if variant is None:
        missing.append("domain/reference architecture")

    obj = None
    if obj_ok := (units is not None and variant is not None):
        obj = ObjectiveSpecInput(
            variant_id=variant,
            annual_units=units,
            deadline_year=year or 2030,
            min_dva=dva if dva is not None else 0.7,
            budget_usd=budget,
        )

    return ParsedObjective(
        objective=obj,
        shocks=shocks,
        interpretations=interp,
        unresolved=missing,
    )


if __name__ == "__main__":
    import json

    examples = [
        "What would it take for India to manufacture 1 million humanoids a year by 2030?",
        "What if Chinese rare-earth magnet exports fell by 80%?",
        "What is the cheapest way to reach 85% domestic value addition?",
        "With $50 billion and five years, what is the maximum production we can reach?",
    ]
    for e in examples:
        print(e)
        print(json.dumps(parse_objective(e).to_json(), indent=1))
