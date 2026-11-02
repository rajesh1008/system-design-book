"""The semantic layer: 41 metrics, their dimensions, and the compiler.

The model never writes SQL. It names a metric, up to three dimensions,
a window, a grain, and filters (a `MetricQuery`); the layer compiles
that into one SELECT whose partitions it knows in advance. A metric
the layer does not have cannot be asked for.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from . import warehouse as W

# Known values for the dimensions a filter may name. A filter value the
# layer does not know is refused, not run: an unknown value returns no
# rows, and no rows reads like zero.
VALUES = {"change_type": W.CHANGE_TYPES + W.REFUND_TYPES,
          "handled_by": W.HANDLERS, "channel": W.CHANNELS,
          "desk": W.DESKS, "carrier": W.CARRIERS,
          "decision": W.DECISIONS, "kind": W.NOTICE_KINDS}

LAYER_FILE = Path(__file__).with_name("layer.toml")
GRAINS = ("none", "day", "week", "month")
TIME_COL = {"changes": "created_at", "contacts": "created_at",
            "refunds": "issued_at", "approvals": "filed_at",
            "effects": "at", "tasks": "at", "queue_snapshots": "at",
            "bookings": "booked_at", "carrier_notices": "received_at",
            "booking_events": "event_at"}


@dataclass(frozen=True)
class Metric:
    name: str
    label: str
    table: str
    kind: str                     # count, sum, ratio, median, p95, max
    dims: tuple
    entitle: tuple                # any one of these roles may ask
    max_window_days: int
    owner: str
    expr: str = ""
    where: str = ""
    num: str = ""
    den: str = ""
    desk_scoped: bool = False


@dataclass(frozen=True)
class Layer:
    version: str
    metrics: dict
    dimensions: dict              # name -> roles needed ([] for none)
    k_min_rows: int

    def get(self, name: str) -> Metric | None:
        return self.metrics.get(name)

    def catalog_text(self) -> str:
        """What the model is shown: names, labels, dimensions. No SQL."""
        return "\n".join(f"{m.name}: {m.label}; by {', '.join(m.dims)}"
                         for m in self.metrics.values())


def load(path: Path = LAYER_FILE, extra: list[dict] | None = None) -> Layer:
    with Path(path).open("rb") as f:
        d = tomllib.load(f)
    rows = d["metric"] + list(extra or [])
    metrics = {}
    for x in rows:
        m = Metric(name=x["name"], label=x["label"], table=x["table"],
                   kind=x["kind"], dims=tuple(x["dims"]),
                   entitle=tuple(x["entitle"]),
                   max_window_days=x["max_window_days"], owner=x["owner"],
                   expr=x.get("expr", ""), where=x.get("where", ""),
                   num=x.get("num", ""), den=x.get("den", ""),
                   desk_scoped=x.get("desk_scoped", False))
        if m.name in metrics:
            raise ValueError(f"metric {m.name} defined twice")
        metrics[m.name] = m
    for m in metrics.values():
        if m.kind == "ratio":
            for part in (m.num, m.den):
                p = metrics.get(part)
                if p is None or p.table != m.table:
                    raise ValueError(f"{m.name}: {part} not on {m.table}")
    dims = {k: tuple(v["needs"]) for k, v in d["dimension"].items()}
    return Layer(d["version"], metrics, dims, d["k_min_rows"])


@dataclass(frozen=True)
class MetricQuery:
    metric: str
    start: date
    end: date                     # inclusive, Chicago days
    dims: tuple = ()
    grain: str = "none"
    filters: tuple = ()           # ((dimension, value), ...)
    limit: int = 1000

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1


@dataclass
class Compiled:
    sql: str
    params: list
    table: str
    months: list = field(default_factory=list)


def problems(layer: Layer, q: MetricQuery) -> list[str]:
    """Why this query is not one the layer can answer (empty if it is)."""
    m = layer.get(q.metric)
    if m is None:
        return [f"no metric named {q.metric!r}"]
    out = []
    if len(q.dims) > 3:
        out.append("more than three dimensions")
    for d in list(q.dims) + [k for k, _ in q.filters]:
        if d not in m.dims:
            out.append(f"{q.metric} has no dimension {d!r}")
    for d, v in q.filters:
        known = VALUES.get(d)
        if known is not None and v not in known:
            near = [k for k in known if v in k or k in v]
            hint = f"; did you mean {near[0]!r}?" if near else ""
            out.append(f"{d} has no value {v!r}{hint}")
    if q.grain not in GRAINS:
        out.append(f"unknown grain {q.grain!r}")
    if q.end < q.start:
        out.append("window ends before it starts")
    return out


def _agg(layer: Layer, m: Metric, in_case: bool) -> str:
    def guard(expr: str, where: str) -> str:
        return f"CASE WHEN {where} THEN {expr} ELSE 0 END" if where \
            else expr
    if m.kind == "count":
        return f"SUM({guard('w', m.where if in_case else '')})"
    if m.kind == "sum":
        return f"SUM({guard(m.expr + ' * w', m.where if in_case else '')})"
    if m.kind == "ratio":
        n, d = layer.get(m.num), layer.get(m.den)
        return (f"1.0 * {_agg(layer, n, True)} / "
                f"NULLIF({_agg(layer, d, True)}, 0)")
    if m.kind in ("median", "p95"):
        return f"pct({m.expr}, {0.5 if m.kind == 'median' else 0.95})"
    if m.kind == "max":
        return f"MAX({m.expr})"
    raise ValueError(m.kind)


def _months(start: date, end: date) -> list[str]:
    out, y, mo = [], start.year, start.month
    while (y, mo) <= (end.year, end.month):
        out.append(f"{y:04d}-{mo:02d}")
        y, mo = (y + 1, 1) if mo == 12 else (y, mo + 1)
    return out


def compile_query(layer: Layer, q: MetricQuery,
                  desks: tuple = ()) -> Compiled:
    """One SELECT. `desks` is the caller's row filter, from entitle."""
    m = layer.metrics[q.metric]
    tcol = TIME_COL[m.table]
    period = {"none": "'all'", "day": f"chi_day({tcol})",
              "week": f"chi_week({tcol})", "month": f"chi_month({tcol})"}
    sel = [f"{period[q.grain]} AS period"] + [f"{d}" for d in q.dims]
    months = _months(q.start, q.end)
    where = ["month BETWEEN ? AND ?",
             f"chi_day({tcol}) BETWEEN ? AND ?"]
    params: list = [months[0], months[-1], q.start.isoformat(),
                    q.end.isoformat()]
    if m.where and m.kind != "ratio":
        where.append(f"({m.where})")
    for k, v in q.filters:
        where.append(f"{k} = ?")
        params.append(v)
    if m.desk_scoped and desks:
        where.append(f"desk IN ({', '.join('?' * len(desks))})")
        params += list(desks)
    group = ["period"] + list(q.dims)
    sql = (f"SELECT {', '.join(sel)}, {_agg(layer, m, False)} AS value, "
           f"COUNT(*) AS n_rows FROM {m.table} "
           f"WHERE {' AND '.join(where)} "
           f"GROUP BY {', '.join(group)} ORDER BY {', '.join(group)} "
           f"LIMIT {q.limit + 1}")
    return Compiled(sql, params, m.table, months)
