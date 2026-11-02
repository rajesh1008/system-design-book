"""Chapter 8 lab: the asynchronous spine.

    python3 -m spine.demo                     # every part, seed 8
    python3 -m spine.demo --part desk         # one part
    python3 -m spine.demo --reviewers 3       # half the desk

Offline. No model is called. Numbers are illustrative.
"""
from __future__ import annotations

import argparse
import json

from common.text import emit

from . import backpressure as bp
from .deadletter import Consumer, parse_v2
from .fanout import QUEUES, deliver, fan_out, itineraries, summary
from .inbox import Inbox
from .order import (Event, LastArrivalWins, SequenceGuard,
                    partition_for, trial)

PARTS = ("twice", "shuffle", "fanout", "desk", "signals", "dead",
         "card")
EVENT = "CXL-0201"


def mmss(s: float) -> str:
    s = int(round(s))
    return f"{s // 60}:{s % 60:02d}"


def part_twice() -> None:
    emit("an itinerary changed twice; two workers, no partition key")
    a = Event("LTG-5172204", 41, "sc-88120", "dep 07:05")
    b = Event("LTG-5172204", 42, "sc-88131", "dep 09:40")
    for name, cls in (("last arrival", LastArrivalWins),
                      ("sequence guard", SequenceGuard)):
        x = cls()
        r = [x.apply(e) for e in (b, a)]
        emit(f"  {name:<15} 42 then 41: {r[0]}, {r[1]:<9}"
             f" final seq {x.state[a.key]}")
    for n in (4, 16):
        emit(f"  partition of {a.key} with {n:>2} partitions:"
             f" {partition_for(a.key, n)}")


def part_shuffle(seed: int) -> None:
    r = trial(seed)
    emit(f"shuffle trial: {r['shuffled']['delivered']:,} events,"
         f" {r['keys']:,} itineraries, seed {seed}")
    emit(f"  {'applier':<13}{'delivered':>10}{'out-of-order':>14}"
         f"{'wrong final':>13}")
    for k in ("shuffled", "partitioned", "guarded"):
        v = r[k]
        emit(f"  {k:<13}{v['delivered']:>10,}{v['out_of_order']:>14,}"
             f"{v['wrong_final']:>13,}")
    rej = r["guarded"]["rejected"]
    emit(f"  guarded rejected {rej['stale']:,} stale and"
         f" {rej['duplicate']:,} duplicates")


def part_fanout(seed: int) -> None:
    rows = itineraries(seed)
    cmds = fan_out(EVENT, rows)
    s = summary(cmds)
    emit(f"fan-out of {EVENT}: {s['total']:,} itineraries")
    emit(f"  {'queue':<11}{'commands':>9}{'in 1st min':>12}"
         f"{'last routed':>13}")
    for q in QUEUES:
        emit(f"  {q:<11}{s['per'][q]:>9,}{s['first_min'][q]:>12,}"
             f"{mmss(s['last_s'][q]):>13}")
    ib = Inbox("planner")
    first = deliver(cmds, ib)
    again = deliver(fan_out(EVENT, rows), ib)
    emit(f"  event delivered twice: applied {first['applied']:,},"
         f" duplicates {again['duplicate']:,}")
    refresh = len(rows) * 6
    emit(f"  status refreshes: {refresh:,} in, {len(rows):,} after"
         f" coalescing")


def approvals_at(seed: int) -> list[int]:
    cmds = fan_out(EVENT, itineraries(seed))
    return [int(c.at_s) for c in cmds if c.queue == "approvals"]


def part_desk(seed: int, reviewers: int) -> None:
    arr = approvals_at(seed)
    rate = bp.absorb_rate(reviewers, 80) * 60
    cap = bp.cap_for(reviewers, 80, 11 * 60)
    emit(f"desk: {len(arr)} approvals in {mmss(max(arr))},"
         f" {reviewers} reviewers, 80 s a card")
    emit(f"  absorb rate {rate:.1f} a minute; cap for an 11-minute"
         f" desk: {cap}")
    runs = (("no cap", None, 0), (f"cap {cap}", cap, 0),
            (f"cap {cap} + reserve 4", cap, 4))
    emit(f"  {'run':<19}{'peak':>5}{'held':>6}{'oldest':>8}"
         f"{'stale':>7}{'drop':>5}{'done':>7}")
    res = {}
    for name, c, extra in runs:
        r = bp.desk(arr, reviewers=reviewers, cap=c, reserve=extra,
                    seed=seed)
        res[name] = r
        emit(f"  {name:<19}{r.peak_pending:>5}{r.peak_held:>6}"
             f"{mmss(bp.sampled_peak(r)):>8}{r.stale_on_review:>7}"
             f"{r.dropped:>5}{mmss(r.last_decision_s):>7}")
    r = res[f"cap {cap} + reserve 4"]
    emit(f"  alert at {mmss(r.alert_s)}: projected drain over the"
         f" 60-minute promise")
    emit(f"  reserve desk working from {mmss(r.reserve_from_s)}")
    emit("  minute  pending  held  oldest   (cap, no reserve)")
    for m, p, h, a in res[f"cap {cap}"].timeline:
        if m % 10 == 0:
            emit(f"  {m:>6}{p:>9}{h:>6}{mmss(a):>8}")


