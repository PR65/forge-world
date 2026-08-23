"""FORGE WORLD API server (FastAPI). Serves the computational core to the console."""
from __future__ import annotations

import os
import re
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from forge.engine import ForgeEngine, ObjectiveSpecInput
from forge.pack import load_pack
from forge.registry import CanonicalRegistry, load_registry

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
_REGISTRY_CACHE: Optional[CanonicalRegistry] = None
_PACK_CACHE_LOCK = Lock()
_REGISTRY_CACHE_LOCK = Lock()
_PACK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def get_pack(pack_id: str):
    if not _PACK_ID.fullmatch(pack_id):
        raise HTTPException(404, f"pack '{pack_id}' not found")
    if pack_id in _PACK_CACHE:
        return _PACK_CACHE[pack_id]
    with _PACK_CACHE_LOCK:
        if pack_id in _PACK_CACHE:
            return _PACK_CACHE[pack_id]
        packs_root = PACKS_DIR.resolve()
        path = (packs_root / f"{pack_id}.yaml").resolve()
        if path.parent != packs_root or not path.exists():
            raise HTTPException(404, f"pack '{pack_id}' not found")
        pk = load_pack(str(path))
        if pk.pack_id != pack_id:
            raise HTTPException(404, f"pack '{pack_id}' not found")
        _PACK_CACHE[pack_id] = pk
        return pk


def get_registry() -> CanonicalRegistry:
    """Load the deterministic file-backed registry once per API process."""
    global _REGISTRY_CACHE
    if _REGISTRY_CACHE is None:
        with _REGISTRY_CACHE_LOCK:
            if _REGISTRY_CACHE is None:
                _REGISTRY_CACHE = load_registry(PACKS_DIR, ROOT / "data" / "registry" / "manifest.yaml")
    return _REGISTRY_CACHE


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
    registry = get_registry()
    projects = []
    for e in pk.world.of_kind("project"):
        registry_node = registry.get_entity(f"pack:{pack_id}:{e.id}") or {}
        metadata = registry_node.get("metadata", {})
        epistemic_role = metadata.get("epistemic_role")
        if e.design_capacity_annual is None:
            control_role = "context"
        elif epistemic_role == "SCENARIO":
            control_role = "scenario"
        else:
            control_role = "fundable"
        projects.append({
            "id": e.id,
            "name": e.name,
            "item_id": e.item_id,
            "state": e.state.value,
            "state_date": e.state_date,
            "design_capacity": str(e.design_capacity_annual) if e.design_capacity_annual else None,
            "commission_window_years": list(e.years_to_commission),
            "notes": e.notes,
            "evidence_ids": list(e.evidence_ids),
            "registry_evidence_ids": list(registry_node.get("evidence_ids", ())),
            "epistemic_class": registry_node.get("epistemic_class", "UNKNOWN"),
            "epistemic_role": epistemic_role,
            "control_role": control_role,
        })
    s["projects"] = projects
    s["id_scope"] = "pack_local_with_registry_ids"
    s["evidence"] = [
        {**record.to_json(), "registry_evidence_id": f"pack:{pack_id}:evidence:{record.claim_id}"}
        for record in pk.evidence.values()
    ]
    s["sources"] = [
        {**source.to_json(), "registry_source_id": f"pack:{pack_id}:source:{source.id}"}
        for source in pk.sources.values()
    ]
    return s


@app.get("/api/world/summary")
def world_summary():
    """Summary of the shared canonical read projection."""
    return get_registry().summary()


@app.get("/api/world/search")
def world_search(
    q: str = "",
    kind: Optional[str] = None,
    pack_id: Optional[str] = None,
    limit: int = 25,
):
    """Search namespaced pack entities and explicit canonical records."""
    registry = get_registry()
    return {
        "query": q,
        "kind": kind,
        "pack_id": pack_id,
        "limit": limit,
        "results": registry.search(q, kind=kind, pack_id=pack_id, limit=limit),
        "snapshot_id": registry.snapshot_id,
    }


@app.get("/api/world/entities/{entity_id:path}")
def world_entity(entity_id: str):
    """Return one canonical or namespaced pack entity."""
    entity = get_registry().get_entity(entity_id)
    if entity is None:
        raise HTTPException(404, f"world entity '{entity_id}' not found")
    return entity


@app.get("/api/world/slice")
def world_slice(
    pack_id: Optional[str] = None,
    root: Optional[str] = None,
    depth: int = 2,
    limit: int = 100,
):
    """Return a bounded deterministic dependency slice."""
    result = get_registry().slice(pack_id=pack_id, root=root, depth=depth, limit=limit)
    if root and result.get("root") is None:
        raise HTTPException(404, f"world entity '{root}' not found")
    return result


@app.get("/api/world/capabilities")
def world_capabilities(
    pack_id: Optional[str] = None,
    limit: int = 200,
):
    registry = get_registry()
    return {
        "capabilities": registry.capabilities(pack_id=pack_id, limit=limit),
        "snapshot_id": registry.snapshot_id,
    }


@app.get("/api/world/builders")
def world_builders(limit: int = 200):
    registry = get_registry()
    return {
        "builders": registry.builders(limit=limit),
        "snapshot_id": registry.snapshot_id,
    }


@app.get("/api/world/evidence/{evidence_id:path}")
def world_evidence(evidence_id: str):
    evidence = get_registry().evidence_for(evidence_id)
    if evidence is None:
        raise HTTPException(404, f"world evidence '{evidence_id}' not found")
    return evidence


@app.get("/api/world/evidence-tasks")
def world_evidence_tasks(
    pack_id: Optional[str] = None,
    limit: int = 200,
):
    registry = get_registry()
    tasks = registry.tasks(pack_id=pack_id, limit=limit)
    return {
        "evidence_tasks": tasks,
        "tasks": tasks,
        "snapshot_id": registry.snapshot_id,
    }


@app.get("/api/world/snapshots")
def world_snapshots():
    return get_registry().snapshots()


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
