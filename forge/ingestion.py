"""Evidence ingestion boundary for the canonical registry.

The implementation lives in :mod:`forge.registry` so registry consumers and
adapters share one immutable contract.  This module provides a stable, obvious
import path for future source connectors without coupling them to the read
model implementation.
"""
from .registry import Observation, Promotion, SourceSnapshot, promote_observation

__all__ = ["SourceSnapshot", "Observation", "Promotion", "promote_observation"]
