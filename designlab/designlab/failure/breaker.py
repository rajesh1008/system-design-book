"""A circuit breaker for one provider (Section 4).

Closed: calls go through, and the breaker watches a sliding window.
It opens when, among at least `min_calls` calls in the last `window_s`
seconds, a share of `trip_share` or more failed or took `slow_s` or
longer. Open: no effect is attempted; effects are held. After
`open_s` the breaker is half-open and sends a read probe, never an
effect. `probes_to_close` good probes in a row (each faster than
`probe_ok_s`) close it; a bad probe opens it again.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


@dataclass
class Breaker:
    window_s: float = 20.0
    min_calls: int = 6
    slow_s: float = 4.0
    trip_share: float = 0.4
    open_s: float = 15.0
    probe_ok_s: float = 2.0
    probes_to_close: int = 2
    state: str = "closed"
    opened_at: float = 0.0
    good_probes: int = 0
    transitions: list[tuple[float, str]] = field(default_factory=list)
    _window: deque = field(default_factory=deque)

    def _go(self, now: float, state: str) -> None:
        self.state = state
        self.transitions.append((now, state))
        if state == "open":
            self.opened_at, self.good_probes = now, 0
            self._window.clear()

    def allows_effect(self, now: float) -> bool:
        return self.state == "closed"

    def due_probe(self, now: float) -> bool:
        if self.state == "open" and now >= self.opened_at + self.open_s:
            self._go(now, "half-open")
        return self.state == "half-open"

    def record(self, now: float, latency_s: float, ok: bool) -> None:
        if self.state != "closed":
            return
        self._window.append((now, (not ok) or latency_s >= self.slow_s))
        while self._window and self._window[0][0] < now - self.window_s:
            self._window.popleft()
        n = len(self._window)
        bad = sum(1 for _, b in self._window if b)
        if n >= self.min_calls and bad / n >= self.trip_share:
            self._go(now, "open")

    def probe(self, now: float, latency_s: float) -> None:
        if self.state != "half-open":
            return
        if latency_s < self.probe_ok_s:
            self.good_probes += 1
            if self.good_probes >= self.probes_to_close:
                self._go(now, "closed")
        else:
            self._go(now, "open")