def part_signals() -> None:
    emit("intake signals at minute 5 of the storm")
    cases = (
        ("approvals full", bp.Signals(50, 50, 0.01, 0.05, 31.0, 120.0)),
        ("room for 12", bp.Signals(38, 50, 0.01, 0.05, 31.0, 120.0)),
        ("supplier 429s", bp.Signals(38, 50, 0.07, 0.05, 31.0, 120.0)),
        ("budget spent", bp.Signals(38, 50, 0.01, 0.05, 120.0, 120.0)),
    )
    for name, s in cases:
        n, why = bp.admit(40, s)
        emit(f"  {name:<15} want 40, admit {n:>2}: {why}")


def part_dead() -> None:
    c = Consumer("schedule", owner="Ben Carter (on call)")
    good = [{"id": f"sc-9{i:04d}", "key": f"LTG-49{i:05d}", "seq": 1,
             "dep": "2026-02-01T18:05:00-07:00"} for i in range(200)]
    bad = {"id": "sc-90777", "key": "LTG-4911777", "seq": 2,
           "dep": "2026-02-01T18:40:00", "zone": "America/Denver"}
    after = {"id": "sc-90778", "key": "LTG-4911777", "seq": 3,
             "dep": "2026-02-01T21:10:00-07:00"}
    out = [c.offer(json.dumps(m).encode()) for m in good[:100]]
    out.append(c.offer(json.dumps(bad).encode()))
    out.append(c.offer(json.dumps(after).encode()))
    out.append(c.offer(json.dumps(good[100]).encode(), flaky=2))
    out += [c.offer(json.dumps(m).encode()) for m in good[101:]]
    emit("dead letters: 203 schedule messages, one poison")
    for k in ("applied", "dead-lettered", "parked"):
        emit(f"  {k:<14}{out.count(k):>4}")
    emit(f"  transient retries {c.retries}, then applied")
    L = c.letters[bad["key"]]
    emit(f"  letter {L.msg_id} key {L.key} attempts {L.attempts}")
    emit(f"    error: {L.error}")
    emit(f"    sha256 {L.sha256[:16]}... owner {L.owner}")
    emit(f"    parked behind it: {len(L.parked)}")
    r1 = c.replay(bad["key"], parse_v2)
    emit(f"  replay after fix: {', '.join(r1)}")
    emit(f"  {bad['key']} now at seq {c.inbox.seq(bad['key'])}")
    again = [c.offer(json.dumps(m).encode()) for m in (bad, after)]
    emit(f"  replay run twice: {', '.join(again)}")


def part_card() -> None:
    emit("messaging card, February 27, 2026 (lab values)")
    for k, v in (("queues", "work, approvals, refusals"),
                 ("ordering", "per itinerary; source seq; stale out"),
                 ("backpressure", "approvals capped at 50 pending"),
                 ("alert", "drain over 60 min, or oldest 15 min"),
                 ("dead letters", "per itinerary; owner; replay"),
                 ("effects", "exactly once at the tool, Ch 7")):
        emit(f"  {k:<14}{v}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=8)
    ap.add_argument("--part", choices=PARTS)
    ap.add_argument("--reviewers", type=int, default=6)
    a = ap.parse_args()
    run = {"twice": part_twice,
           "shuffle": lambda: part_shuffle(a.seed),
           "fanout": lambda: part_fanout(a.seed),
           "desk": lambda: part_desk(a.seed, a.reviewers),
           "signals": part_signals, "dead": part_dead,
           "card": part_card}
    for i, p in enumerate([a.part] if a.part else PARTS):
        if i:
            emit()
        run[p]()


if __name__ == "__main__":
    main()
