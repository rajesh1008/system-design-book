"""Re-record every Chapter 13 fixture from live calls.

    python3 -m models.record [--only NAME ...] [--cap 0.45]

Needs ANTHROPIC_API_KEY in the environment; the key is read by the
shared transport and goes nowhere else. Every call is priced by one
spend meter, and the run stops at the cap. Fixtures are redacted
request and response bodies; a test checks them for secrets.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import shutil
from pathlib import Path

from common.client import HttpTransport
from common.spend import SpendMeter

from . import variance
from .contract import load_contract, load_contracts
from .drift import Repoint
from .runner import golden_cases, run_suite

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"
ARCHIVE = HERE / "contracts" / "archive"

VARIANCE_CASES = ["rr-01", "rr-05", "rr-07", "rr-10", "rr-12", "rr-16"]


def alias_contract():
    """refund-reason as Lakeshore ran it before April 8, 2026: on an
    alias, with the dated snapshot it resolved to as the expected echo."""
    c = load_contracts()["refund-reason"]
    return dataclasses.replace(
        c, role="dated", model_id="claude-haiku-4-5", id_kind="alias",
        expect_echo="claude-haiku-4-5-20251001",
        sampling="temperature not set")


def fresh(d: Path) -> Path:
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    return d


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--cap", type=float, default=0.45)
    a = ap.parse_args(argv)
    want = set(a.only or [])
    on = lambda n: not want or n in want  # noqa: E731
    http, meter = HttpTransport(), SpendMeter(cap_usd=a.cap)
    cs = load_contracts()
    for name in ("refund-reason", "change-intent", "desk-note"):
        if on(name):
            run_suite(cs[name], http, meter, fresh(FIX / name))
    for arch in ("refund-reason-1.2", "desk-note-2.1"):
        if on(arch):
            run_suite(load_contract(ARCHIVE / f"{arch}.toml"), http, meter,
                      fresh(FIX / arch))
    if on("alias"):
        c = alias_contract()
        run_suite(c, http, meter, fresh(FIX / "alias-before"))
        run_suite(c, Repoint(http, "claude-haiku-5-5"), meter,
                  fresh(FIX / "alias-moved"))
    if on("variance"):
        rr = cs["refund-reason"]
        cases = [x for x in golden_cases(rr) if x["id"] in VARIANCE_CASES]
        dated = dataclasses.replace(rr, role="dated",
                                    model_id="claude-haiku-4-5-20251001",
                                    expect_echo="claude-haiku-4-5-20251001")
        for tag, c, cs_, n, t in (("small", rr, cases, 10, None),
                                  ("dated-t0", dated, cases[:5], 8, 0.0),
                                  ("dated-t1", dated, cases[:5], 8, 1.0)):
            s: list[dict] = []
            try:
                variance.collect(c, cs_, n, http, meter, temperature=t,
                                 out=s)
            finally:
                variance.save(FIX / f"variance-{tag}.json",
                              {"contract": c.name, "version": c.version,
                               "model": c.model_id, "temperature": t,
                               "n": n}, s)
    if on("amount"):
        # The archived note ran on mid; the small model is sampled more
        # because its calls cost a fiftieth as much.
        old = load_contract(ARCHIVE / "desk-note-0.9.toml")
        small = dataclasses.replace(old, role="small",
                                    model_id="claude-haiku-5-5",
                                    expect_echo="claude-haiku-5-5")
        for tag, c, n in (("mid", old, 3), ("small", small, 10)):
            s: list[dict] = []
            try:
                variance.collect(c, golden_cases(c), n, http, meter, out=s)
            finally:
                variance.save(FIX / f"variance-amount-{tag}.json",
                              {"contract": c.name, "version": c.version,
                               "model": c.model_id, "temperature": None,
                               "n": n}, s)
    print(json.dumps({"calls": meter.calls,
                      "spent_usd": round(meter.spent_usd, 4)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
