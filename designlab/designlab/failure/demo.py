"""Chapter 12 lab: the refund failure at scale, injected and fixed.

    python3 -m failure.demo                    # everything
    python3 -m failure.demo --part fall        # one part
    python3 -m failure.demo --part tryit --mint attempt
    python3 -m failure.demo --part tryit --slow-s 2.5
    python3 -m failure.demo --part tryit --every 60

Parts: catalog, retry, fall, alert, settle, fixed, breaker, tryit.
Offline. No model is called and no network request leaves the box.
Times are America/Chicago (CDT) on April 14, 2026.
"""
from __future__ import annotations

import argparse
import random

from common.text import emit
from corpus.fall1 import (clock, generate_fall1, hms, most_slow_at,
                          SPIKE_START)

from .batch import replay_fixed, replay_injected, starts_while_open
from .breaker import Breaker
from .catalog import CATALOG, by_plane, kinds
from .degrade import rung
from .reconcile import (extra_credits, interval_scan, ratio_alert,
                        reconcile)
from .retry import POLICIES, RetryBudget, amplification, backoff

PARTS = ("catalog", "retry", "fall", "alert", "settle", "fixed",
         "breaker", "tryit")


def usd(x: float) -> str:
    return f"${x:,.2f}"


def part_catalog(f, a) -> None:
    emit(f"failure catalog: {len(CATALOG)} modes")
    emit("  by plane: " + ", ".join(f"{p} {n}" for p, n in
                                    by_plane().items()))
    emit("  by kind:  " + ", ".join(f"{k} {n}" for k, n in
                                    kinds().items()))
    for x in CATALOG:
        if x.plane == "outside":
            emit(f"  outside: {x.mode}")
            emit(f"    seen by {x.seen_by}; first move: {x.first_move}")


def part_retry(f, a) -> None:
    emit(f"{'plane':<10}{'operation':<20}{'timeout':>8}{'tries':>6}"
         f"  key")
    for p in POLICIES:
        emit(f"{p.plane:<10}{p.operation:<20}{p.timeout_s:>7.1f}s"
             f"{p.attempts:>6}  {p.key}")
    emit(f"three tries at each of five layers: "
         f"{amplification(5, 3)} calls")
    rng = random.Random(12)
    waits = [backoff(n, 1.0, 8.0, rng) for n in (1, 2, 3)]
    emit("full-jitter waits, base 1 s: " +
         ", ".join(f"{w:.2f} s" for w in waits))
    b = RetryBudget(size=3)
    tries = [b.may_retry() for _ in range(5)]
    emit(f"retry budget of 3, five failures: "
         f"{sum(tries)} retries, {5 - sum(tries)} refused")


def _report(run, refunds):
    return reconcile(run.lines(), run.owed(refunds),
                     set(run.ledger.entries))


def part_fall(f, a) -> None:
    refunds = f["fall1_refunds"]
    run = replay_injected(f)
    rep = _report(run, refunds)
    batch = [r for r in refunds if r["path"] == "batch"]
    emit(f"refunds owed: {len(refunds):,} "
         f"(batch {len(batch):,}, gateway {len(refunds) - len(batch)})")
    emit(f"processor calls: {run.calls():,}; credits: {rep.credits:,}")
    emit(f"duplicates: {rep.duplicates} on {len(rep.duplicate_charges)}"
         f" charges ({rep.paid_twice} twice, {rep.paid_three} three"
         f" times)")
    emit(f"paid in error: {usd(rep.duplicate_usd)}")
    ex = extra_credits(run.lines())
    emit(f"first duplicate {clock(ex[0]['at'])}, "
         f"last {clock(ex[-1]['at'])}")
    by = {}
    for x in ex:
        by[x["credential"]] = by.get(x["credential"], 0) + 1
    emit("duplicates by credential: " +
         ", ".join(f"{k} {v}" for k, v in sorted(by.items())))
    gw = [r for r in refunds if r["path"] == "gateway"]
    late = sum(1 for e in run.ledger.entries.values()
               if any(h[1] == "unknown" for h in e.history))
    emit(f"gateway path: {len(gw)} refunds, {late} timeouts, "
         f"{by.get('gw-effects', 0)} duplicates")
    emit(f"ledger entries: {len(run.ledger.entries)}; "
         f"credits with no ledger entry: {rep.orphans:,}")


def part_alert(f, a) -> None:
    run = replay_injected(f)
    runs = [hms(h, m) for h in (14, 15, 16) for m in (22, 52)]
    emit("ratio check: credits / charges, 30-min window, fires >1.05")
    for row in ratio_alert(run.lines(), runs):
        if not row["credits"]:
            continue
        flag = "FIRED" if row["fired"] else ""
        emit(f"  {clock(row['run'])[:5]}  window {clock(row['from'])[:5]}"
             f"-{clock(row['to'])[:5]}  {row['credits']:>5,} / "
             f"{row['charges']:>5,} = {row['ratio']:.3f} {flag}".rstrip())
    last = extra_credits(run.lines())[-1]["at"]
    emit(f"last duplicate {clock(last)}; alert {clock(hms(15, 52))}; "
         f"gap {(hms(15, 52) - last) / 60:.1f} min")


