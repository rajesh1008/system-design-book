"""Budgets as policy: money limits on effects, in the same enforcer.

Chapter 18's enforcer reserves a worst case against every scope a
call belongs to and refuses when any scope would go over. An effect
budget is the same shape with the effect's amount as the worst case:
vouchers-v1 allows $100 each and $5,000 a day across the fleet, and
the engine adds a traveler's day and the unattended loops' share. The
reservation is made when the engine grants a permission and settled
when the gateway spends it or the permission expires.
"""
from __future__ import annotations

from cost.budget import BudgetStop, Enforcer, Limits

VOUCHER_DAY = Limits(task_usd=None, task_steps=None,
                     traveler_day_usd=200.00, day_usd=5000.00,
                     alert=0.80)
LOOP_SHARE = Limits(task_usd=None, task_steps=None,
                    traveler_day_usd=None, day_usd=2000.00, alert=0.80)


class EffectBudgets:
    def __init__(self):
        self.fleet = Enforcer(VOUCHER_DAY)
        self.loops = Enforcer(LOOP_SHARE)
        self.open: dict[str, list[tuple[Enforcer, int]]] = {}

    def reserve(self, permission_id: str, caller: str, traveler: str,
                day: str, usd: float) -> str | None:
        """Reserve on every scope or none. Returns the refusing scope."""
        held: list[tuple[Enforcer, int]] = []
        try:
            held.append((self.fleet, self.fleet.reserve(
                permission_id, traveler, day, usd)))
            if caller.startswith("loop:"):
                held.append((self.loops, self.loops.reserve(
                    permission_id, "loops", day, usd)))
        except BudgetStop as stop:
            for enf, rid in held:
                enf.settle(rid, 0.0)
            return enf_name(stop) or stop.scope
        self.open[permission_id] = held
        return None

    def settle(self, permission_id: str, spent: bool) -> None:
        for enf, rid in self.open.pop(permission_id, []):
            amount = enf._open[rid][1] if spent else 0.0
            enf.settle(rid, amount)

    def day_spent(self, day: str) -> float:
        return self.fleet.store.row(f"day:{day}")["spent"]


def enf_name(stop: BudgetStop) -> str | None:
    if stop.scope == "day" and stop.limit == LOOP_SHARE.day_usd:
        return "loop-share"
    return None
