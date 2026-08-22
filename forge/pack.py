from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import yaml

from .evidence import EvidenceRecord, Source
from .epistemics import Confidence, EpistemicClass
from .model import (
    CapacitySegment, CapabilityClaim, CapabilityVector, DemandPool, EquipmentClass,
    Facility, GeoNode, MaterialGrade, Organization, Part, ProcessStep, ProductionRecipe,
    Project, ProjectState, Qualification, Restriction, Shock, Skill, StandardRef,
    Substitution as SubstitutionEntity, TechnologyRight, TransportCorridor, World,
)
from .units import Quantity, UnitError, register_unit

SUBSTITUTION_REQUIRED_FIELDS = (
    "replaces_part", "alternative_recipe", "level", "functional_envelope",
    "performance_delta", "maturity", "transition_months", "evidence_ids",
)


class PackValidationError(Exception):
    pass


def _qty(spec) -> Quantity:
    if spec is None:
        raise PackValidationError("missing quantity")
    if isinstance(spec, (list, tuple)) and len(spec) == 2:
        try:
            return Quantity(float(spec[0]), str(spec[1]))
        except UnitError as e:
            raise PackValidationError(f"bad quantity {spec}: {e}")
    if isinstance(spec, dict) and "value" in spec and "unit" in spec:
        return Quantity(float(spec["value"]), str(spec["unit"]))
    raise PackValidationError(f"unparseable quantity: {spec!r}")


def _opt_qty(spec) -> Optional[Quantity]:
    return _qty(spec) if spec is not None else None


def _pair(spec, default=None) -> Tuple[float, float]:
    if spec is None:
        return default
    if isinstance(spec, (list, tuple)) and len(spec) == 2:
        return (float(spec[0]), float(spec[1]))
    if isinstance(spec, (int, float)):
        return (float(spec), float(spec))
    raise PackValidationError(f"expected [lo, hi] pair, got {spec!r}")


def _tup(spec) -> Tuple[str, ...]:
    if spec is None:
        return ()
    if isinstance(spec, str):
        return (spec,)
    return tuple(str(x) for x in spec)


@dataclass
class KnowledgePack:
    pack_id: str
    title: str
    version: str
    geography_focus: str
    world: World = field(default_factory=World)
    sources: Dict[str, Source] = field(default_factory=dict)
    evidence: Dict[str, EvidenceRecord] = field(default_factory=dict)
    variants: Dict[str, dict] = field(default_factory=dict)
    substitutions: Dict[str, dict] = field(default_factory=dict)
    crosswalks: List[dict] = field(default_factory=list)
    shocks: Dict[str, Shock] = field(default_factory=dict)
    raw: dict = field(default_factory=dict)
    path: str = ""

    def evidence_or_fail(self, claim_id: str) -> EvidenceRecord:
        if claim_id not in self.evidence:
            raise PackValidationError(f"evidence '{claim_id}' referenced but not defined")
        return self.evidence[claim_id]

    def summary(self) -> Dict:
        w = self.world
        kinds: Dict[str, int] = {}
        for e in w.entities.values():
            kinds[e.kind] = kinds.get(e.kind, 0) + 1
        return dict(
            pack_id=self.pack_id, title=self.title, version=self.version,
            geography_focus=self.geography_focus, sources=len(self.sources),
            evidence=len(self.evidence), entities=len(w.entities), edges=len(w.edges),
            entity_kinds=kinds, variants=sorted(self.variants.keys()),
            substitutions=sorted(self.substitutions.keys()),
        )


