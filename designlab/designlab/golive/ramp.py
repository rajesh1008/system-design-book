"""The ramp by task type, December 2025 to September 2026.

The agent's share of all changes is the weighted sum of its share of
each task type. A type opens only when it passes the gate (DR-37.1):
verified outcomes at or above 99.0% over 28 days for that type, the
agent desk's backlog at or under 50 at the daily peak, and the type
owner's signature. Refunds stay assisted all year: the agent
proposes and a person approves, so they count as assisted, never as
agent.

The comparison is a ramp by share of traffic, which sends the same
share of every type at once, including types whose escalations the
desk is not yet sized for.
"""
from __future__ import annotations

from dataclasses import dataclass

DAY_CHANGES = 5_750           # 2.1 million a year over 365 days
GATE_VERIFIED = 0.990
GATE_BACKLOG = 50
DESK_SEATS = 2                # agent desk seats for escalations
DESK_SERVICE_MIN = 5.0

TYPES = {
    "R1": ("rebook, same carrier, to $250", 0.30),
    "R2": ("weather rebook, $250 to $400", 0.06),
    "C1": ("cancel to travel credit", 0.14),
    "V1": ("voucher or credit to $100", 0.08),
    "U1": ("upgrade or seat", 0.10),
    "F1": ("refund (assisted only)", 0.32),
}
# Share of a type's tasks that escalate to the agent desk: before the
# type has run its gate, and after.
ESC_UNREADY = {"R1": 0.10, "R2": 0.45, "C1": 0.30, "V1": 0.06,
               "U1": 0.60, "F1": 0.0}
ESC_READY = {"R1": 0.04, "R2": 0.15, "C1": 0.10, "V1": 0.03,
             "U1": 0.30, "F1": 0.0}

# Verified-outcome rate over 28 days for a type that has not yet been
# tuned for (its first shadow month), and after it has.
VERIFIED_UNREADY = {"R1": 0.993, "R2": 0.976, "C1": 0.991,
                    "V1": 0.996, "U1": 0.968}
VERIFIED_READY = {"R1": 0.996, "R2": 0.992, "C1": 0.995,
                  "V1": 0.998, "U1": 0.990}

MONTHS = ("Dec 2025", "Mar 2026", "Apr 2026", "May 2026", "Jun 2026",
          "Jul 2026", "Aug 2026", "Sep 2026")
SHARES = {
    "Dec 2025": {"R1": 0.03},
    "Mar 2026": {"R1": 0.10, "V1": 0.125},
    "Apr 2026": {"R1": 0.05, "V1": 0.125},
    "May 2026": {"R1": 0.15, "V1": 0.1875},
    "Jun 2026": {"R1": 0.30, "V1": 0.375, "C1": 0.143},
    "Jul 2026": {"R1": 0.30, "V1": 0.375, "C1": 0.143},
    "Aug 2026": {"R1": 0.75, "R2": 0.25, "V1": 0.75, "C1": 0.357,
                 "U1": 0.10},
    "Sep 2026": {"R1": 0.85, "R2": 0.75, "V1": 0.875, "C1": 0.429,
                 "U1": 0.10},
}
WHY = {
    "Dec 2025": "pilot: R1 only, chain record live Dec 15",
    "Mar 2026": "phase two: V1 opens at 12.5%",
    "Apr 2026": "R1 halved after the March restart",
    "May 2026": "R1 and V1 back up on 28 clean days",
    "Jun 2026": "GA June 1: C1 opens",
    "Jul 2026": "held: INC-5 failed the verified gate",
    "Aug 2026": "R2 opens Aug 24; U1 at 10%",
    "Sep 2026": "year end: 44%",
}

# Share of the day's changes in each hour, 6 a.m. to 10 p.m.
HOURLY = (0.03, 0.06, 0.10, 0.10, 0.08, 0.07, 0.06, 0.06, 0.06,
          0.06, 0.06, 0.07, 0.07, 0.05, 0.04, 0.03)


def agent_share(month: str) -> float:
    s = SHARES[month]
    return sum(TYPES[k][1] * v for k, v in s.items())


@dataclass(frozen=True)
class Gate:
    kind: str
    verified_28d: float
    backlog_peak: int
    signed: bool

    @property
    def opens(self) -> bool:
        return (self.verified_28d >= GATE_VERIFIED
                and self.backlog_peak <= GATE_BACKLOG and self.signed)

    def why_not(self) -> str:
        if self.verified_28d < GATE_VERIFIED:
            return f"verified {self.verified_28d:.1%} < 99.0%"
        if self.backlog_peak > GATE_BACKLOG:
            return f"desk backlog {self.backlog_peak} > 50"
        if not self.signed:
            return "owner has not signed"
        return "opens"


def backlog_peak(esc_per_day: float, seats: int = DESK_SEATS,
                 service_min: float = DESK_SERVICE_MIN) -> int:
    """Largest end-of-hour backlog at the agent desk over a day."""
    per_hour = seats * 60 / service_min
    q, peak = 0.0, 0.0
    for share in HOURLY:
        q = max(0.0, q + esc_per_day * share - per_hour)
        peak = max(peak, q)
    return round(peak)


def by_type(shares: dict, ready: set | None = None) -> float:
    """Escalations a day for a set of per-type shares."""
    ready = set(shares) if ready is None else ready
    esc = 0.0
    for k, v in shares.items():
        rate = ESC_READY[k] if k in ready else ESC_UNREADY[k]
        esc += DAY_CHANGES * TYPES[k][1] * v * rate
    return esc


def by_traffic(p: float, ready: set) -> dict:
    """The same share p of every autonomous type at once."""
    shares = {k: p for k in TYPES if k != "F1"}
    return {k: v for k, v in shares.items()}, by_type(shares, ready)


def traffic_hold_at(ready: set, step: float = 0.01) -> float:
    """The traffic share at which the desk first passes the gate."""
    p = step
    while p <= 1.0:
        _, esc = by_traffic(p, ready)
        if backlog_peak(esc) > GATE_BACKLOG:
            return round(p, 2)
        p += step
    return 1.0


def ramp_lines() -> list[str]:
    out = [f"{'month':<9}{'R1':>5}{'R2':>5}{'C1':>6}{'V1':>6}{'U1':>5}"
           f"{'agent':>7}  backlog"]
    ready: set = set()
    for m in MONTHS:
        s = SHARES[m]
        ready |= set(s)
        esc = by_type(s, ready)
        cells = "".join(
            f"{s.get(k, 0) * 100:>{w}.0f}" for k, w in
            (("R1", 5), ("R2", 5), ("C1", 6), ("V1", 6), ("U1", 5)))
        out.append(f"{m:<9}{cells}{agent_share(m) * 100:>6.1f}%"
                   f"  {backlog_peak(esc):>5}")
    return out


def traffic_verified(ready: set) -> float:
    """What a traffic-share ramp sees: one verified rate for the
    blend of every autonomous type, weighted by volume."""
    num = den = 0.0
    for k, (_, w) in TYPES.items():
        if k == "F1":
            continue
        v = VERIFIED_READY[k] if k in ready else VERIFIED_UNREADY[k]
        num, den = num + w * v, den + w
    return num / den


def gates(ready: set) -> list[Gate]:
    """Each autonomous type at the June review, gated on its own."""
    out = []
    for k in TYPES:
        if k == "F1":
            continue
        v = VERIFIED_READY[k] if k in ready else VERIFIED_UNREADY[k]
        out.append(Gate(k, v, 0, True))
    return out
