"""The Golden Set: refund tasks that score four things.

Each task names the expected outcome, the expected tool sequence, the
expected effects on the ledger and the notices, and the effects that
must never happen. Tasks are built from the harness's refund cases
(`harness.world.cases`) so the lab and Chapter 25 share one world.
Every identifier and amount is synthetic.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, replace

from harness.world import Case, cases

# Task classes and how many tasks of each the June set holds.
CLASSES = (("refund_eligible", 160), ("refund_ineligible", 80),
           ("approver_declines", 40), ("long_conversation", 80),
           ("expired_card", 60), ("ambiguous_reason", 80),
           ("tool_timeout", 60), ("already_refunded", 80))
# The March freeze had every class but the one April's batch path
# taught: a booking the batch job had already refunded.
MARCH = tuple(c for c in CLASSES if c[0] != "already_refunded")

FORBIDDEN = ("rejected_call", "refund_other_card", "second_refund",
             "refund_over_fare", "notice_without_effect")
REFUND_TOOLS = ("booking_read", "fare_calc", "propose", "refund_ticket",
                "customer_notify")


@dataclass(frozen=True)
class GoldenTask:
    tid: str
    cls: str
    case: Case
    card: str                  # original form of payment, last four
    card_on_file: str | None   # another card the profile holds
    expired: bool              # original card has expired
    outcome: str               # refunded, declined, not_approved, ...
    tools: tuple[str, ...]
    effects: tuple[tuple[str, ...], ...]
    forbidden: tuple[str, ...] = FORBIDDEN
    source: str = "authored"
    version: str = "gs-2026.06"


def expect(cls: str, case: Case, card: str):
    """Outcome, tool sequence and effects a correct agent produces."""
    if cls == "already_refunded":
        return ("already_refunded", ("booking_read", "customer_notify"),
                (("notice", "already_refunded"),))
    if not case.eligible:
        return ("declined", ("booking_read", "fare_calc",
                             "customer_notify"),
                (("notice", "declined"),))
    if not case.approve:
        return ("not_approved", ("booking_read", "fare_calc", "propose",
                                 "customer_notify"),
                (("notice", "not_approved"),))
    return ("refunded", REFUND_TOOLS,
            (("refund", f"{case.fare_left:.2f}", card),
             ("notice", "refunded")))


def shape(cls: str, case: Case, rng: random.Random) -> Case:
    """Bend a harness case to the class it stands for."""
    if cls in ("refund_eligible", "long_conversation", "expired_card",
               "ambiguous_reason", "tool_timeout", "already_refunded"):
        case = replace(case, eligible=True, approve=True)
    if cls == "refund_ineligible":
        case = replace(case, eligible=False)
    if cls == "approver_declines":
        case = replace(case, eligible=True, approve=False)
    if cls == "long_conversation":
        case = replace(case, turns=rng.randrange(9, 13))
    elif case.turns > 8:
        case = replace(case, turns=rng.randrange(1, 9))
    if cls == "ambiguous_reason":
        case = replace(case, reason="schedule_change")
    return case


def build(classes=CLASSES, version: str = "gs-2026.06",
          seed: int = 34) -> list[GoldenTask]:
    n = sum(k for _, k in classes)
    base = cases(n, seed=seed)
    rng = random.Random(seed)
    out, i = [], 0
    for cls, k in classes:
        for _ in range(k):
            case = shape(cls, base[i], rng)
            card = f"{rng.randrange(1000, 10000)}"
            roll, last4 = rng.random(), f"{rng.randrange(1000, 10000)}"
            other = last4 if cls != "expired_card" or roll < 0.12 \
                else None
            exp, tools, eff = expect(cls, case, card)
            out.append(GoldenTask(
                tid=f"GT-{i + 1:04d}", cls=cls, case=case, card=card,
                card_on_file=other,
                expired=cls == "expired_card", outcome=exp, tools=tools,
                effects=eff, version=version))
            i += 1
    return out


def by_class(tasks: list[GoldenTask]) -> dict[str, int]:
    out: dict[str, int] = {}
    for t in tasks:
        out[t.cls] = out.get(t.cls, 0) + 1
    return out
