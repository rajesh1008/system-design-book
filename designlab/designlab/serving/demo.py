"""Chapter 14 lab: inference serving.

    python3 -m serving.demo                    # every part, seed 14
    python3 -m serving.demo --part bakeoff     # one part
    python3 -m serving.demo --layout clock-first
    python3 -m serving.demo --part batching --batch 128
    python3 -m serving.demo --part speculative --accept 0.4

Offline. No model is called and no key is read. Engine profiles are
recorded fixtures; prices are the pins in common/models.toml.
"""
from __future__ import annotations

import argparse

from common.text import emit

from . import batching as bt
from . import speculative as sp
from .bakeoff import engines, replay
from .cachekey import probe, response_key
from .clocks import (decode_step_s, in_flight, kv_bytes_per_token,
                     kv_gib, three_clocks)
from .disagg import best_split, colocated
from .layout import LAYOUTS, lint
from .paged import fit
from .tco import break_even_calls, fleet, gpus_for
from .trace import Seg, day

PARTS = ("clocks", "batching", "paged", "layout", "bakeoff", "salt",
         "probe", "speculative", "disagg", "tco", "card")
STORM = 18.6          # model calls a second at the storm peak, Ch 1
APRIL_TASKS = 20100   # agent and assisted tasks a month, April 2026
CALLS = 6


def part_clocks() -> None:
    e = engines()["engines"]["engine-a"]
    emit("three clocks of one call, engine A profile (lab values)")
    for b in (1, 16, 64):
        s = decode_step_s(b, e["decode_base_ms"], e["decode_per_seq_ms"])
        emit(f"  batch {b:>3}: step {s * 1000:5.1f} ms,"
             f" {b / s:>7,.0f} tok/s for the GPU,"
             f" {1 / s:4.0f} tok/s each")
    itl = decode_step_s(64, e["decode_base_ms"], e["decode_per_seq_ms"])
    for label, cached in (("cold", 0), ("warm", 6230)):
        c = three_clocks(0.0, 7970, cached, 1615, e["prefill_tok_s"], itl)
        emit(f"  {label} 7,970-token prompt, 1,615 out:"
             f" TTFT {c.ttft_s:4.2f} s, end {c.e2e_s:5.1f} s")
    emit(f"  KV per token, 8B-class model: "
         f"{kv_bytes_per_token() // 1024} KiB")
    emit(f"  storm, {STORM} calls/s x {c.e2e_s:.0f} s each:"
         f" {in_flight(STORM, c.e2e_s):,.0f} in flight,"
         f" {kv_gib(in_flight(STORM, c.e2e_s), 9600):,.0f} GiB of KV")


def part_batching(seed: int, batch: int) -> None:
    reqs = bt.workload(seed, per_s=0.9)
    emit(f"batching: {len(reqs)} calls at 0.9/s on one GPU, seed {seed}")
    emit(f"  {'policy':<22}{'tok/s':>7}{'TTFT p95':>10}"
         f"{'ITL p95':>9}{'end p95':>9}")
    rows = (("static", 64, None), ("continuous", batch, None),
            ("continuous+chunk512", batch, 512))
    for name, b, ch in rows:
        pol = name.split("+")[0]
        s = bt.run(pol, reqs, max_batch=b, chunk=ch)
        emit(f"  {name + ' b' + str(b):<22}{s['tok_s']:>7,.0f}"
             f"{s['ttft_p95']:>9.1f}s{s['itl_p95']:>8.3f}s"
             f"{s['e2e_p95']:>8.0f}s")


def call_lengths(seed: int) -> list[int]:
    out = []
    for t in day(seed):
        for c in t.calls:
            r = LAYOUTS["stable-first"](t, c)
            out.append(r.tokens + c.output)
    return out


def part_paged(seed: int) -> None:
    ls = call_lengths(seed)
    emit(f"KV memory: 40 GiB at 128 KiB a token, {len(ls):,} calls,"
         f" mean {sum(ls) / len(ls):,.0f} tokens")
    emit(f"  {'scheme':<14}{'fit':>5}{'held':>10}{'in use':>10}"
         f"{'waste':>7}")
    for f in fit(ls, shared_prefix=3240):
        emit(f"  {f.scheme:<14}{f.requests:>5}{f.reserved_tokens:>10,}"
             f"{f.used_tokens:>10,}{f.waste:>7.1%}")


