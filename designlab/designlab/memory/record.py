"""The Memory Record: one remembered thing, with where it came from.

Fields the writer supplies go in a `Draft`. The store adds the tenant
(from the session token), the identifiers, the times, the version, and
the links. A draft never carries a tenant, so content cannot choose
whose memory it becomes.

Scopes, narrowest first:
    session   this conversation only; gone when the session closes
    trip      one itinerary; gone when the trip ends
    standing  every future task for this customer, until it expires
              (memory-retention-v1: 180 days unless confirmed again)

Source kinds:
    customer-stated    the customer said it, in a turn we can point to
    customer-confirmed the customer said it applies from now on
    agent-inferred     the agent concluded it; nobody said it
    desk-entered       a person at the agent desk wrote it
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

SCOPES = ("session", "trip", "standing")
KINDS = ("customer-stated", "customer-confirmed", "agent-inferred",
         "desk-entered")
# A standing memory needs words that say "from now on".
STANDING_KINDS = ("customer-confirmed", "desk-entered")
# Subjects that change money, destination, or consent are never
# written from inference, whatever the confidence.
HIGH_CONSEQUENCE = ("destination", "refund", "consent", "payment",
                    "contact")


@dataclass(frozen=True)
class Source:
    event_id: str            # the turn or contact it came from (CON-...)
    kind: str                # one of KINDS
    quote: str = ""          # the customer's words, verbatim, if any


@dataclass(frozen=True)
class Draft:
    subject: str             # what it is about, e.g. "seat"
    value: str               # e.g. "aisle"
    scope: Optional[str]
    source: Optional[Source]
    confidence: Optional[float]
    trip: Optional[str] = None           # itinerary, for trip scope
    observed_at: Optional[str] = None    # valid time: when it was said
    derived_from: tuple = ()             # memory ids it was made from


@dataclass(frozen=True)
class MemoryRecord:
    memory_id: str
    tenant: str
    session_id: str
    subject: str
    value: str
    scope: str
    trip: Optional[str]
    source: Source
    confidence: float
    observed_at: str         # valid time
    recorded_at: str         # record time: when the store wrote it
    expires_at: Optional[str]
    version: int = 1
    supersedes: Optional[str] = None
    superseded_by: Optional[str] = None
    derived_from: tuple = ()
    status: str = "active"   # active, superseded, deleted
    tags: tuple = field(default=())

    @property
    def head_key(self) -> tuple:
        return (self.tenant, self.subject, self.scope, self.trip)
