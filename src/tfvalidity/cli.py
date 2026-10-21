from __future__ import annotations

import argparse
import json
import sys
import time

from . import pipeline
from .config import load_config


def _run_one(cmd: str, cfg, args):
    if cmd == "fetch":
        return pipeline.stage_fetch(cfg, force=args.force)
    if cmd == "audit":
        return pipeline.stage_audit(cfg)
    if cmd == "multiscale":
        return pipeline.stage_multiscale(cfg)
    if cmd == "backtest":
        return pipeline.stage_backtest(cfg)
    if cmd == "finest":
        return pipeline.stage_finest(cfg)
    if cmd == "stats":
        return pipeline.stage_stats(cfg)
    if cmd == "capacity":
        return pipeline.stage_capacity(cfg)
    if cmd == "equities":
        return pipeline.stage_equities(cfg)
    if cmd == "surrogates":
        return pipeline.stage_surrogates(cfg)
    if cmd == "live":
        if args.loop:
            while True:
                out = pipeline.stage_live(cfg)
                print(json.dumps(out, default=str), flush=True)
                time.sleep(args.interval_seconds)
        return pipeline.stage_live(cfg)
    if cmd == "figures":
        from .plots import make_all

        return {"figures": [str(p) for p in make_all()]}
    if cmd == "report":
        return pipeline.stage_report(cfg)
    raise KeyError(cmd)


ORDER = ["fetch", "audit", "multiscale", "backtest", "finest", "stats", "capacity", "equities", "surrogates", "live", "figures", "report"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tfvalidity", description="Timeframe validity study pipeline")
    parser.add_argument("command", choices=ORDER + ["all"])
    parser.add_argument("--config", default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--interval-seconds", type=int, default=3600)
    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    if args.command == "all":
        for cmd in ORDER:
            print(f"=== {cmd} ===", flush=True)
            out = _run_one(cmd, cfg, args)
            print(json.dumps(out, default=str)[:4000], flush=True)
        return 0
    out = _run_one(args.command, cfg, args)
    print(json.dumps(out, default=str)[:20000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
