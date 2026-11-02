"""The guard: every query is estimated, limited, entitled, and read-only.

    restrict -> estimate -> limits -> entitlement -> run read-only

`Guard.ask` takes a layer `MetricQuery`; `Guard.ask_sql` takes raw SQL
(the shadow trial's path, kept for the lab so the failure can be seen).
Both share one estimator, which reads the statement's tables and
columns from SQLite's authorizer at compile time (nothing runs) and
prices them from the production catalog. A query with no estimate is
refused. Every decision, allowed or refused, is one trail line.
"""
from __future__ import annotations

import hashlib
import re
import sqlite3
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from common.clock import FixedClock
from common.trail import TrailWriter

from . import entitle as E
from . import layer as L
from . import warehouse as W

CHI = ZoneInfo("America/Chicago")
RETAIN = {"booking_events": 13}          # months kept; others: all
REASONS = ("not_in_layer", "unestimated", "window", "cost",
           "entitlement", "write")
_DB_CACHE: dict = {}


def chi_dt(ts: str) -> datetime:
    return datetime.fromisoformat(ts).astimezone(CHI)


def _register(db: sqlite3.Connection) -> None:
    db.create_function("chi_day", 1, lambda t: chi_dt(t).date().isoformat(),
                       deterministic=True)
    db.create_function("chi_month", 1, lambda t: chi_dt(t).strftime("%Y-%m"),
                       deterministic=True)

    def week(t):
        d = chi_dt(t).date()
        return d.fromordinal(d.toordinal() - d.weekday()).isoformat()
    db.create_function("chi_week", 1, week, deterministic=True)

    class Pct:
        def __init__(self):
            self.xs, self.q = [], 0.5

        def step(self, x, q):
            if x is not None:
                self.xs.append(x)
            self.q = q

        def finalize(self):
            if not self.xs:
                return None
            xs = sorted(self.xs)
            return xs[min(len(xs) - 1, int(self.q * len(xs)))]
    db.create_aggregate("pct", 2, Pct)


def warehouse_path(seed: int = 20) -> Path:
    """Build the lab warehouse once per process, as a file."""
    if seed not in _DB_CACHE:
        d = Path(tempfile.mkdtemp(prefix="designlab-wh-"))
        p = d / f"warehouse-{seed}.db"
        W.build(str(p), seed).close()
        _DB_CACHE[seed] = p
    return _DB_CACHE[seed]


ALLOWED = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ,
           sqlite3.SQLITE_FUNCTION}


def read_only(path: Path) -> sqlite3.Connection:
    """Read-only three ways: the file is opened mode=ro, the connection
    is query_only, and the authorizer denies everything but SELECT,
    column reads, and functions."""
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    db.execute("PRAGMA query_only = 1")
    _register(db)
    db.set_authorizer(lambda code, *a: sqlite3.SQLITE_OK
                      if code in ALLOWED else sqlite3.SQLITE_DENY)
    return db


@dataclass
class Estimate:
    bytes: float
    usd: float
    seconds: float
    tables: dict                   # table -> months scanned
    actual_bytes: float = 0.0

    @property
    def actual_usd(self) -> float:
        return _usd(self.actual_bytes)


def _usd(b: float) -> float:
    return b / 1e12 * W.RATE_USD_PER_TB


def reads_of(db: sqlite3.Connection, sql: str) -> tuple[dict, list]:
    """Tables and columns the statement would read, and any action that
    is not a read. Compiles with EXPLAIN; nothing executes."""
    reads: dict = {}
    denied: list = []

    def auth(code, a1, a2, dbname, trig):
        if code == sqlite3.SQLITE_READ and a1:
            reads.setdefault(a1, set())
            if a2:
                reads[a1].add(a2)
        elif code not in ALLOWED:
            denied.append(code)
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK
    db.set_authorizer(auth)
    try:
        db.execute("EXPLAIN " + sql, [None] * sql.count("?"))
    except sqlite3.DatabaseError:
        if not denied:
            raise
    finally:
        db.set_authorizer(None)
    for t in re.findall(r"\b(?:FROM|JOIN)\s+([A-Za-z_]+)", sql, re.I):
        if t in W.CATALOG:
            reads.setdefault(t, set())
    return reads, denied


