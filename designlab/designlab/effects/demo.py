"""Chapter 7 lab: python3 -m effects.demo [section] [options]

Sections: hotel, keys, lookup, lease, saga, replay, sweep, all.
Options for the try-it-yourself exercises:
    --override TOOL=CONTRACT   e.g. fare-charge=none
    --break-at STEP            fail one saga step (hold, charge, ...)
    --rate R                   timeout rate for replay (default 0.05)
    --inject no-key            drop keys on native retries
"""
from __future__ import annotations

import argparse
import sys

from chain.record import Permission
from common.rand import DEFAULT_SEED
from corpus.tools import SupplierSim, SupplierTimeout, spec
from . import replay, saga
from .execute import Executor
from .keys import KeyIssuer, KeyRefused
from .ledger import Ledger, LedgerConflict, StaleLease


def head(title: str) -> None:
    print(f"\n== {title}")


def hotel() -> None:
    head("hotel: the Chapter 2 timeout against a one-room cancel")
    req = {"intent": "INT-HTL-1", "target": "HTL-88214",
           "rooms_to_cancel": 1}
    sim = SupplierSim(spec("hotel-cancel-direct"), faults={1: "late"})
    sim.stock("HTL-88214", 2)
    for attempt in (1, 2):
        try:
            sim.call(req)
            print(f"attempt {attempt}: ok")
            break
        except SupplierTimeout:
            print(f"attempt {attempt}: timeout at 8.0 s, retrying")
    rooms = [r["item"] for r in sim.effects_for("HTL-88214")]
    print(f"unkeyed: rooms canceled {rooms} of 2")
    sim = SupplierSim(spec("hotel-cancel-direct"), faults={1: "late"})
    sim.stock("HTL-88214", 2)
    led = Ledger()
    perm = Permission("PRM-31877", "policy-engine", "hotel-cancel", 800.0)
    ek = KeyIssuer().mint(perm, sim.tool.name, req)
    e = Executor(led, {sim.tool.name: sim}).run(ek, req)
    rooms = [r["item"] for r in sim.effects_for("HTL-88214")]
    print(f"ledger: rooms canceled {rooms} of 2, entry {e.state}")
    for at, state, note in e.history:
        print(f"  +{at:4.1f}s {state:<10} {note}")


def keys() -> None:
    head("keys: three requests, one key")
    issuer, led = KeyIssuer(), Ledger()
    p1 = Permission("PRM-31902", "policy-engine", "refunds-v3", 1500.0)
    req = {"intent": "INT-RF-1", "target": "LTG-4471902",
           "amount_usd": 412.60}
    ek = issuer.mint(p1, "processor-refund", req)
    sim = SupplierSim(spec("processor-refund"))
    ex = Executor(led, {"processor-refund": sim})
    first = ex.run(ek, req)
    print(f"1 key {ek.key[:17]}..: {first.state}, "
          f"{first.receipt['effect_id']}")
    again = ex.run(issuer.mint(p1, "processor-refund", req), req)
    print(f"2 same key, same request: stored receipt "
          f"{again.receipt['effect_id']}, calls {sim.calls}")
    try:
        issuer.mint(p1, "processor-refund", dict(req, amount_usd=41.26))
    except KeyRefused as err:
        print("3 same permission, new amount: KeyRefused")
    try:
        led.reserve(type(ek)(ek.key, ek.permission_id, ek.tool,
                             "0" * 16, 0.0), 0.0)
    except LedgerConflict:
        print("3b same key, different fingerprint: ledger conflict")
    p2 = Permission("PRM-31944", "policy-engine", "refunds-v3", 1500.0)
    ek2 = issuer.mint(p2, "processor-refund", req)
    second = ex.run(ek2, req)
    print(f"4 new permission, same amount: new key, "
          f"{second.receipt['effect_id']}")
    print(f"supplier refunds on LTG-4471902: "
          f"{len(sim.effects_for('LTG-4471902'))}")