def _build_evidence(d: dict, pack_sources: Dict[str, Source]) -> EvidenceRecord:
    try:
        klass = EpistemicClass(d["epistemic_class"])
    except KeyError:
        raise PackValidationError(f"evidence missing epistemic_class: {d.get('claim_id')}")
    except ValueError:
        raise PackValidationError(f"bad epistemic_class in {d.get('claim_id')}")
    src_ids = _tup(d.get("source_ids"))
    for s in src_ids:
        if s not in pack_sources:
            raise PackValidationError(
                f"evidence '{d.get('claim_id')}' references unknown source '{s}'"
            )
    if klass in (EpistemicClass.MEASURED, EpistemicClass.REPORTED) and not src_ids:
        raise PackValidationError(
            f"{klass.value} evidence '{d.get('claim_id')}' requires at least one source (C21)"
        )
    conf_raw = d.get("confidence") or {}
    conf = Confidence({k: (float(v) if v is not None else None) for k, v in conf_raw.items()})
    vq = None
    if d.get("value_quantity") is not None:
        vq_pair = _qty(d["value_quantity"])
        vq = (vq_pair.value, vq_pair.unit)
    return EvidenceRecord(
        claim_id=str(d["claim_id"]),
        subject=str(d.get("subject", "")),
        predicate=str(d.get("predicate", "")),
        epistemic_class=klass,
        value_text=str(d.get("value_text", "")),
        value_quantity=vq,
        unit_note=str(d.get("unit_note", "")),
        source_ids=src_ids,
        publication_date=str(d.get("publication_date", "")),
        effective_date=str(d.get("effective_date", "")),
        retrieval_date=str(d.get("retrieval_date", "")),
        geographic_scope=str(d.get("geographic_scope", "GLOBAL")),
        technical_scope=str(d.get("technical_scope", "")),
        extraction_method=str(d.get("extraction_method", "manual")),
        confidence=conf,
        license=str(d.get("license", "UNSPECIFIED")),
        derived_from=_tup(d.get("derived_from")),
        supersedes=d.get("supersedes"),
        review_status=str(d.get("review_status", "unreviewed")),
        quote_or_caveat=str(d.get("quote_or_caveat", "")),
    )


def _build_recipe(d: dict, w: World) -> ProductionRecipe:
    steps = []
    for s in d.get("steps", []) or []:
        steps.append(ProcessStep(
            id=str(s["id"]), name=str(s.get("name", s["id"])), kind="process_step",
            resource_classes=_tup(s.get("resource_classes")),
            equipment_classes=_tup(s.get("equipment_classes")),
            cycle_time_per_unit=_opt_qty(s.get("cycle_time_per_unit")),
            energy_per_unit=_opt_qty(s.get("energy_per_unit")),
            water_per_unit=_opt_qty(s.get("water_per_unit")),
            labor_skill=_tup(s.get("labor_skill")),
            environment=str(s.get("environment", "")),
            yield_fraction=float(s.get("yield_fraction", 1.0)),
            scrap_fraction=float(s.get("scrap_fraction", 0.0)),
        ))
    inputs = tuple(
        (str(i["id"]), _qty(i["quantity"])) for i in (d.get("inputs") or [])
    )
    return ProductionRecipe(
        id=str(d["id"]), name=str(d.get("name", d["id"])), kind="recipe",
        notes=str(d.get("notes", "")),
        evidence_ids=_tup(d.get("evidence_ids")),
        output_part=str(d.get("output_part", "")),
        output_quantity=_qty(d.get("output_quantity", [1, "pcs"])),
        inputs=inputs,
        steps=tuple(steps),
        route_type=str(d.get("route_type", "primary")),
        maturity=str(d.get("maturity", "series")),
        requires_qualification=_tup(d.get("requires_qualification")),
        applicable_geographies=_tup(d.get("applicable_geographies", ["GLOBAL"])),
        capex_estimate=_opt_qty(d.get("capex_estimate")),
    )


def _build_part(d: dict, w: World) -> Part:
    lt = d.get("lead_time")
    return Part(
        id=str(d["id"]), name=str(d.get("name", d["id"])), kind="part",
        notes=str(d.get("notes", "")),
        evidence_ids=_tup(d.get("evidence_ids")),
        part_class=str(d.get("part_class", "component")),
        mass=_opt_qty(d.get("mass")),
        spec=str(d.get("spec", "")),
        supplied_by_countries=_tup(d.get("supplied_by_countries")),
        concentration_hhi=(float(d["concentration_hhi"]) if d.get("concentration_hhi") is not None else None),
        lead_time=_opt_qty(lt),
        import_eligible=bool(d.get("import_eligible", True)),
    )