def pruned_months(sql: str, table: str) -> list[str] | None:
    """Months a raw statement limits itself to on the partition column,
    or None when it does not (then every retained month is scanned)."""
    lits = re.findall(r"\bmonth\s*(?:=|>=|<=|BETWEEN)\s*'(\d{4}-\d{2})'"
                      r"(?:\s*AND\s*'(\d{4}-\d{2})')?", sql, re.I)
    if not lits:
        return None
    lo = min(a for a, _ in lits)
    hi = max(b or a for a, b in lits)
    return [m for m in retained(table) if lo <= m <= hi]


def retained(table: str) -> list[str]:
    ms = W.months()
    return ms[-RETAIN[table]:] if table in RETAIN else ms


def stats_rows(table: str, month: str | None) -> float:
    t = W.CATALOG[table]
    if month is None:
        return t.rows_per_month
    partial = (W.TODAY.day - 1) / 31 if month == W.LAST else 1.0
    return t.rows_per_month * W.SEASON[int(month[5:])] * partial


def _true_rows(table: str, month: str | None) -> float:
    if month is None:
        return W.CATALOG[table].rows_per_month
    partial = W.TODAY.day / 31 if month == W.LAST else 1.0
    return W.true_rows(table, month) * partial / (
        1.18 if month == W.LAST else 1.0)


def estimate(reads: dict, months: dict, catalog=W.CATALOG
             ) -> Estimate | None:
    """Bytes from catalog statistics. None if any table has none."""
    total = actual = 0.0
    scanned = {}
    for table, cols in reads.items():
        t = catalog.get(table)
        if t is None:
            return None
        cols = [c for c in cols if c != t.partition and c not in t.lab_only]
        if not cols:
            cols = [min(t.columns, key=lambda c: t.columns[c] or 99)]
        width = sum(t.columns[c] for c in cols)
        twidth = sum(W.true_bytes(table, c) for c in cols)
        ms = months.get(table) if t.partition else [None]
        if t.partition and ms is None:
            ms = retained(table)
        rows = sum(stats_rows(table, m) for m in ms)
        trows = sum(_true_rows(table, m) for m in ms)
        total += max(W.MIN_BILLED_BYTES, rows * width)
        actual += max(W.MIN_BILLED_BYTES, trows * twidth)
        scanned[table] = len(ms)
    return Estimate(total, _usd(total), total / W.SCAN_BYTES_PER_S,
                    scanned, actual)


@dataclass
class Decision:
    status: str                         # answered or refused
    reason: str = ""
    detail: str = ""
    sql: str = ""
    estimate: Estimate | None = None
    rows: list = field(default_factory=list)
    truncated: bool = False
    suppressed: int = 0
    trail_line: str = ""


