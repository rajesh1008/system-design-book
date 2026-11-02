"""The four routed steps and their contracts.

change-intent is Chapter 13's contract, loaded from the models package
unchanged; the other three are this chapter's, in `contracts/`, with
golden sets in `golden/`. The policy file says which risk class each
step is in, which tier that class may not go below, and which
candidates the gate measures.
"""
from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path

from models.contract import ModelContract, load_contract, load_contracts
from models.runner import golden_cases

from .budget import Candidate

HERE = Path(__file__).resolve().parent
POLICY = HERE / "policy.toml"


@dataclass(frozen=True)
class Step:
    name: str
    kind: str                     # read, classify, judge
    risk: str                     # low, medium, high
    floor: str                    # lowest tier the risk class allows
    contract: ModelContract
    candidates: tuple[Candidate, ...]
    cascade: tuple[str, str] | None = None   # (first, then)
    measure: str = "all"                   # or "ladder"

    def cases(self) -> list[dict]:
        if self.contract.golden == "change-intent.jsonl":
            return golden_cases(self.contract)      # Chapter 13's set
        path = HERE / "golden" / self.contract.golden
        return [json.loads(x) for x in path.read_text().splitlines() if x]


def policy(path: Path = POLICY) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


def load_steps(path: Path = POLICY) -> dict[str, Step]:
    pol = policy(path)
    ch13 = load_contracts()
    out = {}
    for name, d in pol["steps"].items():
        c = ch13[name] if d["contract"] == "models" else \
            load_contract(HERE / "contracts" / f"{name}.toml")
        cas = d.get("cascade")
        out[name] = Step(name, d["kind"], d["risk"],
                         pol["floors"][d["risk"]], c,
                         tuple(Candidate.parse(x) for x in d["candidates"]),
                         tuple(cas) if cas else None,
                         d.get("measure", "all"))
    return out


def facts_for_golden() -> dict[str, dict]:
    """Facts Lakeshore's booking record would hold for the change-intent
    golden cases: the reference and whether a carrier event exists."""
    path = HERE / "golden" / "change-intent-facts.json"
    facts = json.loads(path.read_text())
    for case in load_steps()["change-intent"].cases():
        facts[case["id"]]["ref"] = case["expect"]["itinerary_ref"]
    return facts
