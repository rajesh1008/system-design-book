"""A seeded April weekday of agent tasks, as segments of tokens.

A segment is a run of tokens with one identity: the tool definitions,
the system instructions, one policy text at one version, one
itinerary, one tool result, one timestamp. Two segments with the same
key hold the same tokens, so a cache can match them without holding
the text. Sizes are illustrative and sit near the pilot's traces.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from common import seeded

# Stable content, the same for every task of a kind.
TOOLS = ("tools-v4", 520)
SYSTEM = ("instructions-v7", 1750)
EXAMPLES = ("examples-v2", 520)
POLICY = {"refund": ("refunds-v3", 980), "change": ("changes-v1", 860),
          "rebook": ("rebook-v2", 900), "voucher": ("vouchers-v1", 640)}
KINDS = ("change", "rebook", "refund", "voucher")
KIND_WEIGHTS = (0.42, 0.28, 0.20, 0.10)
TIMESTAMP_TOKENS = 12
CALLS_PER_TASK = 6
THINKING_SHARE = 0.6        # of output tokens; dropped from history
ITINERARY = (380, 760)
FIRST_MESSAGE = (60, 220)
TOOL_RESULT = (160, 620)
OUTPUT_MU, OUTPUT_SIGMA = 6.75, 0.35   # lognormal, about 900 tokens


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
    output: int             # output tokens, thinking included


@dataclass
class Task:
    id: str
    kind: str
    tenant: str
    customer: str
    arrive_s: float
    itinerary: Seg
    calls: list[Call] = field(default_factory=list)


def day(seed: int = 14, tasks: int = 400, per_min: float = 1.25,
        pause_p: float = 0.12) -> list[Task]:
    """Tasks arrive as a Poisson stream; each makes six model calls."""
    r = seeded(seed, "serving", "trace")
    out, t = [], 0.0
    for i in range(tasks):
        t += r.expovariate(per_min / 60.0)
        kind = r.choices(KINDS, KIND_WEIGHTS)[0]
        tid = f"T{i:04d}"
        cust = f"C{r.randrange(10**6):06d}"
        task = Task(tid, kind, "lakeshore", cust, t,
                    Seg(f"itin:{tid}", r.randint(*ITINERARY)))
        at = t
        for k in range(CALLS_PER_TASK):
            new = []
            if k == 0:
                new.append(Seg(f"msg:{tid}:0", r.randint(*FIRST_MESSAGE)))
            else:
                new.append(Seg(f"asst:{tid}:{k-1}",
                               int(task.calls[-1].output
                                   * (1 - THINKING_SHARE))))
                new.append(Seg(f"tool:{tid}:{k}", r.randint(*TOOL_RESULT)))
            out_tok = int(r.lognormvariate(OUTPUT_MU, OUTPUT_SIGMA))
            task.calls.append(Call(tid, k, at, new, out_tok))
            # model time plus tool time; sometimes the customer answers
            gap = 1.2 + out_tok / 140.0 + r.uniform(1.0, 6.0)
            if k == 2 and r.random() < pause_p:
                gap += r.uniform(120, 900)
            at += gap
        out.append(task)
    return out


def calls_in_time_order(tasks: list[Task]) -> list[tuple[Task, Call]]:
    pairs = [(t, c) for t in tasks for c in t.calls]
    pairs.sort(key=lambda p: (p[1].at_s, p[0].id))
    return pairs
