"""The credential inventory and the identity test.

As found on Tuesday, June 16, 2026: one standing service account,
svc-agent-gw, shared by every run, issued November 3, 2025 (the
pilot's credential, widened twice as tools moved behind the gateway,
never narrowed), never rotated, holding read and write on four
systems of record. The identity test is what the release gate runs against the inventory:

  1 nothing a run can present lives longer than 15 minutes
  2 no standing credential with a write scope is held by anything but
    the broker
  3 every key the broker holds was rotated within 30 days
  4 every credential has a named owner
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from common.rand import seeded

RUN_MAX_S = 900
BROKER_ROTATE_DAYS = 30

SCOPES = tuple(f"{s}:{v}" for s in ("bookings", "payments", "profiles",
                                     "ledger") for v in ("read", "write"))
# what each tool exercises on the systems of record
TOOL_SCOPES = {
    "booking_read": ("bookings:read",),
    "rebook_ticket": ("bookings:write",),
    "refund_ticket": ("payments:write", "ledger:write"),
    "credit_issue": ("payments:write", "ledger:write"),
    "voucher_issue": ("payments:write", "ledger:write"),
    "customer_notify": ("profiles:read",),
}


@dataclass(frozen=True)
class Credential:
    name: str
    holder: str            # who can present it
    scopes: tuple
    issued: str            # ISO date
    rotated: str | None
    lifetime_s: float | None   # None: until someone revokes it
    owner: str = ""

    def age_days(self, today: str) -> int:
        last = self.rotated or self.issued
        return (datetime.fromisoformat(today) -
                datetime.fromisoformat(last)).days


AS_FOUND = [Credential("svc-agent-gw", "gateway (every run)", SCOPES,
                       "2025-11-03", None, None, "Agent Platform")]


def usage(days: int = 30, seed: int = 32) -> dict[str, int]:
    """Thirty days of the gateway's calls, mapped to scopes exercised."""
    rng = seeded(seed, "identity", "usage")
    weights = {"booking_read": 40, "customer_notify": 22,
               "rebook_ticket": 9, "refund_ticket": 6,
               "credit_issue": 3, "voucher_issue": 1}
    counts = {s: 0 for s in SCOPES}
    tools = list(weights)
    for _ in range(days):
        for tool in rng.choices(tools, list(weights.values()),
                                k=rng.randint(380, 460)):
            for s in TOOL_SCOPES[tool]:
                counts[s] += 1
    return counts


def review(cred: Credential, used: dict[str, int]) -> dict:
    never = [s for s in cred.scopes if not used.get(s)]
    return {"granted": len(cred.scopes),
            "exercised": len(cred.scopes) - len(never), "never": never}


def identity_test(inventory: list[Credential], today: str) -> list[str]:
    """Empty means pass. Each failure names the credential and rule."""
    fails = []
    for c in inventory:
        writes = [s for s in c.scopes if s.endswith(":write")]
        if c.holder.startswith("run") and (
                c.lifetime_s is None or c.lifetime_s > RUN_MAX_S):
            fails.append(f"{c.name}: rule 1, run credential outlives "
                         "15 minutes")
        long = c.lifetime_s is None or c.lifetime_s > RUN_MAX_S
        if writes and long and c.holder != "broker":
            fails.append(f"{c.name}: rule 2, standing write held by "
                         f"{c.holder}")
        if c.holder == "broker" and \
                c.age_days(today) > BROKER_ROTATE_DAYS:
            fails.append(f"{c.name}: rule 3, broker key "
                         f"{c.age_days(today)} days since rotation")
        if not c.owner:
            fails.append(f"{c.name}: rule 4, no owner")
    return fails


def after_fix(today: str = "2026-06-22") -> list[Credential]:
    """June 22: svc-agent-gw retired; four broker keys; run tokens."""
    keys = [Credential(f"sor-{s}", "broker", (f"{s}:read", f"{s}:write"),
                       "2026-06-19", None, None, "Agent Platform")
            for s in ("bookings", "payments", "profiles", "documents")]
    run = Credential("run token (per run)", "run", ("one itinerary",),
                     today, None, RUN_MAX_S, "control plane")
    return keys + [run]


INJECTED = Credential("svc-batch-refunds", "refund batch job",
                      ("payments:write",), "2026-06-22", None,
                      90 * 86400, "Payments Engineering")
