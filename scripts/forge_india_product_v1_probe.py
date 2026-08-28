"""Run the bounded FORGE India product-resolution usefulness battery."""

from __future__ import annotations

import json
import statistics
import time
from collections import Counter
from pathlib import Path
from typing import Any

from forge.india_v1.catalog import get_catalog
from forge.india_v1.objective import resolve_objective
from forge.india_v1.view_model import compose_buildability_view_model


QUERY_GROUPS = {
    "machine_tools": ["horizontal boring mill", "tool and cutter grinder", "wire EDM machine", "deep hole drilling machine", "rotary table"],
    "pumps": ["progressive cavity pump", "magnetic drive pump", "boiler feed pump", "peristaltic pump", "submersible sewage pump"],
    "compressors": ["oil free screw compressor", "reciprocating gas compressor", "centrifugal air compressor", "refrigeration compressor", "roots blower"],
    "motors": ["flameproof induction motor", "servo motor", "switched reluctance motor", "gear motor", "linear motor"],
    "transformers": ["furnace transformer", "dry type transformer", "instrument transformer", "traction transformer", "distribution transformer"],
    "textile": ["air jet loom", "carding machine", "rapier loom", "fabric inspection machine", "yarn winding machine"],
    "food": ["milk homogenizer", "spray dryer", "fruit pulping machine", "continuous fryer", "grain color sorter"],
    "packaging": ["carton erecting machine", "tube filling machine", "vacuum packaging machine", "label applicator", "pallet wrapping machine"],
    "medical": ["oxygen concentrator", "anesthesia workstation", "dialysis machine", "ultrasound scanner", "surgical autoclave"],
    "laboratory": ["gas chromatograph", "laboratory centrifuge", "spectrophotometer", "environmental test chamber", "rotary evaporator"],
    "semiconductor": ["plasma etching equipment", "wafer dicing machine", "wire bonder", "spin coater", "semiconductor wet bench"],
    "electronics": ["pick and place machine", "reflow oven", "printed circuit board tester", "industrial power supply", "fiber optic transceiver"],
    "robots": ["delta robot", "welding robot", "autonomous mobile robot", "robotic palletizer", "gantry robot"],
    "agriculture": ["seed drill", "rice transplanter", "combine harvester", "agricultural drone", "feed pellet mill"],
    "construction": ["concrete batching plant", "tower crane", "hydraulic breaker", "road milling machine", "tunnel boring machine"],
    "mining": ["jaw crusher", "flotation cell", "vibrating screen", "slurry pump", "ore sorting machine"],
    "automotive": ["electric vehicle inverter", "automotive stamping press", "battery pack assembly line", "wheel alignment machine", "fuel injection system"],
    "rail_marine": ["railway axle", "railway traction motor", "marine gearbox", "shipboard desalination plant", "railway wheel lathe"],
    "aerospace_energy": ["satellite reaction wheel", "rocket turbopump", "wind turbine gearbox", "industrial heat pump", "electrolyzer stack"],
    "chemicals_materials": ["induction furnace", "ceramic kiln", "polymer extruder", "vacuum furnace", "plate heat exchanger"],
}

FORBIDDEN_PUBLIC_TERMS = (
    "reference primitive", "canonical_name", "record_id", "shared:material:",
    "source pack names a primitive", "canonical v1 record",
)


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round((len(ordered) - 1) * fraction))]


def run() -> dict[str, Any]:
    catalog = get_catalog()
    queries = [(group, query) for group, values in QUERY_GROUPS.items() for query in values]
    assert len(queries) == 100
    rows: list[dict[str, Any]] = []
    latencies: list[float] = []

    for group, query in queries:
        started = time.perf_counter()
        resolved = resolve_objective(query, catalog)
        elapsed_ms = (time.perf_counter() - started) * 1000
        latencies.append(elapsed_ms)
        resolution = resolved["resolution"]
        classification = resolution["classification"]
        row: dict[str, Any] = {
            "group": group,
            "query": query,
            "classification": classification,
            "selected": (resolution.get("selected") or {}).get("title"),
            "nearest": (resolution.get("nearest") or {}).get("title"),
            "candidate_count": len(resolution.get("candidates") or ()),
            "latency_ms": round(elapsed_ms, 2),
            "safe_resolution": bool(
                (classification in {"EXACT", "STRONG"} and resolution.get("can_analyze"))
                or (classification == "NEAREST" and resolution.get("requires_confirmation") and not resolution.get("selected"))
                or (classification == "UNRESOLVED" and not resolution.get("selected"))
            ),
        }
        if classification in {"EXACT", "STRONG"} and resolution.get("selected"):
            view = compose_buildability_view_model(resolution["selected"]["title"], catalog).to_dict()
            serialized = json.dumps(view).casefold()
            typed_count = sum(len(view.get(key) or ()) for key in ("components", "processes", "equipment", "materials", "capabilities"))
            row.update({
                "has_decomposition": bool(view.get("major_systems") or typed_count),
                "typed_requirement_count": typed_count,
                "bottleneck_count": len(view.get("critical_bottlenecks") or ()),
                "localization_step_count": len(view.get("localization_path") or ()),
                "public_payload_clean": not any(term in serialized for term in FORBIDDEN_PUBLIC_TERMS),
            })
        rows.append(row)

    counts = Counter(row["classification"] for row in rows)
    analyzable = [row for row in rows if row["classification"] in {"EXACT", "STRONG"}]
    useful = counts["EXACT"] + counts["STRONG"] + counts["NEAREST"]
    return {
        "schema_version": "forge-india-product-v1-probes-v1",
        "query_count": len(rows),
        "group_count": len(QUERY_GROUPS),
        "classification_counts": dict(sorted(counts.items())),
        "useful_resolution_rate": round(useful / len(rows), 4),
        "safe_resolution_rate": round(sum(bool(row["safe_resolution"]) for row in rows) / len(rows), 4),
        "analyzable_quality": {
            "count": len(analyzable),
            "decomposition_rate": round(sum(bool(row.get("has_decomposition")) for row in analyzable) / max(1, len(analyzable)), 4),
            "bounded_bottleneck_rate": round(sum(0 <= int(row.get("bottleneck_count", 0)) <= 7 for row in analyzable) / max(1, len(analyzable)), 4),
            "localization_path_rate": round(sum(int(row.get("localization_step_count", 0)) > 0 for row in analyzable) / max(1, len(analyzable)), 4),
            "clean_public_payload_rate": round(sum(bool(row.get("public_payload_clean")) for row in analyzable) / max(1, len(analyzable)), 4),
        },
        "latency_ms": {
            "median": round(statistics.median(latencies), 2),
            "p95": round(percentile(latencies, 0.95), 2),
            "max": round(max(latencies), 2),
        },
        "unresolved_queries": [row["query"] for row in rows if row["classification"] == "UNRESOLVED"],
        "results": rows,
    }


if __name__ == "__main__":
    output = Path("docs/FORGE_INDIA_PRODUCT_V1_PROBES.json")
    report = run()
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "results"}, indent=2))
