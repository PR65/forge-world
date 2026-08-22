"""FORGE WORLD API server (FastAPI). Serves the computational core to the console."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from forge.engine import ForgeEngine, ObjectiveSpecInput
from forge.pack import load_pack

ROOT = Path(__file__).resolve().parent.parent
PACKS_DIR = ROOT / "packs"
WEB_DIST = ROOT / "web" / "dist"

app = FastAPI(title="FORGE WORLD API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_PACK_CACHE: Dict[str, Any] = {}


def get_pack(pack_id: str):
    if pack_id in _PACK_CACHE:
        return _PACK_CACHE[pack_id]
    path = PACKS_DIR / f"{pack_id}.yaml"
    if not path.exists():
        raise HTTPException(404, f"pack '{pack_id}' not found")
    pk = load_pack(str(path))
    _PACK_CACHE[pack_id] = pk
    return pk


class ObjectiveIn(BaseModel):
    pack_id: str
    variant_id: str
    annual_units: float = Field(gt=0)
    geography: str = "INDIA"
    deadline_year: int = 2030
    min_dva: float = 0.70
    budget_usd: Optional[float] = None
    funded_projects: List[str] = []
    shocks: List[str] = []
    analyst_capacity_assumptions: Dict[str, List[float]] = {}
    include_deep: bool = True


@app.get("/api/health")
def health():
    return {"status": "ok", "packs": sorted(p.stem for p in PACKS_DIR.glob("*.yaml"))}


@app.get("/api/packs")
def packs():
    out = []
    for p in sorted(PACKS_DIR.glob("*.yaml")):
        try:
            pk = get_pack(p.stem)
            out.append(pk.summary())
        except Exception as e:
            out.append({"pack_id": p.stem, "error": str(e)})
    return out


@app.get("/api/packs/{pack_id}")
def pack_detail(pack_id: str):
    pk = get_pack(pack_id)
    s = pk.summary()
    s["variants"] = [
        {
            "id": vid,
            "name": vd.get("name", vid),
            "notes": vd.get("notes", ""),
            "anchor_evidence": vd.get("anchor_evidence", []),
            "functional_requirements": vd.get("functional_requirements", []),
            "bom": vd.get("bom", []),
        }
        for vid, vd in pk.variants.items()
    ]
    s["shocks"] = [
        {"id": sh.id, "name": sh.name, "description": sh.description}
        for sh in pk.shocks.values()
    ]
    s["substitutions"] = [
        {
            "id": sid,
            "name": c.get("name", sid),
            "replaces_part": c.get("replaces_part"),
            "maturity": c.get("maturity"),
            "performance_delta": c.get("performance_delta", {}),
        }
        for sid, c in pk.substitutions.items()
    ]
    s["projects"] = [
        {
            "id": e.id,
            "name": e.name,
            "item_id": e.item_id,
            "state": e.state.value,
            "state_date": e.state_date,
            "design_capacity": str(e.design_capacity_annual) if e.design_capacity_annual else None,
            "commission_window_years": list(e.years_to_commission),
        }
        for e in pk.world.of_kind("project")
    ]
    s["evidence"] = [r.to_json() for r in pk.evidence.values()]
    s["sources"] = [src.to_json() for src in pk.sources.values()]
    return s


@app.post("/api/solve")
def solve(obj: ObjectiveIn):
    pk = get_pack(obj.pack_id)
    assumptions = {
        k: (float(v[0]), float(v[1])) for k, v in obj.analyst_capacity_assumptions.items()
    }
    spec = ObjectiveSpecInput(
        variant_id=obj.variant_id,
        annual_units=obj.annual_units,
        geography=obj.geography,
        deadline_year=obj.deadline_year,
        min_dva=obj.min_dva,
        budget_usd=obj.budget_usd,
        funded_projects=obj.funded_projects,
        analyst_capacity_assumptions=assumptions,
    )
    eng = ForgeEngine(pk)
    try:
        resp = eng.run_scenario(spec, shock_ids=obj.shocks or None,
                                include_deep=obj.include_deep)
    except KeyError as e:
        raise HTTPException(400, f"unknown entity in objective: {e}")
    return resp


@app.post("/api/parse")
def parse_nl(body: Dict[str, str]):
    """Deterministic NL → structured objective. Fully inspectable; never authoritative."""
    from forge.nlp import parse_objective

    text = str(body.get("text", "")).strip()
    if not text:
        raise HTTPException(400, "empty text")
    return parse_objective(text).to_json()


@app.get("/api/adapter/worldbank")
def adapter_demo(country: str = "IND"):
    from forge.adapters import AdapterError, run_adapter_demo

    try:
        return run_adapter_demo(country.upper())
    except AdapterError as e:
        raise HTTPException(502, str(e))


@app.get("/api/optionvalue")
def option_value():
    """Cross-objective investment prioritization over all loaded packs (V0)."""
    from forge.optionreport import option_value_report

    packs = [(pid, get_pack(pid)) for pid in sorted(p.stem for p in PACKS_DIR.glob("*.yaml"))]
    return option_value_report(
        packs,
        units_by_pack={"humanoid_india": 1_000_000, "battery_gwh_india": 500_000,
                       "smallsat_india": 50},
        dva_by_pack={"humanoid_india": 0.7, "battery_gwh_india": 0.6, "smallsat_india": 0.6},
    )


@app.get("/")
def index():
    if (WEB_DIST / "index.html").exists():
        return FileResponse(WEB_DIST / "index.html")
    return {"error": "frontend not built; run npm run build in web/"}


if WEB_DIST.exists():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")
