"""The fare-watch world: watches, a fare process, and the gateway.

Watches are travelers whose booked fare was hit by a schedule change
and who asked to be told when the fare drops. Fares are a seeded
process: each six-hour block a fare either drifts above the booked
fare or, now and then, drops below it; some drops are basic economy
and not comparable to what the traveler bought. The gateway world is
Chapter 26's, with two loop identities added and two tool servers
replaced by ones that answer with these fares and keep a voucher
ledger. Times are Chicago (CDT). Lakeshore figures are illustrative.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from common import seeded
from gateway.core import Caller
from gateway.servers import ToolServer, respond
from gateway.world import World, build

SEED = 28
T0 = datetime.fromisoformat("2026-06-12T00:00:00-05:00")
WATCHES = 1840
ACTOR = "wl-fare-watch"
VERIFIER = "wl-fare-verifier"
ACTOR_TOOLS = frozenset({"offers_search", "voucher_issue",
                         "customer_notify"})
VERIFIER_TOOLS = frozenset({"offers_search"})
# June 16, 2026: a carrier fare sale on many watched routes
SALE_DAYS = {"2026-06-16": 4.0}


@dataclass(frozen=True)
class Watch:
    wid: str
    booking: str
    segment: int
    flight: str
    booked: float           # the fare the traveler paid, USD


def watches(n: int = WATCHES, seed: int = SEED) -> list[Watch]:
    rng = seeded(seed, "watches", str(n))
    out = []
    for i in range(n):
        out.append(Watch(f"W-{1001 + i}",
                         f"LTG-{5300000 + 37 * i:07d}",
                         rng.choice((1, 1, 1, 2)),
                         f"FLT-{905000 + i:06d}",
                         round(rng.uniform(180, 900), 2)))
    return out


def day_of(hour: int) -> str:
    return (T0 + timedelta(hours=hour)).date().isoformat()


def at(hour: int, minute: float = 0.0) -> datetime:
    return T0 + timedelta(hours=hour, minutes=minute)


def _drop(w: Watch, block: int, seed: int):
    """A drop that starts in this block, or None: (fare, cabin,
    blocks it lasts)."""
    rng = seeded(seed, "fare", w.wid, str(block))
    p = 0.012 * SALE_DAYS.get(day_of(block * 6), 1.0)
    if rng.random() >= p:
        return None
    f = w.booked * (1 - rng.uniform(0.03, 0.18))
    cabin = "basic" if rng.random() < 0.3 else "main"
    return round(f, 2), cabin, rng.randint(1, 4)


def fare(w: Watch, hour: int, seed: int = SEED) -> tuple[float, str]:
    """The fare and cabin the fare source quotes for this watch's
    flight in this hour. Constant within a six-hour block; a drop
    lasts one to four blocks, the latest drop winning."""
    block = hour // 6
    for back in range(4):
        d = _drop(w, block - back, seed) if block - back >= 0 else None
        if d is not None and d[2] > back:
            return d[0], d[1]
    rng = seeded(seed, "base", w.wid, str(block))
    return round(w.booked * (1 + rng.uniform(0.0, 0.08)), 2), "main"


class FareServer(ToolServer):
    """The offers server, answering with the fare process. The clock
    tells it which hour it is serving."""

    def __init__(self, base: ToolServer, book: dict, clock):
        super().__init__(base.name,
                         {t: base.describe(t) for t in base.tools()},
                         base.owner)
        self.book, self.clock = book, clock

    def handle(self, tool: str, args: dict) -> dict:
        self.requests += 1
        if tool != "offers_search":
            return respond(tool, args)
        w = self.book[args["booking_ref"]]
        now = self.clock.peek()
        hour = int((now - T0).total_seconds() // 3600)
        f, cabin = fare(w, hour)
        return {"offers": [{"flight_id": w.flight,
                            "fare_usd": f"{f:.2f}", "cabin": cabin}]}


class LedgerServer(ToolServer):
    """The payments server, keeping its own voucher ledger: what was
    issued, as the payments system records it."""

    def __init__(self, base: ToolServer):
        super().__init__(base.name,
                         {t: base.describe(t) for t in base.tools()},
                         base.owner)
        self.vouchers: list[dict] = []

    def handle(self, tool: str, args: dict) -> dict:
        self.requests += 1
        if tool == "voucher_issue":
            self.vouchers.append(dict(args))
        return {"accepted": True, "tool": tool}


class Clock:
    """Chicago time that the loop moves forward explicitly. `now`
    adds a few milliseconds per read, like the gateway's FixedClock."""

    def __init__(self, start: datetime = T0):
        self.t = start

    def now(self) -> datetime:
        t = self.t
        self.t = t + timedelta(milliseconds=5)
        return t

    def peek(self) -> datetime:
        return self.t

    def set(self, t: datetime) -> None:
        if t > self.t:
            self.t = t


@dataclass
class FareWorld:
    w: World
    clock: Clock
    book: dict
    list: list
    ledger: LedgerServer
    offers: FareServer
    notes: dict = field(default_factory=dict)


def fare_world(n: int = WATCHES, actor_tools=ACTOR_TOOLS,
               start: datetime = T0) -> FareWorld:
    w = build(start=start.isoformat())
    clock = Clock(start)
    w.clock = clock
    w.gateway.clock = clock
    w.trail.clock = clock
    ws = watches(n)
    book = {x.booking: x for x in ws}
    offers = FareServer(w.servers["offers"], book, clock)
    ledger = LedgerServer(w.servers["payments"])
    w.servers["offers"] = offers
    w.servers["payments"] = ledger
    w.gateway.servers = w.servers
    # the loop's grant: three tools, a read rate the supplier can
    # carry (Chapter 10: 20 searches a second at the interface)
    w.callers[ACTOR] = Caller("loop:fare-watch", frozenset(actor_tools),
                              rate_per_s=2.0, burst=20)
    w.callers[VERIFIER] = Caller("verifier:fare-watch", VERIFIER_TOOLS,
                                 rate_per_s=2.0, burst=400)
    return FareWorld(w, clock, book, ws, ledger, offers)
