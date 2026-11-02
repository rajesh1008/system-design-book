"""Triggers: a schedule, an event, a threshold, and the run key.

The schedule is a durable timer in the run store (Chapter 9), so a
worker that restarts finds the next sweep where it left it, and two
sweepers cannot both fire one timer. An event wakes a run for one
watch. A run key names the work, not the wake: the second wake with
the same key fires nothing. The key is stored as a timer that can
fire once, so it survives a restart too.
"""
from __future__ import annotations

from datetime import datetime

from durable.store import RunStore


class Triggers:
    def __init__(self, rs: RunStore, loop: str):
        self.rs, self.loop = rs, loop
        self.fired = 0
        self.deduped = 0

    def schedule(self, name: str, fire_at: datetime) -> None:
        self.rs.set_timer(f"loop:{self.loop}", name, fire_at)

    def due(self, now: datetime) -> list[str]:
        out = []
        for _run, name, _at in self.rs.due(now, f"loop:{self.loop}"):
            if self.rs.fire(f"loop:{self.loop}", name):
                out.append(name)
        return out

    def wake(self, key: tuple, now: datetime) -> bool:
        """An event or a sweep asks for a run of `key`. True when this
        is the first wake for that key."""
        name = "key:" + "|".join(str(k) for k in key)
        self.rs.set_timer(f"run:{self.loop}", name, now)
        if self.rs.fire(f"run:{self.loop}", name):
            self.fired += 1
            return True
        self.deduped += 1
        return False


def threshold(value: float, line: float) -> bool:
    """A threshold trigger fires when a measured value crosses a
    line; here, a fare at least the minimum drop below the floor."""
    return value <= line
