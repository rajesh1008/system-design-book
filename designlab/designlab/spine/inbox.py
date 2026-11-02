"""The inbox: one consumer applies one message once.

A table with a unique constraint on (consumer, msg_id), written in the
same transaction as the consumer's own state change. A redelivered
message hits the constraint and is acknowledged without a second
change. This protects the consumer's database, not the world outside
it: a call to an airline or a processor needs its own key (Chapter 7).
"""
from __future__ import annotations

import sqlite3


class Inbox:
    def __init__(self, consumer: str, db: sqlite3.Connection | None = None
                 ) -> None:
        self.consumer = consumer
        self.db = db or sqlite3.connect(":memory:")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS inbox (
              consumer TEXT NOT NULL,
              msg_id   TEXT NOT NULL,
              PRIMARY KEY (consumer, msg_id));
            CREATE TABLE IF NOT EXISTS itinerary (
              key TEXT PRIMARY KEY, seq INTEGER NOT NULL,
              body TEXT NOT NULL);
        """)

    def handle(self, msg_id: str, key: str, seq: int, body: str) -> str:
        """Record the message and apply it in one transaction.

        Returns applied, duplicate, or stale. Stale is still recorded,
        so a redelivery of a stale event is a duplicate next time.
        """
        try:
            with self.db:
                self.db.execute("INSERT INTO inbox VALUES (?, ?)",
                                (self.consumer, msg_id))
                cur = self.db.execute(
                    "UPDATE itinerary SET seq = ?, body = ? "
                    "WHERE key = ? AND seq < ?", (seq, body, key, seq))
                if cur.rowcount:
                    return "applied"
                row = self.db.execute(
                    "SELECT seq FROM itinerary WHERE key = ?",
                    (key,)).fetchone()
                if row is None:
                    self.db.execute(
                        "INSERT INTO itinerary VALUES (?, ?, ?)",
                        (key, seq, body))
                    return "applied"
                return "stale"
        except sqlite3.IntegrityError:
            return "duplicate"

    def seq(self, key: str) -> int | None:
        row = self.db.execute("SELECT seq FROM itinerary WHERE key = ?",
                              (key,)).fetchone()
        return row[0] if row else None

    def count(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM inbox").fetchone()[0]
