"""A design submission: the file a review reads.

A submission is a TOML file with a [design] table, a diagram in the
method grammar (Chapter 5), its loops, its effects, the facts it acts
on, its outcome metric, and the records it links.
"""
from __future__ import annotations

import copy
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DESIGNS = Path(__file__).resolve().parent / "designs"


@dataclass
class Submission:
    design: dict
    diagram: dict
    loops: list = field(default_factory=list)
    effects: list = field(default_factory=list)
    facts: list = field(default_factory=list)
    memory: dict = field(default_factory=dict)
    outcome: dict = field(default_factory=dict)
    records: list = field(default_factory=list)
    conditions: list = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.design.get("name", "?")

    def node(self, nid: str) -> dict | None:
        for n in self.diagram.get("nodes", []):
            if n.get("id") == nid:
                return n
        return None

    def copy(self) -> "Submission":
        return copy.deepcopy(self)


def from_dict(raw: dict) -> Submission:
    return Submission(
        design=raw.get("design", {}),
        diagram=raw.get("diagram", {"nodes": [], "edges": []}),
        loops=raw.get("loops", []),
        effects=raw.get("effects", []),
        facts=raw.get("facts", []),
        memory=raw.get("memory", {}),
        outcome=raw.get("outcome", {}),
        records=raw.get("records", {}).get("ids", []),
        conditions=raw.get("conditions", []),
    )


def load(name_or_path: str | Path) -> Submission:
    p = Path(name_or_path)
    if not p.suffix:
        p = DESIGNS / f"{name_or_path}.toml"
    with open(p, "rb") as fh:
        return from_dict(tomllib.load(fh))


def inject(sub: Submission, fault: str) -> Submission:
    """Return a copy of a submission with one fault injected."""
    s = sub.copy()
    if fault == "self-verify":
        # The acting agent reads back the partner's status and calls
        # that the verification: the reconciler is gone.
        for e in s.effects:
            e["verifier"] = "agent"
        edges = s.diagram["edges"]
        edges[:] = [e for e in edges
                    if e.get("to") != "recon" and e.get("from") != "recon"]
        s.diagram["nodes"] = [n for n in s.diagram["nodes"]
                              if n.get("id") != "recon"]
        edges.append({"from": "partner", "to": "agent", "kind": "data",
                      "label": "status: posted"})
    elif fault == "no-kill-switch":
        for e in s.effects:
            e["kill_tier_one"] = False
    elif fault == "no-stop":
        for lp in s.loops:
            lp["max_steps"] = 0
            lp["done"] = ""
            lp["on_stop"] = ""
    else:
        raise ValueError(f"unknown fault {fault!r}")
    s.design["name"] = f"{s.design['name']}+{fault}"
    return s


def apply_conditions(sub: Submission) -> Submission:
    """Return a copy with the board's recorded conditions applied."""
    s = sub.copy()
    for c in s.conditions:
        if "fact" in c:
            for f in s.facts:
                if f["name"] == c["fact"]:
                    f["max_age_hours"] = c["max_age_hours"]
        if "outcome_owner" in c:
            s.outcome["owner"] = c["outcome_owner"]
    s.design["name"] = f"{s.design['name']}+conditions"
    return s
