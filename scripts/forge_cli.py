"""FORGE WORLD command line interface (headless runs, byte-reproducible)."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

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

    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
