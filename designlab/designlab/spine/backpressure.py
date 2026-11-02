"""Backpressure from people, tools, and budgets.

Four steps: measure the absorb rate, cap pending, slow intake and never
drop, alert on age and on projected drain. `desk` simulates one
approval desk second by second; `admit` combines the three signals.

Pending means on the desk: waiting for a reviewer or being reviewed.
Held means proposed work the spine has not yet turned into a card.
A held item is not dropped; it waits upstream, cheap and unpriced,
and the customer has already been told a person will decide.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from common.rand import seeded


@dataclass
class DeskResult:
    arrived: int
    decided: int
    dropped: int
    peak_pending: int
    peak_held: int
    peak_oldest_s: int          # oldest card on the desk, at its peak
    stale_on_review: int        # cards older than the quote when opened
    last_decision_s: int
    alert_s: int | None
    reserve_from_s: int | None
    timeline: list[tuple[int, int, int, int]] = field(default_factory=list)
    # (minute, pending, held, oldest card age in seconds)


def desk(arrivals: list[int], reviewers: int = 6, review_s: int = 80,
         cap: int | None = 50, quote_ttl_s: int = 900,
         promise_s: int = 3600, reserve: int = 0,
         reserve_delay_s: int = 600, horizon_s: int = 4 * 3600,
         seed: int = 8) -> DeskResult:
    """Simulate one desk.

    arrivals: second at which each approval is proposed.
    cap: most cards on the desk at once; None means no cap.
    reserve: extra reviewers who join reserve_delay_s after the alert.
    A card is prepared (quote fetched) when it is admitted to the desk,
    so its age is measured from admission. Review times vary from
    60 to 100 seconds around the 80-second mean (seeded).
    """
    rng = seeded(seed, "backpressure", "review")
    arrivals = sorted(arrivals)
    held: list[int] = []          # proposal times not yet admitted
    waiting: list[int] = []       # admission times, FIFO
    busy: list[tuple[int, int]] = []  # (finish, admitted) per reviewer
    i = decided = stale = 0
    peak_p = peak_h = peak_age = 0
    last = 0
    alert_s = reserve_s = None
    staff = reviewers
    tl = []
    window: list[int] = []        # decision times, for the absorb rate
    for t in range(horizon_s):
        while i < len(arrivals) and arrivals[i] <= t:
            held.append(arrivals[i])
            i += 1
        done = [f for f, _ in busy if f <= t]
        busy = [b for b in busy if b[0] > t]
        decided += len(done)
        window += done
        if done:
            last = t
        if reserve_s is not None and t == reserve_s:
            staff += reserve
        pending = len(waiting) + len(busy)
        room = len(held) if cap is None else max(0, cap - pending)
        for _ in range(min(room, len(held))):
            held.pop(0)
            waiting.append(t)
        while waiting and len(busy) < staff:
            adm = waiting.pop(0)
            if t - adm > quote_ttl_s:
                stale += 1
            jitter = rng.randint(-20, 20)
            busy.append((t + review_s + jitter, adm))
        pending = len(waiting) + len(busy)
        on_desk = waiting[:1] + [a for _, a in busy]
        oldest = t - min(on_desk) if on_desk else 0
        peak_p = max(peak_p, pending)
        peak_h = max(peak_h, len(held))
        peak_age = max(peak_age, oldest)
        rate = absorb_rate(staff, review_s)
        backlog = pending + len(held)
        if alert_s is None and backlog and backlog / rate > promise_s:
            alert_s = t
            if reserve:
                reserve_s = t + reserve_delay_s
        if t % 60 == 0:
            tl.append((t // 60, pending, len(held), oldest))
        if i == len(arrivals) and not held and not waiting and not busy:
            break
    return DeskResult(len(arrivals), decided, 0, peak_p, peak_h,
                      peak_age, stale, last, alert_s, reserve_s, tl)


def absorb_rate(reviewers: int, review_s: int) -> float:
    """Decisions per second the desk can make."""
    return reviewers / review_s


def measured_rate(decision_times: list[int], now: int,
                  window_s: int = 600) -> float:
    """Decisions per minute over the trailing window, as a dashboard
    would measure it from decision timestamps."""
    n = sum(1 for d in decision_times if now - window_s < d <= now)
    return n * 60 / window_s


@dataclass(frozen=True)
class Signals:
    pending: int            # cards on the approval desk
    cap: int                # most cards the desk may hold
    tool_throttle: float    # share of supplier calls refused, last 5 min
    throttle_limit: float   # share at which the spine slows tool work
    spend: float            # model and tool spend this hour, USD
    budget: float           # the hour's budget, USD


def admit(wanted: int, s: Signals) -> tuple[int, str]:
    """How many new items intake may start, and the tightest signal.

    Each signal can only lower the number. None of them drops work:
    what is not admitted stays held, oldest first.
    """
    n, why = wanted, "open"
    room = max(0, s.cap - s.pending)
    if room < n:
        n, why = room, "approvals at cap"
    if s.tool_throttle >= s.throttle_limit and n > 0:
        n, why = n // 2, "supplier throttling"
    if s.spend >= s.budget:
        n, why = 0, "hourly budget spent"
    return n, why


def cap_for(reviewers: int, review_s: int, target_age_s: int) -> int:
    """The pending cap a desk can honor: absorb rate times the oldest
    age you are willing to show a reviewer. Derive it; do not guess."""
    return math.ceil(absorb_rate(reviewers, review_s) * target_age_s)


def sampled_peak(res: DeskResult, every_min: int = 5) -> int:
    """Peak oldest age as a dashboard sampling every few minutes sees
    it, in seconds."""
    return max((a for m, _, _, a in res.timeline if m % every_min == 0),
               default=0)
