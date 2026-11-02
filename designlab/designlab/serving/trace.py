"""A seeded April weekday of agent tasks, as segments of tokens.

A segment is a run of tokens with one identity: the tool definitions,
the system instructions, one policy text at one version, one
itinerary, one tool result, one timestamp. Two segments with the same
key hold the same tokens, so a cache can match them without holding
the text. Sizes are illustrative and sit near the pilot's traces.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from common import seeded

# Stable content, the same for every task of a kind.
TOOLS = ("tools-v4", 560)
SYSTEM = ("instructions-v7", 1100)
EXAMPLES = ("examples-v2", 420)
POLICY = {"refund": ("refunds-v3", 820), "change": ("changes-v1", 700),
          "rebook": ("rebook-v2", 760), "voucher": ("vouchers-v1", 520)}
KINDS = ("change", "rebook", "refund", "voucher")
KIND_WEIGHTS = (0.42, 0.28, 0.20, 0.10)
TIMESTAMP_TOKENS = 12
STEPS_MEDIAN, STEPS_SIGMA, STEP_CAP = 7, 0.5, 24   # Chapter 10
ITINERARY = (400, 700)      # itinerary and context packet
FIRST_MESSAGE = (60, 220)
TOOL_RESULT = (150, 700)
OUTPUT_MU, OUTPUT_SIGMA = 5.03, 0.5    # lognormal, mean about 173


@dataclass(frozen=True)
class Seg:
    key: str
    tokens: int


@dataclass
class Call:
    task: str
    step: int
    at_s: float
    new: list[Seg]          # turns this call adds to the history
    output: int             # output tokens
    itin_v: int = 1         # itinerary version the call sees


@dataclass
class Task:
    id: str
    kind: str
    customer: str           # the traveler: the tenant (Chapter 11)
    arrive_s: float
    itinerary: Seg
    calls: list[Call] = field(default_factory=list)


ASSISTED = 9 / 11.5         # April: assisted 9%, agent alone 2.5%
APPROVAL_WAIT = (180, 1800)  # seconds a person takes to approve
CUSTOMER_WAIT = (60, 600)


def day(seed: int = 14, tasks: int = 300, per_min: float = 0.46,
        pause_p: float = 0.3, assisted: float = ASSISTED) -> list[Task]:
    """Tasks arrive as a Poisson stream. Steps per task are lognormal
    with a median of seven, as Chapter 10 fitted them; one model call
    a step, and each call after the first adds the model's tool call and
    the tool's result to the history."""
    r = seeded(seed, "serving", "trace")
    out, t = [], 0.0
    for i in range(tasks):
        t += r.expovariate(per_min / 60.0)
        kind = r.choices(KINDS, KIND_WEIGHTS)[0]
        tid = f"T{i:04d}"
        cust = f"C{r.randrange(10**6):06d}"
        task = Task(tid, kind, cust, t,
                    Seg(f"itin:{tid}", r.randint(*ITINERARY)))
        at = t
        steps = min(STEP_CAP, max(2, round(r.lognormvariate(
            math.log(STEPS_MEDIAN), STEPS_SIGMA))))
        for k in range(steps):
            new = []
            if k == 0:
                new.append(Seg(f"msg:{tid}:0", r.randint(*FIRST_MESSAGE)))
            else:
                new.append(Seg(f"asst:{tid}:{k-1}",
                               task.calls[-1].output))
                new.append(Seg(f"tool:{tid}:{k}", r.randint(*TOOL_RESULT)))
            out_tok = max(12, int(r.lognormvariate(OUTPUT_MU,
                                                   OUTPUT_SIGMA)))
            v = 2 if steps >= 4 and k >= steps - 2 else 1
            task.calls.append(Call(tid, k, at, new, out_tok, v))
            # model time plus tool time; sometimes the customer answers
            gap = 0.6 + out_tok / 140.0 + r.uniform(1.0, 6.0)
            if k == steps // 2 and r.random() < pause_p:
                gap += r.uniform(*CUSTOMER_WAIT)    # customer answers
            if k == steps - 3 and r.random() < assisted:
                gap += r.uniform(*APPROVAL_WAIT)    # a person approves
            at += gap
        out.append(task)
    return out


def calls_in_time_order(tasks: list[Task]) -> list[tuple[Task, Call]]:
    pairs = [(t, c) for t in tasks for c in t.calls]
    pairs.sort(key=lambda p: (p[1].at_s, p[0].id))
    return pairs


def itinerary(task: Task, call: Call) -> Seg:
    """The itinerary as this call sees it. After the change executes,
    the agent re-reads the booking and the itinerary is new text."""
    it = task.itinerary
    return it if call.itin_v == 1 else Seg(f"{it.key}@v2", it.tokens)
