"""The records objectives read.

The tracing package Chapter 35 builds is not a dependency here, so
this module carries the few fields an objective needs, in the shape
the trail and the provider's usage export already have. Each record
names its source, because an objective is only as honest as the
writer of the records it reads: the actor's own counters are one
source, the reconciler, the gateway, the desk queue, and the
provider's usage export are others.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

CDT = timezone(timedelta(hours=-5), "CDT")

SOURCES = {
    "front_door": "load balancer request log (the platform writes it)",
    "reconciler": "PNR and ledger reconciler (reads the airline's record)",
    "gateway": "gateway trail (every effect, allowed or refused)",
    "traces": "task traces, start to verified end",
    "desk": "escalation queue (the desk tool writes it)",
    "provider": "provider usage export (the provider writes it)",
    "actor": "the actor's own counters",
}


def at(day: str, hhmm: str, sec: int = 0) -> datetime:
    """`at("2026-07-08", "14:52", 10)` in Chicago daylight time."""
    h, m = (int(x) for x in hhmm.split(":"))
    y, mo, d = (int(x) for x in day.split("-"))
    return datetime(y, mo, d, h, m, sec, tzinfo=CDT)


def hm(t: datetime) -> str:
    return t.astimezone(CDT).strftime("%H:%M")


def hms(t: datetime) -> str:
    return t.astimezone(CDT).strftime("%H:%M:%S")


@dataclass
class Task:
    """One agent-path task, as the trace and the reconciler see it."""
    task_id: str
    kind: str                 # rebooking, refund, cancellation, credit
    started: datetime
    ended: datetime
    verified: bool | None     # None until the reconciler has read it
    reconciled: datetime | None = None
    cost_usd: float = 0.0
    unauthorized: int = 0
    requests: int = 8         # front-door requests the task made
    errors: int = 0           # of which answered 5xx
    codes: tuple = ()         # classifier codes on schedule-change intake
    message: str = ""
    cause: str = ""           # replay ground truth; objectives never read it

    @property
    def seconds(self) -> float:
        return (self.ended - self.started).total_seconds()


@dataclass
class Escalation:
    case_id: str
    queued: datetime
    picked: datetime | None


@dataclass
class Usage:
    """One minute of the provider's usage export for one key."""
    minute: datetime
    key: str
    calls: int
    input_tokens: int
    rate_limited: int = 0


@dataclass
class Records:
    tasks: list[Task] = field(default_factory=list)
    escalations: list[Escalation] = field(default_factory=list)
    usage: list[Usage] = field(default_factory=list)
    actor_counts: dict = field(default_factory=dict)
    missing: set = field(default_factory=set)   # sources not delivered