def part_layout(seed: int, layout: str) -> None:
    t = day(seed)[0]
    for name in ("pilot", layout):
        r = LAYOUTS[name](t, t.calls[2])
        keys = " ".join(s.key.split(":")[0].split("-")[0]
                        for s in r.segs[:7])
        emit(f"{name}: {keys} ...")
        emit(f"  breakpoints at {r.breakpoints}")
        for f in lint(r) or ["no findings"]:
            emit(f"  lint: {f}")


def part_bakeoff(seed: int, layout: str) -> None:
    tasks = day(seed)
    n = sum(len(t.calls) for t in tasks)
    emit(f"bake-off replay: {len(tasks)} tasks, {n:,} calls, seed {seed}")
    emit(f"  {'layout':<14}{'cache':<10}{'hit':>7}{'$/task':>9}"
         f"{'in/call':>9}")
    base = None
    for lay in dict.fromkeys(("pilot", "stable-first", layout)):
        for c in ("api", "engine-a", "engine-b"):
            r = replay(tasks, lay, c)
            cost = f"{r['usd_per_task']:.4f}" if c == "api" else "-"
            emit(f"  {lay:<14}{c:<10}{r['hit']:>7.2%}{cost:>9}"
                 f"{r['bill'].input_tokens / n:>9,.0f}")
            if c == "api" and lay == "pilot":
                base = r["usd_per_task"]
            elif c == "api" and base:
                emit(f"  {'':<24}cost per task {r['usd_per_task'] / base - 1:+.1%}")


def part_salt(seed: int) -> None:
    tasks = day(seed)
    emit("cache salt on the engine, stable-first layout")
    emit(f"  {'salt':<34}{'engine-a':>10}{'engine-b':>10}")
    for s, label in (("shared", "none (one pool for all)"),
                     ("traveler", "per traveler, first block"),
                     ("boundary", "per traveler, after public")):
        a = replay(tasks, "stable-first", "engine-a", s)["hit"]
        b = replay(tasks, "stable-first", "engine-b", s)["hit"]
        emit(f"  {label:<34}{a:>10.2%}{b:>10.2%}")


def part_probe(seed: int) -> None:
    v = day(seed)[0]
    wrong = Seg("itin:guess", v.itinerary.tokens)
    emit(f"timing probe: attacker guesses {v.id}'s itinerary")
    emit(f"  {'salt':<10}{'right guess':>13}{'wrong guess':>13}"
         f"{'gap':>8}  leak")
    for mode in ("shared", "traveler", "boundary"):
        r, w = probe(v, v.itinerary, mode), probe(v, wrong, mode)
        gap = r["saved_ms"] - w["saved_ms"]
        emit(f"  {mode:<10}{r['matched']:>8,} tok{w['matched']:>9,} tok"
             f"{gap:>6.0f}ms  {'yes' if r['leak'] else 'no'}")
    k1 = response_key("trav-0001", "refunds-v3", "claude-opus-5-5",
                      "stable-first@2", {"ask": "refund LTG-5172204"})
    k2 = response_key("trav-0002", "refunds-v3", "claude-opus-5-5",
                      "stable-first@2", {"ask": "refund LTG-5172204"})
    emit(f"  response key, traveler 1: {k1[:24]}...")
    emit(f"  response key, traveler 2: {k2[:24]}...")


def part_speculative(accept: float) -> None:
    emit(f"speculative decoding, k=4, draft cost 0.05 (lab model)")
    emit(f"  measured tokens per pass at {accept:.0%}:"
         f" {sp.simulate(accept, 4):.3f},"
         f" formula {sp.expected_tokens(accept, 4):.3f}")
    emit(f"  {'acceptance':<12}" + "".join(f"{'b' + str(b):>8}"
                                           for b in (1, 8, 32, 64, 128)))
    for a in dict.fromkeys((0.7, accept)):
        emit(f"  {a:<12.0%}" + "".join(
            f"{sp.speedup(a, 4, 0.05, b):>7.2f}x"
            for b in (1, 8, 32, 64, 128)))
    for b in (1, 64):
        k, s = sp.best_k(accept, 0.05, b)
        emit(f"  best k at {accept:.0%}, batch {b}: k={k}, {s:.2f}x")


