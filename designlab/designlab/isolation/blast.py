"""Blast radius as a number: how many itineraries one session can touch.

A design is a list of resources a session holds: its files, its view of
the knowledge plane, the caches it reads, its credential at the
gateway. Each resource has a probe that tries to reach a given
itinerary from inside one session. `probe_design` runs every probe
against every itinerary in a seeded population, and `blast_radius` is
the size of the union. The count is measured by trying, not read off a
diagram.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from common.rand import seeded
from planes import Fact, KnowledgePlane, NotFound

AS_OF = "2026-03-16T14:00:00+00:00"


class OutOfScope(PermissionError):
    pass


class ScopedKnowledge:
    """One session's view of the knowledge plane: its own itinerary."""

    def __init__(self, plane: KnowledgePlane, itinerary: str):
        self.plane = plane
        self.itinerary = itinerary

    def context(self, itinerary: str):
        if itinerary != self.itinerary:
            raise OutOfScope(itinerary)
        return self.plane.context(itinerary)


class SummaryCache:
    """Booking summaries, keyed by `key(session_owner, locator)`."""

    def __init__(self, key: Callable[[str, str], tuple]):
        self.key = key
        self.data: dict[tuple, str] = {}

    def put(self, owner: str, locator: str, itinerary: str) -> None:
        self.data[self.key(owner, locator)] = itinerary

    def get(self, owner: str, locator: str) -> str | None:
        return self.data.get(self.key(owner, locator))


def by_locator(owner: str, locator: str) -> tuple:
    return ("summary", locator)                   # the bug


def by_tenant(owner: str, locator: str) -> tuple:
    return ("summary", owner, locator)            # the fix


@dataclass
class Resource:
    name: str
    kind: str
    probe: Callable[[str], bool]


@dataclass
class World:
    itineraries: list[str]
    locator: dict[str, str]
    plane: KnowledgePlane
    worker_shift: list[str]
    cached: list[str]


def build_world(seed: int = 11, n: int = 2000, shift: int = 106,
                cached: int = 240, clock=None) -> World:
    from common.clock import FixedClock
    r = seeded(seed, "isolation", "world")
    its = [f"LTG-{4400000 + i}" for i in range(n)]
    letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    loc = {i: "".join(r.choice(letters) for _ in range(6)) for i in its}
    records = {i: [Fact("traveler", f"traveler-{k}", "booking", AS_OF),
                   Fact("locator", loc[i], "booking", AS_OF)]
               for k, i in enumerate(its)}
    plane = KnowledgePlane(records, clock or FixedClock(AS_OF))
    me = its[0]
    others = r.sample(its[1:], shift - 1)
    hot = r.sample(its, cached)
    if me not in hot:
        hot[0] = me
    return World(its, loc, plane, [me] + others, hot)


def design(world: World, me: str, *, shared_dir=False,
           cache_key=by_tenant, scoped=True) -> list[Resource]:
    files = set(world.worker_shift) if shared_dir else {me}
    view = ScopedKnowledge(world.plane, me) if scoped else world.plane
    cache = SummaryCache(cache_key)
    for it in world.cached:
        cache.put(it, world.locator[it], it)

    def knows(it: str) -> bool:
        try:
            view.context(it)
            return True
        except (OutOfScope, NotFound):
            return False

    def cache_hit(it: str) -> bool:
        return cache.get(me, world.locator[it]) == it

    return [Resource("session files", "file", lambda it: it in files),
            Resource("knowledge view", "read", knows),
            Resource("summary cache", "cache", cache_hit),
            Resource("gateway token", "credential", lambda it: it == me)]


def probe_design(world: World, resources: list[Resource]) -> dict:
    return {res.name: {it for it in world.itineraries if res.probe(it)}
            for res in resources}


def blast_radius(reach: dict[str, set]) -> int:
    out: set = set()
    for s in reach.values():
        out |= s
    return len(out)


def warm_pool(arrivals_per_s: float, hold_s: float,
              headroom: float = 1.25) -> tuple[float, int]:
    """Little's law: sandboxes in use L = lambda * W, plus headroom."""
    in_use = arrivals_per_s * hold_s
    return in_use, int(-(-in_use * headroom // 1))
