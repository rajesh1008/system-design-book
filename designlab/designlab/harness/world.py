"""A refund world for the loop labs: cases, a processor behind a
gateway, and a reconciler that did not act.

Everything is seeded, so every run of the lab prints the same numbers.
Amounts are US dollars as Decimal; only fare_calc produces one.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from decimal import Decimal

REASONS = ("schedule_change", "carrier_canceled", "duplicate_charge",
           "changed_plans", "medical", "other")
# Customer turns before the agent starts; most cases are short.
TURN_WEIGHTS = (30, 22, 14, 9, 6, 5, 4, 3, 3, 2, 1, 1)


@dataclass(frozen=True)
class Case:
    cid: str
    booking_ref: str
    ticket: str
    fare_left: Decimal
    eligible: bool
    reason: str
    turns: int            # customer turns before the first step
    approve: bool         # what the person at the permit will decide


def cases(n: int = 1000, seed: int = 25) -> list[Case]:
    rng = random.Random(seed)
    out = []
    for i in range(n):
        eligible = rng.random() < 0.8
        out.append(Case(
            cid=f"R-{i + 1:04d}",
            booking_ref=f"LTG-{rng.randrange(10**6, 10**7):07d}",
            ticket=f"TKT-{rng.randrange(10**4, 10**5):05d}",
            fare_left=Decimal(rng.randrange(8000, 64000)) / 100,
            eligible=eligible,
            reason=rng.choice(REASONS),
            turns=rng.choices(range(1, 13), weights=TURN_WEIGHTS)[0],
            approve=rng.random() < 0.95))
    return out


class ToolTimeout(RuntimeError):
    pass


@dataclass
class World:
    """The processor's ledger and the faults a test injects.

    `faults` maps a tool name to how many of its next calls time out.
    """
    refunds: dict[str, Decimal] = field(default_factory=dict)
    notices: list[tuple[str, str]] = field(default_factory=list)
    faults: dict[str, int] = field(default_factory=dict)

    def _maybe_fail(self, tool: str) -> None:
        if self.faults.get(tool, 0) > 0:
            self.faults[tool] -= 1
            raise ToolTimeout(tool)

    def fare_calc(self, case: Case) -> Decimal:
        self._maybe_fail("fare_calc")
        return case.fare_left if case.eligible else Decimal("0.00")

    def refund(self, case: Case, amount: Decimal, permit: str | None,
               key: str) -> str:
        """The gateway in front of the processor."""
        self._maybe_fail("refund_ticket")
        if permit is None:
            return "refused: no permission"
        if amount > case.fare_left:
            return "refused: over refundable fare"
        if key in self.refunds:
            return "duplicate: no new effect"
        self.refunds[key] = amount
        return "ok"

    def reconcile(self, case: Case) -> Decimal:
        """What the processor holds for this case, read by a component
        that took no part in the run."""
        return sum((a for k, a in self.refunds.items()
                    if k.startswith(case.cid)), Decimal("0.00"))
