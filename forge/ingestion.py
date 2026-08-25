"""Evidence ingestion boundaries for staging and the canonical registry.

The implementation lives in :mod:`forge.registry` so registry consumers and
adapters share one immutable contract.  This module provides a stable, obvious
import path for future source connectors without coupling them to the read
model implementation.  Claim candidates remain non-authoritative until their
identity, relation, conflict, freshness, geography, and rights gates pass.
"""
from .reality import (
    ClaimCandidate,
    ConflictState,
    EntityResolution,
    FreshnessState,
    GeographicResolution,
    PromotionState,
    RawArtifactSnapshot,
    RelationNormalization,
    RelationState,
    ResolutionState,
    SourceLayer,
    SupplierState,
)
from .registry import Observation, Promotion, SourceSnapshot, promote_observation

__all__ = [
    "RawArtifactSnapshot",
    "ClaimCandidate",
    "SourceLayer",
    "ResolutionState",
    "EntityResolution",
    "RelationState",
    "RelationNormalization",
    "ConflictState",
    "FreshnessState",
    "PromotionState",
    "GeographicResolution",
    "SupplierState",
    "SourceSnapshot",
    "Observation",
    "Promotion",
    "promote_observation",
]
