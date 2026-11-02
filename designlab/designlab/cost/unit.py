"""Cost per call, per step, per task, and per verified outcome.

The unit of the bill is a token; the unit of the business is a verified
outcome. This module walks from one to the other on Chapter 10's
recorded pilot tasks (corpus.traces, seed 10), priced with
serving.prices, and then adds what a token bill leaves out: metered
tools and fees, the platform, verification, and people's minutes.

Model tiers: the frontier tier is priced at Lakeshore's contract
(Chapter 10: $3.00 and $15.00 per million tokens); the small and mid
tiers at the pinned public prices in common/models.toml. All amounts
are US dollars. Lakeshore figures are illustrative.
"""
from __future__ import annotations

import functools
import statistics
from dataclasses import dataclass, field, replace

from capacity.budget import Design, _kept
from common import seeded
from corpus.traces import KINDS, generate_traces
from serving.prices import Bill

TIER_ROLE = {"small": "small", "mid": "mid", "frontier": "contract"}
TRACE_SEED = 10   # the pilot trace every chapter reads (Chapter 10)
FRESH = 0.22          # share of a prompt new since the call before it
REPAIR = 0.023        # extra model calls per effect step (Chapter 16)
METERED = {"search_flights": 0.006, "hotel_lookup": 0.004,
           "fare_rules": 0.001}           # supplier fee per request
EFFECT_FEE = {"rebook": 0.40, "refund": 0.22, "cancel": 0.05,
              "credit": 0.02}             # same fee on every path
LOADED_PER_MIN = 42.00 / 60               # Chapter 4's loaded rate


@dataclass(frozen=True)
class Levers:
    """The five levers. Defaults are Lakeshore's May 2026 design."""
    small: float = 0.63          # share of steps on the small model
    mid: float = 0.09            # share on the mid model; rest frontier
    hit: float = 0.7843          # prefix-cache hit (Chapter 14)
    cache: bool = True
    step_cap: int | None = 24
    repeat_cap: int | None = 1
    retry_scale: float = 1.0     # multiply timeouts and repairs
    token_scale: float = 1.0     # multiply prompt tokens a call


MAY_LEVERS = Levers()
# April: every step on the frontier model; the re-layout was adopted on
# April 28 (Chapter 14) and served from April 29, so 28 days at 9.2%
# hit and 2 days at 78.43%.
APRIL_LEVERS = Levers(small=0.0, mid=0.0,
                      hit=round((28 * 0.092 + 2 * 0.7843) / 30, 4))
PILOT_LEVERS = Levers(small=0.0, mid=0.0, hit=0.092)


@dataclass
class TaskCost:
    sid: str
    kind: str
    model: float = 0.0
    tools: float = 0.0
    calls: int = 0
    steps: int = 0
    handoff: bool = False
    tokens: int = 0
    by_tier: dict = field(default_factory=dict)

    @property
    def machine(self) -> float:
        return self.model + self.tools


def call_bill(tokens_in: int, tokens_out: int, lv: Levers) -> Bill:
    if not lv.cache:
        return Bill(uncached=tokens_in, output=tokens_out)
    read = round(tokens_in * lv.hit)
    written = round(tokens_in * min(1.0 - lv.hit, FRESH))
    return Bill(uncached=tokens_in - read - written, written=written,
                read=read, output=tokens_out)


def calls_of(s, lv: Levers = MAY_LEVERS, seed: int = 18):
    """Yield one record per billed model call of a recorded task:
    (step index, tier, tokens in, tokens out, USD, metered tool USD)."""
    design = Design(own_limit=True, repeat_cap=lv.repeat_cap,
                    step_cap=lv.step_cap)
    steps, _ = _kept(s.steps, design)
    rng = seeded(seed, "cost-tier", s.sid)
    for i, x in enumerate(steps):
        r = rng.random()
        tier = ("small" if r < lv.small else
                "mid" if r < lv.small + lv.mid else "frontier")
        n = 1 + round(x.error_s / 10.0 * lv.retry_scale)
        if x.tool == "effect" and rng.random() < REPAIR * lv.retry_scale:
            n += 1
        tin = round(x.tokens_in * lv.token_scale)
        usd = call_bill(tin, x.tokens_out, lv).usd(TIER_ROLE[tier])
        fee = METERED.get(x.tool, 0.0) * len(x.tool_s)
        for j in range(n):
            yield i, tier, tin, x.tokens_out, usd, fee if j == 0 else 0.0


def task_cost(s, lv: Levers = MAY_LEVERS, seed: int = 18) -> TaskCost:
    design = Design(own_limit=True, repeat_cap=lv.repeat_cap,
                    step_cap=lv.step_cap)
    steps, handoff = _kept(s.steps, design)
    t = TaskCost(s.sid, s.kind, steps=len(steps), handoff=handoff)
    for _i, tier, tin, tout, usd, fee in calls_of(s, lv, seed):
        t.model += usd
        t.tools += fee
        t.calls += 1
        t.tokens += tin + tout
        t.by_tier[tier] = t.by_tier.get(tier, 0.0) + usd
    return t


@functools.lru_cache(maxsize=None)
def _tasks():
    return tuple(s for s in generate_traces(TRACE_SEED) if s.is_task)


@functools.lru_cache(maxsize=64)
def sample(lv: Levers = MAY_LEVERS, seed: int = 18) -> tuple:
    """Every recorded pilot task, costed under one set of levers."""
    return tuple(task_cost(s, lv, seed) for s in _tasks())