def _link_variant_tree(pack: KnowledgePack, vid: str, bom: List[dict]):
    w = pack.world
    for entry in bom:
        pid = str(entry["part"])
        w.link(vid, "decomposes_into", pid, qty=float(entry.get("qty", 1)))
        child = entry.get("bom")
        if child:
            _link_variant_tree(pack, pid, child)


def _validate_substitution(s: dict, pack: KnowledgePack):
    sid = s.get("id", "?")
    missing = [f for f in SUBSTITUTION_REQUIRED_FIELDS if f not in s]
    if missing:
        raise PackValidationError(
            f"substitution '{sid}' missing required contract fields: {missing} (C9)"
        )
    w = pack.world
    if not w.has(str(s["replaces_part"])):
        raise PackValidationError(f"substitution '{sid}' replaces unknown part '{s['replaces_part']}'")
    if not w.has(str(s["alternative_recipe"])):
        raise PackValidationError(
            f"substitution '{sid}' references unknown recipe '{s['alternative_recipe']}'"
        )
    if not s.get("evidence_ids"):
        raise PackValidationError(f"substitution '{sid}' has no evidence (C9)")
    for ev in s["evidence_ids"]:
        pack.evidence_or_fail(str(ev))


def load_pack(path: str) -> KnowledgePack:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return build_pack(raw, path=path)


def load_pack_dir(pack_id: str, packs_root: str = "packs") -> KnowledgePack:
    path = os.path.join(packs_root, f"{pack_id}.yaml")
    if not os.path.exists(path):
        raise FileNotFoundError(f"pack not found: {path}")
    return load_pack(path)


