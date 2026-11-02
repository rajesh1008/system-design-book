"""The first fall: April 14, 2026, as it happened (Chapter 12).

A separate generator from corpus v0, so no earlier digest moves. It
covers one afternoon. An airline partner cancels a large part of its
schedule (event CXL-0414), the policy engine grants one refund
permission per affected itinerary, and two paths pay them:

    batch     the involuntary-refund batch, outside the gateway
    gateway   the agent path, through the effect ledger

A latency spike at a card network the processor routes through runs
from 15:08 to 15:50 CDT. Each attempt carries a planned outcome:

    ok     the processor answers in time
    late   the processor applies the refund, then the answer comes
           after the caller's 8.0 s timeout
    lost   the request never reaches the processor

The counts are exact (exact sampling, not coin flips): on the batch
path 194 refunds see one late attempt then ok, 9 see two late
attempts then ok, and 61 see one lost attempt then ok. The duplicate
amounts sum to exactly $61,000.00.

    from corpus.fall1 import generate_fall1
    f = generate_fall1(2026)    # dict of table name -> rows

Times are seconds after midnight, America/Chicago (CDT, -05:00).
Every record is invented.
"""
from __future__ import annotations

import hashlib
import json

from common.rand import DEFAULT_SEED, seeded

FALL1_VERSION = "fall1-v1"
DAY = "2026-04-14"
UTC_OFFSET = "-05:00"
EVENT_ID = "CXL-0414"
TIMEOUT_S = 8.0          # the framework wrapper's timeout
BACKOFF_S = 1.0          # the wrapper's pause between attempts


def hms(h: int, m: int, s: int = 0) -> int:
    return h * 3600 + m * 60 + s


SPIKE_START = hms(15, 8)       # slow answers begin
SPIKE_END = hms(15, 50)        # the network is back to normal
DUP_FROM = hms(15, 10)         # window for late attempts
DUP_TO = hms(15, 49, 30)
BATCH_START = hms(14, 52)
BATCH_END = hms(17, 40)

N_BATCH = 4960
N_GATEWAY = 186                # agent-path refunds that afternoon
LATE_THEN_OK = 194             # one duplicate each
LATE_LATE_OK = 9               # two duplicates each
LOST_THEN_OK = 61              # retried correctly, no duplicate
GATEWAY_LATE = 14              # gateway refunds with a late first try
DUP_TOTAL_USD = 61000.00

FALL1_TABLES = (
    "fall1_refunds", "fall1_attempts", "fall1_profile")


def clock(t: float) -> str:
    """Seconds after midnight to 'HH:MM:SS' (CDT)."""
    t = int(round(t))
    return f"{t // 3600:02d}:{t % 3600 // 60:02d}:{t % 60:02d}"


def iso(t: float) -> str:
    return f"{DAY}T{clock(t)}{UTC_OFFSET}"


def slow_share(t: float) -> float:
    """Share of processor calls in the slow band at time t."""
    if t < SPIKE_START or t >= SPIKE_END:
        return 0.0
    if t < hms(15, 9):
        return 0.65 * (t - SPIKE_START) / 60
    if t < hms(15, 44):
        return 0.65
    return 0.65 * (SPIKE_END - t) / 360


def most_slow_at() -> int:
    """The first second at which half of all calls are slow."""
    return next(t for t in range(SPIKE_START, SPIKE_END)
                if slow_share(t) >= 0.5)


def probe_latency(t: float) -> float:
    """What a read probe of the processor sees at time t."""
    s = slow_share(t)
    return round(1.0 + 9.0 * s, 2)


def _weight(t: float) -> float:
    return max(slow_share(t), 0.02)


def _pick(rng, items: list, weights: list, k: int) -> list:
    """k distinct items, chosen with probability by weight."""
    keyed = sorted(items, key=lambda i: -rng.random() ** (1.0 / weights[i]))
    return sorted(keyed[:k])


def _minute_counts() -> list[tuple[int, int]]:
    """(minute start, refunds submitted) for the batch, summing to
    N_BATCH: about 36 a minute to 16:30, then a tail."""
    first = [(m, 36) for m in range(BATCH_START, hms(16, 30), 60)]
    left = N_BATCH - sum(c for _, c in first)
    tail_mins = list(range(hms(16, 30), BATCH_END, 60))
    base, extra = divmod(left, len(tail_mins))
    tail = [(m, base + (1 if i < extra else 0))
            for i, m in enumerate(tail_mins)]
    return first + tail


def _amount(rng) -> float:
    a = rng.lognormvariate(5.55, 0.42)
    return round(min(max(a, 49.0), 1450.0), 2)


