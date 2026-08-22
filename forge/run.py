from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from . import SOLVER_VERSION
from .evidence import ProofGraph, snapshot_hash, world_snapshot
from .units import Quantity


@dataclass
class ModelRun:
    run_id: str
    pack_id: str
    pack_version: str
    objective: Dict
    scenario: Dict
    assumptions: List[str] = field(default_factory=list)
    solver_version: str = SOLVER_VERSION
    seed: int = 0
    created_at: str = ""
    input_hash: str = ""
    outputs: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    @staticmethod
    def create(
        pack_id: str,
        pack_version: str,
        objective: Dict,
        scenario: Dict,
        data_snapshot_payload: Any,
        assumptions: Optional[List[str]] = None,
        seed: int = 0,
        world=None,
        scenario_opts=None,
        transform_config: Optional[Dict] = None,
    ) -> "ModelRun":
        """Build a run identity over the FULL canonicalized solver-relevant state.

        `data_snapshot_payload` is kept for backward compatibility; when `world` is
        supplied the hash covers its complete entity/edge snapshot instead of any
        summary (V0 hashed counts, so numeric edits were invisible — F21/P7b).
        Timestamps and other non-deterministic metadata are excluded from the hash.
        """
        payload = {
            "pack_id": pack_id,
            "pack_version": pack_version,
            "objective": objective,
            "scenario": scenario,
            "data": (world_snapshot(world) if world is not None else data_snapshot_payload),
            "scenario_options": _jsonify(scenario_opts) if scenario_opts is not None else None,
            "transform_config": transform_config or {},
            "solver": SOLVER_VERSION,
            "seed": seed,
        }
        h = snapshot_hash(payload)
        return ModelRun(
            run_id=f"run_{h[:12]}",
            pack_id=pack_id,
            pack_version=pack_version,
            objective=dict(objective),
            scenario=dict(scenario),
            assumptions=list(assumptions or []),
            seed=seed,
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            input_hash=h,
        )

    def finish(self, outputs: Dict[str, Any], warnings: Optional[List[str]] = None):
        self.outputs = outputs
        self.warnings = list(warnings or [])

    def to_json(self) -> Dict:
        return dict(
            run_id=self.run_id,
            pack_id=self.pack_id,
            pack_version=self.pack_version,
            objective=self.objective,
            scenario=self.scenario,
            assumptions=self.assumptions,
            solver_version=self.solver_version,
            seed=self.seed,
            created_at=self.created_at,
            input_hash=self.input_hash,
            outputs=self.outputs,
            warnings=self.warnings,
        )


def _jsonify(obj):
    """Best-effort canonical JSON form for ScenarioOptions-like objects."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if hasattr(obj, "value") and hasattr(obj, "unit"):
        return [obj.value, obj.unit]
    if isinstance(obj, dict):
        return {str(k): _jsonify(v) for k, v in sorted(obj.items(), key=lambda kv: str(kv[0]))}
    if isinstance(obj, (set, frozenset)):
        return sorted(str(i) for i in obj)
    if isinstance(obj, (list, tuple)):
        return [_jsonify(v) for v in obj]
    if hasattr(obj, "__dict__"):
        return {k: _jsonify(v) for k, v in sorted(obj.__dict__.items())}
    return str(obj)
