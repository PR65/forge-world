"""Build deterministic end-of-campaign accounting for HOMI."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict

from forge.registry import load_registry


ROOT = Path(__file__).resolve().parent.parent
HOMI = ROOT / "research" / "homi"
OUTPUT = HOMI / "campaign_accounting.json"

CORPUS_REPORTS = {
    "manus-01": "pilot/manus_01_report.json",
    "manus-02": "waves/wave2/manus_02_report.json",
    "manus-03": "waves/wave2/manus_03_report.json",
    "manus-04": "waves/wave1/manus_04_report.json",
    "manus-05": "pilot/manus_05_report.json",
    "manus-06": "waves/wave2/manus_06_report.json",
    "manus-07": "waves/wave4/manus_07_report.json",
    "manus-08": "waves/wave3/manus_08_report.json",
    "manus-09": "waves/wave3/manus_09_report.json",
    "manus-10": "waves/wave4/manus_10_report.json",
    "manus-11": "pilot/manus_11_report.json",
    "manus-12": "waves/wave1/manus_12_report.json",
    "manus-13": "waves/wave2/manus_13_materials_reconciliation.json",
    "manus-14": "waves/wave3/manus_14_report.json",
    "manus-15": "waves/wave3/manus_15_report.json",
    "manus-16": "pilot/manus_16_context_report.json",
    "manus-17": "waves/wave4/manus_17_report.json",
    "manus-18": "waves/wave2/manus_18_report.json",
    "manus-19": "waves/wave3/manus_19_report.json",
    "manus-20": "waves/wave3/manus_20_report.json",
}


def _read(path: Path) -> Dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_accounting() -> Dict[str, Any]:
    conditioning = _read(HOMI / "staging" / "conditioning_report.json")
    archives = _read(HOMI / "staging" / "archive_integrity.json")
    gate0 = _read(HOMI / "gate0" / "claim_ledger.json")
    composition = _read(HOMI / "composition" / "novel_objectives.json")
    gaps = _read(HOMI / "composition" / "decision_gaps.json")
    closure = _read(HOMI / "targeted" / "closure_summary.json")
    promotions = _read(HOMI / "targeted" / "promotion_ledger.json")
    registry = load_registry()

    reports = []
    for corpus_id, relative in sorted(CORPUS_REPORTS.items()):
        path = HOMI / relative
        _read(path)
        reports.append(
            {
                "corpus_id": corpus_id,
                "report": f"research/homi/{relative}",
                "report_bytes": path.stat().st_size,
                "report_sha256": _sha(path),
                "promotion_authority": "STAGING_ONLY",
            }
        )

    kind_counts = Counter(node.kind for node in registry.nodes.values())
    evidence_classes = Counter(
        record.epistemic_class.value for record in registry.evidence.values()
    )
    capabilities = [node for node in registry.nodes.values() if node.kind == "capability"]
    cross_sector = [
        node
        for node in capabilities
        if len(node.metadata.get("mapped_pack_ids", ()) or ()) >= 2
    ]
    facilities = [node for node in registry.nodes.values() if node.kind == "facility"]
    capacities = [node for node in registry.nodes.values() if node.kind == "capacity_segment"]

    return {
        "schema_version": "1.0.0",
        "artifact_accounting": {
            "raw_and_research_artifacts": conditioning["artifact_count"],
            "unique_hashes": conditioning["unique_hash_count"],
            "duplicate_artifacts": conditioning["duplicate_artifact_count"],
            "structured_validated": conditioning["structured_artifact_count"],
            "inventoried_context": conditioning["status_counts"]["INVENTORIED_CONTEXT"],
            "staging_repairs": conditioning["repaired_artifact_count"],
            "malformed_unrepaired": conditioning["status_counts"]["MALFORMED_UNREPAIRED"],
            "intentionally_skipped": conditioning["status_counts"]["INTENTIONALLY_SKIPPED"],
            "inaccessible": 0,
            "raw_archive_packages": archives["package_count"],
            "raw_archive_entries": archives["entry_count"],
            "byte_matched_entries": archives["matched_entry_count"],
            "raw_integrity_failures": archives["failure_count"],
        },
        "corpus_coverage": {
            "expected_manus_corpora": 20,
            "reported_manus_corpora": len(reports),
            "complete": len(reports) == 20,
            "reports": reports,
            "counting_note": "Corpus claim/source/entity counts use corpus-specific units and are not summed as if they were independent canonical records.",
        },
        "gate0_staging": {
            "claims": gate0["claim_count"],
            "epistemic_class_counts": gate0["epistemic_class_counts"],
            "conflict_candidates": gate0["conflict_candidate_count"],
            "unspecified_license_claims": gate0["source_license_unspecified_count"],
            "canonical_promotions": gate0["promotion_count"],
        },
        "targeted_research": {
            "research_tasks": closure["research_policy"]["bounded_task_count"],
            "sources": promotions["source_count"],
            "source_snapshots": promotions["snapshot_count"],
            "observations": promotions["observation_count"],
            "promotions": promotions["promotion_count"],
            "source_lineage_fraction": 1.0,
            "effective_qualified_capacity_promotions": promotions[
                "effective_capacity_promotion_count"
            ],
        },
        "canonical_registry": {
            "snapshot_id": registry.snapshot_id,
            "pack_count": len(registry.packs),
            "node_count": len(registry.nodes),
            "edge_count": len(registry.edges),
            "evidence_count": len(registry.evidence),
            "entity_kind_counts": dict(sorted(kind_counts.items())),
            "evidence_epistemic_class_counts": dict(sorted(evidence_classes.items())),
            "facility_count": len(facilities),
            "capacity_segment_count": len(capacities),
            "canonical_capability_count": len(capabilities),
            "cross_sector_capability_count": len(cross_sector),
            "cross_sector_capability_ids": sorted(node.id for node in cross_sector),
        },
        "generalization": {
            "objective_count": composition["objective_count"],
            "mean_composition_coverage": composition["mean_composition_coverage"],
            "decision_critical_unknowns": composition[
                "total_decision_critical_unknowns"
            ],
            "ranked_research_tasks": gaps["task_count"],
            "objective_verdicts": {
                row["objective_id"]: row["adjudication"]["verdict"]
                for row in composition["objectives"]
            },
            "coverage_not_claimed": composition["objectives"][0][
                "coverage_not_claimed"
            ],
            "before_targeted_closure": closure[
                "composition_before_targeted_closure"
            ],
        },
        "derived_and_scenario_only": {
            "registry_derived_evidence": evidence_classes.get("DERIVED", 0),
            "registry_modelled_evidence": evidence_classes.get("MODELLED", 0),
            "registry_scenario_evidence": evidence_classes.get("SCENARIO", 0),
            "note": "Derived/modelled/scenario state remains distinct and never overwrites baseline observations.",
        },
        "known_limitations": [
            "Most external corpus claims remain staging because source rights and original-source snapshot metadata are unspecified.",
            "Facility presence and product scope remain much better covered than facility-specific qualified effective capacity.",
            "The novel-objective layer composes structural worlds but does not yet generate validated quantitative BOMs or solver-ready capacity networks automatically.",
            "Stale evidence is flagged in corpus reports but not yet maintained by an automatic refresh scheduler.",
        ],
    }


def main() -> None:
    payload = build_accounting()
    OUTPUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"artifacts={payload['artifact_accounting']['raw_and_research_artifacts']} "
        f"corpora={payload['corpus_coverage']['reported_manus_corpora']} "
        f"registry_nodes={payload['canonical_registry']['node_count']} "
        f"coverage={payload['generalization']['mean_composition_coverage']}"
    )


if __name__ == "__main__":
    main()