@dataclass(frozen=True)
class Month:
    name: str
    changes: int = 175_000
    agent: float = 0.06          # share of changes the agent completes
    assisted: float = 0.12
    verified_rate: float = 0.991
    handoff: float = 0.12        # agent attempts that end with a person
    platform: float = 5_950.0    # gateway, run store, trail, evals
    verify_usd: float = 0.03     # reconciler share per executed change
    audit: float = 0.05          # next-day sample audit
    audit_min: float = 6.0
    pickup_min: float = 4.0      # a person reads the trail of a hand-off
    rework_min: float = 35.0     # fixing a change that failed checks
    repeat: float = 0.02         # follow-up contact within seven days
    repeat_min: float = 9.0
    levers: Levers = MAY_LEVERS


MAY = Month("May 2026")
APRIL = Month("April 2026", agent=0.025, assisted=0.09,
              verified_rate=0.981, handoff=0.22, platform=3_580.0,
              levers=APRIL_LEVERS)

LINES = ("model tokens", "tools and fees", "platform", "verification",
         "review labor", "rework", "repeat contacts")


def kind_shares() -> dict[str, float]:
    return dict(KINDS)


def month_cost(m: Month = MAY, seed: int = 18) -> dict:
    tasks = sample(m.levers, seed)
    model = statistics.fmean(t.model for t in tasks)
    metered = statistics.fmean(t.tools for t in tasks)
    verified = round(m.changes * m.agent)
    executed = round(verified / m.verified_rate)
    attempts = round(executed / (1.0 - m.handoff))
    fees = sum(executed * share * EFFECT_FEE[k]
               for k, share in kind_shares().items())
    rate = LOADED_PER_MIN
    review_min = (m.audit * executed * m.audit_min
                  + (attempts - executed) * m.pickup_min)
    rework_min = (executed - verified) * m.rework_min
    repeat_min = verified * m.repeat * m.repeat_min
    lines = {
        "model tokens": attempts * model,
        "tools and fees": attempts * metered + fees,
        "platform": m.platform,
        "verification": executed * m.verify_usd,
        "review labor": review_min * rate,
        "rework": rework_min * rate,
        "repeat contacts": repeat_min * rate,
    }
    total = sum(lines.values())
    machine = sum(lines[k] for k in LINES[:4])
    failed = attempts - executed
    left_out = (failed * (model + metered) + failed * m.pickup_min * rate
                + lines["rework"])
    return {"month": m.name, "verified": verified, "executed": executed,
            "attempts": attempts, "lines": lines, "total": total,
            "per_outcome": total / verified,
            "machine_per_outcome": machine / verified,
            "without_failed": (total - left_out) / verified,
            "people_min": review_min + rework_min + repeat_min,
            "model_per_attempt": model, "metered_per_attempt": metered}


def ladder(m: Month = MAY, seed: int = 18) -> list[tuple[str, float]]:
    """The same month's spend divided by six different units."""
    tasks = sample(m.levers, seed)
    c = month_cost(m, seed)
    tokens = sum(t.tokens for t in tasks)
    calls = sum(t.calls for t in tasks)
    model = sum(t.model for t in tasks)
    return [
        ("per million tokens", model / tokens * 1e6),
        ("per model call", model / calls),
        ("per attempt, model and tools", c["model_per_attempt"]
         + c["metered_per_attempt"]),
        ("per outcome, machines only", c["machine_per_outcome"]),
        ("per outcome, failed attempts out", c["without_failed"]),
        ("per verified outcome", c["per_outcome"]),
    ]


def attribute(total_cents: int, weights: dict[str, float]) -> dict:
    """Split shared cents by weight; largest remainder, so it sums."""
    w = sum(weights.values())
    raw = {k: total_cents * v / w for k, v in weights.items()}
    out = {k: int(v) for k, v in raw.items()}
    left = total_cents - sum(out.values())
    for k in sorted(raw, key=lambda k: (out[k] - raw[k], k))[:left]:
        out[k] += 1
    return out


def with_levers(m: Month, **kw) -> Month:
    return replace(m, levers=replace(m.levers, **kw))


def by_kind(m: Month = MAY, seed: int = 18) -> dict[str, dict]:
    """Cost per verified outcome for each kind of change. Direct lines
    come from that kind's own tasks; the platform is shared out by each
    kind's model calls, in cents, so the parts add to the whole."""
    c = month_cost(m, seed)
    tasks = sample(m.levers, seed)
    shares = kind_shares()
    calls = {k: sum(t.calls for t in tasks if t.kind == k) *
             shares[k] / max(1, sum(1 for t in tasks if t.kind == k))
             for k in shares}
    platform = attribute(round(m.platform * 100), calls)
    out = {}
    rate = LOADED_PER_MIN
    for k, share in shares.items():
        kt = [t for t in tasks if t.kind == k]
        verified = c["verified"] * share
        executed = c["executed"] * share
        attempts = c["attempts"] * share
        lines = {
            "model tokens": attempts * statistics.fmean(
                t.model for t in kt),
            "tools and fees": attempts * statistics.fmean(
                t.tools for t in kt) + executed * EFFECT_FEE[k],
            "platform": platform[k] / 100,
            "verification": executed * m.verify_usd,
            "review labor": (m.audit * executed * m.audit_min
                             + (attempts - executed) * m.pickup_min)
            * rate,
            "rework": (executed - verified) * m.rework_min * rate,
            "repeat contacts": verified * m.repeat * m.repeat_min * rate,
        }
        out[k] = {"verified": verified, "lines": lines,
                  "per_outcome": sum(lines.values()) / verified}
    return out
