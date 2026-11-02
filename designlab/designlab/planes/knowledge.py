"""The knowledge plane: facts with a source and an age, never bare context.

Contract C1 (knowledge to action): every fact carries its source and the
time it was read from that source; a fact older than its freshness limit
is returned in `stale`, never silently; an unknown itinerary raises
NotFound rather than returning an empty packet.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


class NotFound(KeyError):
    pass


@dataclass(frozen=True)
class Fact:
    name: str
    value: object
    source: str
    as_of: str          # ISO time the source was read


@dataclass
class ContextPacket:
    itinerary: str
    facts: dict[str, Fact]
    stale: list[str] = field(default_factory=list)

    def value(self, name: str):
        return self.facts[name].value


class KnowledgePlane:
    def __init__(self, records: dict[str, list[Fact]], clock,
                 max_age_s: float = 900.0):
        self.records = records
        self.clock = clock
        self.max_age_s = max_age_s

    def context(self, itinerary: str) -> ContextPacket:
        if itinerary not in self.records:
            raise NotFound(itinerary)
        now = self.clock.now()
        facts, stale = {}, []
        for f in self.records[itinerary]:
            facts[f.name] = f
            age = (now - datetime.fromisoformat(f.as_of)).total_seconds()
            if age > self.max_age_s:
                stale.append(f.name)
        return ContextPacket(itinerary, facts, sorted(stale))
