"""The review log and the review card.

Owen Fletcher's team keeps the log: one row per design reviewed,
with the outcome, the record, and whether a shipped design had a
kill-switch tier before it went live.
"""
from __future__ import annotations

import tomllib
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .store import Store, load_store

DATA = Path(__file__).resolve().parent / "data"
OUTCOMES = ("approve", "change", "decline")


@dataclass(frozen=True)
class Entry:
    id: str
    date: str
    design: str
    team: str
    outcome: str
    record: str
    shipped: bool
    kill_switch: bool
    minutes: int


def load_log(path: Path | None = None) -> list[Entry]:
    with open(path or DATA / "reviewlog.toml", "rb") as fh:
        raw = tomllib.load(fh)
    return [Entry(**e) for e in raw.get("reviews", [])]


def by_month(log: list[Entry]) -> dict[str, Counter]:
    out: dict[str, Counter] = {}
    for e in log:
        out.setdefault(e.date[:7], Counter())[e.outcome] += 1
    return out


def card(log: list[Entry], store: Store | None = None,
         as_of: str = "2026-09-08") -> dict:
    store = store or load_store()
    c = Counter(e.outcome for e in log)
    recorded = [e for e in log if store.get(e.record)]
    return {
        "designs reviewed": len(log),
        "declined": c["decline"],
        "changed": c["change"],
        "approved as submitted": c["approve"],
        "shipped without a kill switch":
            sum(1 for e in log if e.shipped and not e.kill_switch),
        "records": len(recorded),
        "records revisited": len(store.revisited()),
        "records past revisit date":
            len(store.due(date.fromisoformat(as_of))),
        "reviews with no record": len(log) - len(recorded),
        "median minutes": sorted(e.minutes for e in log)[len(log) // 2],
    }
