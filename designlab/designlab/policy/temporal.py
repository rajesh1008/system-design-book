"""Temporal and sequence rules: decisions that need history.

A rule about one call can be checked from that call's arguments. A
rule about time or order needs what happened before, and the engine
keeps that history itself, from the gateway's own records: effects it
forwarded, reads it evaluated, and events from systems of record such
as a fare change. Nothing here comes from the conversation.

Four rule types:
  count_within    at most n effects of a tool per key in a window
  quiet_after     no effect of a tool within m minutes of an event
  escalate_after  once a session has done X, an effect needs approval
  valid_for       a permission expires m minutes after it is granted
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class Event:
    at: datetime
    kind: str          # a tool name, or a system event like fare_change
    key: str           # ticket, itinerary, or session
    session: str = ""


@dataclass
class History:
    events: list[Event] = field(default_factory=list)

    def note(self, at: datetime, kind: str, key: str,
             session: str = "") -> None:
        self.events.append(Event(at, kind, key, session))

    def count(self, kind: str, key: str, since: datetime) -> int:
        return sum(1 for e in self.events
                   if e.kind == kind and e.key == key and e.at >= since)

    def last(self, kind: str, key: str) -> datetime | None:
        ts = [e.at for e in self.events if e.kind == kind and e.key == key]
        return max(ts) if ts else None

    def session_did(self, session: str, kind: str) -> bool:
        return any(e.session == session and e.kind == kind
                   for e in self.events)


def check(rule: dict, tool: str, args: dict, session: str,
          now: datetime, h: History) -> str | None:
    """The reason a temporal or sequence rule objects, or None."""
    t = rule["type"]
    if tool not in rule.get("tools", [tool]):
        return None
    if t == "count_within":
        key = args.get(rule["key"], "")
        since = now - timedelta(hours=rule["hours"])
        if h.count(tool, key, since) >= rule["n"]:
            return "repeat_within_window"
    if t == "quiet_after":
        key = args.get(rule["key"], "")
        last = h.last(rule["event"], key)
        if last is not None and now - last < timedelta(
                minutes=rule["minutes"]):
            return "quiet_period"
    if t == "escalate_after":
        if h.session_did(session, rule["event"]):
            return "untrusted_input_in_session"
    return None
