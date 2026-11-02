"""The outside world for the lab: approval desk, permission store,
airline, and card processor, all in SQLite so they outlive a crash.

Each write commits at once, as an external system would. The desk and
the processor accept a key and return the earlier result for a key
they have seen; the airline accepts no key (requirement A5), so a
caller that may have rebooked must look the itinerary up first.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta

SCHEMA = """
create table if not exists desk(
  request_id text primary key, req_key text, run_id text,
  itinerary text, amount real, filed_at text, grant_at text,
  status text, permission_id text, escalated integer default 0);
create table if not exists permissions(
  permission_id text primary key, granted_by text, policy text,
  max_amount real, request_id text, run_id text, perm_key text,
  granted_at text, valid_until text, used integer default 0);
create table if not exists airline(
  n integer primary key autoincrement, itinerary text, flight text,
  ticket text, at text);
create table if not exists processor(
  n integer primary key autoincrement, pay_key text, itinerary text,
  amount real, at text);
create table if not exists notices(
  n integer primary key autoincrement, run_id text, kind text,
  at text);
"""


def short(*parts: object) -> str:
    return hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:8]


class World:
    def __init__(self, conn: sqlite3.Connection):
        self.c = conn
        self.c.executescript(SCHEMA)
        self.c.commit()

    # ---------------------------------------------------------- desk
    def file(self, run_id: str, itinerary: str, amount: float,
             now: datetime, grant_after_s: float | None,
             req_key: str | None = None) -> str:
        """File an approval request. A known key returns the old id."""
        if req_key is not None:
            row = self.c.execute("select request_id from desk where req_key=?",
                                 (req_key,)).fetchone()
            if row:
                return row[0]
        n = self.c.execute("select count(*) from desk").fetchone()[0] + 1
        rid = f"REQ-{30000 + n}"
        grant_at = None if grant_after_s is None else \
            (now + timedelta(seconds=grant_after_s)).isoformat()
        self.c.execute("insert into desk values(?,?,?,?,?,?,?,?,?,0)",
                       (rid, req_key, run_id, itinerary, amount,
                        now.isoformat(), grant_at, "open", None))
        self.c.commit()
        return rid

    def tick(self, now: datetime) -> None:
        """Supervisors answer requests whose grant time has come."""
        rows = self.c.execute(
            "select request_id, run_id, amount, grant_at from desk "
            "where status='open' and grant_at is not null").fetchall()
        for rid, run_id, amount, grant_at in rows:
            if datetime.fromisoformat(grant_at) <= now:
                pid = self._grant(rid, run_id, amount, "supervisor",
                                  "refunds-v3", now)
                self.c.execute("update desk set status='granted', "
                               "permission_id=? where request_id=?",
                               (pid, rid))
        self.c.commit()

    def status(self, request_id: str) -> tuple[str, str | None]:
        row = self.c.execute("select status, permission_id from desk "
                             "where request_id=?", (request_id,)).fetchone()
        return (row[0], row[1]) if row else ("unknown", None)

    def find_request(self, req_key: str) -> str | None:
        row = self.c.execute("select request_id from desk where req_key=?",
                             (req_key,)).fetchone()
        return row[0] if row else None

    def escalate(self, request_id: str) -> None:
        self.c.execute("update desk set escalated=escalated+1 "
                       "where request_id=?", (request_id,))
        self.c.commit()

    def close_request(self, request_id: str, status: str) -> None:
        self.c.execute("update desk set status=? where request_id=? "
                       "and status='open'", (status, request_id))
        self.c.commit()

    # ---------------------------------------------------- permissions
    def _grant(self, rid, run_id, amount, by, policy, now,
               perm_key=None) -> str:
        n = self.c.execute("select count(*) from permissions"
                           ).fetchone()[0] + 1
        pid = f"PRM-{40000 + n}"
        self.c.execute("insert into permissions values(?,?,?,?,?,?,?,?,?,0)",
                       (pid, by, policy, max(amount, 1500.0), rid, run_id,
                        perm_key, now.isoformat(),
                        (now + timedelta(days=8)).isoformat()))
        return pid

    def policy_grant(self, run_id: str, now: datetime,
                     perm_key: str | None = None) -> str:
        """The policy engine's grant for a rebooking within fare."""
        if perm_key is not None:
            row = self.c.execute("select permission_id from permissions "
                                 "where perm_key=?", (perm_key,)).fetchone()
            if row:
                return row[0]
        pid = self._grant(None, run_id, 0.0, "policy-engine",
                          "changes-v1", now, perm_key)
        self.c.commit()
        return pid

    def permission(self, pid: str) -> dict | None:
        row = self.c.execute("select permission_id, granted_by, policy, "
                             "max_amount, valid_until from permissions "
                             "where permission_id=?", (pid,)).fetchone()
        if not row:
            return None
        return dict(zip(("permission_id", "granted_by", "policy",
                         "max_amount_usd", "valid_until"), row))

    # ------------------------------------------------- airline, card
    def rebook(self, itinerary: str, flight: str, now: datetime) -> str:
        n = self.c.execute("select count(*) from airline").fetchone()[0] + 1
        ticket = f"TKT-{n:05d}"
        self.c.execute("insert into airline(itinerary, flight, ticket, at) "
                       "values(?,?,?,?)",
                       (itinerary, flight, ticket, now.isoformat()))
        self.c.commit()
        return ticket

    def tickets(self, itinerary: str) -> list[str]:
        return [r[0] for r in self.c.execute(
            "select ticket from airline where itinerary=? order by n",
            (itinerary,))]

    def refund(self, pay_key: str, itinerary: str, amount: float,
               now: datetime) -> dict:
        row = self.c.execute("select n from processor where pay_key=?",
                             (pay_key,)).fetchone()
        if row:
            return {"credit": row[0], "replayed": True}
        cur = self.c.execute("insert into processor(pay_key, itinerary, "
                             "amount, at) values(?,?,?,?)",
                             (pay_key, itinerary, amount, now.isoformat()))
        self.c.commit()
        return {"credit": cur.lastrowid, "replayed": False}

    def credits(self, itinerary: str) -> int:
        return self.c.execute("select count(*) from processor where "
                              "itinerary=?", (itinerary,)).fetchone()[0]

    def find_credit(self, pay_key: str) -> int | None:
        row = self.c.execute("select n from processor where pay_key=?",
                             (pay_key,)).fetchone()
        return row[0] if row else None

    def notice(self, run_id: str, kind: str, now: datetime) -> None:
        self.c.execute("insert into notices(run_id, kind, at) "
                       "values(?,?,?)", (run_id, kind, now.isoformat()))
        self.c.commit()

    def count(self, sql: str, *args) -> int:
        return self.c.execute(sql, args).fetchone()[0]

    def dump(self, table: str) -> list[tuple]:
        return self.c.execute(f"select * from {table}").fetchall()


def pay_key(permission_id: str, action: str) -> str:
    """Keys derive from the permission (Chapter 2), so a new permission
    means a new key, and a processor cannot tell the two apart."""
    return "KEY-" + short(permission_id, action)


def dumps(x) -> str:
    return json.dumps(x, sort_keys=True)
