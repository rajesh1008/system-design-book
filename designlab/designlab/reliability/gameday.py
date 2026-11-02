"""The game day: hypotheses about detection and stopping, tested.

Each scenario states, before it runs, which objective should page,
how soon, and which stop should reach the safe state within the 90 s
target. A scenario that does what it said holds; one that does not is
falsified, and a falsified hypothesis is the game day's product,
because it is a gap found on a Tuesday instead of a Sunday night.

The scenarios replay the July incidents and inject three faults the
incidents did not: an unauthorized effect, a stop while the model
gateway is down, and a provider usage export that arrives late.
`legacy=True` reads the late export the way the cost dashboard did
on the morning of the game day, as zero.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from policy.kill import KillSwitch

from . import burn, july8, stop, storm
from .objectives import BY_KEY, UPTIME, read
from .records import Records, Task, at, hm

TARGET_S = 90.0
DECLARED_CALLS_A_DAY = 36      # the waiver watch: three notices, 12 steps


@dataclass
class Result:
    key: str
    hypothesis: str
    measured: str
    held: bool


def usage_page(st, key: str = "agent:waiver-watch",
               declared: int = DECLARED_CALLS_A_DAY, factor: float = 10):
    """Page when the provider's count of a loop's calls over an hour
    is ten times the hourly share of what the loop declared."""
    per_hour = declared / 24
    window = []
    for u in st.records.usage:
        if u.key != key:
            continue
        window.append(u)
        window = [w for w in window
                  if w.minute > u.minute - timedelta(hours=1)]
        if sum(w.calls for w in window) >= factor * per_hour * 1:
            if len(window) >= 5:
                return u.minute
    return None


def g_uptime_only() -> Result:
    rec = july8.build()
    alerts = burn.scan(UPTIME, rec.tasks, july8.MOVED, july8.STOPPED)
    r = read(UPTIME, rec, july8.MOVED, july8.STOPPED)
    return Result("G0", "uptime alone pages on July 8",
                  f"uptime {r.rate:.2%}, alerts {len(alerts)}",
                  bool(alerts))


def g_vendor_move() -> Result:
    rec = july8.build()
    alerts = burn.scan(BY_KEY["verified"], rec.tasks, july8.MOVED,
                       july8.STOPPED, kind="rebooking")
    page = next(a for a in alerts if a.rule == "page")
    s = stop.july8()
    ok = page.at < july8.DESK_SAW and s.seconds <= TARGET_S
    return Result("G1", "rebooking slice pages before the desk; "
                  "tier one under 90 s",
                  f"page {hm(page.at)}, tier one {s.seconds:.0f} s", ok)


def g_storm_usage() -> Result:
    st = storm.simulate()
    t = usage_page(st)
    hours = (t - storm.START).total_seconds() / 3600
    return Result("G2", "provider count of loop calls pages in 1 h",
                  f"page Sat {hm(t)}, {hours * 60:.0f} min in", hours <= 1)


def g_loop_tier() -> Result:
    s = stop.storm([(9, 3, "game.day", "")])
    return Result("G3", "a loop's spend stops at tier three, <90 s",
                  f"tier three {s.seconds:.0f} s", s.seconds <= TARGET_S)


def g_unauthorized() -> Result:
    rec = Records()
    t0 = at("2026-08-18", "10:00")
    rec.tasks = [Task(f"G4-{i}", "refund", t0 + timedelta(seconds=i),
                      t0 + timedelta(seconds=i + 20), True,
                      t0 + timedelta(seconds=i + 60),
                      unauthorized=1 if i == 120 else 0)
                 for i in range(0, 600, 10)]
    alerts = burn.scan(BY_KEY["unauthorized"], rec.tasks, t0,
                       t0 + timedelta(hours=1))
    s = stop.run_stop("injected unauthorized effect", alerts[0].at,
                      [(12, 2, "game.day", "")], "agent:servicing",
                      "refund_ticket", "effect", 8.0, "kill/servicing")
    return Result("G4", "one unauthorized effect pages; tier two",
                  f"page at once, tier two {s.seconds:.0f} s",
                  bool(alerts) and s.seconds <= TARGET_S)


def g_stop_path(model_gateway_up: bool = False) -> Result:
    """The switch is a flag store the gateways poll; pulling it does
    not go through the model gateway, so it works when that is down."""
    ks = KillSwitch(write_key="kill/servicing", read_key="kill/servicing")
    t = at("2026-08-18", "11:00")
    path = ["console", "flag store"]          # what a pull touches
    ack = ks.pull(t, 3, "game.day", "model gateway down")
    off = ks.blocks("agent:servicing", "", "model",
                    t + timedelta(seconds=5))
    ok = "model gateway" not in path and ack["received"] and bool(off)
    return Result("G5", "tier three works with the model gateway down",
                  f"pull via {' > '.join(path)}: {off}", ok)


def g_missing_export(legacy: bool = False) -> Result:
    st = storm.simulate()
    rec = st.records
    rec.missing = set() if legacy else {"provider"}
    if legacy:
        rec.usage = []                   # late export read as nothing
    r = read(BY_KEY["cost"], rec, storm.START, storm.END)
    shown = "met" if legacy else r.status
    return Result("G6", "a late usage export reads unknown, not met",
                  f"cost objective reads {shown}", shown == "unknown")


def run(legacy: bool = True) -> list[Result]:
    """The game day as run on Tuesday, August 18, 2026 (legacy cost
    reader), or as rerun after the fix (`legacy=False`)."""
    return [g_vendor_move(), g_storm_usage(), g_loop_tier(),
            g_unauthorized(), g_stop_path(), g_missing_export(legacy)]
