"""Replay one recorded day through layouts and caches; score them."""
from __future__ import annotations

import json
from pathlib import Path

from .layout import LAYOUTS
from .prefix import EngineCache, PromptCache
from .prices import Bill
from .trace import Task, calls_in_time_order, day

FIXTURES = Path(__file__).with_name("fixtures")


def engines() -> dict:
    with (FIXTURES / "engines.json").open() as f:
        return json.load(f)


def make_cache(name: str, prof: dict | None = None):
    if name == "api":
        return PromptCache()
    p = prof or engines()["engines"][name]
    return EngineCache(p["prefix_cache_tokens"], p["block_tokens"])


def replay(tasks: list[Task], layout: str, cache: str = "api",
           salt_by: str = "tenant") -> dict:
    c = make_cache(cache)
    render = LAYOUTS[layout]
    per_task: dict[str, Bill] = {}
    total = Bill()
    for task, call in calls_in_time_order(tasks):
        salt = task.tenant if salt_by == "tenant" else task.customer
        b = c.call(render(task, call), call.at_s, call.output, salt)
        per_task[task.id] = per_task.get(task.id, Bill()) + b
        total = total + b
    usd = [b.usd("frontier") for b in per_task.values()]
    return {"layout": layout, "cache": cache, "bill": total,
            "hit": total.hit_rate(), "usd_per_task": sum(usd) / len(usd),
            "calls": sum(len(t.calls) for t in tasks)}


def compare(seed: int = 14) -> dict:
    tasks = day(seed)
    return {k: replay(tasks, k) for k in ("pilot", "stable-first")}
