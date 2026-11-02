"""Ordering per itinerary.

Three steps: partition by itinerary, carry the source's sequence
number, reject stale events. `trial` replays shuffled events through
three appliers and counts out-of-order applications: an application
that moves an itinerary back to a version older than one it had.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from common.rand import seeded

APPLIED, STALE, DUPLICATE = "applied", "stale", "duplicate"


@dataclass(frozen=True)
class Event:
    key: str        # itinerary, the ordering scope
    seq: int        # the source's sequence number for this key
    msg_id: str     # unique per publish of one source change
    body: str = ""


def partition_for(key: str, partitions: int) -> int:
    """Same key, same partition, in every process and every run."""
    h = hashlib.sha256(key.encode()).digest()
    return int.from_bytes(h[:4], "big") % partitions


class LastArrivalWins:
    """What a consumer does with no sequence number: apply everything."""

    def __init__(self) -> None:
        self.state: dict[str, int] = {}
        self.out_of_order = 0

    def apply(self, ev: Event) -> str:
        cur = self.state.get(ev.key, 0)
        if ev.seq < cur:
            self.out_of_order += 1
        self.state[ev.key] = ev.seq
        return APPLIED


class SequenceGuard:
    """Apply an event only if it is newer than the last one applied.

    The check and the write are one step for one key, which is what a
    single consumer per partition gives you. Across processes the same
    rule is a conditional write: UPDATE ... WHERE seq < :new.
    """

    def __init__(self) -> None:
        self.state: dict[str, int] = {}
        self.out_of_order = 0
        self.rejected = {STALE: 0, DUPLICATE: 0}

    def apply(self, ev: Event) -> str:
        cur = self.state.get(ev.key, 0)
        if ev.seq == cur:
            self.rejected[DUPLICATE] += 1
            return DUPLICATE
        if ev.seq < cur:
            self.rejected[STALE] += 1
            return STALE
        self.state[ev.key] = ev.seq
        return APPLIED


def make_events(seed: int, n_events: int, per_key: int) -> list[Event]:
    keys = n_events // per_key
    evs = []
    for k in range(keys):
        key = f"LTG-{5100000 + k}"
        for s in range(1, per_key + 1):
            evs.append(Event(key, s, f"{key}:{s}"))
    return evs


def source_order(seed: int, evs: list[Event], swap: float,
                 redeliver: float) -> list[Event]:
    """Per-key order as a real source delivers it: mostly right, with
    adjacent swaps (two publishers, one slow) and late redeliveries."""
    rng = seeded(seed, "order", "source")
    by_key: dict[str, list[Event]] = {}
    for e in evs:
        by_key.setdefault(e.key, []).append(e)
    out = []
    for key, seq in by_key.items():
        seq = list(seq)
        for i in range(len(seq) - 1):
            if rng.random() < swap:
                seq[i], seq[i + 1] = seq[i + 1], seq[i]
        extra = [e for e in seq if rng.random() < redeliver]
        out.append(seq + extra)
    return [e for lst in out for e in lst]


def interleave(seed: int, evs: list[Event], partitions: int):
    """Keep per-key order within a partition; interleave partitions."""
    rng = seeded(seed, "order", "interleave")
    parts: list[list[Event]] = [[] for _ in range(partitions)]
    for e in evs:
        parts[partition_for(e.key, partitions)].append(e)
    idx = [0] * partitions
    live = [p for p in range(partitions) if parts[p]]
    out = []
    while live:
        p = rng.choice(live)
        out.append(parts[p][idx[p]])
        idx[p] += 1
        if idx[p] == len(parts[p]):
            live.remove(p)
    return out


def trial(seed: int = 8, n_events: int = 100_000, per_key: int = 8,
          partitions: int = 16, swap: float = 0.02,
          redeliver: float = 0.01) -> dict:
    """Three appliers over the same changes.

    shuffled: no partition key, any worker takes any event.
    partitioned: per-key order from the source, one consumer per
      partition, last arrival wins.
    guarded: partitioned plus the sequence check.
    """
    evs = make_events(seed, n_events, per_key)
    rng = seeded(seed, "order", "shuffle")
    shuffled = list(evs)
    rng.shuffle(shuffled)
    delivered = interleave(seed, source_order(seed, evs, swap,
                                              redeliver), partitions)
    want = {e.key: per_key for e in evs}
    res = {}
    for name, stream, cls in (("shuffled", shuffled, LastArrivalWins),
                              ("partitioned", delivered,
                               LastArrivalWins),
                              ("guarded", delivered, SequenceGuard)):
        a = cls()
        for e in stream:
            a.apply(e)
        wrong = sum(1 for k, v in want.items() if a.state.get(k) != v)
        res[name] = {"delivered": len(stream),
                     "out_of_order": a.out_of_order,
                     "wrong_final": wrong,
                     "rejected": getattr(a, "rejected", None)}
    res["keys"] = len(want)
    return res


def coalesce(evs: list[Event]) -> list[Event]:
    """Refresh traffic: keep only the newest event per key."""
    best: dict[str, Event] = {}
    for e in evs:
        if e.key not in best or e.seq > best[e.key].seq:
            best[e.key] = e
    return list(best.values())
