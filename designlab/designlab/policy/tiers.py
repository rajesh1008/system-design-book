"""Risk tiers for effects, from the autonomy table's ceilings.

Chapter 6 scores each task type on reversibility, value at risk, and
whether something other than the actor can verify it, and the scores
set a ceiling. The engine turns the level into a risk tier: low runs
unattended inside limits, medium acts and notifies, high acts only
with a person's approval. A suggest-only task is not an agent action
at all; the engine routes it to a person. Reads are evaluated on
every call but carry no risk tier.
"""
from __future__ import annotations

from dataclasses import dataclass

from planes.autonomy import ceiling, load_autonomy

TIER_OF_LEVEL = {"act_unattended": "low", "act_and_notify": "medium",
                 "act_with_approval": "high", "suggest": "person"}
TOOL_TASK = {"refund_ticket": "refund", "rebook_ticket": "rebook",
             "voucher_issue": "voucher", "hotel_cancel": "hotel_cancel"}


@dataclass(frozen=True)
class Scored:
    action: str
    policy: str
    reversibility: int
    value_at_risk: int
    verifiable: int

    @property
    def ceiling(self) -> str:
        return ceiling(self.reversibility, self.value_at_risk,
                       self.verifiable)


# Two effects the January table did not list, scored the same way.
EXTRA = {
    # a goodwill credit can be voided until the traveler spends it
    "credit_issue": Scored("credit", "credits-v1", 1, 1, 2),
    # a templated notice; a correction notice can follow it
    "customer_notify": Scored("notify", "notify-v1", 1, 2, 2),
}


def tier_table() -> dict[str, tuple[str, str, str]]:
    """tool -> (policy version, level, tier), from the signed table."""
    table = load_autonomy()
    out = {}
    for tool, task in TOOL_TASK.items():
        r = table.row(task)
        out[tool] = (r.policy, r.level, TIER_OF_LEVEL[r.level])
    for tool, s in EXTRA.items():
        out[tool] = (s.policy, s.ceiling, TIER_OF_LEVEL[s.ceiling])
    return out


def tier_of(tool: str, kind: str) -> str:
    if kind == "read":
        return "read"
    if kind == "handoff":
        return "handoff"
    row = tier_table().get(tool)
    return row[2] if row else "unlisted"
