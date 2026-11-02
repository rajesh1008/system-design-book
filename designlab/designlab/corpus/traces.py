"""Lakeshore pilot traces for the capacity model (Chapter 10).

A separate generator from corpus v0 and ops-v1, so neither digest
moves. It covers the 90 days from December 1, 2025, to February 28,
2026: every session the pilot's front door opened, with the timing of
every step inside it. Times are America/Chicago (-06:00 in this
window). Every record is invented; the figures are illustrative.

    from corpus.traces import generate_traces
    sessions = generate_traces(2026)

A session is one conversation. A change session holds one task: the
agent's work on a rebook, refund, cancel, or credit. A follow-up
session answers a question about a change already made. Each step is
one model call, which may ask for one tool call.

Two waits are drawn for every model call, so replays are exact:
`wait_shared` is the rate-limit wait the pilot actually had on the
account it shared with the contact center's call-summary tool, and
`wait_own` is the wait it would have had on its own limit.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from common.rand import DEFAULT_SEED, seeded

TRACES_VERSION = "traces-v1"
CT = ZoneInfo("America/Chicago")
START = datetime(2025, 12, 1, 0, 0, tzinfo=CT)
DAYS = 90
SESSIONS_PER_DAY = 238          # about 2% of contacts about a change
CHANGE_SHARE = 0.484            # 2.10M changes of 4.34M contacts
SURGE = 2.69                    # Monday 8 to 10 a.m. against the mean

# Relative arrivals by hour of day (Central time), and by weekday.
HOUR_W = [0.15, 0.10, 0.08, 0.08, 0.10, 0.25, 0.60, 1.10, 1.75,
          1.80, 1.60, 1.45, 1.35, 1.35, 1.30, 1.25, 1.20, 1.10,
          1.00, 0.90, 0.80, 0.65, 0.45, 0.30]
DAY_W = [1.30, 1.05, 1.00, 1.00, 1.05, 0.75, 0.85]   # Mon..Sun

KINDS = (("rebook", 0.42), ("refund", 0.33), ("cancel", 0.15),
         ("credit", 0.10))
# tool: (share of tool calls, median seconds, log sigma)
TOOLS = {
    "search_flights": (0.38, 2.12, 0.55),
    "get_booking": (0.24, 0.22, 0.40),
    "fare_rules": (0.16, 0.30, 0.40),
    "hotel_lookup": (0.08, 0.90, 0.50),
    "effect": (0.14, 1.92, 0.50),
}
TOOL_TIMEOUT_S = 8.0
MODEL_TIMEOUT_S = 10.0


@dataclass
class Step:
    model_s: list[float]        # accepted model calls (1 + errors)
    wait_shared: float          # rate-limit wait, shared account
    wait_own: float             # rate-limit wait, own limit
    rejected_shared: int        # 429s on the shared account
    rejected_own: int
    error_s: float              # time lost to model timeouts
    tool: str                   # "" when the step calls no tool
    tool_s: list[float]         # tool attempts (timeouts included)
    gate_s: list[float]         # gateway plus policy, per attempt
    trail_s: float
    loop_s: float
    tokens_in: int
    tokens_out: int
    repeat: bool                # a re-search the task did not need


@dataclass
class Session:
    sid: str
    started: str                # ISO 8601 with offset
    kind: str                   # change kind, or "follow-up"
    hour_weight: float          # arrival weight of the hour (0..1)
    knowledge_s: float
    steps: list[Step] = field(default_factory=list)
    need: int = 0               # steps the task needed
    approval_s: float = 0.0     # synchronous wait on a person
    customer_s: float = 0.0     # time the customer spent typing
    idle_s: float = 300.0       # idle timeout before close

    @property
    def is_task(self) -> bool:
        return self.kind != "follow-up"


def _weights() -> list[list[float]]:
    """Weekly grid [day][hour], Monday 8 and 9 a.m. set so the
    two-hour surge runs SURGE times the mean hour."""
    w = [[DAY_W[d] * HOUR_W[h] for h in range(24)] for d in range(7)]
    rest = sum(sum(r) for r in w) - w[0][8] - w[0][9]
    x = SURGE * rest / (168 - 2 * SURGE)
    w[0][8] = w[0][9] = x
    mean = sum(sum(r) for r in w) / 168
    return [[v / mean for v in r] for r in w]


def _poisson(rng, lam: float) -> int:
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def _ln(rng, median: float, sigma: float) -> float:
    return median * math.exp(rng.gauss(0.0, sigma))


def _wait(rng, p: float, lo: float, hi: float) -> tuple[float, int]:
    total, n = 0.0, 0
    while rng.random() < p and n < 4:
        total += rng.uniform(lo, hi)
        n += 1
    return total, n


def _pick(rng, table) -> str:
    r, acc = rng.random(), 0.0
    for name, share in table:
        acc += share
        if r < acc:
            return name
    return table[-1][0]


def _step(rng, i: int, hw: float, tool: str, repeat: bool,
          base_in: int, per_step: int) -> Step:
    # Rate limits: the shared account was contended in busy hours,
    # when the call-summary tool's load followed phone volume.
    p_shared = 0.12 * min(1.0, hw / 2.6) ** 2
    ws, ns = _wait(rng, p_shared, 2.0, 8.5)
    wo, no = _wait(rng, 0.002, 1.0, 2.0)
    load = 1.0 + 0.08 * min(1.0, hw / 2.6)
    calls, err = [], 0.0
    while True:
        lat = _ln(rng, 0.85 + 0.012 * i, 0.42) * load
        if rng.random() < 0.005:
            err += MODEL_TIMEOUT_S
            continue
        calls.append(round(lat, 3))
        break
    tool_s, gate_s = [], []
    if tool:
        _, med, sig = TOOLS[tool]
        for _attempt in range(3):
            gate_s.append(round(_ln(rng, 0.0042, 0.30), 4))
            t = _ln(rng, med, sig)
            if t > TOOL_TIMEOUT_S:
                tool_s.append(TOOL_TIMEOUT_S)
                continue
            tool_s.append(round(t, 3))
            break
    return Step(
        model_s=calls, wait_shared=round(ws, 3), wait_own=round(wo, 3),
        rejected_shared=ns, rejected_own=no, error_s=err, tool=tool,
        tool_s=tool_s, gate_s=gate_s,
        trail_s=round(_ln(rng, 0.005, 0.4), 4),
        loop_s=round(_ln(rng, 0.012, 0.3), 4),
        tokens_in=int(base_in + per_step * i + rng.randint(-300, 300)),
        tokens_out=int(_ln(rng, 160, 0.4)), repeat=repeat)


TOOL_TABLE = [(k, v[0]) for k, v in TOOLS.items()]


def _task(rng, s: Session) -> None:
    steps = max(2, round(_ln(rng, 7.37, 0.58)))
    share = 0.0 if rng.random() < 0.50 else rng.uniform(0.15, 0.50)
    need = max(2, steps - round(steps * share))
    s.need = need
    for i in range(steps):
        last = i == steps - 1
        repeat = need - 1 <= i < steps - 1
        if repeat:
            tool = "search_flights"
        elif last or rng.random() > 0.70:
            tool = ""
        else:
            tool = _pick(rng, TOOL_TABLE)
        s.steps.append(_step(rng, i, s.hour_weight, tool, repeat,
                             3400, 620))
    if s.kind == "refund":
        s.approval_s = round(min(120.0, _ln(rng, 61.0, 0.5)), 1)
    s.customer_s = round(_ln(rng, 430.0, 0.6), 1)


def _follow_up(rng, s: Session) -> None:
    n = 1 + (rng.random() < 0.7) + (rng.random() < 0.2)
    for i in range(n):
        tool = "get_booking" if i == 0 else ""
        s.steps.append(_step(rng, i, s.hour_weight, tool, False,
                             3000, 500))
    s.need = n
    s.customer_s = round(_ln(rng, 330.0, 0.6), 1)


def generate_traces(seed: int = DEFAULT_SEED) -> list[Session]:
    rng = seeded(seed, TRACES_VERSION, "arrivals")
    grid = _weights()
    base = SESSIONS_PER_DAY / 24
    out: list[Session] = []
    n = 0
    for hour in range(DAYS * 24):
        t0 = START + timedelta(hours=hour)
        w = grid[t0.weekday()][t0.hour]
        for _ in range(_poisson(rng, base * w)):
            n += 1
            t = t0 + timedelta(seconds=rng.randint(0, 3599))
            change = rng.random() < CHANGE_SHARE
            sid = f"S{n:06d}"
            one = seeded(seed, TRACES_VERSION, sid)
            kind = _pick(one, KINDS) if change else "follow-up"
            s = Session(sid=sid, started=t.isoformat(),
                        kind=kind, hour_weight=round(w, 3),
                        knowledge_s=round(_ln(one, 0.16, 0.5), 3))
            if change:
                _task(one, s)
            else:
                _follow_up(one, s)
            out.append(s)
    return out


def digest(sessions: list[Session]) -> str:
    h = hashlib.sha256()
    for s in sessions:
        h.update(json.dumps(asdict(s), sort_keys=True).encode())
    return h.hexdigest()[:12]
