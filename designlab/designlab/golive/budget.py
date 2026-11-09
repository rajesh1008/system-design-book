"""The fleet-day model budget under load.

Chapter 18 set three scopes for the servicing agent: the task, the
traveler's day, and the fleet's day. At 80% of the fleet day the
enforcer pages the on-call engineer; at 100% the intake gate sends
new conversations to people, and only the CTO, or someone she
delegates to, can release more. The limit had been raised with the
ramp: on September 10 it stood at FLEET_DAY_USD, sized at one and a
half times the busiest day of August.

A storm conversation costs more than an ordinary one because the
traveler's first choice is often gone and the agent searches again:
TASK_USD is the mean the lab charges per agent task on the day, and
CALM_TASK_USD is the ordinary mean. Spend before 6:00 a.m. is
NIGHT_USD. Rule-based fan-out cards make no model call and cost
nothing here.

The voucher day ($5,000, Chapter 31) is a second budget tested the
same morning.
"""
from __future__ import annotations

from dataclasses import dataclass, field

FLEET_DAY_USD = 600.00
PAGE_AT = 0.80
NIGHT_USD = 31.40
CALM_TASK_USD = 0.052
TASK_USD = 0.073
VOUCHER_DAY_USD = 5_000.00


@dataclass
class FleetDay:
    limit: float = FLEET_DAY_USD
    spent: float = NIGHT_USD
    paged_at: float | None = None
    spent_at: float | None = None
    releases: list = field(default_factory=list)
    refused: int = 0

    def admit(self, now: float, usd: float) -> bool:
        if self.spent + usd > self.limit:
            if self.spent_at is None:
                self.spent_at = now
            self.refused += 1
            return False
        self.spent += usd
        if self.paged_at is None and self.spent >= PAGE_AT * self.limit:
            self.paged_at = now
        return True

    def release(self, now: float, usd: float, by: str) -> None:
        self.limit += usd
        self.releases.append((now, usd, by))


@dataclass
class VoucherDay:
    limit: float = VOUCHER_DAY_USD
    spent: float = 0.0
    spent_at: float | None = None
    refused: int = 0

    def take(self, now: float, usd: float) -> bool:
        if self.spent + usd > self.limit:
            if self.spent_at is None:
                self.spent_at = now
            self.refused += 1
            return False
        self.spent += usd
        return True
