"""Chapter 16 demo: the tool-argument layer on a seeded call stream.

    python3 -m toolargs.demo --seed 16
    python3 -m toolargs.demo --seed 16 --inject schema-only
    python3 -m toolargs.demo --seed 16 --inject unbounded-repair
    python3 -m toolargs.demo --seed 16 --rule reason-in-record
    python3 -m toolargs.demo --case okafor
"""
from __future__ import annotations

import argparse
from collections import Counter

from common.clock import FixedClock
from common.text import emit
from common.trail import TrailWriter, check_trail

from . import schema, world
from .cases import SimProposer, Stream
from .layer import Intake, Tool, digest
from .repair import run_call
from .tools import TOOLS

START = "2026-05-18T09:00:00-05:00"     # Monday, May 18, 2026, CDT


def run(seed: int = 16, calls: int = 20000, inject: str | None = None,
        rule: str | None = None, w: world.World | None = None) -> dict:
    w = w or world.build()
    trail = TrailWriter(clock=FixedClock(start=START, step_seconds=0.05))
    mode = "schema-only" if inject == "schema-only" else "full"
    rules = (world.RULES[rule],) if rule else ()
    intake = Intake(w, trail, mode=mode, rules=rules)
    tool = Tool(w)
    proposer = SimProposer(seed)
    unbounded = inject == "unbounded-repair"
    outcomes = Counter()
    repairs_hist = Counter()
    model_calls = 0
    rejected_first = 0
    for case in Stream(w, seed).calls(calls):
        o = run_call(proposer, case, intake, tool,
                     budget=None if unbounded else 2, bare=unbounded)
        model_calls += o.model_calls
        if o.reasons:
            rejected_first += 1
            repairs_hist[o.repairs] += 1
        key = o.status if o.status != "handed_off" else f"off:{o.why}"
        if o.status == "repaired":
            key = f"repaired:{o.repairs}"
        outcomes[key] += 1
    return {"calls": calls, "intake": intake, "tool": tool,
            "outcomes": outcomes, "rejected_first": rejected_first,
            "model_calls": model_calls, "repairs_hist": repairs_hist,
            "trail": trail}


def pct(a, b):
    return f"{100 * a / b:5.1f}%" if b else "  n/a"


def report(r: dict, seed: int, inject, rule) -> None:
    n, i, t, o = r["calls"], r["intake"], r["tool"], r["outcomes"]
    rej = r["rejected_first"]
    label = "schema only" if inject == "schema-only" else "schema+world"
    emit(f"toolargs  seed={seed}  calls={n}  intake={label}")
    if inject:
        emit(f"inject: {inject}")
    if rule:
        emit(f"rule added: {rule}")
    first_valid = n - (i.counts["schema_rejected"])
    emit(f"{'schema-valid proposals':36}{first_valid:>7}  "
         f"{pct(first_valid, n)}")
    emit(f"{'world-rejected on first proposal':36}{rej:>7}  "
         f"{pct(rej, n)}")
    if rej:
        if inject == "unbounded-repair":
            h = r["repairs_hist"]
            fixed = rej - o["off:ceiling"]
            mean = sum(k * v for k, v in h.items()) / rej
            emit(f"{'  eventually accepted':36}{fixed:>7}")
            emit(f"{'  stopped at the ceiling (50)':36}"
                 f"{o['off:ceiling']:>7}")
            emit(f"{'  mean repairs per rejected call':36}{mean:>7.1f}")
            emit(f"{'  rejected calls with 10+ repairs':36}"
                 f"{sum(v for k, v in h.items() if k >= 10):>7}")
            emit(f"{'  most repairs on one call':36}{max(h):>7}")
        else:
            r1, r2 = o["repaired:1"], o["repaired:2"]
            off = o["off:budget"] + o["off:no_progress"]
            emit(f"{'  repaired after 1 attempt':36}{r1:>7}")
            emit(f"{'  repaired after 2 attempts':36}{r2:>7}")
            emit(f"{'  handed off, budget spent':36}{o['off:budget']:>7}")
            emit(f"{'  handed off, no progress':36}"
                 f"{o['off:no_progress']:>7}")
            emit(f"{'repaired within two attempts':36}{r1 + r2:>7}  "
                 f"{pct(r1 + r2, rej)}")
            emit(f"{'handed off to the agent desk':36}{off:>7}  "
                 f"{pct(off, rej)}")
    emit(f"{'world-invalid calls that reached a tool':40}"
         f"{t.world_invalid:>3}")
    emit(f"{'rejected calls that reached a tool':40}"
         f"{t.rejected_by_intake:>3}")
    if t.wrong_ticket:
        emit(f"{'  another passenger ticket reissued':40}"
             f"{t.wrong_ticket:>3}")
    if t.over_fare_usd:
        emit(f"{'  refunded above fare left (USD)':36}"
             f"{t.over_fare_usd:>7.2f}")
    emit(f"{'refunds labeled with no cancellation':40}{t.mislabeled:>3}")
    emit(f"{'model calls per effect call':36}"
         f"{r['model_calls'] / n:>7.3f}")
    if i.reasons:
        emit("rejections by reason (every attempt):")
        for reason, k in i.reasons.most_common():
            emit(f"  {reason:34}{k:>5}")
    probs = check_trail(r["trail"].lines)
    emit(f"trail lines {len(r['trail'].lines)}, "
         f"chain {'intact' if not probs else probs[0]}")


def okafor() -> None:
    """The opening's call, check by check."""
    w = world.build()
    args = {"itinerary_id": "LTG-5208841", "ticket_number": "TKT-40219",
            "passenger_name": "OKAFOR/TUNDE",
            "new_flight_id": "FLT-904452",
            "fare_difference_usd": "318.40", "reason": "voluntary"}
    emit("call: rebook_ticket 2.1, session LTG-5208841")
    for k, v in args.items():
        emit(f"  {k:22}{v}")
    errs = schema.validate(args, TOOLS["rebook_ticket"]["input_schema"])
    emit(f"schema check      {'pass' if not errs else errs}")
    old = w.tickets["TKT-40219"].passenger.split("/")[0]
    on_itin = [w.tickets[x].passenger
               for x in w.itineraries["LTG-5208841"]]
    surname_ok = any(p.split("/")[0] == old for p in on_itin)
    emit(f"May 7 name check  surname on itinerary: "
         f"{'pass' if surname_ok else 'fail'}")
    emit(f"May 7 token check itinerary in session: pass")
    rej = w.check("rebook_ticket", args, "LTG-5208841")
    emit(f"world check       {rej.reason}")
    emit(f"  field {rej.field}")
    emit(f"  hint  {rej.hint}"[:70])
    emit(f"digest a card must bind: {digest('rebook_ticket', args)}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=16)
    ap.add_argument("--calls", type=int, default=20000)
    ap.add_argument("--inject", choices=("schema-only",
                                         "unbounded-repair"))
    ap.add_argument("--rule", choices=tuple(world.RULES))
    ap.add_argument("--case", choices=("okafor",))
    a = ap.parse_args(argv)
    if a.case:
        okafor()
        return
    r = run(a.seed, a.calls, a.inject, a.rule)
    report(r, a.seed, a.inject, a.rule)


if __name__ == "__main__":
    main()
