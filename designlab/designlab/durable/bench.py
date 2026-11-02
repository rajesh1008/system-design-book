"""Replay benchmark: journal N runs, then time a strict replay of each,
including the read from the store. Reports p50, p99, and max."""
from __future__ import annotations

import sqlite3
import tempfile
import time
from pathlib import Path

from .killsuite import OPTIONS, START
from .models import FixtureA
from .replay import replay
from .workflow import Engine, SimClock, Spec


def journal_runs(base: Path, n: int) -> list[str]:
    eng = Engine(base, "durable", FixtureA(), SimClock(START))
    ids = []
    for i in range(n):
        kind = "refund" if i % 3 == 0 else "rebook"
        spec = Spec(f"RUN-{10000 + i}", f"LTG-{4480000 + i}", kind, 486.0,
                    OPTIONS, 360.0)
        eng.submit(spec)
        eng.run(spec.run_id)
        ids.append(spec.run_id)
    eng.close()
    return ids


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def bench(n: int = 2000) -> dict:
    with tempfile.TemporaryDirectory() as d:
        ids = journal_runs(Path(d), n)
        conn = sqlite3.connect(Path(d) / "lab.db")
        ms, diverged, steps = [], 0, 0
        for rid in ids:
            t0 = time.perf_counter()
            r = replay(conn, rid)
            ms.append((time.perf_counter() - t0) * 1000)
            diverged += r.divergence is not None
            steps += r.steps
        conn.close()
    return {"runs": n, "steps": steps, "diverged": diverged,
            "p50_ms": pct(ms, 50), "p99_ms": pct(ms, 99),
            "max_ms": max(ms)}
