"""The run store: checkpoints, the step journal, and durable timers.

One SQLite file stands in for the PostgreSQL schema that sits beside
the Effect Ledger. Every write commits at a commit point the engine
chooses, so a kill between two writes leaves exactly what a real
crash would leave.

Checkpoint schema 2 holds the pending approval, permission, and keys.
Schema 1 is what the February 2026 checkpointer saved: position and
messages only. Resume reads both and refuses to act on a schema 1
checkpoint until the permission has been re-read.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime

SCHEMA_VERSION = 2

DDL = """
create table if not exists checkpoints(
  run_id text, version integer, schema integer, body text,
  primary key(run_id, version));
create table if not exists journal(
  run_id text, seq integer, step text, kind text, step_key text,
  status text, output text, at text, primary key(run_id, seq, status));
create table if not exists timers(
  run_id text, name text, fire_at text, state text,
  primary key(run_id, name));
"""

PENDING = ("request_id", "permission_id", "keys")


class RunStore:
    def __init__(self, conn: sqlite3.Connection):
        self.c = conn
        self.c.executescript(DDL)
        self.c.commit()

    # ------------------------------------------------------ checkpoints
    def save(self, run_id: str, body: dict, schema: int = SCHEMA_VERSION,
             commit: bool = True) -> int:
        row = self.c.execute("select max(version) from checkpoints "
                             "where run_id=?", (run_id,)).fetchone()
        v = (row[0] or 0) + 1
        self.c.execute("insert into checkpoints values(?,?,?,?)",
                       (run_id, v, schema, json.dumps(body, sort_keys=True)))
        if commit:
            self.c.commit()
        return v

    def latest(self, run_id: str) -> tuple[int, dict] | None:
        row = self.c.execute("select schema, body from checkpoints where "
                             "run_id=? order by version desc limit 1",
                             (run_id,)).fetchone()
        return (row[0], json.loads(row[1])) if row else None

    def strip_pending(self, run_id: str) -> None:
        """Lab injection: rewrite the latest checkpoint as schema 1."""
        schema, body = self.latest(run_id)
        for k in PENDING:
            body.pop(k, None)
        self.save(run_id, body, schema=1)

    # ---------------------------------------------------------- journal
    def begin(self, run_id, seq, step, kind, step_key, at: datetime):
        self.c.execute("insert or ignore into journal values"
                       "(?,?,?,?,?,?,?,?)",
                       (run_id, seq, step, kind, step_key, "begun", None,
                        at.isoformat()))
        self.c.commit()

    def done(self, run_id, seq, step, kind, step_key, output,
             at: datetime, commit: bool = True):
        self.c.execute("insert or replace into journal values"
                       "(?,?,?,?,?,?,?,?)",
                       (run_id, seq, step, kind, step_key, "done",
                        json.dumps(output, sort_keys=True),
                        at.isoformat()))
        if commit:
            self.c.commit()

    def entries(self, run_id: str) -> list[dict]:
        rows = self.c.execute("select seq, step, kind, step_key, status, "
                              "output from journal where run_id=? "
                              "order by seq, status desc", (run_id,))
        out = []
        for seq, step, kind, key, status, output in rows:
            out.append({"seq": seq, "step": step, "kind": kind,
                        "key": key, "status": status,
                        "output": json.loads(output) if output else None})
        return out

    def result(self, run_id: str, seq: int):
        row = self.c.execute("select output from journal where run_id=? "
                             "and seq=? and status='done'",
                             (run_id, seq)).fetchone()
        return json.loads(row[0]) if row else None

    def begun(self, run_id: str, seq: int) -> bool:
        return self.c.execute("select 1 from journal where run_id=? and "
                              "seq=? and status='begun'",
                              (run_id, seq)).fetchone() is not None

    def run_ids(self) -> list[str]:
        return [r[0] for r in self.c.execute(
            "select distinct run_id from journal order by run_id")]

    # ----------------------------------------------------------- timers
    def set_timer(self, run_id: str, name: str, fire_at: datetime):
        self.c.execute("insert or ignore into timers values(?,?,?,?)",
                       (run_id, name, fire_at.isoformat(), "set"))
        self.c.commit()

    def cancel_timers(self, run_id: str):
        self.c.execute("update timers set state='cancelled' where "
                       "run_id=? and state='set'", (run_id,))
        self.c.commit()

    def due(self, now: datetime, run_id: str | None = None) -> list[tuple]:
        q = "select run_id, name, fire_at from timers where state='set'"
        rows = self.c.execute(q).fetchall()
        return sorted((r for r in rows
                       if datetime.fromisoformat(r[2]) <= now
                       and (run_id is None or r[0] == run_id)),
                      key=lambda r: r[2])

    def fire(self, run_id: str, name: str) -> bool:
        """Mark fired; False if it already was (a second sweeper)."""
        cur = self.c.execute("update timers set state='fired' where "
                             "run_id=? and name=? and state='set'",
                             (run_id, name))
        self.c.commit()
        return cur.rowcount == 1

    def open_timers(self) -> list[tuple]:
        return self.c.execute("select run_id, name, fire_at from timers "
                              "where state='set' order by fire_at"
                              ).fetchall()
