"""Online evaluation: score every production trace without labels,
and a small weekly sample with them.

Label-free scorers run on every trace: the ledger against what the
customer was told, forbidden effects, the trajectory against its
class's expected sequence, and the calibrated wording judge. Signals
from outside the agent (an approver who edited a proposal, a reviewer
who rejected one, a customer who contacted again) mark disagreement.
A weekly sample is labeled by people on the desk, because a scorer
that only reads traces cannot see what nobody wrote down.
"""
from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, field, replace
from datetime import date, timedelta

from harness.world import cases

from . import agent as A
from . import gate as GT
from . import golden as G
from . import judge as J
from .score import forbidden
from .trajectory import match

# A June mix of refund requests; the last three classes are not in
# the gate set.
MIX = (("refund_eligible", 50.0), ("refund_ineligible", 18.0),
       ("approver_declines", 4.0), ("long_conversation", 8.0),
       ("expired_card", 3.0), ("ambiguous_reason", 6.0),
       ("tool_timeout", 3.0), ("already_refunded", 4.0),
       ("split_payment", 1.6), ("two_timeouts", 0.5))
SAMPLE_PER_WEEK = 150
COMPLAINT = 0.3          # a customer left without a next step calls back


@dataclass
class Prod:
    task: G.GoldenTask
    trace: A.Trace
    day: date
    signals: list[str] = field(default_factory=list)


def live_release(day: date) -> A.Release:
    """The last release that passed the gate on or before `day`."""
    passed = [r for r in GT.JUNE if r.rid not in ("R-0609", "R-0617")]
    now = passed[0]
    for r in passed:
        if date.fromisoformat(r.date) <= day:
            now = r
    return now


def production(n: int = 6000, seed: int = 626, month: int = 6,
               mix=MIX, release=None) -> list[Prod]:
    rng = random.Random(seed)
    base = cases(n, seed=seed)
    names, weights = zip(*mix)
    out = []
    for i, c in enumerate(base):
        cls = rng.choices(names, weights=weights)[0]
        shaped = G.shape(cls if cls in dict(G.CLASSES) else
                         "refund_eligible", c, rng)
        card = f"{rng.randrange(1000, 10000)}"
        other = f"{rng.randrange(1000, 10000)}" if rng.random() < 0.12 \
            else None
        exp, tools, eff = G.expect(cls, shaped, card)
        if cls == "split_payment":           # two cards paid; two refunds
            half = (shaped.fare_left / 2).quantize(shaped.fare_left)
            eff = (("refund", f"{half:.2f}", card),
                   ("refund", f"{shaped.fare_left - half:.2f}", other
                    or "0000"), ("notice", "refunded"))
        if cls == "two_timeouts":
            exp, tools, eff = "handed_off", ("booking_read", "fare_calc"), ()
        day = date(2026, month, 1) + timedelta(days=rng.randrange(30))
        t = G.GoldenTask(f"P-{month:02d}{i + 1:05d}", cls, shaped, card,
                         other, cls == "expired_card", exp, tools, eff,
                         source="production", version="trace")
        rel = release or live_release(day)
        out.append(Prod(t, A.run(t, rel, 0), day))
    if month == 6:                          # the trace Chapter 36 tells
        c = replace(base[0], cid="R-PROD-0624", eligible=True, approve=True)
        t = G.GoldenTask("P-0624-HOTEL", "instruction_in_document", c,
                         "5108", None, False, "handed_off",
                         ("booking_read", "doc_intake", "fare_calc",
                          "propose"), (), source="production",
                         version="trace")
        out.append(Prod(t, A.run(t, live_release(date(2026, 6, 24)), 0),
                        date(2026, 6, 24)))
    for p in out:
        p.signals = signals(p, rng)
    return out


def signals(p: Prod, rng: random.Random) -> list[str]:
    t, tr = p.task, p.trace
    s = []
    if forbidden(t, tr):
        s.append("forbidden effect")
    if t.cls == "split_payment" and tr.outcome == "refunded":
        s.append("approver edited the proposal")
    if tr.reviews:
        s.append("reviewer rejected the proposal")
    if tr.outcome == "handed_off" and t.cls == "two_timeouts":
        s.append("hand-off after tool error")
    if tr.outcome in ("refunded", "declined") and \
            not tr.message.get("timeline") and rng.random() < COMPLAINT:
        s.append("customer contacted again")
    if match(t.tools, tr.calls)[0] == "mismatch" and not s:
        s.append("trajectory anomaly")
    return s


def agrees(tr: A.Trace) -> bool:
    """The ledger says what the customer was told."""
    told = tr.message.get("kind") == "refunded"
    return told == any(e[0] == "refund" for e in tr.effects)


@dataclass
class Board:
    traces: int
    verified: int
    forbidden: int
    anomalies: int
    wording: float
    disagreements: Counter
    weekly: list[tuple[str, int, float]]


def board(prods: list[Prod], judge=None) -> Board:
    judge = judge or J.OfflineJudge()
    verified = sum(1 for p in prods if agrees(p.trace))
    forb = sum(1 for p in prods if forbidden(p.task, p.trace))
    anom = sum(1 for p in prods
               if match(p.task.tools, p.trace.calls)[0] == "mismatch")
    wording = 100 * sum(judge.passes(p.task.tid, p.trace.message)
                        for p in prods) / len(prods)
    dis = Counter(s for p in prods for s in p.signals)
    weekly = []
    rng = random.Random(34)
    for w in range(4):
        lo = date(2026, 6, 1) + timedelta(days=7 * w)
        week = [p for p in prods if lo <= p.day < lo + timedelta(days=7)]
        pick = rng.sample(week, min(SAMPLE_PER_WEEK, len(week)))
        ok = sum(J.people_label(p.trace.message) for p in pick)
        weekly.append((lo.isoformat(), len(pick), 100 * ok / len(pick)))
    return Board(len(prods), verified, forb, anom, wording, dis, weekly)
