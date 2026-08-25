#!/usr/bin/env python3
"""Build a deterministic, hash-only inventory of immutable HOMI corpus roots."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from forge.reality import SourceLayer, inventory_corpus, manifest_payload, write_canonical_json


DEFAULT_ROOTS = (
    ("manus_raw_zips", Path(r"C:\FORGE-RESEARCH-CORPUS\manus\raw-zips"), SourceLayer.RAW),
    ("manus_extracted", Path(r"C:\FORGE-RESEARCH-CORPUS\manus\extracted"), SourceLayer.EXTRACTED),
    ("glm_foundry", Path(r"C:\FORGE-GLM-FOUNDRY"), SourceLayer.EXTRACTED),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "research" / "homi" / "staging" / "corpus_manifest.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    snapshots = []
    roots = []
    for corpus_id, path, layer in DEFAULT_ROOTS:
        resolved = path.resolve(strict=True)
        rows = inventory_corpus(
            resolved,
            corpus_id=corpus_id,
            source_layer=layer,
            license="UNSPECIFIED",
        )
        snapshots.extend(rows)
        roots.append(
            {
                "corpus_id": corpus_id,
                "logical_name": path.name,
                "source_layer": layer.value,
                "storage_posture": "external_immutable",
                "artifact_count": len(rows),
            }
        )
    payload = manifest_payload(snapshots, roots=roots)
    write_canonical_json(args.output, payload)
    print(f"wrote {payload['artifact_count']} artifacts to {args.output}")
    print(f"manifest_hash={payload['manifest_hash']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
