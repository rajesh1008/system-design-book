"""A replayed busy hour through the policy gateway.

Synthetic cases shaped like June's servicing traffic: two reads, then
one effect (rebook, refund, voucher, credit or notify) or a hand-off.
Refunds file approval cards that a desk approver decides after a short
wait. Every call goes through PolicyGateway, so the counts below are
the gateway's and the servers', not the replay's. Identifiers are
synthetic; Lakeshore figures are illustrative.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .world import JOANNA, SERVICING, TERESA, PWorld

MIX = (("rebook", 0.34), ("refund", 0.22), ("voucher", 0.14),
       ("credit", 0.08), ("notify", 0.12), ("handoff", 0.10))
EFFECT_SERVER = {"rebook_ticket": "booking", "refund_ticket": "payments",
                 "voucher_issue": "payments", "credit_issue": "payments",
                 "customer_notify": "messaging",
                 "handoff_to_desk": "desk"}


def set_time(clock, t: datetime) -> None:
    clock.advance((t - clock._t).total_seconds())


def case_ids(i: int) -> tuple[str, str]:
    return f"LTG-{5300000 + i:07d}", f"TKT-{50000 + i % 50000:05d}"


def effect_for(kind: str, i: int, rng: random.Random) -> tuple[str, dict]:
    itin, tkt = case_ids(i)
    if kind == "rebook":
        return "rebook_ticket", {
            "itinerary_id": itin, "ticket_number": tkt,
            "passenger_name": f"TRAVELER/{i:04d}",
            "new_flight_id": f"FLT-{905000 + i % 900:06d}",
            "fare_difference_usd": f"{rng.choice([0, 0, 18, 42, 96, 310])}"
                                   ".00",
            "reason": "schedule_change"}
    if kind == "refund":
        amt = rng.choice([186, 240, 312, 418, 655, 820, 1240, 1980])
        return "refund_ticket", {"itinerary_id": itin,
                                 "ticket_number": tkt,
                                 "amount_usd": f"{amt}.00",
                                 "reason": "canceled_by_carrier"}
    if kind == "voucher":
        return "voucher_issue", {"itinerary_id": itin,
                                 "amount_usd": rng.choice(["50.00",
                                                           "100.00"]),
                                 "reason": "delay"}
    if kind == "credit":
        return "credit_issue", {"itinerary_id": itin,
                                "ticket_number": tkt}
    if kind == "notify":
        return "customer_notify", {"itinerary_id": itin,
                                   "template": "update"}
    return "handoff_to_desk", {"itinerary_id": itin,
                               "summary": "traveler asked for a person"}


@dataclass
class Tally:
    calls: int = 0
    reads: int = 0
    effects_forwarded: int = 0
    handoffs: int = 0
    refused: dict = field(default_factory=dict)
    forwards: list[tuple[datetime, str]] = field(default_factory=list)

    def add(self, reason: str) -> None:
        self.refused[reason] = self.refused.get(reason, 0) + 1


def busy_hour(w: PWorld, cases: int = 600, minutes: float = 60.0,
              seed: int = 31, start: datetime | None = None,
              lags=(0.0, 1.5, 3.0, 4.5), on_time=None) -> Tally:
    """Run `cases` cases spread over `minutes`. `on_time(t)` is called
    before each step so a test can pull the switch mid-replay."""
    rng = random.Random(seed)
    t0 = start or w.clock._t
    steps = []
    for i in range(cases):
        t = t0 + timedelta(seconds=rng.uniform(0, minutes * 60))
        kind = rng.choices([k for k, _ in MIX], [p for _, p in MIX])[0]
        steps.append((t, i, "read1", kind))
        steps.append((t + timedelta(seconds=2), i, "read2", kind))
        steps.append((t + timedelta(seconds=9), i, "effect", kind))
        if kind == "refund":
            steps.append((t + timedelta(seconds=rng.uniform(40, 150)),
                          i, "approve", kind))
            steps.append((t + timedelta(seconds=rng.uniform(155, 170)),
                          i, "retry", kind))
    steps.sort(key=lambda s: (s[0], s[1]))
    tally = Tally()
    cards: dict[int, tuple[str, str]] = {}
    for t, i, what, kind in steps:
        set_time(w.clock, t)
        if on_time:
            on_time(t)
        w.gateway.replica_lag_s = lags[i % len(lags)]
        itin, tkt = case_ids(i)
        if what == "approve":
            if i in cards:
                card, dg = cards[i]
                amount = w.approvals.cards[card].amount_usd
                who = TERESA if amount > 750 else JOANNA
                w.approvals.decide(card, who, dg)
            continue
        tool = ""
        if what == "read1":
            r = w.gateway.call(SERVICING, "booking", "booking_read",
                               {"booking_ref": itin}, session=f"s-{i}")
        elif what == "read2":
            r = w.gateway.call(SERVICING, "fares", "fare_calc",
                               {"ticket_number": tkt}, session=f"s-{i}")
        else:
            if what == "retry" and i not in cards:
                continue
            tool, args = effect_for(kind, i, random.Random(i))
            r = w.gateway.call(SERVICING, EFFECT_SERVER[tool], tool,
                               args, session=f"s-{i}")
            d = w.gateway.last_decision
            if what == "effect" and d is not None and d.card:
                cards[i] = (d.card, d.digest)
        tally.calls += 1
        if what.startswith("read"):
            tally.reads += 1
        if r.ok and tool == "handoff_to_desk" and what == "effect":
            tally.handoffs += 1
        elif r.ok and what not in ("read1", "read2"):
            tally.effects_forwarded += 1
            tally.forwards.append((t, tool))
        if not r.ok:
            tally.add(r.reason)
    return tally
