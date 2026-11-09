"""Evidence-chain coverage, computed from the trail.

An effect is covered when all five links are in the record:

    1 decision   a policy decision on the same arguments digest
    2 permit     that decision granted a permission
    3 call       the gateway allowed the call and logged its digest
    4 verify     a verifier record whose source does not read through
                 the server that performed the effect
    5 result     the use case declares a business result and its owner

A use case is covered when every effect it made in the period is.
The measure cannot see a call that never reached the gateway; that is
what conformance test K2 is for.
"""
from __future__ import annotations

from dataclasses import dataclass, field

LINKS = ("decision", "permit", "call", "verify", "result")


def calls_of(lines: list[dict], identity: str) -> list[dict]:
    return [e for e in lines if e.get("event") == "tool_call"
            and e.get("caller") == identity]


def decision_for(lines: list[dict], call: dict) -> dict | None:
    """The latest decision before the call on the same digest."""
    best = None
    for e in lines:
        if e.get("seq", 0) >= call.get("seq", 0):
            break
        if e.get("event") == "policy_decision" and \
                e.get("digest") == call.get("args_digest") and \
                e.get("tool") == call.get("tool"):
            best = e
    return best


@dataclass
class Effect:
    call: str
    tool: str
    links: dict = field(default_factory=dict)

    @property
    def missing(self) -> list[str]:
        return [k for k in LINKS if not self.links.get(k)]


def effects(plane, m: dict, lines: list[dict] | None = None):
    lines = plane.lines() if lines is None else lines
    u = m["use_case"]
    ver = {e["call"]: e for e in lines
           if e.get("event") == "verification"}
    declared = bool(m.get("result", {}).get("measure")
                    and m["result"].get("owner"))
    out = []
    for e in calls_of(lines, u["identity"]):
        if e["verdict"] != "allowed" or \
                plane.kind_of(e["server"], e["tool"]) != "effect":
            continue
        d = decision_for(lines, e)
        v = ver.get(e["call"])
        out.append(Effect(e["call"], e["tool"], {
            "decision": d is not None,
            "permit": bool(d and d.get("verdict") == "permit"
                           and d.get("permission")),
            "call": bool(e.get("args_digest")),
            "verify": bool(v and v["confirmed"]
                           and v["reads_through"] != e["server"]),
            "result": declared}))
    return out


def coverage(plane, m: dict) -> tuple[int, int, list[str]]:
    """(effects with all five links, effects, links missing)."""
    eff = effects(plane, m)
    full = sum(not x.missing for x in eff)
    miss = sorted({k for x in eff for k in x.missing})
    return full, len(eff), miss


def use_case_covered(plane, m: dict) -> bool:
    full, n, _ = coverage(plane, m)
    return n > 0 and full == n
