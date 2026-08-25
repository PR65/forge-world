"""Claim-centric staging boundary for FORGE WORLD reality injection.

The staging layer is intentionally separate from the canonical registry and the
solver.  It records what a corpus artifact appears to claim, together with the
unresolved identity, relation, rights, conflict, and freshness decisions that
must be reviewed before an :class:`forge.registry.Observation` can exist.

Nothing in this module mutates a knowledge pack or canonical registry.  In
particular, similar names are never auto-merged and weak proxies (trade,
facility existence, announcements, reserves, or nameplate capacity) are never
silently rewritten as qualified effective supply.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Optional, Sequence, Tuple

from .epistemics import EpistemicClass
from .model import ALLOWED_EDGES
from .registry import Observation, SourceSnapshot


STAGING_SCHEMA_VERSION = "1.0.0"
CSV_REPAIR_VERSION = "1.0.0"


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _jsonable(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((_jsonable(item) for item in value), key=canonical_json)
    if isinstance(value, Path):
        return value.as_posix()
    if hasattr(value, "to_json"):
        return _jsonable(value.to_json())
    return value


def canonical_json(value: Any) -> str:
    """Serialize a staging value deterministically."""

    return json.dumps(
        _jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def content_hash(payload: bytes | str) -> str:
    data = payload.encode("utf-8") if isinstance(payload, str) else payload
    return hashlib.sha256(data).hexdigest()


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze(item) for item in value)
    return value


def _clean_logical_path(value: str) -> str:
    """Return a stable corpus-relative path and reject path traversal."""

    text = value.replace("\\", "/").strip()
    path = PurePosixPath(text)
    if path.is_absolute() or not text or ".." in path.parts:
        raise ValueError(f"artifact path must be non-empty and corpus-relative: {value!r}")
    return path.as_posix()


class SourceLayer(str, Enum):
    RAW = "RAW"
    EXTRACTED = "EXTRACTED"
    STAGING = "STAGING"
    CANONICAL = "CANONICAL"
    DERIVED_SCENARIO = "DERIVED_SCENARIO"


class ResolutionState(str, Enum):
    UNREVIEWED = "UNREVIEWED"
    RESOLVED_EXISTING = "RESOLVED_EXISTING"
    NEW_CANONICAL_CANDIDATE = "NEW_CANONICAL_CANDIDATE"
    AMBIGUOUS = "AMBIGUOUS"
    RELATED_NOT_IDENTICAL = "RELATED_NOT_IDENTICAL"
    SPLIT_REQUIRED = "SPLIT_REQUIRED"
    DUPLICATE = "DUPLICATE"
    REJECTED = "REJECTED"


class RelationState(str, Enum):
    UNREVIEWED = "UNREVIEWED"
    NORMALIZED = "NORMALIZED"
    AMBIGUOUS = "AMBIGUOUS"
    UNSUPPORTED = "UNSUPPORTED"
    REJECTED = "REJECTED"


class ConflictState(str, Enum):
    UNCHECKED = "UNCHECKED"
    NONE_FOUND = "NONE_FOUND"
    POSSIBLE = "POSSIBLE"
    CONFIRMED = "CONFIRMED"
    SUPERSEDED = "SUPERSEDED"


class FreshnessState(str, Enum):
    UNKNOWN = "UNKNOWN"
    CURRENT = "CURRENT"
    AGING = "AGING"
    STALE = "STALE"
    HISTORICAL_CONTEXT = "HISTORICAL_CONTEXT"


class PromotionState(str, Enum):
    STAGED = "STAGED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    BLOCKED = "BLOCKED"
    READY_FOR_OBSERVATION = "READY_FOR_OBSERVATION"
    PROMOTED = "PROMOTED"
    REJECTED = "REJECTED"


class SupplierState(str, Enum):
    """Non-interchangeable supplier evidence states, ordered only for display."""

    KNOWN_MANUFACTURER = "KNOWN_MANUFACTURER"
    POTENTIAL_SUPPLIER = "POTENTIAL_SUPPLIER"
    QUALIFIED_SUPPLIER = "QUALIFIED_SUPPLIER"
    AVAILABLE_CAPACITY = "AVAILABLE_CAPACITY"


@dataclass(frozen=True)
class GeographicResolution:
    input_text: str = "UNKNOWN"
    canonical_geo_id: str = ""
    resolved: bool = False
    method: str = "unreviewed"
    rationale: str = ""

    def __post_init__(self) -> None:
        if self.resolved and not self.canonical_geo_id:
            raise ValueError("resolved geography requires a canonical geography id")
        if not self.resolved and self.canonical_geo_id:
            raise ValueError("canonical geography id requires resolved state")
        if self.resolved and "fuzzy" in self.method.casefold():
            raise ValueError("fuzzy matching cannot resolve geography")

    def to_json(self) -> dict[str, Any]:
        return _jsonable(self.__dict__)


class RepairSeverity(str, Enum):
    LOSSLESS = "LOSSLESS"
    AMBIGUOUS = "AMBIGUOUS"


@dataclass(frozen=True)
class RawArtifactSnapshot:
    corpus_id: str
    logical_path: str
    content_hash: str
    byte_length: int
    source_layer: SourceLayer = SourceLayer.RAW
    media_type: str = "application/octet-stream"
    license: str = "UNSPECIFIED"
    storage_posture: str = "external_immutable"
    metadata: Mapping[str, Any] = field(default_factory=dict)
    artifact_id: str = ""

    def __post_init__(self) -> None:
        logical_path = _clean_logical_path(self.logical_path)
        object.__setattr__(self, "logical_path", logical_path)
        digest = self.content_hash.lower()
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError("content_hash must be a SHA-256 hex digest")
        object.__setattr__(self, "content_hash", digest)
        if self.byte_length < 0:
            raise ValueError("byte_length cannot be negative")
        if not self.artifact_id:
            identity = content_hash(
                canonical_json(
                    {
                        "corpus_id": self.corpus_id,
                        "logical_path": logical_path,
                        "content_hash": digest,
                    }
                )
            )
            object.__setattr__(self, "artifact_id", f"artifact:{identity[:24]}")
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    @classmethod
    def from_file(
        cls,
        path: Path,
        *,
        corpus_root: Path,
        corpus_id: str,
        source_layer: SourceLayer,
        license: str = "UNSPECIFIED",
    ) -> "RawArtifactSnapshot":
        resolved = path.resolve(strict=True)
        root = corpus_root.resolve(strict=True)
        try:
            relative = resolved.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"artifact is outside corpus root: {resolved}") from exc
        payload = resolved.read_bytes()
        return cls(
            corpus_id=corpus_id,
            logical_path=relative.as_posix(),
            content_hash=content_hash(payload),
            byte_length=len(payload),
            source_layer=source_layer,
            license=license,
            media_type=_media_type(resolved.suffix.lower()),
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "corpus_id": self.corpus_id,
            "logical_path": self.logical_path,
            "content_hash": self.content_hash,
            "byte_length": self.byte_length,
            "source_layer": self.source_layer.value,
            "media_type": self.media_type,
            "license": self.license,
            "storage_posture": self.storage_posture,
            "metadata": _jsonable(self.metadata),
        }


@dataclass(frozen=True)
class QuantityCandidate:
    original_text: str = ""
    low: Optional[float] = None
    high: Optional[float] = None
    original_unit: str = ""
    normalized_unit: str = ""
    normalization_basis: str = ""

    def __post_init__(self) -> None:
        if self.low is not None:
            object.__setattr__(self, "low", float(self.low))
        if self.high is not None:
            object.__setattr__(self, "high", float(self.high))
        if self.low is not None and self.high is not None and self.low > self.high:
            raise ValueError("quantity lower bound exceeds upper bound")
        if self.normalized_unit and not self.normalization_basis:
            raise ValueError("normalized unit requires an explicit normalization basis")

    def to_json(self) -> dict[str, Any]:
        return _jsonable(self.__dict__)


@dataclass(frozen=True)
class EntityResolution:
    state: ResolutionState = ResolutionState.UNREVIEWED
    canonical_ids: Tuple[str, ...] = ()
    candidate_ids: Tuple[str, ...] = ()
    method: str = "manual_review_required"
    rationale: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "canonical_ids", tuple(sorted(set(self.canonical_ids))))
        object.__setattr__(self, "candidate_ids", tuple(sorted(set(self.candidate_ids))))
        if self.state == ResolutionState.RESOLVED_EXISTING and len(self.canonical_ids) != 1:
            raise ValueError("RESOLVED_EXISTING requires exactly one canonical id")
        if self.state != ResolutionState.RESOLVED_EXISTING and self.canonical_ids:
            raise ValueError("canonical ids require RESOLVED_EXISTING")
        if "fuzzy" in self.method.casefold() and self.state == ResolutionState.RESOLVED_EXISTING:
            raise ValueError("fuzzy matching may propose candidates but cannot resolve identity")

    def to_json(self) -> dict[str, Any]:
        return _jsonable(self.__dict__)


@dataclass(frozen=True)
class RelationNormalization:
    original_relation: str
    state: RelationState = RelationState.UNREVIEWED
    normalized_relation: str = ""
    rationale: str = ""

    def __post_init__(self) -> None:
        if self.state == RelationState.NORMALIZED:
            if self.normalized_relation not in ALLOWED_EDGES:
                raise ValueError(
                    f"normalized relation is outside the canonical ontology: {self.normalized_relation!r}"
                )
        elif self.normalized_relation:
            raise ValueError("normalized relation requires NORMALIZED state")

    def to_json(self) -> dict[str, Any]:
        return _jsonable(self.__dict__)


@dataclass(frozen=True)
class ClaimCandidate:
    artifact_id: str
    locator: str
    subject_text: str
    predicate_text: str
    value_text: str
    candidate_epistemic_class: EpistemicClass = EpistemicClass.UNKNOWN
    quantity: Optional[QuantityCandidate] = None
    geography: str = "UNKNOWN"
    geographic_resolution: GeographicResolution = field(default_factory=GeographicResolution)
    publication_date: str = ""
    effective_date: str = ""
    retrieval_date: str = ""
    technical_scope: str = ""
    caveat: str = ""
    unknown_dimensions: Tuple[str, ...] = ()
    source_class: str = "corpus_document"
    source_license: str = "UNSPECIFIED"
    supplier_state: Optional[SupplierState] = None
    entity_resolution: EntityResolution = field(default_factory=EntityResolution)
    relation: Optional[RelationNormalization] = None
    conflict_state: ConflictState = ConflictState.UNCHECKED
    conflicting_claim_ids: Tuple[str, ...] = ()
    freshness_state: FreshnessState = FreshnessState.UNKNOWN
    promotion_state: PromotionState = PromotionState.STAGED
    escalation_reason: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    claim_id: str = ""

    def __post_init__(self) -> None:
        if not self.locator.strip():
            raise ValueError("claim locator is required")
        if not self.subject_text.strip() or not self.predicate_text.strip():
            raise ValueError("claim subject and predicate are required")
        klass = self.candidate_epistemic_class
        if not isinstance(klass, EpistemicClass):
            klass = EpistemicClass(str(klass).upper())
            object.__setattr__(self, "candidate_epistemic_class", klass)
        object.__setattr__(self, "unknown_dimensions", tuple(sorted(set(self.unknown_dimensions))))
        object.__setattr__(
            self, "conflicting_claim_ids", tuple(sorted(set(self.conflicting_claim_ids)))
        )
        if self.conflict_state == ConflictState.CONFIRMED and not self.conflicting_claim_ids:
            raise ValueError("confirmed conflict requires conflicting claim ids")
        if self.conflict_state == ConflictState.CONFIRMED and klass != EpistemicClass.CONFLICTED:
            raise ValueError("confirmed conflict must use CONFLICTED epistemic class")
        if klass == EpistemicClass.CONFLICTED and self.conflict_state not in {
            ConflictState.POSSIBLE,
            ConflictState.CONFIRMED,
        }:
            raise ValueError("CONFLICTED epistemic class requires a possible or confirmed conflict")
        if not self.claim_id:
            identity = content_hash(
                canonical_json(
                    {
                        "schema": STAGING_SCHEMA_VERSION,
                        "artifact_id": self.artifact_id,
                        "locator": self.locator.strip(),
                        "subject_text": self.subject_text.strip(),
                        "predicate_text": self.predicate_text.strip(),
                    }
                )
            )
            object.__setattr__(self, "claim_id", f"staged-claim:{identity[:24]}")
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    def promotion_blockers(self) -> Tuple[str, ...]:
        blockers: list[str] = []
        if self.promotion_state != PromotionState.READY_FOR_OBSERVATION:
            blockers.append("promotion_state_not_ready")
        if self.entity_resolution.state != ResolutionState.RESOLVED_EXISTING:
            blockers.append("entity_identity_unresolved")
        if self.relation is None or self.relation.state != RelationState.NORMALIZED:
            blockers.append("relation_not_normalized")
        if self.conflict_state in {ConflictState.UNCHECKED, ConflictState.POSSIBLE, ConflictState.CONFIRMED}:
            blockers.append("conflict_unresolved")
        if self.candidate_epistemic_class in {EpistemicClass.MEASURED, EpistemicClass.REPORTED}:
            if not self.source_license.strip() or self.source_license.upper() == "UNSPECIFIED":
                blockers.append("source_license_unspecified")
        geography = self.geography.strip().upper()
        if geography not in {"GLOBAL", "UNKNOWN"} and not (
            len(geography) == 3 and geography.isalpha()
        ) and not self.geographic_resolution.resolved:
            blockers.append("geography_unresolved")
        if self.supplier_state == SupplierState.AVAILABLE_CAPACITY:
            if self.quantity is None:
                blockers.append("available_capacity_requires_quantity")
            if any(
                dimension not in self.metadata
                for dimension in (
                    "availability",
                    "utilization",
                    "yield_fraction",
                    "qualification_fraction",
                    "allocation_fraction",
                )
            ):
                blockers.append("available_capacity_dimensions_unresolved")
        blockers.extend(_semantic_proxy_blockers(self))
        return tuple(dict.fromkeys(blockers))

    def to_observation(self, source_snapshot: SourceSnapshot) -> Observation:
        """Create an observation only after every staging gate is explicit."""

        blockers = self.promotion_blockers()
        if blockers:
            raise ValueError(f"claim cannot become an observation: {', '.join(blockers)}")
        if source_snapshot.license != self.source_license:
            raise ValueError("staged source license does not match source snapshot")
        assert self.relation is not None
        value_quantity = None
        if self.quantity and self.quantity.low is not None and self.quantity.low == self.quantity.high:
            unit = self.quantity.normalized_unit or self.quantity.original_unit
            if unit:
                value_quantity = (self.quantity.low, unit)
        return Observation(
            observation_id=self.claim_id,
            source_snapshot_id=source_snapshot.snapshot_id,
            subject=self.entity_resolution.canonical_ids[0],
            predicate=self.relation.normalized_relation,
            value_text=self.value_text,
            value_quantity=value_quantity,
            epistemic_class=self.candidate_epistemic_class,
            observed_at=self.effective_date,
            geographic_scope=self.geography,
            technical_scope=self.technical_scope,
            caveat=self.caveat,
            metadata={
                "publication_date": self.publication_date,
                "retrieval_date": self.retrieval_date,
                "staged_claim_id": self.claim_id,
                "artifact_id": self.artifact_id,
                "locator": self.locator,
                "unknown_dimensions": self.unknown_dimensions,
                **dict(self.metadata),
            },
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "artifact_id": self.artifact_id,
            "locator": self.locator,
            "subject_text": self.subject_text,
            "predicate_text": self.predicate_text,
            "value_text": self.value_text,
            "candidate_epistemic_class": self.candidate_epistemic_class.value,
            "quantity": self.quantity.to_json() if self.quantity else None,
            "geography": self.geography,
            "geographic_resolution": self.geographic_resolution.to_json(),
            "publication_date": self.publication_date,
            "effective_date": self.effective_date,
            "retrieval_date": self.retrieval_date,
            "technical_scope": self.technical_scope,
            "caveat": self.caveat,
            "unknown_dimensions": list(self.unknown_dimensions),
            "source_class": self.source_class,
            "source_license": self.source_license,
            "supplier_state": self.supplier_state.value if self.supplier_state else None,
            "entity_resolution": self.entity_resolution.to_json(),
            "relation": self.relation.to_json() if self.relation else None,
            "conflict_state": self.conflict_state.value,
            "conflicting_claim_ids": list(self.conflicting_claim_ids),
            "freshness_state": self.freshness_state.value,
            "promotion_state": self.promotion_state.value,
            "escalation_reason": self.escalation_reason,
            "metadata": _jsonable(self.metadata),
            "promotion_blockers": list(self.promotion_blockers()),
        }


@dataclass(frozen=True)
class RepairAction:
    code: str
    locator: str
    before_hash: str
    after_hash: str
    severity: RepairSeverity
    note: str = ""

    def to_json(self) -> dict[str, Any]:
        return _jsonable(self.__dict__)


@dataclass(frozen=True)
class CsvRepairResult:
    repaired_bytes: bytes
    actions: Tuple[RepairAction, ...]
    rows_before: int
    rows_after: int
    column_count: int
    validation_result: str = "VALID"
    repair_version: str = CSV_REPAIR_VERSION

    @property
    def content_hash(self) -> str:
        return content_hash(self.repaired_bytes)

    @property
    def row_count(self) -> int:
        return self.rows_after

    def to_json(self) -> dict[str, Any]:
        return {
            "repair_version": self.repair_version,
            "rows_before": self.rows_before,
            "rows_after": self.rows_after,
            "column_count": self.column_count,
            "repaired_hash": self.content_hash,
            "validation_result": self.validation_result,
            "actions": [action.to_json() for action in self.actions],
        }


def repair_csv_bytes(payload: bytes, *, delimiter: str = ",") -> CsvRepairResult:
    """Produce a deterministic staging copy of a CSV and a provenance log.

    The input bytes are never written or modified.  BOM/NUL/newline changes are
    lossless.  Rows wider than the header are joined into their final field and
    marked ambiguous; narrower rows are padded and marked ambiguous.  Reviewers
    can therefore reject a repair rather than inheriting an invisible guess.
    """

    if len(delimiter) != 1:
        raise ValueError("delimiter must be one character")
    original_hash = content_hash(payload)
    text = payload.decode("utf-8-sig", errors="strict")
    actions: list[RepairAction] = []
    if "\x00" in text:
        before = content_hash(text)
        text = text.replace("\x00", "")
        actions.append(
            RepairAction(
                "REMOVE_NUL", "document", before, content_hash(text), RepairSeverity.LOSSLESS
            )
        )
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
    rows = [list(row) for row in reader]
    if not rows:
        return CsvRepairResult(b"", tuple(actions), 0, 0, 0)
    width = len(rows[0])
    if width == 0:
        raise ValueError("CSV header has no columns")
    normalized: list[list[str]] = [rows[0]]
    for index, row in enumerate(rows[1:], start=2):
        before = canonical_json(row)
        if len(row) < width:
            row = row + [""] * (width - len(row))
            actions.append(
                RepairAction(
                    "PAD_SHORT_ROW",
                    f"row:{index}",
                    content_hash(before),
                    content_hash(canonical_json(row)),
                    RepairSeverity.AMBIGUOUS,
                    "Missing trailing fields padded; semantic review required",
                )
            )
        elif len(row) > width:
            row = row[: width - 1] + [delimiter.join(row[width - 1 :])]
            actions.append(
                RepairAction(
                    "JOIN_OVERFLOW_FIELDS",
                    f"row:{index}",
                    content_hash(before),
                    content_hash(canonical_json(row)),
                    RepairSeverity.AMBIGUOUS,
                    "Overflow joined into final field; semantic review required",
                )
            )
        normalized.append(row)
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=delimiter, lineterminator="\n")
    writer.writerows(normalized)
    repaired = output.getvalue().encode("utf-8")
    if repaired != payload and not actions:
        actions.append(
            RepairAction(
                "CANONICALIZE_ENCODING_NEWLINES",
                "document",
                original_hash,
                content_hash(repaired),
                RepairSeverity.LOSSLESS,
            )
        )
    return CsvRepairResult(
        repaired,
        tuple(actions),
        rows_before=len(rows),
        rows_after=len(normalized),
        column_count=width,
    )


def inventory_corpus(
    root: Path,
    *,
    corpus_id: str,
    source_layer: SourceLayer,
    license: str = "UNSPECIFIED",
) -> Tuple[RawArtifactSnapshot, ...]:
    resolved = root.resolve(strict=True)
    if not resolved.is_dir():
        raise ValueError(f"corpus root is not a directory: {resolved}")
    snapshots = [
        RawArtifactSnapshot.from_file(
            path,
            corpus_root=resolved,
            corpus_id=corpus_id,
            source_layer=source_layer,
            license=license,
        )
        for path in sorted((item for item in resolved.rglob("*") if item.is_file()), key=lambda p: p.as_posix().casefold())
    ]
    return tuple(sorted(snapshots, key=lambda item: item.logical_path.casefold()))


def manifest_payload(
    snapshots: Sequence[RawArtifactSnapshot], *, roots: Optional[Sequence[Mapping[str, Any]]] = None
) -> dict[str, Any]:
    artifacts = [item.to_json() for item in sorted(snapshots, key=lambda x: x.artifact_id)]
    payload = {
        "schema_version": STAGING_SCHEMA_VERSION,
        "roots": list(roots or ()),
        "artifacts": artifacts,
        "artifact_count": len(artifacts),
        "total_bytes": sum(item["byte_length"] for item in artifacts),
    }
    payload["manifest_hash"] = content_hash(canonical_json(payload))
    return payload


def write_canonical_json(path: Path, payload: Any) -> None:
    """Write one deterministic repository artifact without touching source data."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(payload), indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _media_type(suffix: str) -> str:
    return {
        ".csv": "text/csv",
        ".json": "application/json",
        ".jsonl": "application/x-ndjson",
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".yaml": "application/yaml",
        ".yml": "application/yaml",
        ".zip": "application/zip",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }.get(suffix, "application/octet-stream")


def _semantic_proxy_blockers(claim: ClaimCandidate) -> Iterable[str]:
    predicate = claim.predicate_text.casefold().replace("-", "_").replace(" ", "_")
    normalized = claim.relation.normalized_relation if claim.relation else ""
    if any(token in predicate for token in ("trade", "import", "export")) and normalized in {
        "has_capacity", "supplied_by", "requires_capability"
    }:
        yield "trade_is_not_capability_or_supply"
    if any(token in predicate for token in ("facility_exists", "factory_exists", "plant_exists")) and normalized == "has_capacity":
        yield "facility_existence_is_not_capacity"
    if any(token in predicate for token in ("announcement", "order", "policy_target")) and normalized in {
        "has_capacity", "enabled_by_project"
    }:
        yield "announcement_is_not_operating_capacity"
    if "reserve" in predicate and normalized in {"has_capacity", "supplied_by", "requires_input"}:
        yield "mineral_reserve_is_not_usable_supply"
    if "nameplate" in predicate and normalized == "has_capacity" and any(
        dimension not in claim.metadata
        for dimension in ("availability", "utilization", "yield_fraction", "qualification_fraction")
    ):
        yield "nameplate_is_not_effective_capacity"
