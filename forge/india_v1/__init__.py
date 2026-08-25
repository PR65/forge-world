"""FORGE India V1 atlas primitives for domains 01-04.

The public helpers are intentionally small:

``generate_atlas()``
    Build the shared-foundation graph plus all four domain views.
``generate_domain_records("01")``
    Return only records owned by one domain (shared primitives remain one copy
    in the full atlas).
``validate_atlas(...)`` / ``check_integrity(...)``
    Run deterministic identity, enum, reference, dependency, and ladder checks.
"""

from .generator import (
    GENERATOR_VERSION,
    assert_integrity,
    build_atlas,
    build_records,
    check_integrity,
    domain_counts,
    domain_counts_by_code,
    generate_atlas,
    generate_atlas_dict,
    generate_atlas_records,
    generate_domain,
    generate_domain_records,
    generate_records,
    generate,
    integrity_check,
    validate_atlas,
)
from .schema import (
    ATLAS_SCHEMA_VERSION,
    DEPENDENCY_GROUPS,
    EPISTEMIC_CLASSES,
    INDIA_STATUS_ENUM,
    KINDS,
    LADDER_ACTIONS,
    MAKING_ACTIONS,
    RECORD_KINDS,
    STATUSES,
    Atlas,
    AtlasIntegrityError,
    AtlasRecord,
    IntegrityReport,
    LadderStep,
)

__all__ = [
    "ATLAS_SCHEMA_VERSION",
    "GENERATOR_VERSION",
    "KINDS",
    "RECORD_KINDS",
    "STATUSES",
    "INDIA_STATUS_ENUM",
    "EPISTEMIC_CLASSES",
    "DEPENDENCY_GROUPS",
    "LADDER_ACTIONS",
    "MAKING_ACTIONS",
    "Atlas",
    "AtlasRecord",
    "IntegrityReport",
    "AtlasIntegrityError",
    "LadderStep",
    "generate_atlas",
    "generate_atlas_dict",
    "generate_atlas_records",
    "generate_domain",
    "generate_records",
    "generate_domain_records",
    "generate",
    "build_atlas",
    "build_records",
    "check_integrity",
    "integrity_check",
    "validate_atlas",
    "assert_integrity",
    "domain_counts",
    "domain_counts_by_code",
]
