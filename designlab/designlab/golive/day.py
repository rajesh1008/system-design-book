"""The storm day as records: Thursday, September 10, 2026, CDT.

O'Hare closed at about 11:00 a.m. and reopened at about 5:00 p.m.
STORM_CHANGES itinerary changes arrive in that window; the day's
other arrivals (the morning before it and the evening tail after
it) come from the same generator with their own mix. Every record
is invented; times are minutes after midnight in Chicago, and the
day's offset is -05:00 (CDT).

A change is one of seven kinds:
    rebook       weather rebooking inside rebook-v3's ceiling; the
                 agent acts and notifies, so no card
    rebook_card  above the ceiling or on another carrier; a card
                 for the agent desk, with the new flight's departure
    refund_inv   involuntary refund (the carrier canceled); a card
                 for the refund approver desk under refunds-v3
    refund_vol   voluntary refund on a refundable fare; a card
    credit       travel credit; a card
    voucher      meal or hotel voucher up to $100; acts alone
                 inside the $5,000 voucher day
    cancel       cancel to credit, seat or upgrade; acts alone
Involuntary refunds also arrive by rule from the carriers'
schedule-change events (source "fanout"), with no model call, as
Chapter 8's fan-out built them.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from common.rand import seeded
from corpus.names import AIRPORTS

STORM_CHANGES = 41_000
CLOSE, REOPEN = 11 * 60, 17 * 60          # 11:00 a.m., 5:00 p.m.
ANNOUNCED = 14 * 60 + 35                  # reopening time announced
DAY_START, DAY_END = 6 * 60, 24 * 60
MORNING_PER_H = 300                       # an ordinary Thursday
TAIL_START_PER_H, TAIL_END_PER_H = 1_500, 250
OFFSET = "-05:00"                         # CDT on September 10

STORM_MIX = {"rebook": 0.498, "rebook_card": 0.072, "refund_inv": 0.25,
             "refund_vol": 0.05, "credit": 0.05, "voucher": 0.08}
CALM_MIX = {"rebook": 0.36, "rebook_card": 0.06, "refund_inv": 0.10,
            "refund_vol": 0.22, "credit": 0.11, "voucher": 0.01,
            "cancel": 0.14}
FANOUT_SHARE = 0.60       # involuntary refunds proposed by rule
CARD_KINDS = ("rebook_card", "refund_inv", "refund_vol", "credit")
SERVICE_MIN = {"rebook_card": 5.0, "refund_inv": 2.0,
               "refund_vol": 2.0, "credit": 2.0}
MEDIAN_USD = {"refund_inv": 320.0, "refund_vol": 280.0,
              "credit": 180.0, "rebook_card": 460.0}
FARES = (("basic", 0.35), ("main", 0.50), ("premium", 0.15))


@dataclass(frozen=True)
class Change:
    cid: str
    kind: str
    source: str            # "chat" (a conversation) or "fanout"
    t: float               # arrival, minutes after midnight
    dep: float | None      # new departure (rebook kinds), minutes
    amount: float
    fare: str
    dest: str

    @property
    def card(self) -> bool:
        return self.kind in CARD_KINDS

    @property
    def service(self) -> float:
        return SERVICE_MIN.get(self.kind, 0.0)


def storm_weight(m: float) -> float:
    """Arrival shape inside the closure: a climb over the first
    hour, a plateau, then a drop at 2:35 p.m., when the reopening
    time was announced and the carriers stopped canceling."""
    x = m - CLOSE
    if x < 60:
        return 0.45 + 0.75 * x / 60
    if m < ANNOUNCED:
        return 1.2
    return 0.40 - 0.15 * (m - ANNOUNCED) / (REOPEN - ANNOUNCED)


def _minutes(rng, n: int, lo: int, hi: int, weight) -> list[float]:
    ws = [weight(m) for m in range(lo, hi)]
    total = sum(ws)
    out, carry = [], 0.0
    for m, w in zip(range(lo, hi), ws):
        carry += n * w / total
        k = int(carry)
        carry -= k
        out += [m + rng.random() for _ in range(k)]
    while len(out) < n:
        out.append(hi - rng.random())
    return out


def _pick(rng, mix: dict) -> str:
    r, acc = rng.random(), 0.0
    for kind, p in mix.items():
        acc += p
        if r < acc:
            return kind
    return kind


def _departure(rng, t: float) -> float:
    """Through another hub within hours, the same evening after the
    reopening, or tomorrow."""
    r = rng.random()
    if r < 0.30:
        return t + 75 + rng.random() * 225
    if r < 0.55:
        lo = max(t + 90, REOPEN + 15)
        if lo < DAY_END - 30:
            return lo + rng.random() * (DAY_END - 30 - lo)
    return DAY_END + 6 * 60 + rng.random() * 14 * 60


def _amount(rng, kind: str) -> float:
    if kind == "voucher":
        return float(rng.choice((25, 50, 75, 100)))
    med = MEDIAN_USD.get(kind)
    if med is None:
        return 0.0
    return round(med * math.exp(rng.gauss(0.0, 0.55)), 2)


def _fare(rng) -> str:
    r, acc = rng.random(), 0.0
    for name, p in FARES:
        acc += p
        if r < acc:
            return name
    return name


def _change(rng, n: int, t: float, mix: dict) -> Change:
    kind = _pick(rng, mix)
    source = "chat"
    if kind == "refund_inv" and rng.random() < FANOUT_SHARE:
        source = "fanout"
    dep = _departure(rng, t) if kind.startswith("rebook") else None
    return Change(f"CHG-0910-{n:05d}", kind, source, t, dep,
                  _amount(rng, kind), _fare(rng), rng.choice(AIRPORTS))


def generate(seed: int = 2026) -> list[Change]:
    """Every change of the day from 6:00 a.m. to midnight, by time."""
    rng = seeded(seed, "golive", "day")
    morning = _minutes(rng, MORNING_PER_H * 5, DAY_START, CLOSE,
                       lambda m: 1.0)
    storm = _minutes(rng, STORM_CHANGES, CLOSE, REOPEN, storm_weight)
    span = DAY_END - REOPEN

    def tail(m):
        return TAIL_START_PER_H + (TAIL_END_PER_H - TAIL_START_PER_H) * (
            m - REOPEN) / span
    n_tail = int(sum(tail(m) for m in range(REOPEN, DAY_END)) / 60)
    evening = _minutes(rng, n_tail, REOPEN, DAY_END, tail)
    out, n = [], 0
    for ts, mix in ((morning, CALM_MIX), (storm, STORM_MIX),
                    (evening, STORM_MIX)):
        for t in sorted(ts):
            n += 1
            out.append(_change(rng, n, t, mix))
    return out


def in_window(changes, lo: float = CLOSE, hi: float = REOPEN) -> int:
    return sum(1 for c in changes if lo <= c.t < hi)


def clock(m: float) -> str:
    """12-hour Chicago time for a minute of the day (or the next)."""
    m = int(round(m))
    day = "" if m < DAY_END else " +1d"
    h, mm = divmod(m % DAY_END, 60)
    suffix = "a.m." if h < 12 else "p.m."
    h12 = h % 12 or 12
    return f"{h12}:{mm:02d} {suffix}{day}"


def stamp(m: float) -> str:
    """Log form: 2026-09-10T14:40:00-05:00."""
    m = int(round(m))
    d = 10 + m // DAY_END
    h, mm = divmod(m % DAY_END, 60)
    return f"2026-09-{d:02d}T{h:02d}:{mm:02d}:00{OFFSET}"
