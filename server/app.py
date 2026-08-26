"""FORGE WORLD API server (FastAPI). Serves the computational core to the console."""
from __future__ import annotations

import json
import math
import os
import re
from collections import deque
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Sequence

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from forge.engine import ForgeEngine, ObjectiveSpecInput
from forge.pack import load_pack
from forge.registry import CanonicalRegistry, load_registry
from forge.india_v1.catalog import (
    DEPTH_PROFILE as INDIA_DEPTH_PROFILE,
    DOMAIN_ORDER as INDIA_DOMAIN_ORDER,
    EPISTEMIC_CLASSES as INDIA_EPISTEMIC_CLASSES,
    KINDS as INDIA_KINDS,
    STATUSES as INDIA_STATUSES,
    domains as india_domains,
    get_catalog as get_india_catalog,
    summary as india_summary,
)

ROOT = Path(__file__).resolve().parent.parent
PACKS_DIR = ROOT / "packs"
WEB_DIST = ROOT / "web" / "dist"

app = FastAPI(title="FORGE WORLD API", version="0.2.0")
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
    annual_units: float = Field(gt=0, allow_inf_nan=False)
    geography: str = "INDIA"
    deadline_year: int = Field(default=2030, ge=2026, le=2200)
    min_dva: float = Field(default=0.70, ge=0.0, le=1.0, allow_inf_nan=False)
    budget_usd: Optional[float] = Field(default=None, ge=0.0, allow_inf_nan=False)
    funded_projects: List[str] = Field(default_factory=list)
    shocks: List[str] = Field(default_factory=list)
    analyst_capacity_assumptions: Dict[str, tuple[float, float]] = Field(default_factory=dict)
    per_item_import_cap: Dict[str, float] = Field(default_factory=dict)
    include_deep: bool = True

    @field_validator("analyst_capacity_assumptions")
    @classmethod
    def validate_capacity_assumptions(
        cls, value: Dict[str, tuple[float, float]]
    ) -> Dict[str, tuple[float, float]]:
        for item_id, (lo, hi) in value.items():
            if not item_id.strip():
                raise ValueError("capacity assumption item id must not be blank")
            if not math.isfinite(lo) or not math.isfinite(hi):
                raise ValueError(f"capacity assumption for '{item_id}' must be finite")
            if lo < 0 or hi < lo:
                raise ValueError(
                    f"capacity assumption for '{item_id}' must satisfy 0 <= lo <= hi"
                )
        return value

    @field_validator("per_item_import_cap")
    @classmethod
    def validate_import_caps(cls, value: Dict[str, float]) -> Dict[str, float]:
        for item_id, cap in value.items():
            if not item_id.strip():
                raise ValueError("import-cap item id must not be blank")
            if not math.isfinite(cap) or not 0.0 <= cap <= 1.0:
                raise ValueError(
                    f"per-item import cap for '{item_id}' must be a finite fraction in [0, 1]"
                )
        return value


class DesignIn(ObjectiveIn):
    substitution_id: str


class ResearchResolveIn(BaseModel):
    objective: ObjectiveIn
    task: Dict[str, Any]
    capture: Dict[str, Any]
    reviewer: str = Field(min_length=1)
    approve_for_scenario: bool = False


def _objective_spec(obj: ObjectiveIn) -> ObjectiveSpecInput:
    assumptions = {
        key: (float(value[0]), float(value[1]))
        for key, value in obj.analyst_capacity_assumptions.items()
    }
    return ObjectiveSpecInput(
        variant_id=obj.variant_id,
        annual_units=obj.annual_units,
        geography=obj.geography,
        deadline_year=obj.deadline_year,
        min_dva=obj.min_dva,
        budget_usd=obj.budget_usd,
        funded_projects=obj.funded_projects,
        analyst_capacity_assumptions=assumptions,
        per_item_import_cap={
            key: float(value) for key, value in obj.per_item_import_cap.items()
        },
    )


@app.get("/api/health")
def health():
    return {"status": "ok", "packs": sorted(p.stem for p in PACKS_DIR.glob("*.yaml"))}


