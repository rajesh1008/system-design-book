"""Approval gates: a person decides, bound to exactly what will run.

The engine files a card when a rule needs approval. The card is
rendered from the arguments the gateway holds, never from the agent's
summary, and carries their digest. A decision counts only when:

  the approver is a named person, not the agent and not the requester
  the approver's role limit covers the amount (Chapter 4 roles)
  the digest the approver saw is the digest that will run
  the card is still open and inside its validity window

Refunds wait synchronously for 120 seconds, then go to the approvals
queue with a 60-minute promise (autonomy table, January 2026). An
approval is valid for 30 minutes; after that the agent must ask again.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

ROLE_LIMIT_USD = {"desk agent": 750.00, "team lead": 5000.00}
SYNC_S = 120
PROMISE_MIN = 60
VALID_MIN = 30


@dataclass
class Approver:
    name: str
    role: str
    principal: str     # the identity the approval tool authenticates


@dataclass
class Card:
    card_id: str
    tool: str
    digest: str
    lines: list[str]          # what the approver reads
    amount_usd: float
    requester: str            # the identity that proposed the effect
    filed_at: datetime
    rule: str
    state: str = "open"       # open, approved, refused, expired
    approver: str = ""
    decided_at: datetime | None = None
    log: list[str] = field(default_factory=list)

    @property
    def sync_until(self) -> datetime:
        return self.filed_at + timedelta(seconds=SYNC_S)

    @property
    def promise_by(self) -> datetime:
        return self.sync_until + timedelta(minutes=PROMISE_MIN)

    def valid(self, now: datetime) -> bool:
        return (self.state == "approved" and self.decided_at is not None
                and now - self.decided_at <= timedelta(minutes=VALID_MIN))


def render(tool: str, args: dict) -> list[str]:
    """The card shows the arguments that will run, field by field."""
    return [f"{tool}"] + [f"  {k}: {args[k]}" for k in sorted(args)]


class ApprovalGate:
    def __init__(self, clock):
        self.clock = clock
        self.cards: dict[str, Card] = {}
        self.n = 0

    def file(self, tool: str, args: dict, digest: str, requester: str,
             rule: str) -> Card:
        for c in self.cards.values():
            if c.digest == digest and c.state == "open":
                return c
        self.n += 1
        c = Card(f"ap-{self.n:04d}", tool, digest, render(tool, args),
                 float(args.get("amount_usd", "0") or 0), requester,
                 self.clock.now(), rule)
        self.cards[c.card_id] = c
        return c

    def decide(self, card_id: str, who: Approver, seen_digest: str,
               approve: bool = True) -> str:
        """Returns 'approved', 'refused', or the reason it did not count."""
        c = self.cards[card_id]
        now = self.clock.now()
        if c.state != "open":
            return why(c, f"card_{c.state}")
        if who.principal.startswith("agent:") or who.principal == \
                c.requester:
            return why(c, "approver_is_requester")
        limit = ROLE_LIMIT_USD.get(who.role)
        if limit is None or c.amount_usd > limit:
            return why(c, "over_role_limit")
        if seen_digest != c.digest:
            return why(c, "digest_mismatch")
        c.state = "approved" if approve else "refused"
        c.approver, c.decided_at = who.name, now
        c.log.append(f"{now.isoformat(timespec='seconds')} {c.state} "
                     f"by {who.name}")
        return c.state

    def approved_for(self, digest: str, now: datetime) -> Card | None:
        for c in self.cards.values():
            if c.digest != digest:
                continue
            if c.state == "approved" and not c.valid(now):
                c.state = "expired"
            if c.valid(now):
                return c
        return None

    def spend(self, card: Card) -> None:
        card.state = "spent"


def why(c: Card, reason: str) -> str:
    c.log.append(reason)
    return reason
