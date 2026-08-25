#!/usr/bin/env python3
"""Run the frozen novel-objective composition benchmark and rank its gaps."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from forge.composition import compose_benchmark_set, load_objective_seeds, rank_decision_gaps
from forge.reality import write_canonical_json
from forge.registry import load_registry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--objectives", type=Path, default=ROOT / "data" / "objectives" / "novel_objectives.yaml"
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "research" / "homi" / "composition" / "novel_objectives.json"
    )
    parser.add_argument(
        "--gaps", type=Path, default=ROOT / "research" / "homi" / "composition" / "decision_gaps.json"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    benchmark = load_objective_seeds(args.objectives)
    registry = load_registry()
    composition = compose_benchmark_set(registry, benchmark)
    gaps = rank_decision_gaps(composition)
    write_canonical_json(args.output, composition)
    write_canonical_json(args.gaps, gaps)
    print(
        f"objectives={composition['objective_count']} "
        f"mean_coverage={composition['mean_composition_coverage']:.3f} "
        f"decision_critical_unknowns={composition['total_decision_critical_unknowns']}"
    )
    print(f"ranked_gap_tasks={gaps['task_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
