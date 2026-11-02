"""Static against continuous batching, one GPU, a step at a time.

Static batching gathers a batch, runs it until its longest member is
done, and only then lets anyone else in. Continuous batching admits
and retires requests at every step. The step cost is the decode model
in clocks.py; a step that admits new requests also pays their prefill.
"""
from __future__ import annotations

from dataclasses import dataclass

from common import seeded

from .clocks import decode_step_s


@dataclass
class Req:
    arrive: float
    prompt: int
    output: int
    first: float = -1.0
    done: float = -1.0
    left: int = 0
    worst_gap: float = 0.0
    pre: int = 0            # prompt tokens not yet prefilled


def workload(seed: int = 14, n: int = 500, per_s: float = 5.0,
             prompt: int = 1368, out_mu: float = 5.03,
             out_sigma: float = 0.5) -> list[Req]:
    """Lakeshore-shaped calls: the 1,368 prompt tokens a call that the
    prefix cache does not hold (22% of 6,217) and about 173 out."""
    r = seeded(seed, "serving", "batching")
    t, out = 0.0, []
    for _ in range(n):
        t += r.expovariate(per_s)
        o = max(8, int(r.lognormvariate(out_mu, out_sigma)))
        out.append(Req(t, prompt, o, left=o, pre=prompt))
    return out


def pct(xs: list[float], p: float) -> float:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * len(xs)))]


def summary(reqs: list[Req], wall: float) -> dict:
    toks = sum(q.output for q in reqs)
    return {"tok_s": toks / wall,
            "ttft_p50": pct([q.first - q.arrive for q in reqs], 0.50),
            "ttft_p95": pct([q.first - q.arrive for q in reqs], 0.95),
            "itl_p95": pct([q.worst_gap for q in reqs], 0.95),
            "e2e_p95": pct([q.done - q.arrive for q in reqs], 0.95)}


def run(policy: str, reqs: list[Req], max_batch: int = 64,
        base_ms: float = 17.5, per_seq_ms: float = 0.34,
        prefill_tok_s: float = 11800, wait_s: float = 2.0,
        chunk: int | None = None) -> dict:
    """chunk=None prefills each admitted prompt in one step; chunk=512
    spreads prefill over steps, 512 prompt tokens a step at most."""
    reqs = [Req(q.arrive, q.prompt, q.output, left=q.output,
                pre=q.prompt) for q in reqs]
    t, i, waiting, running = 0.0, 0, [], []
    while i < len(reqs) or waiting or running:
        while i < len(reqs) and reqs[i].arrive <= t:
            waiting.append(reqs[i])
            i += 1
        if not running and not waiting:
            t = reqs[i].arrive
            continue
        admit: list[Req] = []
        if policy == "continuous":
            room = max_batch - len(running)
            admit, waiting = waiting[:room], waiting[room:]
        elif not running:
            full = len(waiting) >= max_batch
            old = waiting and t - waiting[0].arrive >= wait_s
            if not (full or old or i >= len(reqs)):
                t = min(reqs[i].arrive, waiting[0].arrive + wait_s) \
                    if waiting else reqs[i].arrive
                continue
            admit, waiting = waiting[:max_batch], waiting[max_batch:]
        running += admit
        budget = chunk if chunk else 10**9
        pre_now = 0
        for q in running:
            if q.pre and budget:
                take = min(q.pre, budget)
                q.pre -= take
                budget -= take
                pre_now += take
        decoding = [q for q in running if not q.pre and q.left > 0]
        step = decode_step_s(len(running), base_ms, per_seq_ms)
        step += pre_now / prefill_tok_s
        t += step
        for q in decoding:
            q.left -= 1
            if q.first < 0:
                q.first = t
            else:
                q.worst_gap = max(q.worst_gap, step)
            if q.left == 0:
                q.done = t
        if policy == "continuous" or all(q.left <= 0 for q in running):
            running = [q for q in running if q.left > 0]
    return summary(reqs, t - reqs[0].arrive)
