"""The lab warehouse and its catalog.

Two things live here. `build()` makes a small SQLite warehouse: monthly
partitions from January 2025 to May 2026, each row standing for `w`
production rows, so a count is SUM(w). `CATALOG` holds the production
statistics the guard estimates from: rows a month, bytes a column, the
partition column. The statistics are refreshed nightly, so they lag the
true partition sizes a little; `true_rows` is what a scan would read.
All figures are illustrative.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from common.rand import seeded

FIRST, LAST = "2025-01", "2026-05"
TODAY = date(2026, 5, 27)          # the lab's "today", a Wednesday
RATE_USD_PER_TB = 5.00             # Lakeshore's contract rate (illustrative)
MIN_BILLED_BYTES = 10_000_000      # 10 MB minimum per table scanned
SCAN_BYTES_PER_S = 12.5e9          # shared interactive pool


def months(first: str = FIRST, last: str = LAST) -> list[str]:
    y, m = map(int, first.split("-"))
    out = []
    while f"{y:04d}-{m:02d}" <= last:
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


@dataclass(frozen=True)
class Table:
    name: str
    rows_per_month: float           # production, from the last stats run
    columns: dict                   # column -> average bytes (production)
    partition: str | None = "month"
    lab_only: tuple = ("w",)        # columns production does not have
    domain: str = "ops"             # ops, finance, pii, events
    w: int = 1                      # production rows per lab row
    lab_rows_per_month: int = 0


def _t(name, rpm, cols, w, domain="ops", partition="month"):
    return Table(name, rpm, cols, partition, ("w",), domain, w,
                 max(1, round(rpm / w)) if partition else 0)


CATALOG: dict[str, Table] = {t.name: t for t in [
    _t("changes", 175_000, {"change_id": 16, "month": 0, "created_at": 8,
       "change_type": 12, "handled_by": 8, "channel": 8, "desk": 6,
       "carrier": 4, "handle_minutes": 4, "itinerary_id": 12,
       "repeat_7d": 1, "cost_usd": 8}, 500),
    _t("contacts", 1_170_000, {"contact_id": 16, "month": 0,
       "created_at": 8, "channel": 8, "desk": 6, "change_id": 16,
       "transcript": 2_400}, 5_000),
    _t("refunds", 58_300, {"refund_id": 16, "month": 0, "issued_at": 8,
       "change_type": 12, "carrier": 4, "desk": 6, "handled_by": 8,
       "amount_usd": 8, "settled_at": 8, "clock_met": 1, "matured": 1,
       "error": 1, "verified": 1, "customer_id": 12}, 500),
    _t("approvals", 20_000, {"approval_id": 16, "month": 0,
       "filed_at": 8, "desk": 6, "wait_minutes": 4, "decision": 8,
       "approver_id": 10}, 100),
    _t("effects", 10_500, {"effect_id": 16, "month": 0, "at": 8,
       "change_type": 12, "verified": 1, "duplicate": 1}, 50),
    _t("tasks", 10_500, {"task_id": 16, "month": 0, "at": 8,
       "latency_s": 4, "change_type": 12, "model_usd": 8}, 50),
    _t("queue_snapshots", 104_000, {"desk": 6, "month": 0, "at": 8,
       "depth": 4}, 500),
    _t("bookings", 1_000_000, {"booking_id": 16, "month": 0,
       "booked_at": 8, "carrier": 4, "channel": 8, "gross_usd": 8,
       "customer_id": 12}, 1_000),
    _t("carrier_notices", 30_000, {"notice_id": 16, "month": 0,
       "received_at": 8, "carrier": 4, "kind": 12}, 100),
    _t("booking_events", 4.0e9, {"event_id": 16, "month": 0,
       "event_at": 8, "itinerary_id": 12, "event_type": 10,
       "carrier": 4, "payload": 610}, 1_000_000, domain="events"),
    _t("fin_ledger", 1_000_000, {"entry_id": 16, "month": 0,
       "posted_at": 8, "carrier": 4, "account": 10, "amount_usd": 8,
       "margin_usd": 8, "receivable_usd": 8}, 1_000, domain="finance"),
    _t("fin_payroll", 2_600, {"employee_id": 10, "month": 0,
       "desk": 6, "salary_usd": 8, "bonus_usd": 8}, 100,
       domain="finance"),
    Table("customers", 6_200_000, {"customer_id": 12, "name": 32,
          "email": 28, "phone": 14, "card_last4": 4, "tier": 8},
          partition=None, domain="pii", w=1, lab_rows_per_month=0),
]}

DESKS = ("CHI-1", "CHI-2", "CHI-3", "DFW-1", "DFW-2", "ATL-1",
         "ATL-2", "DEN-1", "PHX-1", "MSP-1", "BOS-1", "SEA-1")
CARRIERS = ("LKA", "NRA", "PWX", "SKY", "BLU", "CRN")
CHANGE_TYPES = ("voluntary_rebooking", "cancel_for_credit",
                "involuntary_rebooking", "hotel_cancellation",
                "cancel_with_refund", "involuntary_refund", "upgrade",
                "accept_schedule_change", "hotel_date_change",
                "ancillary_refund", "car_rental_change", "name_correction")
REFUND_TYPES = ("cancel_with_refund", "involuntary_refund",
                "hotel_cancellation", "ancillary_refund")
EVENT_TYPES = ("status_poll", "price_check", "view", "schedule_update",
               "refund_requested", "refund_issued", "refund_reversed",
               "carrier_refund_reported", "ticketed", "note")
SEASON = {1: .93, 2: .88, 3: 1.02, 4: 1.0, 5: 1.04, 6: 1.12, 7: 1.15,
          8: 1.08, 9: .95, 10: .96, 11: .97, 12: .98}
HANDLED_2026 = {"2026-01": (.03, .10, .36, .51), "2026-02": (.03, .10,
                .36, .51), "2026-03": (.04, .11, .37, .48), "2026-04":
                (.05, .12, .38, .45), "2026-05": (.06, .12, .38, .44)}


def true_rows(table: str, month: str, seed: int = 20) -> float:
    """Rows a scan of this partition really reads. Stats lag the truth:
    each month drifts a few percent, and the current month is partial
    in the stats run but has grown since."""
    t = CATALOG[table]
    r = seeded(seed, "truth", table, month)
    drift = 1 + r.uniform(-0.06, 0.09)
    grow = 1.18 if month == LAST else 1.0
    return t.rows_per_month * SEASON[int(month[5:])] * drift * grow


def true_bytes(table: str, column: str, seed: int = 20) -> float:
    t = CATALOG[table]
    r = seeded(seed, "truth-bytes", table, column)
    return t.columns[column] * (1 + r.uniform(-0.08, 0.12))


def _ts(month: str, r) -> str:
    y, m = map(int, month.split("-"))
    days = 31 if m in (1, 3, 5, 7, 8, 10, 12) else 30 if m != 2 else 28
    if month == LAST:
        days = TODAY.day
    d = datetime(y, m, r.randint(1, days), r.randint(0, 23),
                 r.randint(0, 59), tzinfo=timezone.utc)
    return d.isoformat()


def _schema(t: Table) -> str:
    types = {"amount_usd": "REAL", "cost_usd": "REAL", "gross_usd": "REAL",
             "margin_usd": "REAL", "receivable_usd": "REAL",
             "salary_usd": "REAL", "bonus_usd": "REAL",
             "model_usd": "REAL", "latency_s": "REAL",
             "handle_minutes": "REAL", "wait_minutes": "REAL"}
    cols = [f"{c} {types.get(c, 'TEXT')}" for c in t.columns]
    if t.partition:
        cols.append("w INTEGER NOT NULL")
    return f"CREATE TABLE {t.name} ({', '.join(cols)})"


def build(path: str = ":memory:", seed: int = 20) -> sqlite3.Connection:
    """Create and fill the lab warehouse. Deterministic for a seed."""
    db = sqlite3.connect(path)
    for t in CATALOG.values():
        db.execute(_schema(t))
    for name in ("changes", "refunds", "contacts", "approvals",
                 "queue_snapshots", "bookings", "carrier_notices",
                 "booking_events", "fin_ledger", "fin_payroll"):
        _fill(db, CATALOG[name], seed)
    for month in months("2026-01", LAST):
        _fill_agent(db, month, seed)
    _fill_customers(db, seed)
    db.commit()
    return db


def _n(t: Table, month: str, r) -> int:
    n = t.lab_rows_per_month * SEASON[int(month[5:])]
    if month == LAST:
        n *= TODAY.day / 31
    return max(1, round(n * r.uniform(0.95, 1.05)))


def _handled(month: str, r) -> str:
    shares = HANDLED_2026.get(month, (0.0, .08, .35, .57))
    x, acc = r.random(), 0.0
    for who, s in zip(("agent", "assisted", "self_service", "person"),
                      shares):
        acc += s
        if x < acc:
            return who
    return "person"


def _fill(db, t: Table, seed: int) -> None:
    for month in months():
        r = seeded(seed, "wh", t.name, month)
        rows = []
        for i in range(_n(t, month, r)):
            rows.append(_row(t.name, month, i, r))
        ph = ", ".join("?" * (len(t.columns) + 1))
        db.executemany(f"INSERT INTO {t.name} VALUES ({ph})",
                       [(*row, t.w) for row in rows])


def _row(name: str, month: str, i: int, r) -> tuple:
    at = _ts(month, r)
    desk, car = r.choice(DESKS), r.choice(CARRIERS)
    key = f"{month.replace('-', '')}{i:06d}"
    if name == "changes":
        ct = r.choice(CHANGE_TYPES)
        return (f"CHG-{key}", month, at, ct, _handled(month, r),
                r.choice(("chat", "phone", "email", "app")), desk, car,
                round(r.lognormvariate(2.4, 0.6), 1), f"LTG-{key[-7:]}",
                int(r.random() < 0.11), round(r.uniform(4, 60), 2))
    if name == "refunds":
        amt = round(r.lognormvariate(5.4, 0.7), 2)
        late = r.random() < 0.05
        return (f"RFD-{key}", month, at, r.choice(REFUND_TYPES), car, desk,
                _handled(month, r), amt, at, int(not late),
                int(month <= "2026-01"), int(r.random() < 0.008),
                int(r.random() < 0.99), f"CUS-{r.randint(1, 3000):05d}")
    if name == "contacts":
        return (f"CON-{key}", month, at, r.choice(("chat", "phone",
                "email", "app")), desk, f"CHG-{key}", "(text)")
    if name == "approvals":
        return (f"APR-{key}", month, at, desk,
                round(r.lognormvariate(1.6, 1.0), 1),
                r.choice(("approved", "approved", "approved", "refused")),
                f"EMP-{r.randint(1, 140):04d}")
    if name == "queue_snapshots":
        return (desk, month, at, r.randint(0, 60))
    if name == "bookings":
        return (f"BKG-{key}", month, at, car, r.choice(("web", "app",
                "agency")), round(r.lognormvariate(6.2, 0.6), 2),
                f"CUS-{r.randint(1, 3000):05d}")
    if name == "carrier_notices":
        return (f"NTC-{key}", month, at, car, r.choice((
                "schedule_change", "cancellation", "equipment", "gate")))
    if name == "booking_events":
        et = r.choices(EVENT_TYPES, (60, 18, 12, 4, 1, 1, .2, 1, 2, .8))[0]
        return (f"EVT-{key}", month, at, f"LTG-{key[-7:]}", et, car,
                '{"type":"' + et + '"}')
    if name == "fin_ledger":
        g = round(r.lognormvariate(6.2, 0.6), 2)
        return (f"FIN-{key}", month, at, car, "revenue", g,
                round(g * r.uniform(.04, .11), 2), round(g * .01, 2))
    if name == "fin_payroll":
        return (f"EMP-{i:04d}", month, desk, round(r.uniform(3800, 7400),
                2), round(r.uniform(0, 600), 2))
    raise KeyError(name)


def _fill_agent(db, month: str, seed: int) -> None:
    """Effects and tasks exist from the agent's phase two onward."""
    r = seeded(seed, "wh-agent", month)
    share = HANDLED_2026[month][0] / 0.06
    n = max(1, round(210 * share * (TODAY.day / 31 if month == LAST
                                    else 1)))
    for i in range(n):
        at, ct = _ts(month, r), r.choice(CHANGE_TYPES)
        key = f"{month.replace('-', '')}{i:06d}"
        db.execute("INSERT INTO effects VALUES (?,?,?,?,?,?,?)",
                   (f"EFF-{key}", month, at, ct,
                    int(r.random() < 0.991), 0, 50))
        db.execute("INSERT INTO tasks VALUES (?,?,?,?,?,?,?)",
                   (f"TSK-{key}", month, at,
                    round(r.lognormvariate(2.9, 0.45), 1), ct,
                    round(r.uniform(0.05, 0.09), 4), 50))


def _fill_customers(db, seed: int) -> None:
    r = seeded(seed, "wh-customers")
    db.executemany("INSERT INTO customers VALUES (?,?,?,?,?,?)",
                   [(f"CUS-{i:05d}", f"Traveler {i}", f"t{i}@example.com",
                     "555-0100", f"{r.randint(0, 9999):04d}",
                     r.choice(("base", "silver", "gold")))
                    for i in range(1, 3001)])


def chicago(ts: datetime) -> str:
    """Lab clock in America/Chicago with the day's offset (CDT in May)."""
    off = -5 if 3 <= ts.month <= 10 else -6
    return ts.astimezone(timezone(timedelta(hours=off))).isoformat()