def _attempts(rng, start: float, plan: list[str]) -> list[dict]:
    out, t = [], start
    for n, outcome in enumerate(plan, 1):
        if outcome == "late":
            lat = round(rng.uniform(8.4, 24.0), 2)
        elif outcome == "lost":
            lat = TIMEOUT_S
        elif rng.random() < slow_share(t):
            lat = round(rng.uniform(2.5, 7.9), 2)
        else:
            lat = round(rng.uniform(0.6, 2.4), 2)
        out.append({"attempt": n, "outcome": outcome, "start": round(t, 2),
                    "latency_s": lat})
        t = t + (TIMEOUT_S + BACKOFF_S if outcome != "ok" else lat)
    return out


def generate_fall1(seed: int = DEFAULT_SEED) -> dict[str, list[dict]]:
    rng = seeded(seed, "fall1", "refunds")
    refunds: list[dict] = []
    n = 0
    for minute, count in _minute_counts():
        times = sorted(rng.uniform(minute, minute + 60) for _ in range(count))
        for t in times:
            n += 1
            refunds.append({
                "refund_id": f"RFQ-{n:05d}", "path": "batch",
                "itinerary": f"LTG-{5300000 + n}",
                "permission_id": f"PRM-{52000 + n}",
                "charge_id": f"CHG-{8100000 + n}",
                "amount_usd": _amount(rng), "submitted": round(t, 2)})
    g = seeded(seed, "fall1", "gateway")
    for i in range(N_GATEWAY):
        n += 1
        t = g.uniform(hms(14, 40), hms(17, 40))
        refunds.append({
            "refund_id": f"RFQ-{n:05d}", "path": "gateway",
            "itinerary": f"LTG-{5300000 + n}",
            "permission_id": f"PRM-{52000 + n}",
            "charge_id": f"CHG-{8100000 + n}",
            "amount_usd": _amount(g), "submitted": round(t, 2)})
    refunds.sort(key=lambda r: (r["submitted"], r["refund_id"]))

    # exact sampling of the planned outcomes on the batch path
    pick = seeded(seed, "fall1", "plans")
    batch = [i for i, r in enumerate(refunds) if r["path"] == "batch"
             and DUP_FROM <= r["submitted"] < DUP_TO]
    w = {i: _weight(refunds[i]["submitted"]) for i in batch}
    first = batch[0]                      # the first duplicate, 15:10
    rest = _pick(pick, batch[1:], w, LATE_THEN_OK - 1 + LATE_LATE_OK)
    doubles = [first] + rest
    triples = sorted(pick.sample(rest, LATE_LATE_OK))
    taken = set(doubles)
    lost = _pick(pick, [i for i in batch if i not in taken], w,
                 LOST_THEN_OK)
    gw = [i for i, r in enumerate(refunds) if r["path"] == "gateway"
          and SPIKE_START <= r["submitted"] < SPIKE_END]
    gw_late = set(pick.sample(gw, min(GATEWAY_LATE, len(gw))))
    plans = {i: ["ok"] for i in range(len(refunds))}
    for i in doubles:
        plans[i] = ["late", "late", "ok"] if i in triples else ["late", "ok"]
    for i in lost:
        plans[i] = ["lost", "ok"]
    for i in gw_late:
        plans[i] = ["late", "ok"]

    # scale the duplicated amounts so they sum to $61,000.00 exactly
    extra = {i: len([p for p in plans[i] if p == "late"])
             for i in doubles}
    raw = sum(refunds[i]["amount_usd"] * extra[i] for i in doubles)
    f = DUP_TOTAL_USD / raw
    for i in doubles:
        refunds[i]["amount_usd"] = round(refunds[i]["amount_usd"] * f, 2)
    cents = round((DUP_TOTAL_USD - sum(refunds[i]["amount_usd"] * extra[i]
                                       for i in doubles)) * 100)
    fix = next(i for i in doubles if extra[i] == 1)
    refunds[fix]["amount_usd"] = round(refunds[fix]["amount_usd"]
                                       + cents / 100, 2)

    a = seeded(seed, "fall1", "attempts")
    attempts = []
    for i, r in enumerate(refunds):
        for row in _attempts(a, r["submitted"], plans[i]):
            attempts.append({"refund_id": r["refund_id"], **row})
    profile = [{"t": t, "slow_share": round(slow_share(t), 4),
                "probe_latency_s": probe_latency(t)}
               for t in range(hms(14, 40), hms(17, 40), 60)]
    return {"fall1_refunds": refunds, "fall1_attempts": attempts,
            "fall1_profile": profile}


def fall1_digest(t: dict[str, list[dict]]) -> str:
    h = hashlib.sha256(FALL1_VERSION.encode())
    for name in FALL1_TABLES:
        h.update(name.encode())
        h.update(json.dumps(t[name], sort_keys=True).encode())
    return h.hexdigest()
