"""The approval queue: every card waiting for a person's decision.

Approvers are counted as seated people, each deciding cards at the
card's service time (two minutes for a refund or a credit, five for
a rebooking above the ceiling). The order decides which card a
free approver takes next:

    newest     the desk tool's default: newest card first, so a
               traveler still on the line in refunds-v3's
               120-second window gets an answer
    oldest     first in, first out
    departure  R-RBK-1: a rebooking whose new flight leaves within
               URGENT_H hours first, earliest departure first; then
               every other card in the desk's default order
    fare       premium fares first, then main, then basic (a Try It)

A rebooking card still waiting MISS_MARGIN minutes before its
departure is a missed departure: the traveler cannot make the new
flight, and a person has to start again.

Approvers do not take one card at a time from the queue. The desk
tool lets each approver claim a page of CLAIM cards in the current
order and work the page top to bottom, which is how a person keeps
context between similar cards. A claimed card is still waiting.

Approval latency is the desk dashboard's number: the median wait of
the cards decided in the last ten minutes. Depth is every card
waiting, claimed or not.
"""
from __future__ import annotations

import heapq
from collections import deque
from dataclasses import dataclass, field
from statistics import median

from .day import Change

MISS_MARGIN = 45
CLAIM = 8
DAY = 24 * 60
FARE_RANK = {"premium": 0, "main": 1, "basic": 2}
ORDERS = ("newest", "oldest", "departure", "fare")


URGENT_H = 6


def deadline(c: Change) -> float:
    if c.kind == "rebook_card" and c.dep is not None:
        return c.dep - MISS_MARGIN
    return c.t + DAY


def key(order: str, c: Change, now: float = 0.0) -> tuple:
    if order == "newest":
        return (-c.t,)
    if order == "oldest":
        return (c.t,)
    if order == "departure":
        if c.kind == "rebook_card" and c.dep - now <= URGENT_H * 60:
            return (0, deadline(c))
        return (1, -c.t)
    if order == "fare":
        return (FARE_RANK[c.fare], c.t)
    raise ValueError(f"unknown order {order}")


@dataclass
class Decided:
    cid: str
    kind: str
    at: float
    wait: float
    amount: float
    by: str               # "person" or "surge"


@dataclass
class Desk:
    order: str = "newest"
    live: dict = field(default_factory=dict)
    heap: list = field(default_factory=list)
    claimed: deque = field(default_factory=deque)
    by_deadline: list = field(default_factory=list)
    decided: list = field(default_factory=list)
    missed: list = field(default_factory=list)
    carry: float = 0.0
    person_minutes: float = 0.0
    now: float = 0.0

    def add(self, c: Change) -> None:
        self.live[c.cid] = c
        heapq.heappush(self.heap, (key(self.order, c, self.now), c.cid))
        if c.kind == "rebook_card":
            heapq.heappush(self.by_deadline, (deadline(c), c.cid))

    @property
    def depth(self) -> int:
        return len(self.live)

    def reorder(self, order: str | None = None) -> None:
        """New order for unclaimed cards; pages already claimed stay.
        Called with no order, it re-keys the current one, which is how
        a rebooking whose flight is now within URGENT_H hours rises."""
        self.order = order or self.order
        mine = set(self.claimed)
        self.heap = [(key(self.order, c, self.now), cid)
                     for cid, c in self.live.items() if cid not in mine]
        heapq.heapify(self.heap)

    def tick(self, now: float) -> None:
        self.now = now
        if self.order == "departure" and now % 10 == 0:
            self.reorder()

    def _top(self) -> Change | None:
        while self.heap:
            _, cid = self.heap[0]
            if cid in self.live:
                return self.live[cid]
            heapq.heappop(self.heap)
        return None

    def remove(self, cid: str) -> Change:
        return self.live.pop(cid)

    def expire(self, now: float) -> int:
        """Rebooking cards past their deadline become misses."""
        n = 0
        while self.by_deadline and self.by_deadline[0][0] <= now:
            _, cid = heapq.heappop(self.by_deadline)
            if cid in self.live:
                self.missed.append(self.remove(cid))
                n += 1
        return n

    def _claim(self, seated: float) -> None:
        while len(self.claimed) < seated * CLAIM:
            c = self._top()
            if c is None:
                return
            heapq.heappop(self.heap)
            self.claimed.append(c.cid)

    def work(self, now: float, seated: float) -> int:
        """One minute of seated approvers working their claimed pages."""
        self._claim(seated)
        self.carry += seated
        n = 0
        while self.claimed:
            cid = self.claimed[0]
            if cid not in self.live:
                self.claimed.popleft()
                continue
            c = self.live[cid]
            if c.service > self.carry:
                break
            self.claimed.popleft()
            self.carry -= c.service
            self.person_minutes += c.service
            self.remove(cid)
            done = now + 1                     # end of the minute
            self.decided.append(Decided(cid, c.kind, done, done - c.t,
                                        c.amount, "person"))
            n += 1
            self._claim(seated)
        if not self.claimed:
            self.carry = min(self.carry, seated)
        return n

    def sweep(self, now: float, eligible, limit: int) -> int:
        """A signed rule re-decides queued cards without a person."""
        hits = [cid for cid, c in self.live.items() if eligible(c)]
        hits.sort(key=lambda cid: self.live[cid].t)
        for cid in hits[:limit]:
            c = self.remove(cid)
            self.decided.append(Decided(cid, c.kind, now, now - c.t,
                                        c.amount, "surge"))
        return min(len(hits), limit)

    def pull(self, kinds) -> list[Change]:
        """Take every queued card of these kinds off the desk."""
        out = [c for c in self.live.values() if c.kind in kinds]
        for c in out:
            self.remove(c.cid)
        return out

    def latency(self, now: float, window: float = 10.0) -> float:
        ws = [d.wait for d in self.decided
              if d.by == "person" and now - window < d.at <= now + 1]
        return median(ws) if ws else 0.0

    def oldest(self, now: float) -> float:
        return max((now - c.t for c in self.live.values()), default=0.0)
