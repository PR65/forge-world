"""Canonical, evidence-linked read model for the FORGE WORLD knowledge packs.

The solver intentionally keeps each :class:`~forge.pack.KnowledgePack` isolated.
This module is the complementary read projection: it gives pack-local records a
stable namespace and binds only explicitly declared, reusable concepts to
canonical identifiers.  A binding is not a capability assessment and never
creates capacity, supply, qualification, or builder status.

The module also contains the small ingestion boundary used by future adapters.
Source snapshots and observations are immutable; an observation becomes an
``EvidenceRecord`` only through an explicit promotion call.  Nothing in the
registry loader promotes observations automatically.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import yaml

from .evidence import EvidenceRecord, Source, world_snapshot
from .epistemics import EpistemicClass
from .pack import KnowledgePack, load_pack


REGISTRY_VERSION = "0.1.0"
_VALID_EPISTEMIC = {e.value for e in EpistemicClass}


def _jsonable(value: Any) -> Any:
    """Return a deterministic JSON-compatible representation.

    YAML mappings preserve insertion order, while registry identity must not
    depend on formatting or ordering in a source file.  This helper is kept
    local so the canonical projection does not alter solver serialization.
    """

    if hasattr(value, "to_json"):
        return _jsonable(value.to_json())
    if isinstance(value, Mapping):
        return {str(k): _jsonable(value[k]) for k in sorted(value, key=lambda x: str(x))}
    if isinstance(value, (tuple, list)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (set, frozenset)):
        return sorted((_jsonable(v) for v in value), key=lambda x: json.dumps(x, sort_keys=True))
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "value") and not isinstance(value, (str, bytes)):
        # Enum values are stable strings in the model; do not call ``value`` on
        # arbitrary numeric objects unless they also expose a unit.
        return _jsonable(value.value)
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def namespace(pack_id: str, entity_id: str) -> str:
    """Return the public identifier for a pack-local entity."""

    return f"pack:{pack_id}:{entity_id}"


def evidence_namespace(pack_id: str, claim_id: str) -> str:
    return f"pack:{pack_id}:evidence:{claim_id}"


def source_namespace(pack_id: str, source_id: str) -> str:
    return f"pack:{pack_id}:source:{source_id}"


def _freeze(value: Any) -> Any:
    """Recursively freeze registry state while keeping JSON export lossless."""

    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze(item) for item in value)
    return value


def _freeze_mapping(value: Optional[Mapping[str, Any]]) -> Mapping[str, Any]:
    return _freeze(dict(value or {}))


@dataclass(frozen=True)
class SourceSnapshot:
    """Immutable reference to one retrieved source state.

    Only metadata and a content/metadata hash are retained for referenced web
    pages.  The registry deliberately does not mirror raw third-party pages.
    ``snapshot_id`` is derived when omitted, so construction remains
    deterministic and does not depend on wall-clock time.
    """

    source_id: str
    content_hash: str = ""
    hash_scope: str = "reference_metadata"
    raw_payload_stored: bool = False
    access_date: str = ""
    license: str = "UNSPECIFIED"
    storage_posture: str = "reference_only"
    url: str = ""
    source_type: str = "document"
    metadata: Mapping[str, Any] = field(default_factory=dict)
    snapshot_id: str = ""

    def __post_init__(self) -> None:
        content_hash = self.content_hash
        if not content_hash:
            content_hash = _sha256(
                {
                    "source_id": self.source_id,
                    "access_date": self.access_date,
                    "license": self.license,
                    "url": self.url,
                    "source_type": self.source_type,
                    "metadata": self.metadata,
                }
            )
            object.__setattr__(self, "content_hash", content_hash)
        if not self.snapshot_id:
            object.__setattr__(
                self,
                "snapshot_id",
                f"source-snapshot:{self.source_id}:{content_hash[:16]}",
            )
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))

    @classmethod
    def from_source(cls, source: Source, *, namespaced_id: Optional[str] = None) -> "SourceSnapshot":
        payload = source.to_json()
        # The hash covers the source reference metadata, not the page body.  It
        # therefore remains rights-safe and changes when a source reference is
        # corrected.
        return cls(
            source_id=namespaced_id or source.id,
            content_hash=_sha256(payload),
            hash_scope="reference_metadata",
            raw_payload_stored=False,
            access_date=source.access_date,
            license=source.license,
            storage_posture="reference_only",
            url=source.url,
            source_type=source.source_type,
            metadata={"name": source.name, "publisher": source.publisher, "notes": source.notes},
        )

    def to_json(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "source_id": self.source_id,
            "content_hash": self.content_hash,
            "hash_scope": self.hash_scope,
            "raw_payload_stored": self.raw_payload_stored,
            "access_date": self.access_date,
            "license": self.license,
            "storage_posture": self.storage_posture,
            "url": self.url,
            "source_type": self.source_type,
            "metadata": _jsonable(self.metadata),
        }


@dataclass(frozen=True)
class Observation:
    """Normalized, immutable observation prior to evidence promotion."""

    observation_id: str
    source_snapshot_id: str
    subject: str
    predicate: str
    value_text: str = ""
    value_quantity: Optional[Tuple[float, str]] = None
    epistemic_class: EpistemicClass = EpistemicClass.UNKNOWN
    observed_at: str = ""
    geographic_scope: str = "GLOBAL"
    technical_scope: str = ""
    caveat: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.epistemic_class, EpistemicClass):
            object.__setattr__(self, "epistemic_class", EpistemicClass(str(self.epistemic_class)))
        if self.value_quantity is not None:
            if len(self.value_quantity) != 2:
                raise ValueError("value_quantity must be (value, unit)")
            object.__setattr__(
                self,
                "value_quantity",
                (float(self.value_quantity[0]), str(self.value_quantity[1])),
            )
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))

    def to_json(self) -> Dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "source_snapshot_id": self.source_snapshot_id,
            "subject": self.subject,
            "predicate": self.predicate,
            "value_text": self.value_text,
            "value_quantity": list(self.value_quantity) if self.value_quantity else None,
            "epistemic_class": self.epistemic_class.value,
            "observed_at": self.observed_at,
            "geographic_scope": self.geographic_scope,
            "technical_scope": self.technical_scope,
            "caveat": self.caveat,
            "metadata": _jsonable(self.metadata),
        }


@dataclass(frozen=True)
class Promotion:
    """Audit record for an explicit Observation -> EvidenceRecord promotion."""

    observation_id: str
    claim_id: str
    source_snapshot_id: str
    reviewer: str = ""
    promoted_at: str = ""
    rationale: str = ""

    def to_json(self) -> Dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "claim_id": self.claim_id,
            "source_snapshot_id": self.source_snapshot_id,
            "reviewer": self.reviewer,
            "promoted_at": self.promoted_at,
            "rationale": self.rationale,
        }


def promote_observation(
    observation: Observation,
    source_snapshot: SourceSnapshot,
    *,
    claim_id: Optional[str] = None,
    reviewer: str = "",
    promoted_at: str = "",
    rationale: str = "",
) -> Tuple[EvidenceRecord, Promotion]:
    """Explicitly promote an observation into an immutable evidence record.

    The source snapshot must be supplied by the caller and must match the
    observation reference.  This makes it impossible for a parser to silently
    mutate the checked-in registry merely by fetching a page.  UNKNOWN remains
    UNKNOWN unless the caller explicitly supplies a new observation with a
    different epistemic class and rationale.
    """

    if observation.source_snapshot_id != source_snapshot.snapshot_id:
        raise ValueError("observation source_snapshot_id does not match supplied source snapshot")
    if observation.epistemic_class in (EpistemicClass.MEASURED, EpistemicClass.REPORTED):
        if not source_snapshot.source_id.strip():
            raise ValueError(f"{observation.epistemic_class.value} promotion requires a source id")
        if not source_snapshot.license.strip() or source_snapshot.license.strip().upper() == "UNSPECIFIED":
            raise ValueError(f"{observation.epistemic_class.value} promotion requires a declared source license")
    cid = str(claim_id or observation.observation_id)
    rec = EvidenceRecord(
        claim_id=cid,
        subject=observation.subject,
        predicate=observation.predicate,
        epistemic_class=observation.epistemic_class,
        value_text=observation.value_text,
        value_quantity=observation.value_quantity,
        source_ids=(source_snapshot.source_id,),
        effective_date=observation.observed_at,
        retrieval_date=source_snapshot.access_date,
        geographic_scope=observation.geographic_scope,
        technical_scope=observation.technical_scope,
        extraction_method="promoted_observation",
        license=source_snapshot.license,
        review_status="promoted",
        quote_or_caveat=observation.caveat,
    )
    promotion = Promotion(
        observation_id=observation.observation_id,
        claim_id=cid,
        source_snapshot_id=source_snapshot.snapshot_id,
        reviewer=reviewer,
        promoted_at=promoted_at,
        rationale=rationale,
    )
    return rec, promotion


@dataclass(frozen=True)
class RegistryNode:
    id: str
    name: str
    kind: str
    pack_id: Optional[str]
    canonical_id: Optional[str]
    epistemic_class: str
    evidence_ids: Tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        klass = self.epistemic_class.value if isinstance(self.epistemic_class, EpistemicClass) else str(self.epistemic_class)
        if klass not in _VALID_EPISTEMIC:
            raise ValueError(f"unknown epistemic class '{klass}'")
        object.__setattr__(self, "epistemic_class", klass)
        object.__setattr__(self, "evidence_ids", tuple(str(x) for x in self.evidence_ids))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))

    def to_json(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "pack_id": self.pack_id,
            "canonical_id": self.canonical_id,
            "epistemic_class": self.epistemic_class,
            "evidence_ids": list(self.evidence_ids),
            "metadata": _jsonable(self.metadata),
        }


@dataclass(frozen=True)
class RegistryEdge:
    source: str
    target: str
    relation: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))

    def to_json(self) -> Dict[str, Any]:
        # source/target are the public graph vocabulary; src/dst aliases make
        # the projection convenient for callers that consume forge.model.Edge.
        return {
            "source": self.source,
            "target": self.target,
            "src": self.source,
            "dst": self.target,
            "relation": self.relation,
            "meta": _jsonable(self.metadata),
            "metadata": _jsonable(self.metadata),
        }


@dataclass(frozen=True)
class PackSnapshot:
    pack_id: str
    version: str
    path: str
    content_hash: str
    entity_count: int
    edge_count: int
    source_ids: Tuple[str, ...] = ()
    evidence_ids: Tuple[str, ...] = ()

    @property
    def hash(self) -> str:
        return self.content_hash

    def to_json(self) -> Dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "version": self.version,
            "path": self.path,
            "hash": self.content_hash,
            "content_hash": self.content_hash,
            "entity_count": self.entity_count,
            "edge_count": self.edge_count,
            "source_ids": list(self.source_ids),
            "evidence_ids": list(self.evidence_ids),
        }


@dataclass(frozen=True)
class RegistrySnapshot:
    registry_version: str
    snapshot_id: str
    content_hash: str
    manifest_hash: str
    pack_snapshots: Tuple[PackSnapshot, ...]
    source_snapshots: Tuple[SourceSnapshot, ...]

    @property
    def hash(self) -> str:
        return self.content_hash

    def to_json(self) -> Dict[str, Any]:
        return {
            "registry_version": self.registry_version,
            "snapshot_id": self.snapshot_id,
            "hash": self.content_hash,
            "content_hash": self.content_hash,
            "manifest_hash": self.manifest_hash,
            "pack_snapshots": [p.to_json() for p in self.pack_snapshots],
            "source_snapshots": [s.to_json() for s in self.source_snapshots],
        }


def _normalise_epistemic(value: Any, default: str = EpistemicClass.UNKNOWN.value) -> str:
    if isinstance(value, EpistemicClass):
        return value.value
    candidate = str(value or default).upper()
    return candidate if candidate in _VALID_EPISTEMIC else default


def _value_signature(rec: EvidenceRecord) -> Tuple[Any, ...]:
    return (rec.value_text, rec.value_quantity, rec.unit_note)


def _has_unknown_marker(entity: Any) -> bool:
    fields: List[Any] = []
    for name in getattr(entity, "__dataclass_fields__", {}):
        try:
            fields.append(getattr(entity, name))
        except Exception:
            continue
    blob = _canonical_json(fields).upper()
    return "UNKNOWN" in blob


class CanonicalRegistry:
    """Versioned read projection over all checked-in knowledge packs."""

    def __init__(
        self,
        packs: Sequence[KnowledgePack],
        manifest: Optional[Mapping[str, Any]] = None,
        *,
        manifest_path: str = "",
    ) -> None:
        self.packs: Tuple[KnowledgePack, ...] = tuple(sorted(packs, key=lambda p: p.pack_id))
        self.manifest: Dict[str, Any] = dict(_jsonable(manifest or {}))
        self.manifest_path = str(manifest_path)
        self.nodes: Dict[str, RegistryNode] = {}
        self.edges: List[RegistryEdge] = []
        self.sources: Dict[str, Source] = {}
        self.evidence: Dict[str, EvidenceRecord] = {}
        self.source_snapshots: Dict[str, SourceSnapshot] = {}
        self.pack_snapshots: Dict[str, PackSnapshot] = {}
        self.aliases: Dict[str, Dict[str, Any]] = {}
        self.evidence_tasks: Dict[str, Dict[str, Any]] = {}
        self._canonical_alias_lookup: Dict[str, str] = {}
        self._local_to_public: Dict[Tuple[str, str], str] = {}
        self._build()

    @classmethod
    def from_files(
        cls,
        packs_dir: Path | str,
        manifest_path: Path | str,
        *,
        pack_ids: Optional[Iterable[str]] = None,
    ) -> "CanonicalRegistry":
        root = Path(packs_dir)
        selected = set(str(x) for x in pack_ids) if pack_ids is not None else None
        paths = sorted(root.glob("*.yaml"), key=lambda p: p.stem)
        packs = []
        for path in paths:
            if selected is not None and path.stem not in selected:
                continue
            packs.append(load_pack(str(path)))
        if selected:
            missing = selected - {p.pack_id for p in packs}
            if missing:
                raise FileNotFoundError(f"pack(s) not found: {sorted(missing)}")
        mpath = Path(manifest_path)
        if mpath.exists():
            with mpath.open("r", encoding="utf-8") as handle:
                manifest = yaml.safe_load(handle) or {}
        else:
            raise FileNotFoundError(f"registry manifest not found: {mpath}")
        return cls(packs, manifest, manifest_path=str(mpath))

    def _build(self) -> None:
        # Build pack snapshots and evidence/source indexes first.  They are
        # independent of manifest order and therefore deterministic.
        for pk in self.packs:
            self._index_pack_metadata(pk)
        self._index_pack_entities()
        self._index_manifest()
        self._sort_edges()
        self._snapshot = self._make_snapshot()

    def _index_pack_metadata(self, pk: KnowledgePack) -> None:
        source_ids: List[str] = []
        for sid, src in sorted(pk.sources.items()):
            public_sid = source_namespace(pk.pack_id, sid)
            source_ids.append(public_sid)
            self.sources[public_sid] = src
            self.source_snapshots[public_sid] = SourceSnapshot.from_source(src, namespaced_id=public_sid)

        evidence_ids: List[str] = []
        for cid, rec in sorted(pk.evidence.items()):
            public_cid = evidence_namespace(pk.pack_id, cid)
            evidence_ids.append(public_cid)
            self.evidence[public_cid] = rec

        raw_payload = {
            "pack_id": pk.pack_id,
            "title": pk.title,
            "version": pk.version,
            "geography_focus": pk.geography_focus,
            "raw": pk.raw,
            "typed_world": world_snapshot(pk.world),
            "sources": {k: v.to_json() for k, v in sorted(pk.sources.items())},
            "evidence": {k: v.to_json() for k, v in sorted(pk.evidence.items())},
        }
        self.pack_snapshots[pk.pack_id] = PackSnapshot(
            pack_id=pk.pack_id,
            version=pk.version,
            # Store a repository-relative logical path, not the loader's
            # absolute checkout path, so snapshots compare across environments.
            path=f"packs/{pk.pack_id}.yaml" if pk.path else "",
            content_hash=_sha256(raw_payload),
            entity_count=len(pk.world.entities),
            edge_count=len(pk.world.edges),
            source_ids=tuple(source_ids),
            evidence_ids=tuple(evidence_ids),
        )

    def _entity_evidence(self, pk: KnowledgePack, entity: Any) -> Tuple[str, ...]:
        local_ids = tuple(str(x) for x in getattr(entity, "evidence_ids", ()) or ())
        return tuple(evidence_namespace(pk.pack_id, x) for x in local_ids)

    def _entity_epistemic(self, pk: KnowledgePack, entity: Any, evidence_ids: Sequence[str]) -> Tuple[str, Dict[str, Any]]:
        explicit = getattr(entity, "epistemic_class", None)
        explicit_class = _normalise_epistemic(explicit, "") if explicit else ""
        recs = [self.evidence[eid] for eid in evidence_ids if eid in self.evidence]
        superseded_claim_ids = {str(r.supersedes) for r in recs if r.supersedes}
        active_recs = [r for r in recs if r.claim_id not in superseded_claim_ids]
        classes = sorted({r.epistemic_class.value for r in active_recs})
        details: Dict[str, Any] = {
            "epistemic_classes": classes,
            "local_evidence_ids": [x.split(":evidence:", 1)[-1] for x in evidence_ids],
        }
        if superseded_claim_ids:
            details["superseded_evidence_ids"] = sorted(
                evidence_namespace(pk.pack_id, claim_id) for claim_id in superseded_claim_ids
            )

        # Detect contradictions before applying a typed entity's summary class.
        # A pack may carry an explicit REPORTED label while two linked records
        # disagree; flattening that disagreement would violate C17.
        by_subject_predicate: Dict[Tuple[str, str], List[EvidenceRecord]] = {}
        for rec in active_recs:
            by_subject_predicate.setdefault((rec.subject, rec.predicate), []).append(rec)
        conflicts: List[str] = []
        for same_key in by_subject_predicate.values():
            signatures = {_value_signature(r) for r in same_key}
            if len(signatures) > 1:
                conflicts.extend(evidence_namespace(pk.pack_id, r.claim_id) for r in same_key)
        if conflicts or any(r.epistemic_class == EpistemicClass.CONFLICTED for r in active_recs):
            if conflicts:
                details["conflicting_evidence_ids"] = sorted(set(conflicts))
            klass = EpistemicClass.CONFLICTED.value
        # A typed capacity segment's own epistemic class is authoritative for
        # that parameter when there is no contradiction. Unknown markers in a
        # capability vector are likewise retained even when the claim has no
        # linked source.
        elif explicit_class:
            klass = explicit_class
        elif _has_unknown_marker(entity):
            klass = EpistemicClass.UNKNOWN.value
        elif not active_recs:
            klass = EpistemicClass.UNKNOWN.value
        else:
            if len(classes) == 1:
                klass = classes[0]
            elif EpistemicClass.UNKNOWN.value in classes:
                # An unresolved observation keeps the aggregate unresolved; the
                # full class set remains visible in metadata.
                klass = EpistemicClass.UNKNOWN.value
            else:
                # The aggregate is not a numerical parameter.  Preserve a
                # conservative modelled status rather than claiming the most
                # authoritative record dominates all others.
                klass = EpistemicClass.MODELLED.value
        return klass, details

    def _index_pack_entities(self) -> None:
        for pk in self.packs:
            local_to_public: Dict[str, str] = {}
            for local_id, entity in sorted(pk.world.entities.items()):
                public_id = namespace(pk.pack_id, local_id)
                local_to_public[local_id] = public_id
                self._local_to_public[(pk.pack_id, local_id)] = public_id
                evidence_ids = self._entity_evidence(pk, entity)
                klass, epistemic_meta = self._entity_epistemic(pk, entity, evidence_ids)
                metadata: Dict[str, Any] = {
                    "local_id": local_id,
                    "notes": getattr(entity, "notes", ""),
                    "tags": list(getattr(entity, "tags", ()) or ()),
                    **epistemic_meta,
                }
                # Keep the typed record useful to read clients without exposing
                # raw YAML or changing the solver's model classes.
                try:
                    typed = entity.to_json()
                    if isinstance(typed, dict):
                        metadata["typed"] = _jsonable(typed)
                except Exception:
                    pass
                self.nodes[public_id] = RegistryNode(
                    id=public_id,
                    name=str(getattr(entity, "name", local_id)),
                    kind=str(getattr(entity, "kind", "entity")),
                    pack_id=pk.pack_id,
                    canonical_id=None,
                    epistemic_class=klass,
                    evidence_ids=evidence_ids,
                    metadata=metadata,
                )

            for edge in pk.world.edges:
                src = local_to_public.get(edge.src, namespace(pk.pack_id, edge.src))
                dst = local_to_public.get(edge.dst, namespace(pk.pack_id, edge.dst))
                self.edges.append(
                    RegistryEdge(
                        source=src,
                        target=dst,
                        relation=edge.relation,
                        metadata={"pack_id": pk.pack_id, **dict(edge.meta)},
                    )
                )

    def _manifest_capabilities(self) -> Sequence[Mapping[str, Any]]:
        value = self.manifest.get("canonical_capabilities", ())
        return value if isinstance(value, list) else ()

    def _canonical_resolve(self, value: str) -> Optional[str]:
        if value in self._canonical_alias_lookup:
            return self._canonical_alias_lookup[value]
        if value.startswith("cap:") and value in self.nodes:
            return value
        return None

    def _add_manifest_node(
        self,
        *,
        node_id: str,
        name: str,
        kind: str,
        epistemic_class: Any = EpistemicClass.UNKNOWN.value,
        evidence_ids: Sequence[str] = (),
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        if node_id in self.nodes:
            # Manifest IDs are explicit and duplicate definitions should fail
            # loudly instead of silently merging unsupported assertions.
            raise ValueError(f"duplicate registry node id '{node_id}'")
        self.nodes[node_id] = RegistryNode(
            id=node_id,
            name=name,
            kind=kind,
            pack_id=None,
            canonical_id=node_id,
            epistemic_class=_normalise_epistemic(epistemic_class),
            evidence_ids=tuple(evidence_ids),
            metadata=metadata or {},
        )

    def _manifest_evidence_ids(self, refs: Sequence[Any], default_pack: Optional[str] = None) -> Tuple[str, ...]:
        out: List[str] = []
        for ref in refs or ():
            raw = str(ref)
            if raw in self.evidence:
                out.append(raw)
                continue
            if raw.startswith("pack:") and raw.count(":") >= 3:
                out.append(raw)
                continue
            if ":" in raw:
                pid, cid = raw.split(":", 1)
                candidate = evidence_namespace(pid, cid)
                if candidate in self.evidence:
                    out.append(candidate)
                    continue
            if default_pack:
                candidate = evidence_namespace(default_pack, raw)
                if candidate in self.evidence:
                    out.append(candidate)
                    continue
            # Retain an explicit unresolved reference in metadata via caller;
            # do not turn it into an invented evidence record.
        return tuple(dict.fromkeys(out))

    def _manifest_bindings(self, entry: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
        bindings = entry.get("mappings", entry.get("bindings", ()))
        return bindings if isinstance(bindings, list) else ()

    def _index_manifest(self) -> None:
        # Canonical capability nodes are always UNKNOWN unless the checked-in
        # manifest explicitly carries a supported evidence reference.  Mapping
        # rows default to ASSUMPTION because they are ontology decisions, not
        # observations about capability status.
        for entry in sorted(self._manifest_capabilities(), key=lambda x: str(x.get("id", ""))):
            cid = str(entry.get("id", ""))
            if not cid:
                raise ValueError("canonical capability requires id")
            if not cid.startswith("cap:"):
                cid = f"cap:{cid}"
            name = str(entry.get("name", cid.removeprefix("cap:").replace("-", " ").title()))
            refs = self._manifest_evidence_ids(entry.get("evidence_ids", ()), entry.get("pack_id"))
            metadata = {
                "description": str(entry.get("description", "")),
                "status": str(entry.get("status", "UNKNOWN")),
                "mapping_source": str(entry.get("mapping_source", "ASSUMPTION")),
                "aliases": [str(a) for a in entry.get("aliases", ()) or ()],
                "mapping_count": 0,
                "mapped_pack_ids": [],
                "mapped_entity_ids": [],
                "evidence_task_ids": [],
            }
            self._add_manifest_node(
                node_id=cid,
                name=name,
                kind="capability",
                epistemic_class=entry.get("epistemic_class", EpistemicClass.UNKNOWN.value),
                evidence_ids=refs,
                metadata=metadata,
            )
            self._canonical_alias_lookup[cid] = cid
            for alias in entry.get("aliases", ()) or ():
                alias_text = str(alias)
                self._canonical_alias_lookup[alias_text] = cid
                # Accept explicit cap:-prefixed spellings in both kebab and
                # snake forms while retaining one canonical node identity.
                alias_slug = _slug(alias_text)
                self._canonical_alias_lookup[f"cap:{alias_slug}"] = cid
                self._canonical_alias_lookup[f"cap:{alias_slug.replace('-', '_')}"] = cid

            for binding in self._manifest_bindings(entry):
                pack_id = str(binding.get("pack_id", ""))
                local_ids = binding.get("entity_ids", binding.get("entity_id", ()))
                if isinstance(local_ids, str):
                    local_ids = [local_ids]
                if not isinstance(local_ids, list):
                    continue
                relation = str(binding.get("relation", "maps_to_canonical"))
                basis = str(binding.get("mapping_source", binding.get("epistemic_class", "ASSUMPTION")))
                rationale = str(binding.get("rationale", ""))
                for local_id in local_ids:
                    public_id = self._local_to_public.get((pack_id, str(local_id)))
                    if not public_id:
                        # Bad manifest references are not silently interpreted as
                        # new entities.  Keep the task/read model loadable while
                        # exposing the unresolved row in capability metadata.
                        unresolved = self.nodes[cid].metadata.get("unresolved_mappings", [])
                        unresolved = list(unresolved) if isinstance(unresolved, (list, tuple)) else []
                        unresolved.append({"pack_id": pack_id, "entity_id": str(local_id)})
                        merged = dict(self.nodes[cid].metadata)
                        merged["unresolved_mappings"] = sorted(unresolved, key=lambda x: (x["pack_id"], x["entity_id"]))
                        self.nodes[cid] = RegistryNode(
                            id=self.nodes[cid].id,
                            name=self.nodes[cid].name,
                            kind=self.nodes[cid].kind,
                            pack_id=self.nodes[cid].pack_id,
                            canonical_id=self.nodes[cid].canonical_id,
                            epistemic_class=self.nodes[cid].epistemic_class,
                            evidence_ids=self.nodes[cid].evidence_ids,
                            metadata=merged,
                        )
                        continue
                    existing = self.nodes[public_id]
                    merged = dict(existing.metadata)
                    canonical_ids = list(merged.get("canonical_ids", []))
                    if cid not in canonical_ids:
                        canonical_ids.append(cid)
                    merged["canonical_ids"] = sorted(canonical_ids)
                    mappings = list(merged.get("canonical_mappings", []))
                    mapping_record = {
                        "canonical_id": cid,
                        "mapping_source": basis,
                        "rationale": rationale,
                    }
                    if mapping_record not in mappings:
                        mappings.append(mapping_record)
                    merged["canonical_mappings"] = sorted(
                        mappings, key=lambda x: (str(x.get("canonical_id", "")), str(x.get("rationale", "")))
                    )
                    self.nodes[public_id] = RegistryNode(
                        id=existing.id,
                        name=existing.name,
                        kind=existing.kind,
                        pack_id=existing.pack_id,
                        canonical_id=cid if not existing.canonical_id else existing.canonical_id,
                        epistemic_class=existing.epistemic_class,
                        evidence_ids=existing.evidence_ids,
                        metadata=merged,
                    )
                    self.edges.append(
                        RegistryEdge(
                            source=public_id,
                            target=cid,
                            relation=relation,
                            metadata={
                                "pack_id": pack_id,
                                "local_entity_id": str(local_id),
                                "mapping_source": basis,
                                "epistemic_class": "ASSUMPTION",
                                "rationale": rationale,
                            },
                        )
                    )
                    cap_node = self.nodes[cid]
                    cap_meta = dict(cap_node.metadata)
                    cap_meta["mapping_count"] = int(cap_meta.get("mapping_count", 0)) + 1
                    cap_meta["mapped_pack_ids"] = sorted(
                        set(list(cap_meta.get("mapped_pack_ids", ())) + [pack_id])
                    )
                    cap_meta["mapped_entity_ids"] = sorted(
                        set(list(cap_meta.get("mapped_entity_ids", ())) + [public_id])
                    )
                    self.nodes[cid] = RegistryNode(
                        id=cap_node.id,
                        name=cap_node.name,
                        kind=cap_node.kind,
                        pack_id=cap_node.pack_id,
                        canonical_id=cap_node.canonical_id,
                        epistemic_class=cap_node.epistemic_class,
                        evidence_ids=cap_node.evidence_ids,
                        metadata=cap_meta,
                    )

        # Aliases are separate records.  They never overwrite pack-local names
        # or fuzzy-match entities.
        aliases = self.manifest.get("aliases", ())
        if isinstance(aliases, list):
            for row in aliases:
                if not isinstance(row, Mapping):
                    continue
                alias_id = str(row.get("id", ""))
                alias = str(row.get("alias", row.get("name", "")))
                target = str(row.get("canonical_id", row.get("target", "")))
                if not alias_id:
                    alias_id = f"alias:{_slug(alias)}"
                canonical = self._canonical_resolve(target) or target
                record = {
                    "id": alias_id,
                    "alias": alias,
                    "canonical_id": canonical,
                    "kind": str(row.get("kind", "capability_alias")),
                    "epistemic_class": "ASSUMPTION",
                    "evidence_ids": list(self._manifest_evidence_ids(row.get("evidence_ids", ()), row.get("pack_id"))),
                    "metadata": {"mapping_source": str(row.get("mapping_source", "ASSUMPTION"))},
                }
                self.aliases[alias_id] = record
                if alias:
                    self._canonical_alias_lookup[alias] = canonical
                if canonical in self.nodes:
                    aliases_for_node = list(self.nodes[canonical].metadata.get("aliases", []))
                    if alias and alias not in aliases_for_node:
                        aliases_for_node.append(alias)
                    meta = dict(self.nodes[canonical].metadata)
                    meta["aliases"] = sorted(aliases_for_node)
                    self.nodes[canonical] = RegistryNode(
                        id=self.nodes[canonical].id,
                        name=self.nodes[canonical].name,
                        kind=self.nodes[canonical].kind,
                        pack_id=self.nodes[canonical].pack_id,
                        canonical_id=self.nodes[canonical].canonical_id,
                        epistemic_class=self.nodes[canonical].epistemic_class,
                        evidence_ids=self.nodes[canonical].evidence_ids,
                        metadata=meta,
                    )

        self._index_builders()
        self._index_evidence_tasks()

    def _index_builders(self) -> None:
        rows = self.manifest.get("builders", ())
        if not isinstance(rows, list):
            return
        for row in sorted((x for x in rows if isinstance(x, Mapping)), key=lambda x: str(x.get("id", ""))):
            bid = str(row.get("id", ""))
            if not bid:
                continue
            if not bid.startswith("builder:"):
                bid = f"builder:{bid}"
            refs = self._manifest_evidence_ids(row.get("evidence_ids", ()), row.get("pack_id"))
            self._add_manifest_node(
                node_id=bid,
                name=str(row.get("name", bid.removeprefix("builder:").replace("_", " ").title())),
                kind="builder",
                epistemic_class=row.get("epistemic_class", EpistemicClass.UNKNOWN.value),
                evidence_ids=refs,
                metadata={
                    "mapping_source": str(row.get("mapping_source", "ASSUMPTION")),
                    "notes": str(row.get("notes", "")),
                    "capability_ids": [],
                },
            )
            for capability in row.get("capability_ids", ()) or ():
                cid = self._canonical_resolve(str(capability)) or str(capability)
                if cid.startswith("cap:") and cid in self.nodes:
                    edge_meta = {
                        "mapping_source": str(row.get("mapping_source", "ASSUMPTION")),
                        "epistemic_class": "ASSUMPTION",
                        "rationale": str(row.get("capability_rationale", "")),
                    }
                    self.edges.append(RegistryEdge(bid, cid, "associated_with", edge_meta))
                    meta = dict(self.nodes[bid].metadata)
                    ids = list(meta.get("capability_ids", []))
                    if cid not in ids:
                        ids.append(cid)
                    meta["capability_ids"] = sorted(ids)
                    old = self.nodes[bid]
                    self.nodes[bid] = RegistryNode(old.id, old.name, old.kind, old.pack_id, old.canonical_id,
                                                   old.epistemic_class, old.evidence_ids, meta)

            bindings = row.get("mappings", row.get("pack_bindings", ()))
            if isinstance(bindings, Mapping):
                bindings = [bindings]
            for binding in bindings or ():
                if not isinstance(binding, Mapping):
                    continue
                pid = str(binding.get("pack_id", ""))
                local_id = str(binding.get("entity_id", binding.get("org_id", "")))
                public_id = self._local_to_public.get((pid, local_id))
                if public_id:
                    existing = self.nodes[public_id]
                    meta = dict(existing.metadata)
                    meta["builder_ids"] = sorted(set(list(meta.get("builder_ids", [])) + [bid]))
                    self.nodes[public_id] = RegistryNode(existing.id, existing.name, existing.kind, existing.pack_id,
                                                         bid if not existing.canonical_id else existing.canonical_id,
                                                         existing.epistemic_class, existing.evidence_ids, meta)
                    self.edges.append(RegistryEdge(public_id, bid, "maps_to_builder", {
                        "pack_id": pid,
                        "mapping_source": str(binding.get("mapping_source", "ASSUMPTION")),
                        "epistemic_class": "ASSUMPTION",
                    }))

    def _index_evidence_tasks(self) -> None:
        rows = self.manifest.get("evidence_tasks", self.manifest.get("evidence_tasks_open", ()))
        if not isinstance(rows, list):
            return
        for row in sorted((x for x in rows if isinstance(x, Mapping)), key=lambda x: str(x.get("id", ""))):
            tid = str(row.get("id", ""))
            if not tid:
                continue
            target = str(row.get("target_canonical_id", row.get("target", "")))
            target = self._canonical_resolve(target) or target
            task = {
                "id": tid,
                "title": str(row.get("title", row.get("question", tid))),
                "question": str(row.get("question", "")),
                "target_canonical_id": target,
                "status": str(row.get("status", "OPEN")),
                "priority": str(row.get("priority", "medium")),
                "epistemic_class": _normalise_epistemic(row.get("epistemic_class", "UNKNOWN")),
                "evidence_ids": list(self._manifest_evidence_ids(row.get("evidence_ids", ()), row.get("pack_id"))),
                "suggested_source_types": [str(x) for x in row.get("suggested_source_types", ()) or ()],
                "metadata": {
                    "mapping_source": str(row.get("mapping_source", "ASSUMPTION")),
                    "notes": str(row.get("notes", "")),
                },
            }
            self.evidence_tasks[tid] = task
            if target in self.nodes:
                meta = dict(self.nodes[target].metadata)
                tids = list(meta.get("evidence_task_ids", []))
                if tid not in tids:
                    tids.append(tid)
                meta["evidence_task_ids"] = sorted(tids)
                old = self.nodes[target]
                self.nodes[target] = RegistryNode(old.id, old.name, old.kind, old.pack_id, old.canonical_id,
                                                  old.epistemic_class, old.evidence_ids, meta)

    def _sort_edges(self) -> None:
        self.edges.sort(key=lambda e: (e.source, e.target, e.relation, _canonical_json(e.metadata)))

    def _make_snapshot(self) -> RegistrySnapshot:
        manifest_hash = _sha256(self.manifest)
        pack_rows = tuple(self.pack_snapshots[k] for k in sorted(self.pack_snapshots))
        source_rows = tuple(self.source_snapshots[k] for k in sorted(self.source_snapshots))
        payload = {
            "registry_version": self.manifest.get("registry_version", REGISTRY_VERSION),
            "manifest_hash": manifest_hash,
            # Filesystem paths are reporting metadata, not world state.  Keep
            # them in the snapshot response but exclude them from identity so
            # loading an identical checkout from a different directory is
            # still reproducible.
            "packs": [
                {
                    "pack_id": p.pack_id,
                    "version": p.version,
                    "hash": p.content_hash,
                    "entity_count": p.entity_count,
                    "edge_count": p.edge_count,
                    "source_ids": list(p.source_ids),
                    "evidence_ids": list(p.evidence_ids),
                }
                for p in pack_rows
            ],
            "sources": [s.to_json() for s in source_rows],
            "nodes": [self.nodes[k].to_json() for k in sorted(self.nodes)],
            "edges": [e.to_json() for e in self.edges],
            "aliases": [self.aliases[k] for k in sorted(self.aliases)],
            "evidence_tasks": [self.evidence_tasks[k] for k in sorted(self.evidence_tasks)],
        }
        digest = _sha256(payload)
        return RegistrySnapshot(
            registry_version=str(self.manifest.get("registry_version", REGISTRY_VERSION)),
            snapshot_id=f"registry-snapshot:{digest[:16]}",
            content_hash=digest,
            manifest_hash=manifest_hash,
            pack_snapshots=pack_rows,
            source_snapshots=source_rows,
        )

    @property
    def snapshot(self) -> RegistrySnapshot:
        return self._snapshot

    @property
    def snapshot_id(self) -> str:
        return self._snapshot.snapshot_id

    @property
    def content_hash(self) -> str:
        return self._snapshot.content_hash

    def summary(self) -> Dict[str, Any]:
        kinds: Dict[str, int] = {}
        epistemic_counts: Dict[str, int] = {}
        for node in self.nodes.values():
            kinds[node.kind] = kinds.get(node.kind, 0) + 1
            epistemic_counts[node.epistemic_class] = epistemic_counts.get(node.epistemic_class, 0) + 1
        return {
            "registry_version": self._snapshot.registry_version,
            "snapshot_id": self._snapshot.snapshot_id,
            "hash": self._snapshot.content_hash,
            "packs": len(self.packs),
            "pack_ids": [p.pack_id for p in self.packs],
            "pack_count": len(self.packs),
            "nodes": len(self.nodes),
            "node_count": len(self.nodes),
            "edges": len(self.edges),
            "edge_count": len(self.edges),
            "source_count": len(self.sources),
            "evidence_count": len(self.evidence),
            "capabilities": sum(1 for n in self.nodes.values() if n.kind == "capability"),
            "capability_count": sum(1 for n in self.nodes.values() if n.kind == "capability"),
            "builder_count": sum(1 for n in self.nodes.values() if n.kind == "builder"),
            "alias_count": len(self.aliases),
            "evidence_task_count": len(self.evidence_tasks),
            "entity_kinds": dict(sorted(kinds.items())),
            "epistemic_counts": dict(sorted(epistemic_counts.items())),
        }

    def _resolve_id(self, entity_id: str, pack_id: Optional[str] = None) -> Optional[str]:
        raw = str(entity_id)
        if raw in self.nodes:
            return raw
        canonical = self._canonical_alias_lookup.get(raw)
        if canonical in self.nodes:
            return canonical
        if pack_id and (pack_id, raw) in self._local_to_public:
            return self._local_to_public[(pack_id, raw)]
        matches = [public for (pid, local), public in self._local_to_public.items() if local == raw]
        return matches[0] if len(matches) == 1 else None

    def get_entity(self, entity_id: str, *, pack_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        resolved = self._resolve_id(entity_id, pack_id)
        if resolved is None:
            return None
        return self.nodes[resolved].to_json()

    def evidence_for(self, evidence_id: str) -> Optional[Dict[str, Any]]:
        raw = str(evidence_id)
        resolved = raw if raw in self.evidence else None
        if resolved is None and raw.startswith("pack:"):
            resolved = raw
        if resolved is None:
            matches = [k for k in self.evidence if k.endswith(f":evidence:{raw}")]
            resolved = matches[0] if len(matches) == 1 else None
        if resolved is None or resolved not in self.evidence:
            return None
        pack_id = resolved.split(":", 2)[1] if resolved.startswith("pack:") else None
        rec = self.evidence[resolved]
        payload = rec.to_json()
        payload.update({"evidence_id": resolved, "pack_id": pack_id, "local_claim_id": rec.claim_id})
        source_rows = []
        for sid in rec.source_ids:
            source_public = source_namespace(pack_id, sid) if pack_id else sid
            snap = self.source_snapshots.get(source_public)
            if snap:
                source_rows.append(snap.to_json())
        payload["source_snapshots"] = source_rows
        return payload

    def search(
        self,
        query: str = "",
        *,
        kind: Optional[str] = None,
        pack_id: Optional[str] = None,
        limit: int = 25,
    ) -> List[Dict[str, Any]]:
        q = str(query or "").strip().casefold()
        cap = max(0, min(int(limit), 500))
        candidates: List[Tuple[Tuple[Any, ...], RegistryNode]] = []
        for node in self.nodes.values():
            if kind and node.kind != kind:
                continue
            if pack_id and node.pack_id != pack_id:
                continue
            haystack = " ".join(
                [node.id, node.name, node.kind, str(node.metadata.get("local_id", "")),
                 " ".join(str(x) for x in node.metadata.get("aliases", []) or ())]
            ).casefold()
            if q and q not in haystack:
                continue
            exact = 0 if q and (node.id.casefold() == q or node.name.casefold() == q) else 1
            candidates.append(((exact, node.name.casefold(), node.id), node))
        candidates.sort(key=lambda x: x[0])
        return [node.to_json() for _, node in candidates[:cap]]

    def capabilities(self, *, pack_id: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
        rows = [n for n in self.nodes.values() if n.kind == "capability"]
        if pack_id:
            # Canonical nodes are cross-pack; retain one when at least one
            # explicit mapping lands in the requested pack.
            mapped = {
                e.target for e in self.edges
                if e.relation in {"maps_to_canonical", "capability_reference", "requires_or_represents"}
                and e.metadata.get("pack_id") == pack_id
            }
            rows = [n for n in rows if n.id in mapped]
        rows.sort(key=lambda n: n.id)
        return [n.to_json() for n in rows[: max(0, min(int(limit), 500))]]

    def builders(self, *, limit: int = 200) -> List[Dict[str, Any]]:
        rows = sorted((n.to_json() for n in self.nodes.values() if n.kind == "builder"), key=lambda n: n["id"])
        return rows[: max(0, min(int(limit), 500))]

    def tasks(self, *, pack_id: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
        rows = list(self.evidence_tasks.values())
        if pack_id:
            target_ids = {
                e.target for e in self.edges
                if e.metadata.get("pack_id") == pack_id and e.target.startswith("cap:")
            }
            rows = [r for r in rows if r.get("target_canonical_id") in target_ids]
        rows.sort(key=lambda r: (str(r.get("priority", "")), str(r.get("id", ""))))
        return [_jsonable(r) for r in rows[: max(0, min(int(limit), 500))]]

    def slice(
        self,
        *,
        pack_id: Optional[str] = None,
        root: Optional[str] = None,
        depth: int = 2,
        limit: int = 100,
    ) -> Dict[str, Any]:
        cap = max(0, min(int(limit), 1000))
        max_depth = max(0, min(int(depth), 32))
        resolved_root = self._resolve_id(root, pack_id) if root else None
        if resolved_root is None and root:
            return {"nodes": [], "edges": [], "root": None, "truncated": False}

        if resolved_root is None:
            pack_candidates = [
                n.id for n in self.nodes.values()
                if n.kind == "product_variant" and (not pack_id or n.pack_id == pack_id)
            ]
            candidates = pack_candidates or [
                n.id for n in self.nodes.values() if not pack_id or n.pack_id == pack_id
            ]
            resolved_root = sorted(candidates)[0] if candidates else None
        if resolved_root is None:
            return {"nodes": [], "edges": [], "root": None, "truncated": False}

        adjacency: Dict[str, List[str]] = {}
        for edge in self.edges:
            adjacency.setdefault(edge.source, []).append(edge.target)
            adjacency.setdefault(edge.target, []).append(edge.source)
        for values in adjacency.values():
            values.sort()

        visited = {resolved_root}
        frontier = [resolved_root]
        levels = {resolved_root: 0}
        while frontier:
            current = frontier.pop(0)
            current_depth = levels[current]
            if current_depth >= max_depth:
                continue
            for neighbor in adjacency.get(current, []):
                if neighbor in visited or neighbor not in self.nodes:
                    continue
                # A pack filter constrains pack-local nodes, but canonical nodes
                # and mapped nodes remain traversable for cross-pack reuse.
                if pack_id and self.nodes[neighbor].pack_id not in (None, pack_id):
                    continue
                visited.add(neighbor)
                levels[neighbor] = current_depth + 1
                frontier.append(neighbor)

        ordered_ids = sorted(visited, key=lambda nid: (levels.get(nid, 0), nid))
        truncated = False
        if len(ordered_ids) > cap:
            truncated = True
            ordered_ids = ordered_ids[:cap]
        keep = set(ordered_ids)
        rows = [self.nodes[nid].to_json() for nid in ordered_ids]
        edge_rows = [
            e.to_json() for e in self.edges
            if e.source in keep and e.target in keep
        ]
        # A node limit can remove edges even when BFS did not exhaust depth.
        if len(edge_rows) < sum(1 for e in self.edges if e.source in visited and e.target in visited):
            truncated = True
        return {"nodes": rows, "edges": edge_rows, "root": resolved_root, "truncated": truncated}

    def snapshots(self) -> Dict[str, Any]:
        registry_json = self._snapshot.to_json()
        return {
            "snapshot_id": self._snapshot.snapshot_id,
            "hash": self._snapshot.content_hash,
            "manifest_hash": self._snapshot.manifest_hash,
            "registry": registry_json,
            "registry_snapshot": registry_json,
            "packs": [self.pack_snapshots[k].to_json() for k in sorted(self.pack_snapshots)],
            "pack_snapshots": [self.pack_snapshots[k].to_json() for k in sorted(self.pack_snapshots)],
            "sources": [self.source_snapshots[k].to_json() for k in sorted(self.source_snapshots)],
            "source_snapshots": [self.source_snapshots[k].to_json() for k in sorted(self.source_snapshots)],
        }

    def to_json(self) -> Dict[str, Any]:
        return {
            "summary": self.summary(),
            "nodes": [self.nodes[k].to_json() for k in sorted(self.nodes)],
            "edges": [e.to_json() for e in self.edges],
            "aliases": [self.aliases[k] for k in sorted(self.aliases)],
            "evidence_tasks": [self.evidence_tasks[k] for k in sorted(self.evidence_tasks)],
            "snapshots": self.snapshots(),
        }


def _slug(value: str) -> str:
    chars = []
    for ch in str(value).casefold():
        chars.append(ch if ch.isalnum() else "-")
    return "".join(chars).strip("-") or "unknown"


def load_registry(
    packs_dir: Path | str = Path(__file__).resolve().parent.parent / "packs",
    manifest_path: Path | str = Path(__file__).resolve().parent.parent / "data" / "registry" / "manifest.yaml",
    *,
    pack_ids: Optional[Iterable[str]] = None,
) -> CanonicalRegistry:
    """Load the checked-in manifest and every selected YAML pack."""

    return CanonicalRegistry.from_files(packs_dir, manifest_path, pack_ids=pack_ids)


def build_registry(
    packs: Sequence[KnowledgePack],
    manifest: Optional[Mapping[str, Any]] = None,
    *,
    manifest_path: str = "",
) -> CanonicalRegistry:
    """Build a registry from already-loaded packs (useful for adapters/tests)."""

    return CanonicalRegistry(packs, manifest, manifest_path=manifest_path)


# Friendly aliases for integrations that use shorter names.
Registry = CanonicalRegistry
RegistryNodeRecord = RegistryNode


__all__ = [
    "CanonicalRegistry",
    "Registry",
    "RegistryNode",
    "RegistryNodeRecord",
    "RegistryEdge",
    "RegistrySnapshot",
    "PackSnapshot",
    "SourceSnapshot",
    "Observation",
    "Promotion",
    "promote_observation",
    "load_registry",
    "build_registry",
    "namespace",
    "evidence_namespace",
    "source_namespace",
]
