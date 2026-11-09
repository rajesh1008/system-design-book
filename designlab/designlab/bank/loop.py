"""Build an interview loop from the bank (Chapter 47).

A loop is a list of rounds from data/loop.toml for one role. For each
round the builder draws questions from the indexed bank: the round's
tag, at the role's tier or one above (the Chapter 46 ladder asks one
rung up; a round may fix its own tier, as the phone screen does), one question per 15 minutes beyond the first 15, ordered by
a seeded hash so a loop is reproducible and two candidates can be
given different, comparable questions.
"""
from __future__ import annotations

import hashlib
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .taxonomy import TIER_LEVEL

DATA = Path(__file__).with_name("data") / "loop.toml"
TIER_ORDER = list(TIER_LEVEL)


@dataclass
class Round:
    tag: str
    minutes: int
    who: str
    evidence: str
    probe: str
    writes: str
    tier: str = ""


@dataclass
class Planned:
    round: Round
    pool: int
    questions: list[str]


def config(path: Path = DATA) -> dict:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    rounds = {r["tag"]: Round(**r) for r in data["round"]}
    roles = {r["id"]: r for r in data["role"]}
    return {"rounds": rounds, "roles": roles}


def tiers_for(tier: str) -> tuple[str, ...]:
    i = TIER_ORDER.index(tier)
    return tuple(TIER_ORDER[i:i + 2])


def per_round(minutes: int) -> int:
    return max(1, (minutes - 15) // 15)


def _key(qid: str, seed: str) -> str:
    return hashlib.sha256(f"{seed}:{qid}".encode()).hexdigest()


def plan(rows: list[dict], tags: list[str], tier: str, seed: str = "1",
         rounds: dict[str, Round] | None = None,
         minutes: dict[str, int] | None = None) -> list[Planned]:
    rounds = rounds or config()["rounds"]
    out = []
    for tag in tags:
        rd = rounds[tag]
        allowed = tiers_for(rd.tier or tier)
        if minutes and tag in minutes:
            rd = Round(**{**rd.__dict__, "minutes": minutes[tag]})
        pool = [r for r in rows
                if r["loop_round"] == tag and r["level"] in allowed]
        pool.sort(key=lambda r: _key(r["qid"], seed))
        picks = [r["qid"] for r in pool[:per_round(rd.minutes)]]
        out.append(Planned(rd, len(pool), picks))
    return out


def fit(rows: list[dict], budget: int, tier: str,
        tags: list[str], seed: str = "1") -> list[Planned]:
    """Split a time budget evenly over the named rounds."""
    each = budget // len(tags)
    return plan(rows, tags, tier, seed,
                minutes={t: each for t in tags})


def total(planned: list[Planned]) -> int:
    return sum(p.round.minutes for p in planned)
