"""Capacity for a queue of people: the approval desk in a surge.

Chapter 10 sized the model side of a surge (sessions, slots, the
token limit). This sizes the human side, the part that broke on
September 10, 2026: approvers for an arrival rate and a promised
wait, the time a backlog takes to drain, and the backlog a surge
leaves when the seats arrive later than the cards.

    seats_for(cards_per_h, service_min, promise_min)
    drain_hours(backlog, seats, service_min, inflow_per_h)
    backlog_after(cards_per_h, seats_per_h, hours)
"""
from __future__ import annotations

import math

from .queue import erlang_c


def offered(cards_per_h: float, service_min: float) -> float:
    """Erlangs: approvers busy on average."""
    return cards_per_h * service_min / 60


def p_late(seats: int, cards_per_h: float, service_min: float,
           promise_min: float) -> float:
    """Share of cards that wait longer than the promise, M/M/c."""
    a = offered(cards_per_h, service_min)
    if a >= seats:
        return 1.0
    c = erlang_c(seats, a)
    rate = (seats - a) / service_min          # per minute
    return c * math.exp(-rate * promise_min)


def seats_for(cards_per_h: float, service_min: float,
              promise_min: float, max_late: float = 0.05) -> int:
    """Fewest approvers so at most max_late of cards miss the
    promised wait."""
    s = max(1, math.ceil(offered(cards_per_h, service_min)))
    while p_late(s, cards_per_h, service_min, promise_min) > max_late:
        s += 1
    return s


def drain_hours(backlog: float, seats: float, service_min: float,
                inflow_per_h: float = 0.0) -> float:
    """Hours to empty a backlog with the inflow still arriving."""
    out = seats * 60 / service_min
    if out <= inflow_per_h:
        return math.inf
    return backlog / (out - inflow_per_h)


def backlog_after(cards_per_h: list[float], seats: list[float],
                  service_min: float) -> list[float]:
    """Hour-by-hour backlog: cards in, seats working, carried over."""
    q, out = 0.0, []
    for n, s in zip(cards_per_h, seats):
        q = max(0.0, q + n - s * 60 / service_min)
        out.append(q)
    return out