def lookup() -> None:
    head("lookup: an unknown rebooking, resolved by asking")
    sim = SupplierSim(spec("airline-rebook-b"), faults={1: "late"})
    led = Ledger()
    perm = Permission("PRM-32015", "policy-engine", "rebook", 800.0)
    req = {"intent": "INT-RB-1", "target": "LTG-4380117",
           "flight": "ORD-DEN 1735"}
    ek = KeyIssuer().mint(perm, sim.tool.name, req)
    ex = Executor(led, {sim.tool.name: sim}, lags=lambda _: 22.0)
    e = ex.run(ek, req)
    for at, state, note in e.history:
        print(f"  +{at:4.1f}s {state:<10} {note}")
    print(f"supplier tickets: {len(sim.records)}, open "
          f"{e.resolutions[0][0]:.0f} s after the timeout")


def lease() -> None:
    head("lease: a paused run wakes up holding a stale token")
    led = Ledger()
    perm = Permission("PRM-32100", "policy-engine", "rebook", 800.0)
    req = {"intent": "INT-RB-2", "target": "LTG-4479310"}
    ek = KeyIssuer().mint(perm, "airline-rebook-a", req)
    led.reserve(ek, 0.0)
    a = led.acquire(ek.key, "worker-a", 0.0, ttl=30.0)
    print(f"worker-a holds token {a}, then pauses for an approval")
    b = led.acquire(ek.key, "worker-b", 95.0, ttl=30.0)
    led.move(ek.key, "attempting", 95.0, "attempt 1", b)
    print(f"worker-b takes token {b} at +95 s and attempts")
    try:
        led.move(ek.key, "committed", 140.0, "worker-a result", a)
    except StaleLease as err:
        print(f"worker-a at +140 s: StaleLease, token {a}, "
              f"current {led.entries[ek.key].lease_token}")


def saga_section(override, break_at: str) -> None:
    head("saga: rebooking, 1,000 failure injections per order")
    for name, order in (("safe order", saga.SAFE),
                        ("pilot order", saga.PILOT)):
        r = saga.inject(1_000, order)
        print(f"{name:<12} stranded {r['stranded']:>3}, restored "
              f"{r['restored']:>3}, rebooked {r['rebooked']:>3}")
    step = break_at or "issue"
    kind = "timeout" if override else "refused"
    head(f"saga: break at {step} ({kind})")
    s = saga.run_saga(saga.SAFE, step, kind, override=override)
    print(f"done {s.done}")
    print(f"failed at {s.failed_at}: {s.why}")
    print(f"compensations fired {s.compensated}")
    print(f"to a person {s.for_people or 'none'}")
    print(f"old seat kept {s.old_seat}, stranded {s.stranded}")


def replay_section(rate: float, override, inject: str) -> int:
    head("replay: 10,000 runs, keyed against unkeyed")
    status = 0
    for keyed in (False, True):
        r = replay.run(10_000, rate, keyed=keyed, override=override,
                       inject=inject if keyed else "")
        print("\n".join(r.lines()))
        print()
        if keyed and not r.report.ok:
            status = 1
    return status


def sweep() -> None:
    head("sweep: duplicates against timeout rate, 10,000 runs each")
    print("rate   unkeyed  keyed")
    for rate, u, k in replay.sweep():
        print(f"{rate:>4.0%}   {u:>7}  {k:>5}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="effects.demo")
    ap.add_argument("section", nargs="?", default="all")
    ap.add_argument("--override", action="append", default=[])
    ap.add_argument("--break-at", default="")
    ap.add_argument("--rate", type=float, default=0.05)
    ap.add_argument("--inject", default="")
    a = ap.parse_args(argv)
    override = dict(o.split("=", 1) for o in a.override) or None
    print(f"seed {DEFAULT_SEED}, corpus tools 18, clock simulated")
    s = a.section
    status = 0
    if s in ("hotel", "all"):
        hotel()
    if s in ("keys", "all"):
        keys()
    if s in ("lookup", "all"):
        lookup()
    if s in ("lease", "all"):
        lease()
    if s in ("saga", "all"):
        saga_section(override, a.break_at)
    if s in ("replay", "all"):
        status = replay_section(a.rate, override, a.inject)
    if s in ("sweep",):
        sweep()
    return status


if __name__ == "__main__":
    sys.exit(main())
