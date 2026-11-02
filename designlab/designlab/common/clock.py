"""Clocks. Labs use FixedClock so their output is the same on every run."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    """Wall-clock time in UTC."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class FixedClock:
    """Starts at `start` and moves `step_seconds` forward on every read."""

    def __init__(self, start: str = "2026-01-05T09:00:00+00:00",
                 step_seconds: float = 1.0):
        self._t = datetime.fromisoformat(start)
        if self._t.tzinfo is None:
            self._t = self._t.replace(tzinfo=timezone.utc)
        self._step = timedelta(seconds=step_seconds)

    def now(self) -> datetime:
        t = self._t
        self._t = t + self._step
        return t

    def advance(self, seconds: float) -> None:
        self._t += timedelta(seconds=seconds)
