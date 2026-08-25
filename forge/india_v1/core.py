"""Compatibility facade for the India V1 atlas core.

Keeping this small facade lets callers use either ``forge.india_v1`` or the
more explicit ``forge.india_v1.core`` import without creating a second model.
"""

from .generator import (
    assert_integrity,
    check_integrity,
    domain_counts,
    domain_counts_by_code,
    generate,
    generate_atlas,
    generate_atlas_dict,
    generate_atlas_records,
    generate_domain,
    generate_domain_records,
    generate_records,
    validate_atlas,
)
from .schema import (
    ATLAS_SCHEMA_VERSION,
    DEPENDENCY_GROUPS,
    EPISTEMIC_CLASSES,
    KINDS,
    LADDER_ACTIONS,
    STATUSES,
    Atlas,
    AtlasIntegrityError,
    AtlasRecord,
    IntegrityReport,
    LadderStep,
)

__all__ = [
    "ATLAS_SCHEMA_VERSION",
    "KINDS",
    "STATUSES",
    "EPISTEMIC_CLASSES",
    "DEPENDENCY_GROUPS",
    "LADDER_ACTIONS",
    "Atlas",
    "AtlasRecord",
    "IntegrityReport",
    "AtlasIntegrityError",
    "LadderStep",
    "generate",
    "generate_atlas",
    "generate_atlas_dict",
    "generate_atlas_records",
    "generate_domain",
    "generate_records",
    "generate_domain_records",
    "domain_counts",
    "domain_counts_by_code",
    "check_integrity",
    "validate_atlas",
    "assert_integrity",
]
