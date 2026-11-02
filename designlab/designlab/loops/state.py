"""Persisted watch state, in the run store.

One checkpoint row per change, keyed by the watch. A run reads the
latest row, works, and writes a row only when something changed, so
the run store holds the watch's history and nothing else. `Memory`
is the injection: the same interface, kept in the worker, gone when
the worker restarts.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sqlite3

from durable.store import RunStore

PROGRESS = ("floor_usd", "last_digest", "verdicts", "vouchers_usd")


def fresh(booked: float) -> dict:
    return {"floor_usd": booked, "last_digest": "", "last_fare": None,
            "verdicts": {}, "vouchers_usd": 0.0, "no_progress": 0,
            "recent": [], "status": "active"}


def progress_digest(st: dict) -> str:
    body = json.dumps({k: st[k] for k in PROGRESS}, sort_keys=True)
    return hashlib.sha256(body.encode()).hexdigest()[:12]


class Persisted:
    def __init__(self, conn: sqlite3.Connection | None = None):
        self.rs = RunStore(conn or sqlite3.connect(":memory:"))
        self.writes = 0

    def load(self, wid: str, booked: float) -> dict:
        got = self.rs.latest(f"watch:{wid}")
        return got[1] if got else fresh(booked)

    def save(self, wid: str, st: dict) -> None:
        self.rs.save(f"watch:{wid}", st)
        self.writes += 1


class Memory:
    """State in the worker. A restart (a new process, a new worker
    after a deploy) starts every watch from nothing."""

    def __init__(self):
        self.rows: dict[str, dict] = {}
        self.writes = 0

    def load(self, wid: str, booked: float) -> dict:
        return copy.deepcopy(self.rows.get(wid, fresh(booked)))

    def save(self, wid: str, st: dict) -> None:
        self.rows[wid] = copy.deepcopy(st)
        self.writes += 1

    def restart(self) -> None:
        self.rows.clear()
