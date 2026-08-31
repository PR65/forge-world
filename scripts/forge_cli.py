"""FORGE WORLD command line interface (headless runs, byte-reproducible)."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from forge.engine import ForgeEngine, ObjectiveSpecInput
from forge.pack import load_pack


def cmd_run(args):
    pack_path = args.pack if os.path.sep in args.pack or args.pack.endswith(".yaml") else str(
        Path(__file__).resolve().parent.parent / "packs" / f"{args.pack}.yaml"
    )
    pk = load_pack(pack_path)
    eng = ForgeEngine(pk)
    obj = ObjectiveSpecInput(
        variant_id=args.variant,
        annual_units=args.units,
        geography=args.geography,
        deadline_year=args.deadline,
        min_dva=args.min_dva,
        budget_usd=args.budget,
        funded_projects=args.fund.split(",") if args.fund else [],
        analyst_capacity_assumptions=_parse_assumptions(args.assume),
    )
    resp = eng.run_scenario(obj, shock_ids=args.shocks.split(",") if args.shocks else None)
    payload = resp if args.full else _slim(resp)
    print(json.dumps(payload, indent=1, default=str))


def _parse_assumptions(spec: Optional[str]):
    out = {}
    if not spec:
        return out
    for part in spec.split(";"):
        if ":" not in part:
            continue
        item, rng = part.split(":", 1)
        lo, hi = rng.split("-")
        out[item.strip()] = (float(lo), float(hi))
    return out


def _slim(resp):
    return {
        "run_id": resp["run"]["run_id"],
        "pack": resp["pack"],
        "result": {
            k: v
            for k, v in resp["result"].items()
            if k not in ("years",)
        },
        "years": resp["result"]["years"],
        "dva": {"fraction": resp["dva"]["fraction"]},
        "plan": resp["plan"],
        "voi": resp["voi"],
        "reverse": resp["reverse"],
        "frontier": resp["frontier"],
    }


def cmd_packs(_args):
    from pathlib import Path

    for p in sorted(Path("packs").glob("*.yaml")):
        try:
            pk = load_pack(str(p))
            s = pk.summary()
            print(f"{s['pack_id']:24s} v{s['version']:8s} entities={s['entities']:4d} "
                  f"evidence={s['evidence']:3d} variants={len(s['variants'])}")
        except Exception as e:
            print(f"{p.stem}: LOAD ERROR {e}")


def cmd_adapter(args):
    from forge.adapters import run_adapter_demo

    print(json.dumps(run_adapter_demo(args.country), indent=1)[:6000])


def _objective_constraints(args):
    from forge.india_v1.objective_models import ObjectiveConstraint

    constraints = [ObjectiveConstraint(kind="avoid_country", value=value) for value in args.avoid_country]
    for raw in args.constraint:
        if "=" not in raw:
            raise ValueError("--constraint must use KIND=VALUE")
        kind, value = raw.split("=", 1)
        constraints.append(ObjectiveConstraint(kind=kind.strip(), value=value.strip()))
    return tuple(constraints)


def cmd_objective_compile(args):
    from forge.india_v1.objective_compiler import compile_industrial_objective
    from forge.india_v1.objective_models import IndustrialObjective

    objective = IndustrialObjective(
        objective_type="manufacture",
        product=args.product,
        quantity=args.quantity,
        output_unit=args.unit,
        period=args.period,
        geography=args.geography,
        target_year=args.target_year,
        constraints=_objective_constraints(args),
        confirm_family=args.confirm_family,
    )
    compilation = compile_industrial_objective(objective, use_fixtures=not args.no_fixtures)
    print(json.dumps(compilation.to_dict(), indent=2, sort_keys=True, ensure_ascii=False))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="forge")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run a scenario and emit JSON")
    r.add_argument("--pack", required=True)
    r.add_argument("--variant", required=True)
    r.add_argument("--units", type=float, required=True)
    r.add_argument("--geography", default="INDIA")
    r.add_argument("--deadline", type=int, default=2030)
    r.add_argument("--min-dva", type=float, default=0.70)
    r.add_argument("--budget", type=float, default=None)
    r.add_argument("--fund", default="")
    r.add_argument("--shocks", default="")
    r.add_argument("--assume", default="", help="item:lo-hi;item:lo-hi capacity assumptions")
    r.add_argument("--full", action="store_true")
    r.set_defaults(func=cmd_run)

    p = sub.add_parser("packs", help="list knowledge packs")
    p.set_defaults(func=cmd_packs)

    a = sub.add_parser("adapter", help="fetch live World Bank observations")
    a.add_argument("--country", default="IND")
    a.set_defaults(func=cmd_adapter)

    objective = sub.add_parser("objective", help="compile a bounded industrial objective")
    objective_sub = objective.add_subparsers(dest="objective_cmd", required=True)
    compile_parser = objective_sub.add_parser("compile", help="compile objective demand, capacity, and closure JSON")
    compile_parser.add_argument("--product", required=True)
    compile_parser.add_argument("--quantity", required=True, type=float)
    compile_parser.add_argument("--unit", default="units")
    compile_parser.add_argument("--per", dest="period", choices=("year", "month", "week", "day"), default="year")
    compile_parser.add_argument("--geography", default="INDIA")
    compile_parser.add_argument("--target-year", type=int, default=2030)
    compile_parser.add_argument("--avoid-country", action="append", default=[])
    compile_parser.add_argument("--constraint", action="append", default=[], metavar="KIND=VALUE")
    compile_parser.add_argument("--confirm-family", action="store_true")
    compile_parser.add_argument("--no-fixtures", action="store_true", help="disable deterministic validation fixtures")
    compile_parser.add_argument("--json", action="store_true", help="emit deterministic JSON (the V0 output format)")
    compile_parser.set_defaults(func=cmd_objective_compile)

    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