def _india_summary_record(catalog, record_id: str) -> Dict[str, Any]:
    record = catalog.by_id.get(record_id)
    if record is None:
        raise HTTPException(404, f"India V1 record '{record_id}' not found")
    return {
        "id": record["id"],
        "canonical_name": record["canonical_name"],
        # ``canonical_name`` remains the source-facing label; ``name`` is the
        # compact quality-normalized display label used by the UI.
        "name": record.get("display_name") or record["canonical_name"],
        "display_name": record.get("display_name") or record["canonical_name"],
        "family_key": record.get("family_key") or record["id"],
        "family_label": record.get("family_label") or record["canonical_name"],
        "variant_label": record.get("variant_label", ""),
        "aliases": list(record["aliases"][:20]),
        "domain_id": record["domain_id"],
        "domain_code": record["domain_code"],
        "domain": record["domain"],
        "category": record["category"],
        "kind": record["kind"],
        "explanation": str(record["explanation"])[:1200],
        "uses": list(record["uses"][:20]),
        "use": record["uses"][0] if record["uses"] else "",
        "status": record["status"],
        "india_status": record["status"],
        "status_epistemic_class": record["status_epistemic_class"],
        "status_basis": record["status_basis"],
        "is_reference_only": record["is_reference_only"],
        "depth_profile": INDIA_DEPTH_PROFILE,
    }


def _india_link_dto(catalog, record_id: str) -> Dict[str, Any]:
    """Return a bounded graph link without recursively embedding a record."""

    record = catalog.by_id.get(record_id)
    if record is None:
        raise HTTPException(404, f"India V1 record '{record_id}' not found")
    display = record.get("display_name") or record["canonical_name"]
    return {
        "id": record["id"],
        "canonical_name": record["canonical_name"],
        "name": display,
        "display_name": display,
        "family_key": record.get("family_key") or record["id"],
        "family_label": record.get("family_label") or display,
        "variant_label": record.get("variant_label", ""),
        "domain_id": record["domain_id"],
        "domain_code": record["domain_code"],
        "domain": record["domain"],
        "kind": record["kind"],
        "status": record["status"],
        "status_epistemic_class": record["status_epistemic_class"],
        "is_reference_only": record["is_reference_only"],
    }


def _india_full_record(catalog, record_id: str) -> Dict[str, Any]:
    record = catalog.by_id.get(record_id)
    if record is None:
        raise HTTPException(404, f"India V1 record '{record_id}' not found")

    dependencies: Dict[str, List[Dict[str, Any]]] = {}
    dependency_ids: Dict[str, List[str]] = {}
    for group, references in record["dependencies"].items():
        dependency_ids[group] = list(references)
        dependencies[group] = [_india_link_dto(catalog, reference) for reference in references]

    # Highly reused foundations can unlock thousands of records. Keep a
    # record response readable and bounded; the graph/search endpoints retain
    # access to the wider branch.
    link_limit = 100

    def linked(references: Sequence[str]) -> List[Dict[str, Any]]:
        return [_india_link_dto(catalog, reference) for reference in references[:link_limit]]

    upstream = linked(record["upstream"])
    downstream = linked(record["downstream"])
    related = linked(record["related"])
    payload = {
        **_india_summary_record(catalog, record_id),
        "explanation": record["explanation"],
        "uses": list(record["uses"]),
        "use": record["uses"][0] if record["uses"] else "",
        "status_basis": record["status_basis"],
        "status_epistemic": record["status_epistemic_class"],
        "epistemic_class": record["status_epistemic_class"],
        "dependencies": dependencies,
        "dependency_ids": [reference for values in dependency_ids.values() for reference in values],
        "dependency_ids_by_group": dependency_ids,
        "gaps": list(record["gaps"]),
        "import_notes": list(record["import_notes"]),
        "gap_import_notes": record["gap_import_notes"],
        "making_ladder": list(record["making_ladder"]),
        "upstream": upstream,
        "upstream_ids": list(record["upstream"][:link_limit]),
        "downstream": downstream,
        "downstream_ids": list(record["downstream"][:link_limit]),
        "unlocks": downstream,
        "unlock_ids": list(record["downstream"][:link_limit]),
        "related": related,
        "related_ids": list(record["related"][:link_limit]),
        "link_counts": {
            "upstream": len(record["upstream"]),
            "downstream": len(record["downstream"]),
            "unlocks": len(record["downstream"]),
            "related": len(record["related"]),
        },
        "links_truncated": {
            "upstream": len(record["upstream"]) > link_limit,
            "downstream": len(record["downstream"]) > link_limit,
            "unlocks": len(record["downstream"]) > link_limit,
            "related": len(record["related"]) > link_limit,
        },
        "links": {
            "upstream": upstream,
            "downstream": downstream,
            "unlocks": downstream,
            "related": related,
        },
        "source_spec": record["source_spec"],
    }
    return payload


