"""The three legs, read from configuration rather than from a diagram.

A session that holds all three of untrusted input, private data, and a
way to send data out can be turned against its own customer by one
injected instruction. The Agents Rule of Two widens the third leg to
any change of state, so a servicing agent with effect tools holds all
three of its properties and needs validation outside the model on every
effect. Each leg here is computed from what the session actually has:
the registry's approved tools, the egress policy, and the reply filter.
"""
from __future__ import annotations

from dataclasses import dataclass

from .controls import REPLY_LINK_HOSTS

INTERNAL = ".lakeshore.internal"
PRIVATE_READS = ("booking_read", "doc_intake")
UNTRUSTED_SURFACES = ("customer chat", "tool results (untagged)")


@dataclass(frozen=True)
class Leg:
    name: str
    present: bool
    evidence: str


def legs(registry, egress) -> list[Leg]:
    tools = {e.tool for e in registry.approved()}
    private = sorted(t for t in PRIVATE_READS if t in tools)
    outside = sorted(h for h, _ in egress.hosts
                     if not h.endswith(INTERNAL))
    reply_out = [h for h in REPLY_LINK_HOSTS
                 if not h.endswith("lakeshore.com")]
    out_ev = ", ".join(outside + reply_out) or \
        "internal hosts only; text replies"
    return [Leg("untrusted input", True, "; ".join(UNTRUSTED_SURFACES)),
            Leg("private data", bool(private), ", ".join(private)),
            Leg("outbound channel", bool(outside or reply_out), out_ev)]


def state_change(registry) -> Leg:
    """The Rule of Two's third property is wider than the trifecta's:
    changing state counts, not only sending data out."""
    eff = sorted(e.tool for e in registry.approved() if e.kind == "effect")
    return Leg("state change", bool(eff),
               f"{len(eff)} effect tools, each through policy")


def verdict(ls: list[Leg]) -> str:
    n = sum(leg.present for leg in ls)
    if n == 3:
        return "all three legs: private data has a way out"
    return f"{n} of 3 legs: no way out for private data"


def rule_of_two(ls: list[Leg], change: Leg) -> str:
    a, b, out = (leg.present for leg in ls)
    if a and b and (out or change.present):
        return "Rule of Two: A, B and C; C must pass validation"
    return "Rule of Two: at most two of A, B, C"