def part_settle(f, a) -> None:
    run = replay_injected(f)
    rep = _report(run, f["fall1_refunds"])
    emit("settlement file for April 14 against the permissions")
    emit(f"  refunds owed           {rep.owed:>7,}")
    emit(f"  credits in the file    {rep.credits:>7,}")
    emit(f"  charges paid           {rep.charges_paid:>7,}")
    emit(f"  owed and not paid      {rep.missing:>7,}")
    emit(f"  extra credits          {rep.duplicates:>7,}")
    emit(f"  extra, in dollars      {usd(rep.duplicate_usd):>10}")
    emit(f"  no ledger entry        {rep.orphans:>7,}")
    emit(f"found {rep.duplicates} of {rep.duplicates} by charge, "
         f"with no ledger needed")


def part_fixed(f, a) -> None:
    run = replay_fixed(f)
    rep = _report(run, f["fall1_refunds"])
    emit("April 28 path: key at grant, ledger, guarded client")
    emit(f"  processor calls {run.calls():,}; credits {rep.credits:,}")
    emit(f"  duplicates {rep.duplicates}; owed and not paid "
         f"{rep.missing}; no ledger entry {rep.orphans}")
    states = run.ledger.by_state()
    emit("  ledger: " + ", ".join(f"{k} {v:,}" for k, v in
                                  sorted(states.items())))
    rogue = replay_injected(f)
    emit(f"  same afternoon, old path: {_report(rogue, f['fall1_refunds']).duplicates}"
         f" duplicates")


def _breaker_run(f, slow_s: float):
    b = Breaker(slow_s=slow_s)
    run = replay_fixed(f, breaker=b)
    return b, run


def part_breaker(f, a) -> None:
    b, run = _breaker_run(f, a.slow_s)
    rep = _report(run, f["fall1_refunds"])
    opened = b.transitions[0][0]
    closed = [t for t, s in b.transitions if s == "closed"][-1]
    probes = sum(1 for _, s in b.transitions if s == "half-open")
    emit(f"breaker: {b.trip_share:.0%} of calls >= {b.slow_s} s or "
         f"failed, {b.window_s:.0f} s window")
    emit(f"  slow band begins {clock(SPIKE_START)}; half slow "
         f"{clock(most_slow_at())}")
    emit(f"  opened {clock(opened)} "
         f"({opened - most_slow_at():.0f} s after half were slow)")
    emit(f"  read probes {probes}; closed {clock(closed)}")
    emit(f"  rung while open: {rung(breaker_open=True)}")
    emit(f"  effects started while open: {starts_while_open(run)}")
    emit(f"  refunds held {run.held:,}; longest wait "
         f"{max(run.queue.waits) / 60:.1f} min")
    emit(f"  held refunds paid by {clock(run.drained_at)}")
    emit(f"  processor calls {run.calls():,}; duplicates "
         f"{rep.duplicates}; not paid {rep.missing}")


def part_tryit(f, a) -> None:
    if a.mint:
        for enforce in (False, True):
            run = replay_fixed(f, mint=a.mint, enforce=enforce)
            rep = _report(run, f["fall1_refunds"])
            emit(f"key per {a.mint}, guard {'on' if enforce else 'off'}:"
                 f" duplicates {rep.duplicates}, refused {run.refused},"
                 f" to people {run.to_people}")
    if a.slow_s != 4.0 or a.part == "tryit" and not (a.mint or a.every):
        for s in sorted({2.0, 4.0, 6.0, a.slow_s}):
            b, run = _breaker_run(f, s)
            opened = b.transitions[0][0] if b.transitions else None
            held = run.held
            emit(f"slow at {s:.1f} s: opened "
                 f"{clock(opened) if opened else 'never'}, "
                 f"held {held:,}, open-starts {starts_while_open(run)}")
    if a.every:
        run = replay_injected(f)
        for m in sorted({5, 60, a.every}):
            s = interval_scan(run.lines(), m * 60, hms(14, 0),
                              hms(18, 0))
            emit(f"scan every {m:>2} min: first flag "
                 f"{clock(s['flag_at'])}, {s['paid_before']} extra "
                 f"paid ({usd(s['usd_before'])})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices=PARTS)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--mint", choices=("action", "attempt"))
    ap.add_argument("--slow-s", type=float, default=4.0)
    ap.add_argument("--every", type=int, default=0)
    a = ap.parse_args()
    f = generate_fall1(a.seed)
    parts = [a.part] if a.part else PARTS[:-1]
    for i, p in enumerate(parts):
        if i:
            emit()
        emit(f"-- {p} --")
        globals()[f"part_{p}"](f, a)


if __name__ == "__main__":
    main()