def _india_domain_filter(catalog, value: Optional[str]) -> Optional[str]:
    if value is None or not value.strip():
        return None
    resolved = catalog.resolve_domain(value)
    if resolved is None:
        raise HTTPException(422, f"unknown India V1 domain '{value}'")
    return resolved


def _india_kind_filter(value: Optional[str]) -> Optional[str]:
    if value is None or not value.strip():
        return None
    normalized = value.strip().upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "FINISHED_PRODUCT": "PRODUCT",
        "COMPONENT": "PRODUCT",
        "MACHINE": "EQUIPMENT",
        "HEAVY_EQUIPMENT": "EQUIPMENT",
        "INSTRUMENT": "EQUIPMENT",
        "CHEMICAL": "MATERIAL",
        "PROCESS_CAPABILITY": "PROCESS",
        "UTILITY_CAPABILITY": "CAPABILITY",
        "SERVICE_CAPABILITY": "CAPABILITY",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in INDIA_KINDS:
        raise HTTPException(422, f"invalid India V1 kind '{value}'")
    return normalized


def _india_status_filter(value: Optional[str]) -> Optional[str]:
    if value is None or not value.strip():
        return None
    normalized = value.strip().upper()
    aliases = {
        "STRONG / AVAILABLE IN INDIA": "AVAILABLE",
        "PARTIAL / SCALE-LIMITED": "SCALE_LIMITED",
        "SPECIFICATION GAP": "PARTIAL",
        "QUALIFICATION GAP": "PARTIAL",
        "CAPACITY GAP": "SCALE_LIMITED",
        "IMPORT-DEPENDENT": "IMPORT_DEPENDENT",
        "MISSING / NO EVIDENCED DOMESTIC CAPABILITY": "MISSING",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in INDIA_STATUSES:
        raise HTTPException(422, f"invalid India V1 status '{value}'")
    return normalized


@app.get("/api/india/summary")
def india_summary_api():
    """Return deterministic combined Run 1 coverage and distributions."""

    return india_summary(get_india_catalog())


@app.get("/api/india/domains")
def india_domains_api():
    return {
        "depth_profile": INDIA_DEPTH_PROFILE,
        "domain_count": len(INDIA_DOMAIN_ORDER),
        "domains": india_domains(get_india_catalog()),
    }


@app.get("/api/india/search")
def india_search_api(
    q: str = Query(default="", max_length=200),
    domain: Optional[str] = Query(default=None, max_length=120),
    kind: Optional[str] = Query(default=None, max_length=50),
    status: Optional[str] = Query(default=None, max_length=80),
    limit: int = Query(default=25, ge=1, le=100),
    include_variants: bool = Query(default=False),
):
    catalog = get_india_catalog()
    domain_code = _india_domain_filter(catalog, domain)
    kind_value = _india_kind_filter(kind)
    status_value = _india_status_filter(status)
    hits = catalog.search_hits(
        q.strip(),
        domain=domain_code,
        kind=kind_value,
        status=status_value,
        limit=limit,
        include_variants=include_variants,
    )
    results = []
    for rank, hit in enumerate(hits, start=1):
        record = hit["record"]
        results.append(
            {
                **_india_summary_record(catalog, record["id"]),
                "rank": rank,
                "score": int(hit["score"]),
                "match_type": str(hit.get("match_type", "")),
                "matched_on": list(hit.get("matched_on", ())),
                "coverage": float(hit.get("coverage", 0.0)),
                "domain_match": bool(hit.get("domain_match", False)),
            }
        )
    return {
        "query": q,
        "domain": domain_code,
        "kind": kind_value,
        "status": status_value,
        "limit": limit,
        "include_variants": include_variants,
        "count": len(results),
        "results": results,
        "depth_profile": INDIA_DEPTH_PROFILE,
    }


@app.get("/api/india/bootstrap")
def india_bootstrap_api(limit: int = Query(default=12, ge=1, le=24)):
    """Return one bounded payload for first-load India V1 navigation."""

    catalog = get_india_catalog()
    return {
        "summary": india_summary(catalog),
        "domains": india_domains(catalog),
        "discover": india_discover_api(limit),
        "depth_profile": INDIA_DEPTH_PROFILE,
    }


@app.get("/api/india/records/{record_id:path}")
def india_record_api(record_id: str):
    if not record_id.strip() or len(record_id) > 240:
        raise HTTPException(404, f"India V1 record '{record_id}' not found")
    return _india_full_record(get_india_catalog(), record_id)


@app.get("/api/india/graph/{record_id:path}")
def india_graph_api(
    record_id: str,
    depth: int = Query(default=1, ge=0, le=4),
    limit: int = Query(default=100, ge=1, le=200),
):
    catalog = get_india_catalog()
    if record_id not in catalog.by_id:
        raise HTTPException(404, f"India V1 record '{record_id}' not found")

    visited: Dict[str, int] = {record_id: 0}
    queue: deque[tuple[str, int]] = deque([(record_id, 0)])
    edges: set[tuple[str, str, str]] = set()
    truncated = False
    while queue:
        current_id, current_depth = queue.popleft()
        current = catalog.by_id[current_id]
        if current_depth >= depth:
            continue
        neighbors: list[tuple[str, str]] = []
        for group, references in current["dependencies"].items():
            neighbors.extend((f"dependency:{group}", reference) for reference in references)
        neighbors.extend(("upstream", reference) for reference in current["upstream"])
        neighbors.extend(("downstream", reference) for reference in current["downstream"])
        neighbors.extend(("related", reference) for reference in current["related"])
        for relation, target_id in sorted(set(neighbors), key=lambda item: (item[0], item[1])):
            if target_id not in catalog.by_id:
                continue
            if target_id not in visited:
                if len(visited) >= limit:
                    truncated = True
                    continue
                visited[target_id] = current_depth + 1
                queue.append((target_id, current_depth + 1))
            if target_id in visited:
                edges.add((current_id, target_id, relation))

    nodes = []
    for node_id, node_depth in sorted(visited.items(), key=lambda item: (item[1], item[0])):
        nodes.append({**_india_summary_record(catalog, node_id), "depth": node_depth})
    edge_rows = [
        {"source": source, "target": target, "relation": relation}
        for source, target, relation in sorted(edges)
    ]
    return {
        "root": _india_summary_record(catalog, record_id),
        "nodes": nodes,
        "edges": edge_rows,
        "depth": depth,
        "limit": limit,
        "truncated": truncated,
        "depth_profile": INDIA_DEPTH_PROFILE,
    }


@app.get("/api/india/discover")
def india_discover_api(limit: int = Query(default=12, ge=1, le=50)):
    """Return fixed, cross-domain discovery examples with no random ordering."""

    catalog = get_india_catalog()
    prompts = (
        ("launch vehicle", "Aerospace and space systems expose deep recursive manufacturing routes."),
        ("nuclear", "Nuclear records expose strategic qualification and safety dependencies."),
        ("semiconductor", "Electronics records expose computing and advanced-package dependencies."),
        ("precision grinding", "Precision process records recur across machine tools and strategic products."),
        ("battery electric", "Mobility records expose energy, power-electronics, and service routes."),
        ("industrial controls", "Controls and automation are cross-domain option-value primitives."),
        ("water treatment", "Water and effluent systems recur as physical industrial prerequisites."),
        ("medical imaging", "Medical equipment demonstrates qualification-sensitive system depth."),
        ("materials engineering", "Materials engineering is a reusable cross-domain capability."),
        ("CNC machining", "Machining links product architecture to equipment, metrology, and process control."),
        ("satellite", "Space products make the product-to-process-to-material recursion visible."),
        ("robotics", "Robotics connects motion, controls, precision mechanics, and qualification."),
    )
    examples: list[Dict[str, Any]] = []
    seen: set[str] = set()
    for query, rationale in prompts:
        matches = catalog.ranked_search(query, limit=8)
        chosen = next((record for record, _score in matches if not record["is_reference_only"] and record["id"] not in seen), None)
        if chosen is None:
            continue
        seen.add(chosen["id"])
        examples.append({"id": chosen["id"], "rationale": rationale, "record": _india_summary_record(catalog, chosen["id"])})
        if len(examples) >= limit:
            break
    return {
        "depth_profile": INDIA_DEPTH_PROFILE,
        "limit": limit,
        "examples": examples,
        "records": [example["record"] for example in examples],
    }


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
    s["scenario_presets"] = list(pk.raw.get("scenario_presets", ()) or ())
    s["research_tasks"] = list(
        pk.raw.get("research_tasks", ())
        or (pk.raw.get("execution_model", {}) or {}).get("research_tasks", ())
        or ()
    )
    s["execution_model"] = dict(pk.raw.get("execution_model", {}) or {})
    s["program_model"] = dict(pk.raw.get("program_model", {}) or {})
    s["reverse_buildability_scenarios"] = list(
        pk.raw.get("reverse_buildability_scenarios", ()) or ()
    )
    s["supplier_links"] = list(pk.raw.get("supplier_links", ()) or ())
    s["facilities"] = [
        {
            "id": entity.id,
            "name": entity.name,
            "country": entity.country,
            "geo_id": entity.geo_id,
            "lat": entity.lat,
            "lon": entity.lon,
            "owner_org": entity.owner_org,
            "operator_org": entity.operator_org,
            "status": entity.status,
            "notes": entity.notes,
            "evidence_ids": list(entity.evidence_ids),
        }
        for entity in pk.world.of_kind("facility")
    ]
    s["organizations"] = [
        {
            "id": entity.id,
            "name": entity.name,
            "org_type": entity.org_type,
            "countries": list(entity.countries),
            "notes": entity.notes,
            "evidence_ids": list(entity.evidence_ids),
        }
        for entity in pk.world.of_kind("organization")
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
    spec = _objective_spec(obj)
    eng = ForgeEngine(pk)
    try:
        resp = eng.run_scenario(spec, shock_ids=obj.shocks or None,
                                include_deep=obj.include_deep)
    except KeyError as e:
        raise HTTPException(400, f"unknown entity in objective: {e}")
    return resp


@app.post("/api/workbench/case")
def operational_case(obj: ObjectiveIn):
    """One progressively disclosed operational projection over a single run."""
    from forge.operations import (
        build_case_brief,
        build_execution_plan,
        build_research_queue,
        capability_leverage,
        program_timeline,
        reverse_buildability_report,
        shock_impact,
    )

    pk = get_pack(obj.pack_id)
    spec = _objective_spec(obj)
    try:
        solve_response = ForgeEngine(pk).run_scenario(
            spec,
            shock_ids=obj.shocks or None,
            include_deep=obj.include_deep,
        )
        research_queue = build_research_queue(pk, spec, solve_response)
        execution = build_execution_plan(pk, spec, solve_response, research_queue)
        brief = build_case_brief(pk, spec, solve_response, research_queue)
        reverse = reverse_buildability_report(pk, spec, shock_ids=obj.shocks or None)
        shock = shock_impact(pk, spec, obj.shocks) if obj.shocks else None
    except (KeyError, ValueError) as exc:
        raise HTTPException(400, str(exc))
    return {
        "brief": brief,
        "analysis": solve_response,
        "research": {"tasks": research_queue, "count": len(research_queue)},
        "execution": execution,
        "reverse_buildability": reverse,
        "shock_impact": shock,
        "program": program_timeline(pk),
        "discover": capability_leverage(get_registry(), limit=20),
        "registry_snapshot_id": get_registry().snapshot_id,
    }


@app.post("/api/design/compare")
def design_compare(body: DesignIn):
    from forge.operations import compare_design

    try:
        return compare_design(
            get_pack(body.pack_id),
            _objective_spec(body),
            body.substitution_id,
            shock_ids=body.shocks or None,
        )
    except KeyError as exc:
        raise HTTPException(404, str(exc))
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@app.post("/api/research/resolve")
def research_resolve(body: ResearchResolveIn):
    from forge.research import process_research_capture

    pk = get_pack(body.objective.pack_id)
    try:
        return process_research_capture(
            pk,
            _objective_spec(body.objective),
            body.task,
            body.capture,
            reviewer=body.reviewer,
            approve_for_scenario=body.approve_for_scenario,
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(400, str(exc))


@app.get("/api/discover/capabilities")
def discover_capabilities(limit: int = 50):
    from forge.operations import capability_leverage

    return capability_leverage(get_registry(), limit=limit)


@app.post("/api/reverse-buildability")
def reverse_buildability_api(obj: ObjectiveIn):
    from forge.operations import reverse_buildability_report

    try:
        return reverse_buildability_report(
            get_pack(obj.pack_id),
            _objective_spec(obj),
            shock_ids=obj.shocks or None,
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(400, str(exc))


@app.post("/api/shocks/impact")
def shock_impact_api(obj: ObjectiveIn):
    from forge.operations import shock_impact

    if not obj.shocks:
        raise HTTPException(400, "at least one shock is required")
    try:
        return shock_impact(get_pack(obj.pack_id), _objective_spec(obj), obj.shocks)
    except (KeyError, ValueError) as exc:
        raise HTTPException(400, str(exc))


@app.get("/api/program/{pack_id}")
def program_api(pack_id: str):
    from forge.operations import program_timeline

    return program_timeline(get_pack(pack_id))


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


def _adapter_result_json(result) -> Dict[str, Any]:
    return {
        "source": result.source.to_json(),
        "source_snapshot": result.source_snapshot.to_json(),
        "observations": [row.to_json() for row in result.observations],
        "records": [row.to_json() for row in result.records],
        "promotions": [row.to_json() for row in result.promotions],
        "payload_hash": result.raw_payload_hash,
        "fetched_at": result.fetched_at,
        "notes": result.notes,
    }


@app.get("/api/adapter/comtrade")
def comtrade_adapter(
    reporter_code: int = 699,
    hs_code: str = "8458",
    period: int = 2024,
    flow_code: str = "M",
    partner_code: int = 0,
):
    """Live official trade flow; explicitly not a capability/capacity claim."""
    from forge.adapters import AdapterError, UNComtradeAdapter

    try:
        return _adapter_result_json(
            UNComtradeAdapter().fetch_trade(
                reporter_code=reporter_code,
                hs_code=hs_code,
                period=period,
                flow_code=flow_code,
                partner_code=partner_code,
            )
        )
    except AdapterError as exc:
        raise HTTPException(502, str(exc))


@app.get("/api/adapter/official")
def official_record_adapter():
    """Deterministic primary-document extraction pathway with entity resolution."""
    from forge.adapters import AdapterError, OfficialRecordCatalogAdapter

    try:
        results = OfficialRecordCatalogAdapter(
            ROOT / "data" / "ingestion" / "official_observations.yaml"
        ).load()
    except AdapterError as exc:
        raise HTTPException(500, str(exc))
    registry = get_registry()
    rows = []
    for result in results:
        payload = _adapter_result_json(result)
        payload["entity_bindings"] = [
            {
                "observation_id": observation.observation_id,
                "subject": observation.subject,
                "resolved_entity": registry.get_entity(observation.subject),
                "automatic_model_mutation": False,
            }
            for observation in result.observations
        ]
        rows.append(payload)
    return {
        "pathway": "CHECKED_IN_OFFICIAL_RECORD_CATALOG",
        "registry_snapshot_id": registry.snapshot_id,
        "results": rows,
    }


@app.get("/api/adapter/official/targeted")
def targeted_official_record_adapter():
    """Reviewed HOMI gap-closure observations with canonical bindings."""
    from forge.adapters import AdapterError, OfficialRecordCatalogAdapter

    try:
        results = OfficialRecordCatalogAdapter(
            ROOT / "data" / "ingestion" / "homi_targeted_observations.yaml"
        ).load()
    except AdapterError as exc:
        raise HTTPException(500, str(exc))
    registry = get_registry()
    rows = []
    for result in results:
        payload = _adapter_result_json(result)
        payload["entity_bindings"] = [
            {
                "observation_id": observation.observation_id,
                "subject": observation.subject,
                "resolved_entity": registry.get_entity(observation.subject),
                "automatic_model_mutation": False,
            }
            for observation in result.observations
        ]
        rows.append(payload)
    return {
        "pathway": "HOMI_TARGETED_PRIMARY_SOURCE_CATALOG",
        "registry_snapshot_id": registry.snapshot_id,
        "results": rows,
    }


@app.get("/api/ingestion/status")
def ingestion_status():
    """Show which operational pathways reach resolvable world entities."""
    from forge.adapters import OfficialRecordCatalogAdapter

    results = OfficialRecordCatalogAdapter(
        ROOT / "data" / "ingestion" / "official_observations.yaml"
    ).load()
    targeted_results = OfficialRecordCatalogAdapter(
        ROOT / "data" / "ingestion" / "homi_targeted_observations.yaml"
    ).load()
    registry = get_registry()
    observations = [observation for result in results for observation in result.observations]
    resolved = [observation for observation in observations if registry.get_entity(observation.subject)]
    targeted_observations = [
        observation for result in targeted_results for observation in result.observations
    ]
    targeted_resolved = [
        observation
        for observation in targeted_observations
        if registry.get_entity(observation.subject)
    ]
    return {
        "pathways": [
            {
                "id": "world_bank_api",
                "mode": "LIVE_JSON_API",
                "operational": True,
                "model_role": "national statistical context",
            },
            {
                "id": "un_comtrade_api",
                "mode": "LIVE_JSON_API",
                "operational": True,
                "model_role": "trade context only; never capability or capacity",
            },
            {
                "id": "official_record_catalog",
                "mode": "DETERMINISTIC_CHECKED_IN_EXTRACTION",
                "operational": True,
                "model_role": "primary document observation and explicit entity binding",
            },
            {
                "id": "homi_targeted_primary_sources",
                "mode": "REVIEWED_SOURCE_SNAPSHOT_OBSERVATION_PROMOTION",
                "operational": True,
                "model_role": "decision-ranked facility/process/test observations mapped to canonical world state",
            },
            {
                "id": "research_resolution",
                "mode": "HUMAN_REVIEWED_CAPTURE_TO_SCENARIO_OVERLAY",
                "operational": True,
                "model_role": "UNKNOWN resolution without silent persistent mutation",
            },
            {
                "id": "local_corpus_claim_staging",
                "mode": "DETERMINISTIC_LOCAL_CORPUS_STAGING",
                "operational": True,
                "model_role": "non-authoritative claims blocked pending rights, identity, relation, conflict, and promotion review",
            },
        ],
        "official_catalog_observations": len(observations),
        "resolved_world_subjects": len(resolved),
        "targeted_catalog_observations": len(targeted_observations),
        "targeted_resolved_world_subjects": len(targeted_resolved),
        "unresolved_world_subjects": sorted(
            observation.subject
            for observation in observations
            if registry.get_entity(observation.subject) is None
        ),
        "registry_snapshot_id": registry.snapshot_id,
    }


def _read_homi_json(relative_path: str) -> Dict[str, Any]:
    path = ROOT / "research" / "homi" / relative_path
    if not path.exists():
        raise HTTPException(404, f"HOMI artifact '{relative_path}' is not available")
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise HTTPException(500, f"HOMI artifact '{relative_path}' is malformed")
    return value


@app.get("/api/reality/status")
def reality_status():
    """Expose raw integrity, staging, promotion, conflict, and rights posture."""

    barrier = _read_homi_json("gate0/barrier.json")
    ledger = _read_homi_json("gate0/claim_ledger.json")
    conditioning = _read_homi_json("staging/conditioning_report.json")
    targeted = _read_homi_json("targeted/promotion_ledger.json")
    closure = _read_homi_json("targeted/closure_summary.json")
    return {
        "layers": {
            "L0_raw": "EXTERNAL_IMMUTABLE",
            "L1_staging": "NON_AUTHORITATIVE",
            "L2_canonical": "EXPLICIT_REVIEW_ONLY",
            "L3_derived_scenario": "NEVER_OVERWRITES_BASELINE",
        },
        "gate0": barrier,
        "staged_claims": ledger["claim_count"],
        "promotions": ledger["promotion_count"],
        "epistemic_class_counts": ledger["epistemic_class_counts"],
        "conflict_candidates": ledger["conflict_candidate_count"],
        "source_license_unspecified": ledger["source_license_unspecified_count"],
        "targeted_closure": {
            "sources": targeted["source_count"],
            "observations": targeted["observation_count"],
            "promotions": targeted["promotion_count"],
            "effective_capacity_promotions": targeted[
                "effective_capacity_promotion_count"
            ],
            "composition": closure["composition_after_targeted_closure"],
        },
        "conditioning": {
            "artifacts": conditioning["artifact_count"],
            "unique_hashes": conditioning["unique_hash_count"],
            "duplicates": conditioning["duplicate_artifact_count"],
            "structured": conditioning["structured_artifact_count"],
            "repaired": conditioning["repaired_artifact_count"],
            "status_counts": conditioning["status_counts"],
            "raw_integrity_failures": conditioning["raw_integrity_failure_count"],
        },
        "registry_snapshot_id": get_registry().snapshot_id,
    }


@app.get("/api/reality/claims")
def reality_claims(limit: int = 50):
    """Return a bounded deterministic view of non-authoritative staged claims."""

    ledger = _read_homi_json("gate0/claim_ledger.json")
    bounded = max(1, min(int(limit), 200))
    return {
        "authority": ledger["authority"],
        "claim_count": ledger["claim_count"],
        "promotion_count": ledger["promotion_count"],
        "claims": ledger["claims"][:bounded],
        "truncated": ledger["claim_count"] > bounded,
        "ledger_hash": ledger["ledger_hash"],
    }


@app.get("/api/composition/novel")
def novel_objective_composition():
    """Compose the frozen novel objectives without claiming solver verdicts."""

    from forge.composition import (
        compose_benchmark_set,
        load_objective_seeds,
        rank_decision_gaps,
    )

    benchmark = load_objective_seeds(ROOT / "data" / "objectives" / "novel_objectives.yaml")
    composition = compose_benchmark_set(get_registry(), benchmark)
    return {"composition": composition, "decision_gaps": rank_decision_gaps(composition)}


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


_PUBLIC_DOCS = {
    "DATA_SOURCES.md": ROOT / "docs" / "DATA_SOURCES.md",
    "DATA_RIGHTS.md": ROOT / "docs" / "DATA_RIGHTS.md",
    "FORGE_INDIA_V1_KNOWN_LIMITATIONS.md": ROOT / "docs" / "FORGE_INDIA_V1_KNOWN_LIMITATIONS.md",
}


@app.get("/docs/{document_name}")
def public_document(document_name: str):
    """Serve the small, explicit public documentation surface linked by V1."""

    document = _PUBLIC_DOCS.get(document_name)
    if document is None or not document.exists():
        raise HTTPException(404, "Public document not found")
    return FileResponse(document, media_type="text/markdown; charset=utf-8")


@app.get("/india")
@app.get("/india/")
@app.get("/india/records/{record_id:path}")
def india_frontend(record_id: str | None = None):
    """Return the SPA shell for launch routes and direct record deep links."""

    if (WEB_DIST / "index.html").exists():
        return FileResponse(WEB_DIST / "index.html")
    return {"error": "frontend not built; run npm run build in web/"}


if WEB_DIST.exists():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")
