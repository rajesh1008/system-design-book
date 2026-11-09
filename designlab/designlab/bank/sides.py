"""Read a control-round note from both sides of the table (Ch 47).

The interviewer listens for six things (data/control-round.toml). The
checker reports, per candidate, which were heard and at what minute,
which never were, and whether the candidate ever put permission
outside the model: the line a debrief turns on.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).with_name("data") / "control-round.toml"


@dataclass
class Heard:
    candidate: str
    first: dict[str, int]
    missing: list[str]
    circled: list[tuple[int, str]]
    probes: list[tuple[int, str]]

    @property
    def named_policy(self) -> bool:
        return "permission" in self.first


def load(path: Path = DATA) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def hear(note: dict, listen: dict[str, str]) -> Heard:
    first: dict[str, int] = {}
    circled, probes = [], []
    for line in note["said"]:
        for item in line.get("shows", []):
            if item not in listen:
                raise ValueError(f"{note['id']}: unknown item {item}")
            first.setdefault(item, line["at"])
        if line.get("circled"):
            circled.append((line["at"], line["text"]))
        if line.get("probe"):
            probes.append((line["at"], line["text"]))
    missing = [k for k in listen if k not in first]
    return Heard(note["id"], first, missing, circled, probes)


def read(path: Path = DATA) -> tuple[dict, list[Heard]]:
    data = load(path)
    return data, [hear(c, data["listen"]) for c in data["candidate"]]
