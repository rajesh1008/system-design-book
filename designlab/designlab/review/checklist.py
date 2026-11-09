"""The production checklist by plane, executable over a submission.

Sixteen items, four per plane. Each item is a question, a check that
reads the submission, and two flags:

  blocking  the design may not go live while the item fails;
  shape     the fix needs a new box or arrow, not a new value.

The board's verdict rule (board.py) reads the flags: a failing shape
item declines the design, a failing value item changes it.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable

from method.lint import lint_diagram
from org import rights

from .submission import Submission

DATA = Path(__file__).resolve().parent / "data"
PINNED = ("claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5")


def signed_keys(as_of: date) -> dict[str, str]:
    """Decision keys signed on or before a day, with their owner."""
    keys = {d.key: (d.owners[0] if d.owners else "")
            for d in rights.SIGNED}
    with open(DATA / "keys.toml", "rb") as fh:
        extra = tomllib.load(fh).get("keys", [])
    for k in extra:
        if date.fromisoformat(k["signed"]) <= as_of:
            keys[k["key"]] = k["owner"]
    return keys


def _grm(sub: Submission, rule: str) -> list[str]:
    return [f.where + ": " + f.message
            for f in lint_diagram(sub.diagram) if f.rule == rule]


# Each check returns a list of problems; empty means the item passes.

def a1(s):
    bad = [f"{e['name']} skips the gateway" for e in s.effects
           if not e.get("via_gateway")]
    return bad + _grm(s, "GRM-1")


def a2(s):
    out = []
    for lp in s.loops:
        keys = ["max_steps", "max_minutes"]
        if lp.get("model", True):
            keys.append("max_usd")
        miss = [k for k in keys if not lp.get(k)]
        if not lp.get("done"):
            miss.append("done state")
        if not lp.get("on_stop"):
            miss.append("who gets it")
        if miss:
            out.append(f"loop {lp['name']}: no " + ", ".join(miss))
    return out


def a3(s):
    return [f"{e['name']}: retry is a {e.get('retry')}"
            for e in s.effects
            if e.get("retry") != "same key"
            or e.get("idempotency", "none") == "none"]


def a4(s):
    m = s.design.get("model", "")
    return [] if m in PINNED else [f"model {m or 'unnamed'} not pinned"]


def c1(s):
    return [f"{e['name']}: permitted by {e.get('permit') or 'nobody'}"
            for e in s.effects
            if not str(e.get("permit", "")).startswith("bundle:")]


def c2(s):
    return [f"{e['name']}: limits in the {e.get('limits_in')}"
            for e in s.effects if e.get("limits_in") != "policy"]


def c3(s):
    return [f"{e['name']}: no tier-one hold" for e in s.effects
            if not e.get("kill_tier_one")]


def c4(s):
    key = s.design.get("decision_key", "")
    day = date.fromisoformat(s.design["review"])
    owner = signed_keys(day).get(key)
    if not key:
        return ["no decision key named"]
    return [] if owner else [f"{key} not signed by {day.isoformat()}"]


def k1(s):
    out = []
    for f in s.facts:
        if not f.get("source"):
            out.append(f"fact {f['name']}: no source")
        if not f.get("max_age_hours"):
            out.append(f"fact {f['name']}: no age limit")
    return out


def k2(s):
    return [f"fact {f['name']}: stale goes to the agent"
            for f in s.facts if not f.get("stale_to_person")]


def k3(s):
    if s.memory.get("writes") and not s.memory.get("writes_source"):
        return ["memory written without a source"]
    return []


def k4(s):
    return [f"fact {f['name']}: no owner" for f in s.facts
            if not f.get("owner")]


def t1(s):
    out = []
    actors = {e["from"] for e in s.diagram.get("edges", [])
              if e.get("kind") == "effect"}
    for e in s.effects:
        v = e.get("verifier", "")
        n = s.node(v) if v else None
        if not v:
            out.append(f"{e['name']}: no verifier")
        elif v in actors:
            out.append(f"{e['name']}: verified by {v}, which acted")
        elif not n or n.get("kind") != "verifier":
            out.append(f"{e['name']}: {v} is not a verifier")
    return out + [p for p in _grm(s, "GRM-2") if "acted" in p]


def t2(s):
    return [p for p in _grm(s, "GRM-2") if "writes" in p]


def t3(s):
    o = s.outcome
    out = []
    if o.get("counts") != "verified":
        out.append(f"counts {o.get('metric', 'nothing')!r}, "
                   "not verified outcomes")
    if not o.get("owner"):
        out.append("business result has no owner")
    return out


def t4(s):
    from .store import load_store
    store = load_store()
    out = []
    if not s.records:
        return ["no decision record linked"]
    for rid in s.records:
        r = store.get(rid)
        if r is None:
            out.append(f"record {rid} not in the store")
        elif not (r.revisit_date or r.revisit_trigger):
            out.append(f"record {rid}: no revisit")
    return out


@dataclass(frozen=True)
class Item:
    id: str
    plane: str
    question: str
    blocking: bool
    shape: bool
    check: Callable[[Submission], list[str]]


ITEMS: list[Item] = [
    Item("A1", "action", "Does every effect go through the gateway?",
         True, True, a1),
    Item("A2", "action", "Does every loop have a stop condition?",
         True, True, a2),
    Item("A3", "action", "Is a retry the same request (same key)?",
         True, False, a3),
    Item("A4", "action", "Is the model pinned to a listed version?",
         False, False, a4),
    Item("C1", "control", "Is permission granted outside the loop?",
         True, True, c1),
    Item("C2", "control", "Do the limits live in policy?",
         True, False, c2),
    Item("C3", "control", "Can tier one hold every effect?",
         True, False, c3),
    Item("C4", "control", "Is the decision key signed, with an owner?",
         True, False, c4),
    Item("K1", "knowledge", "Has every fact a source and age limit?",
         False, False, k1),
    Item("K2", "knowledge", "Does a stale fact go to a person?",
         False, False, k2),
    Item("K3", "knowledge", "Is every memory write sourced?",
         False, False, k3),
    Item("K4", "knowledge", "Has every fact an owner?",
         False, False, k4),
    Item("T1", "trail", "Does something that did not act verify?",
         True, True, t1),
    Item("T2", "trail", "Does it read a source the actor cannot write?",
         True, True, t2),
    Item("T3", "trail", "Is the verified business result counted?",
         False, False, t3),
    Item("T4", "trail", "Is the decision recorded, with a revisit?",
         False, False, t4),
]


@dataclass(frozen=True)
class Result:
    item: Item
    problems: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.problems


def run(sub: Submission, items: list[Item] | None = None
        ) -> list[Result]:
    return [Result(it, tuple(it.check(sub))) for it in (items or ITEMS)]
