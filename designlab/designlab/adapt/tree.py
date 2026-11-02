"""The adaptation decision tree.

A request to adapt a model is walked from the cheapest fix to the
dearest: name the failure, check it is not policy, try the context,
try the tools and contracts, and adapt only a narrow step that the
golden set can measure and that has labels to learn from.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Request:
    ask: str
    failure: str | None = None       # named, with a measured rate
    policy: bool = False             # the fix is a rule, not a skill
    context: str | None = None       # None untried, "fixed", "short"
    tools: str | None = None         # None untried, "fixed", "short", "n/a"
    narrow: bool = False             # one step, one input, one output
    golden: bool = False             # the golden set measures the step
    labels: str | None = None        # "frontier", "approver", or None
    kind: str = "distill"            # or "preference"


@dataclass(frozen=True)
class Verdict:
    node: int
    outcome: str
    why: str


def walk(r: Request) -> Verdict:
    if not r.failure:
        return Verdict(1, "stop", "no failure named or measured")
    if r.policy:
        return Verdict(2, "rule", "the fix is policy; change the rule")
    if r.context is None:
        return Verdict(3, "try context", "context untried")
    if r.context == "fixed":
        return Verdict(3, "context", "fixed by context")
    if r.tools is None:
        return Verdict(4, "try tools", "tools and contracts untried")
    if r.tools == "fixed":
        return Verdict(4, "tools", "fixed by a tool or contract")
    if not (r.narrow and r.golden):
        return Verdict(5, "refuse", "no narrow step the golden set "
                                    "measures")
    if not r.labels:
        return Verdict(6, "collect", "no labels to learn from yet")
    return Verdict(7, "adapt: " + r.kind, f"narrow, measured, labels "
                                          f"from {r.labels}")


# Marcus Bell's request of April 2026, as Hannah Clarke split it.
MARCUS = [
    Request("better refunds", "refund amount corrected on 0.6% of drafts",
            context="short", tools="fixed"),
    Request("sound like us", "tone flagged in 3% of reviews",
            context="fixed"),
    Request("know our policies", "cites a retired fare rule",
            context="fixed"),
    Request("stop asking twice", "asks for the booking ref twice",
            context="short", tools="fixed"),
    Request("classify the change right",
            "small model 4 points short on case packets",
            context="short", tools="n/a", narrow=True, golden=True,
            labels="frontier"),
    Request("refund reasons the desk keeps fixing",
            "approver edits 12% of reasons", context="short",
            tools="fixed", narrow=True, golden=True, labels="approver",
            kind="preference"),
]