class Guard:
    def __init__(self, layer: L.Layer | None = None, seed: int = 20,
                 cap_usd: float = 1.00, max_seconds: float = 60.0,
                 row_limit: int = 1000, trail: TrailWriter | None = None,
                 estimator=estimate, raw_allowed: bool = False):
        self.layer = layer or L.load()
        self.path = warehouse_path(seed)
        self.db = read_only(self.path)
        self.scratch = sqlite3.connect(f"file:{self.path}?mode=ro",
                                       uri=True)
        _register(self.scratch)
        self.cap_usd, self.max_seconds = cap_usd, max_seconds
        self.row_limit = row_limit
        self.trail = trail or TrailWriter(clock=FixedClock(
            "2026-05-27T09:15:00-05:00", step_seconds=7))
        self.estimator = estimator
        self.raw_allowed = raw_allowed

    # -- the layer path ------------------------------------------------
    def ask(self, q: L.MetricQuery, ent: E.Entitlement) -> Decision:
        p = L.problems(self.layer, q)                       # 1 restrict
        if p:
            return self._done(Decision("refused", "not_in_layer", p[0]),
                              q.metric, ent)
        m = self.layer.metrics[q.metric]
        limit = self.row_limit if self.row_limit else 10**9
        q2 = L.MetricQuery(q.metric, q.start, q.end, q.dims, q.grain,
                           q.filters, min(q.limit, limit))
        c = L.compile_query(self.layer, q2, E.desk_filter(m, ent))
        reads, _ = reads_of(self.scratch, c.sql)
        est = self.estimator(reads, {c.table: c.months})    # 2 estimate
        d = Decision("refused", sql=c.sql, estimate=est)
        if est is None:
            d.reason, d.detail = "unestimated", "no estimate, no query"
        elif q.days > m.max_window_days:                    # 3 limits
            d.reason = "window"
            d.detail = f"{q.days} days > {m.max_window_days} for {m.name}"
        elif est.usd > self.cap_usd or est.seconds > self.max_seconds:
            d.reason = "cost"
            d.detail = f"${est.usd:,.2f} > ${self.cap_usd:.2f} cap"
        else:
            why = E.check_metric(self.layer, m, q.dims, q.filters, ent)
            if why:                                         # 4 entitle
                d.reason, d.detail = "entitlement", why[0]
            else:                                           # 5 run
                self._run(d, c.sql, c.params, q2.limit)
        return self._done(d, q.metric, ent)

    # -- the raw path (shadow trial) ----------------------------------
    def ask_sql(self, sql: str, ent: E.Entitlement) -> Decision:
        d = Decision("refused", sql=sql)
        try:
            reads, denied = reads_of(self.scratch, sql)
        except sqlite3.DatabaseError as e:
            d.reason, d.detail = "not_in_layer", f"does not compile: {e}"
            return self._done(d, "(raw)", ent)
        if denied:
            d.reason, d.detail = "write", "statement is not a read"
            return self._done(d, "(raw)", ent)
        months = {t: pruned_months(sql, t) for t in reads}
        est = self.estimator(reads, months)
        d.estimate = est
        if not self.raw_allowed:
            d.reason, d.detail = "not_in_layer", "raw SQL is not offered"
        elif est is None:
            d.reason, d.detail = "unestimated", "no estimate, no query"
        elif est.usd > self.cap_usd or est.seconds > self.max_seconds:
            d.reason = "cost"
            d.detail = f"${est.usd:,.2f} > ${self.cap_usd:.2f} cap"
        else:
            why = E.check_reads(reads, ent)
            if why:
                d.reason, d.detail = "entitlement", why[0]
            else:
                self._run(d, sql, [], self.row_limit or 10**9)
        return self._done(d, "(raw)", ent)

    def _run(self, d: Decision, sql: str, params: list, limit: int):
        rows = self.db.execute(sql, params).fetchall()
        d.status = "answered"
        d.truncated = len(rows) > limit
        rows = rows[:limit]
        k = self.layer.k_min_rows
        out = []
        for r in rows:
            if len(r) >= 2 and isinstance(r[-1], int) and r[-1] < k and \
                    len(r) > 3:
                d.suppressed += 1
                r = (*r[:-2], None, r[-1])
            out.append(r)
        d.rows = out

    def _done(self, d: Decision, metric: str, ent: E.Entitlement):
        e = d.estimate
        d.trail_line = self.trail.append({
            "kind": "knowledge.query", "caller": ent.subject,
            "grant": ent.token_id, "roles": list(ent.roles),
            "metric": metric, "layer": self.layer.version,
            "sql_sha": hashlib.sha256(d.sql.encode()).hexdigest()[:12],
            "est_usd": None if e is None else round(e.usd, 4),
            "est_bytes": None if e is None else int(e.bytes),
            "decision": d.status, "reason": d.reason,
            "rows": len(d.rows)})
        return d
