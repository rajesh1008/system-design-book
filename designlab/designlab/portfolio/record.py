"""Record the chapter's calls live, once.

    PYTHONPATH=. python3 -m portfolio.record [--only STEP] [--cap 0.45]
        [--check]

Runs every candidate of every step against its golden set, then (with
--check) the forty router tasks under each rule, through the pool:
a request already recorded, here or in Chapter 13, is replayed free.
The key is read from the environment by the client and never printed.
"""
from __future__ import annotations

import argparse
import sys

from common.client import HttpTransport
from common.spend import SpendMeter

from .cases import router_tasks
from .check import run_check
from .pool import PoolTransport
from .steps import load_steps
from . import table as tbl


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--cap", type=float, default=0.45)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--tasks", type=int, default=20)
    ap.add_argument("--rules", default="gated,cost-only")
    a = ap.parse_args(argv)
    live = SpendMeter(cap_usd=a.cap)
    meter = SpendMeter(cap_usd=50.0)       # replays are priced, not paid
    tr = PoolTransport(live=HttpTransport(), live_meter=live)
    steps = load_steps()
    for name, step in steps.items():
        if a.only and name != a.only:
            continue
        runs = tbl.measure(step, tr, meter)
        for label, res in runs.items():
            print(f"{name:14} {label:9} {res.passed}/{len(res.cases)}"
                  f" p95 {res.p95_s:5.1f}s ${res.cost_usd:.4f}"
                  f" live ${live.spent_usd:.4f}")
            for r in res.cases:
                if not r.passed:
                    print("   ", r.case_id,
                          "; ".join(f"{v.code}: {v.detail}"[:70]
                                    for v in r.violations))
    if a.check:
        tasks = router_tasks()[:a.tasks]
        for rule in a.rules.split(","):
            table = tbl.build(steps, tr, rule, meter)
            res = run_check(tasks, steps, table, tr, rule, meter)
            print(f"check {rule:9} {res.success}/{res.n_tasks}"
                  f" ${res.cost_per_task:.4f}/task"
                  f" live ${live.spent_usd:.4f}")
    print(f"sent {tr.sent} new calls; live ${live.spent_usd:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
