"""Verify and materialize the HOMI targeted research promotion ledger."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from forge.adapters import OfficialRecordCatalogAdapter
from forge.pack import load_pack
from forge.registry import load_registry


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "data" / "ingestion" / "homi_targeted_observations.yaml"
PACK = ROOT / "packs" / "targeted_industrial_reality.yaml"
OUTPUT = ROOT / "research" / "homi" / "targeted" / "promotion_ledger.json"


def build_ledger() -> Dict[str, Any]:
    results = OfficialRecordCatalogAdapter(CATALOG).load()
    pack = load_pack(PACK)
    registry = load_registry()
    rows = []
    for result in results:
        for observation, record, promotion in zip(
            result.observations, result.records, result.promotions
        ):
            if record.claim_id not in pack.evidence:
                raise ValueError(f"target pack is missing promoted evidence {record.claim_id}")
            registry_evidence_id = (
                f"pack:{pack.pack_id}:evidence:{record.claim_id}"
            )
            canonical = registry.nodes.get(observation.subject)
            if canonical is None:
                raise ValueError(f"observation subject is not canonical: {observation.subject}")
            mapped = []
            for node_id in canonical.metadata.get("mapped_entity_ids", ()) or ():
                node = registry.nodes.get(node_id)
                if (
                    node is not None
                    and node.pack_id == pack.pack_id
                    and registry_evidence_id in node.evidence_ids
                ):
                    mapped.append(node_id)
            if not mapped:
                raise ValueError(
                    f"no evidence-bearing targeted mapping for {observation.observation_id}"
                )
            rows.append(
                {
                    "claim_id": record.claim_id,
                    "source_id": result.source.id,
                    "source_snapshot_id": result.source_snapshot.snapshot_id,
                    "observation_id": observation.observation_id,
                    "canonical_subject": observation.subject,
                    "mapped_registry_entity_ids": sorted(mapped),
                    "epistemic_class": record.epistemic_class.value,
                    "registry_evidence_id": registry_evidence_id,
                    "promotion_record": promotion.to_json(),
                    "promotion_state": "PROMOTED_TO_EVIDENCE_AND_MAPPED_WORLD_STATE",
                    "capacity_semantics": "NO_EFFECTIVE_QUALIFIED_CAPACITY_PROMOTED",
                    "source_license": result.source_snapshot.license,
                }
            )
    rows.sort(key=lambda row: row["claim_id"])
    return {
        "schema_version": "1.0.0",
        "catalog": str(CATALOG.relative_to(ROOT)).replace("\\", "/"),
        "pack": str(PACK.relative_to(ROOT)).replace("\\", "/"),
        "source_count": len(results),
        "snapshot_count": len(results),
        "observation_count": len(rows),
        "promotion_count": len(rows),
        "effective_capacity_promotion_count": 0,
        "all_promotions_source_linked": all(row["source_id"] for row in rows),
        "rows": rows,
    }


def main() -> None:
    payload = build_ledger()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"sources={payload['source_count']} observations={payload['observation_count']} "
        f"promotions={payload['promotion_count']} effective_capacity=0"
    )


if __name__ == "__main__":
    main()
