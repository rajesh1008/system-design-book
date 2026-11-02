"""The post-incident review record, and the gate that closes it.

A review is a record with fixed parts: what happened, read from the
records and not from memory; what was done to the effects already
made; what made the incident possible, with no person as a cause;
the actions, each with an owner and a date; and what the review
hands to another owner. It closes when every effect is accounted
for, every temporary authority is back where it was, and every action
has an owner and a date. Closing is not the same as finishing the
actions; it is knowing who finishes each one, and by when.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Action:
    what: str
    owner: str
    due: str


@dataclass
class Review:
    incident: str
    held_on: str
    timeline: list[tuple] = field(default_factory=list)
    effects: dict = field(default_factory=dict)       # kind -> open count
    temporary: dict = field(default_factory=dict)     # authority -> state
    factors: list[str] = field(default_factory=list)
    actions: list[Action] = field(default_factory=list)
    handoffs: list[str] = field(default_factory=list)
    numbers: dict = field(default_factory=dict)


PEOPLE_AS_CAUSE = ("error by", "failed to", "should have", "careless")


def gate(r: Review) -> list[str]:
    out = []
    for k, n in r.effects.items():
        if n:
            out.append(f"{n} {k} not accounted for")
    for k, v in r.temporary.items():
        if v != "restored":
            out.append(f"temporary {k}: {v}")
    for a in r.actions:
        if not a.owner or not a.due:
            out.append(f"action without owner or date: {a.what[:30]}")
    for f in r.factors:
        if any(p in f.lower() for p in PEOPLE_AS_CAUSE):
            out.append(f"factor names a person: {f[:30]}")
    for need in ("time to detect", "time to stop", "affected"):
        if need not in r.numbers:
            out.append(f"missing number: {need}")
    return out


INC5 = Review(
    "INC-5 vendor model alias moved", "Monday, July 13, 2026",
    timeline=[("01:15", "vendor alias moves (vendor's log)"),
              ("07:53", "first reissue on an old number"),
              ("14:41", "desk lead posts rework count"),
              ("14:52:10", "decision: tier one, rebook_ticket"),
              ("14:53:13", "bookings count flat: stopped"),
              ("15:20", "schedule-change intake propose-only"),
              ("15:31", "tier one lowered after a fresh decision"),
              ("21:30", "last of 40 tickets reissued correctly")],
    effects={"wrong reissues": 0, "held reissues": 0},
    temporary={"propose-only on schedule-change intake": "restored",
               "tier one on rebook_ticket": "restored"},
    factors=["classifier called by alias, not by dated version",
             "no echo of the vendor's model in the response",
             "golden set had no retime-and-renumber message",
             "objectives read front-door availability, not outcomes",
             "classifier codes not checked against the message text"],
    actions=[Action("vendor contract: dated model, echo, 14 days notice",
                    "Dr. Hannah Clarke", "2026-07-31"),
             Action("golden set: combined messages, 4 cases added",
                    "Dr. Hannah Clarke", "2026-07-15"),
             Action("code check against raw message, holds the case",
                    "Daniel Price", "2026-07-17"),
             Action("five objectives with budgets, read from records",
                    "Ben Carter", "2026-07-20")],
    handoffs=["change log counts vendor changes as releases (Ch39)"],
    numbers={"time to detect": "13 h 26 min", "time to stop": "64 s",
             "affected": "40 travelers, 0 flew on a wrong ticket"})

INC6 = Review(
    "INC-6 waiver watch retry storm", "Wednesday, July 29, 2026",
    timeline=[("Sat 02:14", "carrier feed serves maintenance page"),
              ("Sat 02:15", "first extraction call times out"),
              ("Sun 18:00", "first 429 on the shared small-model limit"),
              ("Sun 19:28", "task latency pages (fast burn)"),
              ("Sun 19:36:00", "decision: stop the waiver watch"),
              ("Sun 19:36:09", "tier two: model calls continue"),
              ("Sun 19:36:53", "tier three on agent:waiver-watch"),
              ("Sun 19:37:55", "provider count flat: stopped")],
    effects={"traveler messages sent": 0, "queued runs": 0},
    temporary={"tier three on the waiver watch": "restored"},
    factors=["three layers retried the same call",
             "a timeout was classed transient, re-queued with no cap",
             "enforcer released reservations on calls with no usage",
             "run key on page digest, new on every fetch",
             "no objective read the provider's count of calls",
             "runbook had tier two first for every incident"],
    actions=[Action("retries in one layer: the client; others fail",
                    "Daniel Price", "2026-08-07"),
             Action("timeout on a model step is a failure, not transient",
                    "Daniel Price", "2026-08-07"),
             Action("usage alert from provider export, per identity",
                    "Ben Carter", "2026-07-31"),
             Action("loop runbook: tier three first for spend",
                    "Ben Carter", "2026-07-29")],
    handoffs=["what the storm cost, and spend policies (Ch38)"],
    numbers={"time to detect": "41 h 14 min", "time to stop": "116 s",
             "affected": "0 travelers; servicing p95 over 40 s 1 h"})

REVIEWS = (INC5, INC6)
