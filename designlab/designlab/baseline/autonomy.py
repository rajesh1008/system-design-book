"""The honest automation rate, and the test that guards its definition.

Automated means finished and verified with no person in the loop, where
verified means a record the bot does not write agrees. For an agent that
acts, the record is the system the change landed in. For the 2024
answer-only pilot, it is the contact log: no contact from the customer,
on any channel, in the seven days after the bot closed the session. A
contact handed to a person is never automated. An abandoned contact is
never automated. An answer the customer came back about is not either.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class Definition:
    name: str
    count_handoffs: bool = False
    count_abandons: bool = False
    count_unverified: bool = False
    count_opt_outs: bool = False

    def automated(self, s: dict) -> bool:
        if s["verified"] and not s["reached_person"]:
            return True
        if self.count_unverified and s["bot_said_resolved"]:
            return True
        if self.count_handoffs and s["routed_by_bot"]:
            return True
        if self.count_abandons and s["abandoned"]:
            return True
        return self.count_opt_outs and not s["bot_engaged"]


HONEST = Definition("verified, no person")
VENDOR = Definition("vendor dashboard", count_handoffs=True,
                    count_unverified=True)


def automation_rate(sessions: list[dict], d: Definition) -> float:
    return sum(1 for s in sessions if d.automated(s)) / len(sessions)


def metric_test(sessions: list[dict], d: Definition) -> dict[str, int]:
    """Count counted sessions by the rule they break; empty means pass."""
    broken: Counter[str] = Counter()
    for s in sessions:
        if not d.automated(s):
            continue
        if s["reached_person"]:
            broken["counts a contact a person handled"] += 1
        elif s["abandoned"]:
            broken["counts an abandoned contact"] += 1
        elif not s["verified"]:
            broken["counts an unverified resolution"] += 1
    return dict(broken)


def autonomy_share(changes: list[dict]) -> dict:
    """Shares of all changes by handling path (the scoreboard split)."""
    n = len(changes)
    paths = ("agent", "assisted", "self-service", "person")
    return {p: sum(1 for c in changes if c["handled_by"] == p) / n
            for p in paths}