def build_pack(raw: dict, path: str = "") -> KnowledgePack:
    if not raw.get("pack_id"):
        raise PackValidationError("pack_id required")
    pk = KnowledgePack(
        pack_id=str(raw["pack_id"]),
        title=str(raw.get("title", raw["pack_id"])),
        version=str(raw.get("version", "0.0.0")),
        geography_focus=str(raw.get("geography_focus", "INDIA")),
        raw=raw,
        path=path,
    )
    w = pk.world

    for sd in raw.get("sources", []) or []:
        src = Source(
            id=str(sd["id"]), name=str(sd.get("name", sd["id"])),
            publisher=str(sd.get("publisher", "")), url=str(sd.get("url", "")),
            source_type=str(sd.get("source_type", "document")),
            license=str(sd.get("license", "UNSPECIFIED")),
            access_date=str(sd.get("access_date", "")), notes=str(sd.get("notes", "")),
        )
        pk.sources[src.id] = src

    for ed in raw.get("evidence", []) or []:
        rec = _build_evidence(ed, pk.sources)
        pk.evidence[rec.claim_id] = rec

    for md in raw.get("materials", []) or []:
        m = MaterialGrade(
            id=str(md["id"]), name=str(md.get("name", md["id"])), kind="material_grade",
            notes=str(md.get("notes", "")), evidence_ids=_tup(md.get("evidence_ids")),
            family=str(md.get("family", "")), grade_spec=str(md.get("grade_spec", "")),
            purity=(float(md["purity"]) if md.get("purity") is not None else None),
            form=str(md.get("form", "")),
        )
        w.add(m)

    for pd in raw.get("parts", []) or []:
        p = _build_part(pd, w)
        w.add(p)

    for rd in raw.get("recipes", []) or []:
        r = _build_recipe(rd, w)
        w.add(r)
        if r.output_part:
            if not w.has(r.output_part):
                w.add(Part(id=r.output_part, name=r.output_part, kind="part", part_class="component"))
            w.link(r.output_part, "produced_via", r.id)
        for iname, iq in r.inputs:
            if not w.has(iname):
                w.add(Part(id=iname, name=iname, kind="part", part_class="component"))
            w.link(r.id, "requires_input", iname, quantity=str(iq))
        for st in r.steps:
            for ec in st.equipment_classes:
                if not w.has(ec):
                    w.add(EquipmentClass(id=ec, name=ec, kind="equipment_class"))
                w.link(r.id, "requires_equipment", ec)
            for rc in st.resource_classes:
                if not w.has(rc):
                    w.add(ResourceClassStub(rc))
                w.link(r.id, "requires_input", rc)

    for vd in raw.get("product_variants", []) or []:
        vid = str(vd["id"])
        from .model import Entity
        v = Entity(id=vid, name=str(vd.get("name", vid)), kind="product_variant",
                   notes=str(vd.get("notes", "")), evidence_ids=_tup(vd.get("anchor_evidence")))
        w.add(v)
        pk.variants[vid] = vd
        for fr in vd.get("functional_requirements", []) or []:
            fid = f"{vid}.fr.{fr.get('metric', 'req')}"
            from .model import FunctionalRequirement
            w.add(FunctionalRequirement(
                id=fid, name=str(fr.get("name", fid)), kind="functional_requirement",
                metric=str(fr.get("metric", "")),
                envelope_min=(float(fr["min"]) if fr.get("min") is not None else None),
                envelope_max=(float(fr["max"]) if fr.get("max") is not None else None),
                unit=str(fr.get("unit", "")),
            ))
            w.link(fid, "derived_from", vid)
        if vd.get("bom"):
            _link_variant_tree(pk, vid, vd["bom"])

    for rcd in raw.get("resource_classes", []) or []:
        from .model import ResourceClass
        rc = ResourceClass(
            id=str(rcd["id"]), name=str(rcd.get("name", rcd["id"])), kind="resource_class",
            notes=str(rcd.get("notes", "")), evidence_ids=_tup(rcd.get("evidence_ids")),
            category=str(rcd.get("category", "material")),
            unit=str(rcd.get("unit", "pcs")),
            substitutable_with=_tup(rcd.get("substitutable_with")),
            supplied_by_countries=_tup(rcd.get("supplied_by_countries")),
            concentration_hhi=(float(rcd["concentration_hhi"]) if rcd.get("concentration_hhi") is not None else None),
            lead_time=_opt_qty(rcd.get("lead_time")),
            import_eligible=bool(rcd.get("import_eligible", True)),
        )
        w.add(rc)

    for od in raw.get("organizations", []) or []:
        w.add(Organization(id=str(od["id"]), name=str(od.get("name", od["id"])), kind="organization",
                           notes=str(od.get("notes", "")), evidence_ids=_tup(od.get("evidence_ids")),
                           org_type=str(od.get("org_type", "company")),
                           countries=_tup(od.get("countries"))))

    for fd in raw.get("facilities", []) or []:
        w.add(Facility(id=str(fd["id"]), name=str(fd.get("name", fd["id"])), kind="facility",
                       notes=str(fd.get("notes", "")), evidence_ids=_tup(fd.get("evidence_ids")),
                       geo_id=str(fd.get("geo_id", "UNKNOWN")),
                       country=str(fd.get("country", "UNKNOWN")),
                       lat=(float(fd["lat"]) if fd.get("lat") is not None else None),
                       lon=(float(fd["lon"]) if fd.get("lon") is not None else None),
                       owner_org=str(fd.get("owner_org", "")),
                       operator_org=str(fd.get("operator_org", "")),
                       status=str(fd.get("status", "operating"))))

    for cd in raw.get("capacity_segments", []) or []:
        seg = CapacitySegment(
            id=str(cd["id"]), name=str(cd.get("name", cd["id"])), kind="capacity_segment",
            notes=str(cd.get("notes", "")), evidence_ids=_tup(cd.get("evidence_ids")),
            item_id=str(cd["item_id"]), facility_id=str(cd.get("facility_id", "")),
            org_id=str(cd.get("org_id", "")), geography=str(cd.get("geography", "INDIA")),
            nameplate_annual=_opt_qty(cd.get("nameplate_annual")),
            availability=float(cd.get("availability", 1.0)),
            utilization=float(cd.get("utilization", 1.0)),
            yield_fraction=float(cd.get("yield_fraction", 1.0)),
            qualification_fraction=float(cd.get("qualification_fraction", 1.0)),
            product_compat=_tup(cd.get("product_compat")),
            valid_from=int(cd.get("valid_from", 1900)), valid_to=int(cd.get("valid_to", 2100)),
            epistemic_class=str(cd.get("epistemic_class", "REPORTED")),
            is_project_capacity=bool(cd.get("is_project_capacity", False)),
            project_id=str(cd.get("project_id", "")),
        )
        w.add(seg)
        w.link(seg.id, "has_capacity", seg.item_id)
        if seg.facility_id and w.has(seg.facility_id):
            w.link(seg.id, "located_at", seg.facility_id)

    for prd in raw.get("projects", []) or []:
        try:
            st = ProjectState(prd.get("state", "concept"))
        except ValueError:
            raise PackValidationError(f"project '{prd['id']}' bad state '{prd.get('state')}'")
        prj = Project(
            id=str(prd["id"]), name=str(prd.get("name", prd["id"])), kind="project",
            notes=str(prd.get("notes", "")), evidence_ids=_tup(prd.get("evidence_ids")),
            item_id=str(prd["item_id"]), geography=str(prd.get("geography", "INDIA")),
            state=st, state_date=str(prd.get("state_date", "")),
            earliest_start_year=int(prd.get("earliest_start_year", 2026)),
            years_to_commission=_pair(prd.get("years_to_commission"), (0.0, 0.0)),
            commission_year_estimate=(int(prd["commission_year_estimate"]) if prd.get("commission_year_estimate") else None),
            design_capacity_annual=_opt_qty(prd.get("design_capacity_annual")),
            ramp_points=tuple((float(a), float(b)) for a, b in (prd.get("ramp_points") or ((0, 0.5), (2, 0.9), (4, 1.0)))),
            qualification_gate=_tup(prd.get("qualification_gate")),
            required_capital_goods=_tup(prd.get("required_capital_goods")),
            capex=_opt_qty(prd.get("capex")),
            owner_org=str(prd.get("owner_org", "")),
        )
        w.add(prj)
        w.link(prj.id, "enabled_by_project", prj.item_id)
        for ev in prj.evidence_ids:
            pk.evidence_or_fail(ev)

    for cc in raw.get("capability_claims", []) or []:
        vec = CapabilityVector(dict(cc.get("vector") or {}))
        claim = CapabilityClaim(
            id=str(cc["id"]), name=str(cc.get("name", cc["id"])), kind="capability_claim",
            notes=str(cc.get("notes", "")), evidence_ids=_tup(cc.get("evidence_ids")),
            capability_item=str(cc["capability_item"]), org_id=str(cc.get("org_id", "")),
            geography=str(cc.get("geography", "INDIA")), vector=vec,
            claim_vs_assessment=str(cc.get("claim_vs_assessment", "assessment")),
        )
        w.add(claim)
        w.link(claim.id, "derived_from", claim.capability_item)

    for qd in raw.get("qualifications", []) or []:
        q = Qualification(
            id=str(qd["id"]), name=str(qd.get("name", qd["id"])), kind="qualification",
            item_id=str(qd["item_id"]), qualifier=str(qd.get("qualifier", "customer")),
            standard_ref=str(qd.get("standard_ref", "")),
            status=str(qd.get("status", "not_started")),
            latency_months=_pair(qd.get("latency_months"), (6.0, 24.0)),
            evidence_ids=_tup(qd.get("evidence_ids")),
        )
        w.add(q)
        w.link(q.id, "gated_by", q.item_id)

    for dd in raw.get("demand_pools", []) or []:
        dp = DemandPool(
            id=str(dd["id"]), name=str(dd.get("name", dd["id"])), kind="demand_pool",
            resource_id=str(dd["resource_id"]),
            baseline_annual=_opt_qty(dd.get("baseline_annual")),
            contestable_fraction=float(dd.get("contestable_fraction", 0.15)),
            geography=str(dd.get("geography", "GLOBAL")),
            growth_pa=float(dd.get("growth_pa", 0.03)),
            note=str(dd.get("note", "")),
        )
        w.add(dp)
        w.link(dp.id, "competes_for", dp.resource_id)

    for cod in raw.get("corridors", []) or []:
        c = TransportCorridor(
            id=str(cod["id"]), name=str(cod.get("name", cod["id"])), kind="corridor",
            from_geo=str(cod.get("from_geo", "")), to_geo=str(cod.get("to_geo", "")),
            mode=str(cod.get("mode", "maritime")),
            transit_days=_pair(cod.get("transit_days"), (10.0, 40.0)),
            capacity_te_per_year=_opt_qty(cod.get("capacity_te_per_year")),
            disruption_exposure=_tup(cod.get("disruption_exposure")),
        )
        w.add(c)

    for sd in raw.get("shocks", []) or []:
        sh = Shock(
            id=str(sd["id"]), name=str(sd.get("name", sd["id"])), kind="shock",
            notes=str(sd.get("notes", "")), evidence_ids=_tup(sd.get("evidence_ids")),
            shock_id=str(sd["id"]), description=str(sd.get("description", "")),
            edits=tuple(dict(e) for e in (sd.get("edits") or [])),
        )
        w.add(sh)
        pk.shocks[sh.id] = sh

    for sb in raw.get("substitutions", []) or []:
        _validate_substitution(sb, pk)
        pk.substitutions[str(sb["id"])] = dict(sb)
        se = SubstitutionEntity(
            id=str(sb["id"]), name=str(sb.get("name", sb["id"])), kind="substitution",
            notes=str(sb.get("notes", "")), evidence_ids=_tup(sb.get("evidence_ids")),
        )
        w.add(se)
        w.link(se.id, "substitutable_with", str(sb["replaces_part"]))
        w.link(se.id, "produced_via", str(sb["alternative_recipe"]))

    for cwd in raw.get("crosswalks", []) or []:
        if "from_code" not in cwd or "to_entity" not in cwd:
            raise PackValidationError(f"crosswalk missing fields: {cwd}")
        pk.crosswalks.append(dict(cwd))

    _validate_pack_integrity(pk)
    return pk


def ResourceClassStub(rid: str):
    from .model import ResourceClass
    return ResourceClass(id=rid, name=rid, kind="resource_class")


def _validate_pack_integrity(pk: KnowledgePack):
    w = pk.world
    for r in w.of_kind("recipe"):
        for st in r.steps:
            if not (0.0 < st.yield_fraction <= 1.0):
                raise PackValidationError(f"recipe '{r.id}' step '{st.id}' yield out of (0,1]")
            if not (0.0 <= st.scrap_fraction < 1.0):
                raise PackValidationError(f"recipe '{r.id}' step '{st.id}' scrap out of [0,1)")
    for seg in w.of_kind("capacity_segment"):
        for f in (seg.availability, seg.utilization, seg.yield_fraction, seg.qualification_fraction):
            if not (0.0 <= f <= 1.0):
                raise PackValidationError(f"capacity segment '{seg.id}' factor out of [0,1]")
    for prj in w.of_kind("project"):
        if prj.design_capacity_annual is not None and prj.design_capacity_annual.value < 0:
            raise PackValidationError(f"project '{prj.id}' negative capacity")
    for vid, vd in pk.variants.items():
        if not vd.get("bom"):
            raise PackValidationError(f"variant '{vid}' has no BOM")