def part_disagg() -> None:
    emit("prefill and decode: one pool or two (toy model)")
    emit(f"  {'workload':<22}{'pool':<10}{'TTFT':>7}{'ITL p95':>9}"
         f"{'batch':>7}")
    for name, rate, p, o, g in (("Lakeshore storm", STORM, 1750, 1600, 24),
                                ("long prompt, short", 6.0, 12000, 250, 12)):
        c = colocated(rate, p, o, g)
        emit(f"  {name:<22}{'one/' + str(g):<10}{c.ttft_s:>6.2f}s"
             f"{c.itl_p95_s * 1000:>7.0f}ms{c.decode_batch:>7.0f}")
        gp, s = best_split(rate, p, o, g)
        emit(f"  {'  in ' + str(p) + ', out ' + str(o):<22}"
             f"{str(gp) + '+' + str(g - gp):<10}{s.ttft_s:>6.2f}s"
             f"{s.itl_p95_s * 1000:>7.0f}ms{s.decode_batch:>7.0f}")


def part_tco(seed: int, gpu_hour: float) -> None:
    r = replay(day(seed), "stable-first")
    per_call = {k: r["bill"].usd(k) / r["calls"]
                for k in ("frontier", "small")}
    month = APRIL_TASKS * CALLS
    emit(f"cost a month, April volume: {month:,} calls")
    emit(f"  API frontier at 78% hit    ${month * per_call['frontier']:>9,.0f}")
    emit(f"  API small at 78% hit       ${month * per_call['small']:>9,.0f}")
    storm = gpus_for(STORM, 1750, 1600)
    for label, g in (("floor", 2), ("storm", storm)):
        f = fleet(g, gpu_hour)
        emit(f"  self-host {label}, {g:>2} GPUs      ${f.monthly:>9,.0f}"
             f"  (GPUs ${f.gpu_usd:,.0f})")
    f = fleet(2, gpu_hour)
    be = break_even_calls(f, per_call["frontier"])
    emit(f"  floor breaks even with frontier at {be:,.0f} calls")
    emit(f"    that is {be / CALLS:,.0f} tasks a month;"
         f" small: {break_even_calls(f, per_call['small']) / CALLS:,.0f}")
    emit(f"  GPU-hour ${gpu_hour:.2f}; staff half of $16,000;"
         f" illustrative")


def part_card() -> None:
    emit("serving card, April 28, 2026 (lab values)")
    for k, v in (("frontier steps", "provider API, pinned model"),
                 ("prompt layout", "stable-first, two breakpoints"),
                 ("cache hit", "78% replayed; alert under 60%"),
                 ("cache scope", "public prefix shared; traveler salt"),
                 ("clocks", "TTFT, ITL, end to end, per step"),
                 ("self-hosting", "deferred; revisit at 50,000/mo"),
                 ("disaggregation", "not at this ratio; revisit")):
        emit(f"  {k:<16}{v}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=14)
    ap.add_argument("--part", choices=PARTS)
    ap.add_argument("--layout", choices=tuple(LAYOUTS),
                    default="stable-first")
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--accept", type=float, default=0.7)
    ap.add_argument("--gpu-hour", type=float, default=3.20)
    a = ap.parse_args()
    run = {"clocks": part_clocks,
           "batching": lambda: part_batching(a.seed, a.batch),
           "paged": lambda: part_paged(a.seed),
           "layout": lambda: part_layout(a.seed, a.layout),
           "bakeoff": lambda: part_bakeoff(a.seed, a.layout),
           "salt": lambda: part_salt(a.seed),
           "probe": lambda: part_probe(a.seed),
           "speculative": lambda: part_speculative(a.accept),
           "disagg": part_disagg,
           "tco": lambda: part_tco(a.seed, a.gpu_hour),
           "card": part_card}
    for i, p in enumerate([a.part] if a.part else PARTS):
        if i:
            emit()
        run[p]()


if __name__ == "__main__":
    main()
