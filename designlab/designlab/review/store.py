"""The record store: every review's record, and the revisit queue.

A record is due when its revisit date has passed or when someone has
marked its trigger as crossed. Ben Carter's Monday on-call review
(Chapter 5) reads the due list.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .record import Record, from_dict, validate

DATA = Path(__file__).resolve().parent / "data"


@dataclass
class Store:
    records: dict

    def get(self, rid: str) -> Record | None:
        return self.records.get(rid)

    def all(self) -> list[Record]:
        return list(self.records.values())

    def revisited(self) -> list[Record]:
        return [r for r in self.all() if r.status == "revisited"]

    def due(self, today: date) -> list[Record]:
        out = []
        for r in self.all():
            if r.status != "active" or not r.revisit_date:
                continue
            if date.fromisoformat(r.revisit_date) <= today:
                out.append(r)
        return sorted(out, key=lambda r: r.revisit_date)

    def invalid(self) -> dict[str, list[str]]:
        return {r.id: p for r in self.all() if (p := validate(r))}


def load_store(path: Path | None = None) -> Store:
    with open(path or DATA / "records.toml", "rb") as fh:
        raw = tomllib.load(fh)
    recs = [from_dict(r) for r in raw.get("records", [])]
    return Store({r.id: r for r in recs})
