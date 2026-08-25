"""Schema primitives for the FORGE India V1 industrial atlas.

The atlas is deliberately a small, read-oriented contract.  It is not a
replacement for the V0.1 solver ``World`` model and it does not manufacture
capacity evidence.  Domain packs use this schema to provide reusable identity,
first-order dependencies, and explicit India-status uncertainty before richer
evidence is ingested.
"""
from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, Iterable, List, Sequence, Tuple


ATLAS_SCHEMA_VERSION = "india_v1.0"

KINDS: Tuple[str, ...] = (
    "PRODUCT",
    "CAPABILITY",
    "PROCESS",
    "MATERIAL",
    "EQUIPMENT",
)
STATUSES: Tuple[str, ...] = (
    "STRONG",
    "AVAILABLE",
    "PARTIAL",
    "SCALE_LIMITED",
    "IMPORT_DEPENDENT",
    "MISSING",
    "UNKNOWN",
    "CONFLICTED",
)
EPISTEMIC_CLASSES: Tuple[str, ...] = (
    "MEASURED",
    "REPORTED",
    "DERIVED",
    "ESTIMATED",
    "MODELLED",
    "ASSUMPTION",
    "SCENARIO",
    "UNKNOWN",
    "CONFLICTED",
)
DEPENDENCY_GROUPS: Tuple[str, ...] = (
    "systems",
    "processes",
    "materials",
    "equipment",
    "capabilities",
)
LADDER_ACTIONS: Tuple[str, ...] = (
    "IMPORT",
    "DEVELOP",
    "LICENSE",
    "JV",
    "BUILD",
    "SUBSTITUTE",
    "REDESIGN",
    "R&D",
)
LINK_GROUPS: Tuple[str, ...] = ("upstream", "downstream", "related")
# Descriptive aliases keep the contract discoverable for lightweight clients.
INDIA_STATUS_ENUM = STATUSES
RECORD_KINDS = KINDS
MAKING_ACTIONS = LADDER_ACTIONS


def _tuple_strings(values: Iterable[str] | None) -> Tuple[str, ...]:
    """Normalize a sequence to a deterministic, duplicate-free tuple."""

    if values is None:
        return ()
    return tuple(sorted({str(value) for value in values if str(value).strip()}))


@dataclass(frozen=True)
class LadderStep:
    """A first-order route for making or securing a record.

    These are intentionally coarse actions.  They are candidate transformations
    for a later evidence-backed planner, not claims that every action is
    currently feasible.
    """

    sequence: int
    action: str
    purpose: str
    condition: str = ""

    def __post_init__(self) -> None:
        if self.action not in LADDER_ACTIONS:
            raise ValueError(f"invalid making-ladder action: {self.action}")
        if self.sequence < 1:
            raise ValueError("making-ladder sequence must be positive")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sequence": self.sequence,
            "action": self.action,
            "purpose": self.purpose,
            "condition": self.condition,
        }


