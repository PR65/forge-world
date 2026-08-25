"""Evidence-aware composition of novel objectives from canonical primitives.

Composition is a read-model diagnostic, not a solver verdict.  Objective seeds
declare an inspectable architecture hypothesis (ASSUMPTION); the composer then
reports which requirements reuse canonical capability families, which mapped
pack records carry evidence, and which decision-sensitive gaps remain UNKNOWN.
It never invents BOM coefficients, capacity, suppliers, or feasibility.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

import yaml

from .registry import CanonicalRegistry


COMPOSITION_SCHEMA_VERSION = "1.0.0"
EVIDENCED_CLASSES = {"MEASURED", "REPORTED", "DERIVED", "MODELLED"}


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def load_objective_seeds(path: Path | str) -> Dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not raw.get("frozen"):
        raise ValueError("novel-objective benchmark set must be explicitly frozen")
    objectives = raw.get("objectives")
    if not isinstance(objectives, list) or not objectives:
        raise ValueError("novel-objective benchmark set requires objectives")
    ids = [str(row.get("id", "")) for row in objectives if isinstance(row, Mapping)]
    if not all(ids) or len(ids) != len(set(ids)):
        raise ValueError("novel-objective ids must be non-empty and unique")
    for objective in objectives:
        requirements = objective.get("requirements", ())
        if not isinstance(requirements, list) or not requirements:
            raise ValueError(f"objective '{objective.get('id')}' requires architecture seeds")
        requirement_ids = [str(row.get("id", "")) for row in requirements]
        if not all(requirement_ids) or len(requirement_ids) != len(set(requirement_ids)):
            raise ValueError(f"objective '{objective.get('id')}' requirement ids must be unique")
        for requirement in requirements:
            weight = float(requirement.get("decision_weight", 1.0))
            if weight <= 0:
                raise ValueError("decision weights must be positive")
    raw["benchmark_hash"] = _stable_hash(
        {key: value for key, value in raw.items() if key != "benchmark_hash"}
    )
    return raw


def _mapped_nodes(registry: CanonicalRegistry, canonical_id: str) -> list[Any]:
    capability = registry.nodes.get(canonical_id)
    if capability is None:
        return []
    ids = capability.metadata.get("mapped_entity_ids", ()) or ()
    return [registry.nodes[node_id] for node_id in ids if node_id in registry.nodes]


def compose_objective(registry: CanonicalRegistry, objective: Mapping[str, Any]) -> Dict[str, Any]:
    rows: list[dict[str, Any]] = []
    total_weight = 0.0
    covered_weight = 0.0
    relation_types: set[str] = set()
    reused_nodes: set[str] = set()
    reused_packs: set[str] = set()
    epistemic_counts: Counter[str] = Counter()
    decision_unknowns: list[dict[str, Any]] = []

    for requirement in objective.get("requirements", ()):
        rid = str(requirement["id"])
        canonical_id = str(requirement.get("canonical_id", ""))
        weight = float(requirement.get("decision_weight", 1.0))
        total_weight += weight
        capability = registry.nodes.get(canonical_id) if canonical_id else None
        mapped = _mapped_nodes(registry, canonical_id) if capability else []
        mapped_ids = sorted(node.id for node in mapped)
        mapped_packs = sorted({node.pack_id for node in mapped if node.pack_id})
        classes = sorted({node.epistemic_class for node in mapped})
        for klass in classes or ["UNKNOWN"]:
            epistemic_counts[klass] += 1

        if capability and mapped:
            state = "REUSED_CANONICAL"
            covered_weight += weight
            reused_nodes.update(mapped_ids)
            reused_packs.update(mapped_packs)
        elif capability:
            state = "CANONICAL_SEED_ONLY"
        else:
            state = "UNRESOLVED_PRIMITIVE"

        supporting_evidence_ids = sorted(
            {evidence_id for node in mapped for evidence_id in node.evidence_ids}
        )
        supporting_evidence_classes = sorted(
            {
                registry.evidence[evidence_id].epistemic_class.value
                for evidence_id in supporting_evidence_ids
                if evidence_id in registry.evidence
            }
        )
        # A capability node may correctly collapse to UNKNOWN because dimensions
        # such as qualified capacity remain unknown while still carrying a
        # scoped REPORTED facility/process observation. Evidence presence and
        # residual capability-vector uncertainty are therefore reported
        # separately rather than allowing UNKNOWN to erase source-backed state.
        evidenced_world_state = bool(
            set(supporting_evidence_classes) & EVIDENCED_CLASSES
        )
        relation_rows = [
            edge
            for edge in registry.edges
            if edge.target == canonical_id and edge.source in mapped_ids
        ]
        relation_types.update(edge.relation for edge in relation_rows)
        critical = bool(requirement.get("decision_critical", False))
        if critical and (state != "REUSED_CANONICAL" or not evidenced_world_state):
            decision_unknowns.append(
                {
                    "requirement_id": rid,
                    "label": str(requirement.get("label", rid)),
                    "canonical_id": canonical_id or None,
                    "reason": (
                        "canonical primitive missing"
                        if not capability
                        else "no mapped evidence-bearing world-state record"
                    ),
                    "decision_weight": weight,
                    "research_question": str(requirement.get("research_question", "")),
                }
            )

        rows.append(
            {
                "requirement_id": rid,
                "label": str(requirement.get("label", rid)),
                "role": str(requirement.get("role", "industrial_requirement")),
                "architecture_seed_epistemic_class": "ASSUMPTION",
                "canonical_id": canonical_id or None,
                "composition_state": state,
                "decision_weight": weight,
                "decision_critical": critical,
                "mapped_entity_ids": mapped_ids,
                "mapped_pack_ids": mapped_packs,
                "world_epistemic_classes": classes or ["UNKNOWN"],
                "supporting_evidence_ids": supporting_evidence_ids,
                "supporting_evidence_classes": supporting_evidence_classes,
                "evidenced_world_state": evidenced_world_state,
            }
        )

    coverage = covered_weight / total_weight if total_weight else 0.0
    return {
        "objective_id": str(objective["id"]),
        "title": str(objective.get("title", objective["id"])),
        "geography": str(objective.get("geography", "GLOBAL")),
        "target": dict(objective.get("target", {}) or {}),
        "status": "COMPOSITION_DIAGNOSTIC_NOT_SOLVER_VERDICT",
        "architecture_seed_epistemic_class": "ASSUMPTION",
        "composition_coverage": round(coverage, 6),
        "coverage_formula": "sum(decision_weight for REUSED_CANONICAL requirements) / sum(all decision_weight)",
        "coverage_not_claimed": [
            "feasibility",
            "qualified supply",
            "capacity closure",
            "BOM completeness",
            "economic viability",
        ],
        "reused_canonical_primitive_count": sum(
            row["composition_state"] == "REUSED_CANONICAL" for row in rows
        ),
        "reused_entity_count": len(reused_nodes),
        "reused_pack_ids": sorted(reused_packs),
        "reused_relation_types": sorted(relation_types),
        "new_unresolved_requirement_count": sum(
            row["composition_state"] == "UNRESOLVED_PRIMITIVE" for row in rows
        ),
        "canonical_seed_only_count": sum(
            row["composition_state"] == "CANONICAL_SEED_ONLY" for row in rows
        ),
        "epistemic_closure": {
            "world_record_class_counts": dict(sorted(epistemic_counts.items())),
            "decision_critical_unknown_count": len(decision_unknowns),
            "decision_critical_unknowns": decision_unknowns,
            "note": "Class counts remain disaggregated; no confidence scalar is computed.",
        },
        "requirements": rows,
    }


def compose_benchmark_set(
    registry: CanonicalRegistry, benchmark: Mapping[str, Any]
) -> Dict[str, Any]:
    objectives = [compose_objective(registry, row) for row in benchmark["objectives"]]
    mean_coverage = sum(row["composition_coverage"] for row in objectives) / len(objectives)
    return {
        "schema_version": COMPOSITION_SCHEMA_VERSION,
        "benchmark_version": str(benchmark.get("version", "")),
        "benchmark_hash": str(benchmark["benchmark_hash"]),
        "registry_snapshot_id": registry.snapshot_id,
        "registry_content_hash": registry.content_hash,
        "objective_count": len(objectives),
        "mean_composition_coverage": round(mean_coverage, 6),
        "total_decision_critical_unknowns": sum(
            row["epistemic_closure"]["decision_critical_unknown_count"] for row in objectives
        ),
        "objectives": objectives,
    }


def rank_decision_gaps(composition: Mapping[str, Any]) -> Dict[str, Any]:
    grouped: dict[str, dict[str, Any]] = {}
    for objective in composition.get("objectives", ()):
        for gap in objective["epistemic_closure"]["decision_critical_unknowns"]:
            key = str(gap.get("canonical_id") or gap["requirement_id"])
            row = grouped.setdefault(
                key,
                {
                    "gap_key": key,
                    "label": gap["label"],
                    "canonical_id": gap.get("canonical_id"),
                    "objective_ids": [],
                    "aggregate_decision_weight": 0.0,
                    "research_questions": [],
                    "reasons": [],
                },
            )
            row["objective_ids"].append(objective["objective_id"])
            row["aggregate_decision_weight"] += float(gap["decision_weight"])
            if gap.get("research_question"):
                row["research_questions"].append(gap["research_question"])
            row["reasons"].append(gap["reason"])
    rows = []
    for row in grouped.values():
        row["objective_ids"] = sorted(set(row["objective_ids"]))
        row["research_questions"] = sorted(set(row["research_questions"]))
        row["reasons"] = sorted(set(row["reasons"]))
        row["cross_objective_count"] = len(row["objective_ids"])
        row["decision_value_proxy"] = round(
            row["aggregate_decision_weight"] * (1.0 + 0.5 * (row["cross_objective_count"] - 1)),
            6,
        )
        row["task_id"] = f"research-task:{_stable_hash(row['gap_key'])[:16]}"
        row["status"] = "OPEN"
        row["epistemic_class"] = "UNKNOWN"
        rows.append(row)
    rows.sort(key=lambda row: (-row["decision_value_proxy"], row["gap_key"]))
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return {
        "ranking_method": "aggregate decision weight with 0.5 cross-objective reuse multiplier",
        "not_claimed": ["monetary value of information", "causal intervention value"],
        "task_count": len(rows),
        "tasks": rows,
    }
