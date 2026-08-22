from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from . import SOLVER_VERSION
from .evidence import ProofGraph, snapshot_hash


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
    ) -> "ModelRun":
        payload = {
            "pack_id": pack_id,
            "pack_version": pack_version,
            "objective": objective,
            "scenario": scenario,
            "data": data_snapshot_payload,
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