@dataclass(frozen=True)
class AtlasRecord(Mapping[str, Any]):
    """Canonical V1 atlas record.

    The object implements ``Mapping`` so callers can use either typed access
    (``record.id``) or the JSON-like access expected by lightweight clients
    (``record["id"]``).  Tuples are used internally to keep generated records
    immutable and reproducible; :meth:`to_dict` returns ordinary JSON data.
    """

    id: str
    canonical_name: str
    aliases: Tuple[str, ...]
    domain: str
    category: str
    kind: str
    explanation: str
    uses: Tuple[str, ...]
    status: str
    status_epistemic_class: str
    status_basis: str
    dependencies: Mapping[str, Tuple[str, ...]]
    gap_import_notes: str
    making_ladder: Tuple[LadderStep, ...]
    upstream: Tuple[str, ...] = ()
    downstream: Tuple[str, ...] = ()
    related: Tuple[str, ...] = ()
    # A tiny provenance hook for generators and downstream evidence loaders.
    source_spec: str = "curated_india_v1_archetype"

    def __post_init__(self) -> None:
        if not self.id or not self.canonical_name:
            raise ValueError("atlas records require stable id and canonical_name")
        if self.kind not in KINDS:
            raise ValueError(f"invalid atlas kind: {self.kind}")
        if self.status not in STATUSES:
            raise ValueError(f"invalid atlas India status: {self.status}")
        if self.status_epistemic_class not in EPISTEMIC_CLASSES:
            raise ValueError(
                f"invalid status epistemic class: {self.status_epistemic_class}"
            )
        unknown_groups = set(self.dependencies) - set(DEPENDENCY_GROUPS)
        if unknown_groups:
            raise ValueError(f"unknown dependency groups: {sorted(unknown_groups)}")
        missing_groups = set(DEPENDENCY_GROUPS) - set(self.dependencies)
        if missing_groups:
            raise ValueError(f"missing dependency groups: {sorted(missing_groups)}")
        normalized_dependencies = {
            group: _tuple_strings(self.dependencies[group]) for group in DEPENDENCY_GROUPS
        }
        object.__setattr__(self, "dependencies", MappingProxyType(normalized_dependencies))
        object.__setattr__(self, "aliases", _tuple_strings(self.aliases))
        object.__setattr__(self, "uses", _tuple_strings(self.uses))
        object.__setattr__(self, "upstream", _tuple_strings(self.upstream))
        object.__setattr__(self, "downstream", _tuple_strings(self.downstream))
        object.__setattr__(self, "related", _tuple_strings(self.related))
        object.__setattr__(self, "making_ladder", tuple(self.making_ladder))

    @property
    def dependencies_flat(self) -> Tuple[str, ...]:
        return tuple(
            sorted({ref for group in DEPENDENCY_GROUPS for ref in self.dependencies[group]})
        )

    @property
    def status_epistemic(self) -> str:
        """Canonical epistemic class string for lightweight clients."""

        return self.status_epistemic_class

    @property
    def status_epistemic_basis(self) -> Dict[str, str]:
        return {"class": self.status_epistemic_class, "basis": self.status_basis}

    @property
    def domain_code(self) -> str:
        """Stable numeric domain code inferred from the namespaced id."""

        if self.id.startswith("d") and ":" in self.id:
            return self.id.split(":", 1)[0][1:]
        return "shared"

    @property
    def gap_notes(self) -> str:
        return self.gap_import_notes

    @property
    def import_notes(self) -> str:
        return self.gap_import_notes

    @property
    def ladder_actions(self) -> Tuple[str, ...]:
        return tuple(step.action for step in self.making_ladder)

    def to_dict(self) -> Dict[str, Any]:
        dependencies = {
            group: list(self.dependencies[group]) for group in DEPENDENCY_GROUPS
        }
        links = {
            "upstream": list(self.upstream),
            "downstream": list(self.downstream),
            "related": list(self.related),
        }
        return {
            "id": self.id,
            "canonical_name": self.canonical_name,
            "aliases": list(self.aliases),
            "domain": self.domain,
            "domain_code": self.domain_code,
            "domain_id": self.domain_code,
            "category": self.category,
            "kind": self.kind,
            "explanation": self.explanation,
            "uses": list(self.uses),
            "status": self.status,
            "status_epistemic_class": self.status_epistemic_class,
            "epistemic_class": self.status_epistemic_class,
            "status_basis": self.status_basis,
            "epistemic_basis": self.status_basis,
            "status_epistemic": self.status_epistemic,
            "status_epistemic_basis": self.status_epistemic_basis,
            "dependencies": dependencies,
            "dependency_ids": dependencies,
            "gap_import_notes": self.gap_import_notes,
            "gap_notes": self.gap_notes,
            "import_notes": self.import_notes,
            "making_ladder": [step.to_dict() for step in self.making_ladder],
            "ladder_actions": list(self.ladder_actions),
            "upstream": links["upstream"],
            "downstream": links["downstream"],
            "related": links["related"],
            "upstream_ids": links["upstream"],
            "downstream_ids": links["downstream"],
            "related_ids": links["related"],
            "links": links,
            "source_spec": self.source_spec,
        }

    def to_json(self) -> Dict[str, Any]:
        """JSON-compatible alias used by the rest of FORGE's read models."""

        return self.to_dict()

    # Mapping implementation.  The conversion is deterministic and keeps the
    # public object pleasant to use in notebooks/tests without exposing mutable
    # internal lists.
    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.to_dict())

    def __len__(self) -> int:
        return len(self.to_dict())


@dataclass(frozen=True)
class IntegrityReport:
    """Result of deterministic atlas validation."""

    ok: bool
    record_count: int
    counts_by_domain: Mapping[str, int]
    counts_by_kind: Mapping[str, int]
    errors: Tuple[str, ...] = ()
    warnings: Tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return self.ok

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "record_count": self.record_count,
            "counts_by_domain": dict(self.counts_by_domain),
            "counts_by_kind": dict(self.counts_by_kind),
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class Atlas:
    """Immutable generated atlas with convenient list-like behavior."""

    records: Tuple[AtlasRecord, ...]
    schema_version: str = ATLAS_SCHEMA_VERSION
    generator_version: str = "1.0.0"

    def __len__(self) -> int:
        return len(self.records)

    def __iter__(self) -> Iterator[AtlasRecord]:
        return iter(self.records)

    def __getitem__(self, index: int | slice) -> AtlasRecord | Tuple[AtlasRecord, ...]:
        return self.records[index]

    @property
    def by_id(self) -> Dict[str, AtlasRecord]:
        return {record.id: record for record in self.records}

    @property
    def domains(self) -> Tuple[str, ...]:
        return tuple(sorted({record.domain for record in self.records}))

    @property
    def domain_codes(self) -> Tuple[str, ...]:
        return tuple(sorted({record.domain_code for record in self.records}))

    def records_for_domain(self, domain: str) -> Tuple[AtlasRecord, ...]:
        key = str(domain).casefold()
        compact = "".join(ch for ch in key if ch.isalnum())
        return tuple(
            record
            for record in self.records
            if (
                record.domain.casefold() == key
                or record.domain_code.casefold() == key
                or "".join(ch for ch in record.domain.casefold() if ch.isalnum()) == compact
            )
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generator_version": self.generator_version,
            "records": [record.to_dict() for record in self.records],
        }

    def to_json(self) -> Dict[str, Any]:
        return self.to_dict()

    def to_records(self) -> List[Dict[str, Any]]:
        return [record.to_dict() for record in self.records]


class AtlasIntegrityError(ValueError):
    """Raised when the generated atlas violates its structural contract."""


__all__ = [
    "ATLAS_SCHEMA_VERSION",
    "KINDS",
    "STATUSES",
    "EPISTEMIC_CLASSES",
    "DEPENDENCY_GROUPS",
    "LADDER_ACTIONS",
    "LINK_GROUPS",
    "INDIA_STATUS_ENUM",
    "RECORD_KINDS",
    "MAKING_ACTIONS",
    "LadderStep",
    "AtlasRecord",
    "IntegrityReport",
    "Atlas",
    "AtlasIntegrityError",
]
