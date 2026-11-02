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
from .tco import break_even_calls, fleet, utilization
from .trace import Seg, day

PARTS = ("clocks", "batching", "paged", "layout", "bakeoff", "salt",
         "probe", "speculative", "disagg", "tco", "card")
# Chapter 10's measured loop and plan. All amounts are US dollars.
PEAK = 2.37           # model calls a second at the planned surge
PROVIDER_CALL_S = 1.04  # mean provider call at that surge
CALLS = 8.79          # model calls a change, as run
PROMPT = 6217         # input tokens a model call, mean
OUTPUT = 173          # output tokens a model call, mean
APRIL_TASKS = 20100   # agent and assisted tasks a month, April 2026


def part_clocks() -> None:
    e = engines()["engines"]["engine-a"]
    emit("three clocks of one call, engine A profile (lab values)")
    for b in (1, 16, 64):
        s = decode_step_s(b, e["decode_base_ms"], e["decode_per_seq_ms"])
        emit(f"  batch {b:>3}: step {s * 1000:5.1f} ms,"
             f" {b / s:>6,.0f} tok/s for the GPU,"
             f" {1 / s:3.0f} tok/s each")
    itl = decode_step_s(16, e["decode_base_ms"], e["decode_per_seq_ms"])
    warm = round(PROMPT * 0.78)
    for label, cached in (("cold", 0), ("warm", warm)):
        c = three_clocks(0.0, PROMPT, cached, OUTPUT, e["prefill_tok_s"],
                         itl)
        emit(f"  {label}, {PROMPT:,} in, {OUTPUT} out, batch 16:"
             f" TTFT {c.ttft_s:4.2f} s, end {c.e2e_s:4.2f} s")
    emit(f"  provider, Chapter 10: {PROVIDER_CALL_S:.2f} s mean,"
         f" 1.9 s p95")
    emit(f"  KV per token, 8B-class model:"
         f" {kv_bytes_per_token() // 1024} KiB")
    n = in_flight(PEAK, c.e2e_s)
    emit(f"  planned surge, {PEAK} calls/s x {c.e2e_s:.2f} s:"
         f" {n:4.1f} in flight, {kv_gib(n, PROMPT + OUTPUT):4.1f} GiB KV")


def part_batching(seed: int, batch: int) -> None:
    reqs = bt.workload(seed)
    emit(f"batching: {len(reqs)} calls at 5/s on one GPU, seed {seed}")
    emit(f"  {'policy':<24}{'tok/s':>6}{'TTFT p95':>10}"
         f"{'ITL p95':>9}{'end p95':>9}")
    rows = (("static", 64, None), ("continuous", batch, None),
            ("continuous+chunk512", batch, 512))
    for name, b, ch in rows:
        pol = name.split("+")[0]
        s = bt.run(pol, bt.workload(seed), max_batch=b, chunk=ch)
        emit(f"  {name + ' b' + str(b):<24}{s['tok_s']:>6,.0f}"
             f"{s['ttft_p95']:>9.1f}s{s['itl_p95']:>8.3f}s"
             f"{s['e2e_p95']:>8.1f}s")


def call_lengths(seed: int) -> list[int]:
    out = []
    for t in day(seed):
        for c in t.calls:
            r = LAYOUTS["stable-first"](t, c)
            out.append(r.tokens + c.output)
    return out


def part_paged(seed: int) -> None:
    ls = call_lengths(seed)
    emit(f"KV memory: 60 GiB at 128 KiB a token, {len(ls):,} calls,"
         f" mean {sum(ls) / len(ls):,.0f} tokens")
    emit(f"  {'scheme':<14}{'fit':>5}{'held':>10}{'served':>10}"
         f"{'waste':>7}{'served/held':>13}")
    for f in fit(ls, shared_prefix=2880):
        emit(f"  {f.scheme:<14}{f.requests:>5}{f.reserved_tokens:>10,}"
             f"{f.used_tokens:>10,}{f.waste:>7.1%}"
             f"{f.served_per_held:>12.2f}x")


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
    emit("speculative decoding, k=4, draft cost 0.05 (lab model)")
    emit(f"  measured tokens per pass at {accept:.0%}:"
         f" {sp.simulate(accept, 4):.3f},"
         f" formula {sp.expected_tokens(accept, 4):.3f}")
    emit(f"  {'acceptance':<12}" + "".join(f"{'b' + str(b):>8}"
                                           for b in (1, 8, 32, 64, 128)))
    for a in dict.fromkeys((0.7, 0.4, accept)):
        emit(f"  {a:<12.0%}" + "".join(
            f"{sp.speedup(a, 4, 0.05, b):>7.2f}x"
            for b in (1, 8, 32, 64, 128)))
    for b in (1, 64):
        k, s = sp.best_k(accept, 0.05, b)
        emit(f"  best k at {accept:.0%}, batch {b}: k={k}, {s:.2f}x")


def part_disagg() -> None:
    emit("prefill and decode: one pool or two (toy model)")
    emit(f"  {'workload':<21}{'pool':<7}{'TTFT':>6}{'ITL':>7}"
         f"{'p95':>6}{'call':>7}{'batch':>6}")
    uncached = round(PROMPT * 0.22)
    for name, rate, p, o, g in (
            ("Lakeshore surge", PEAK, uncached, OUTPUT, 3),
            ("Lakeshore x10", PEAK * 10, uncached, OUTPUT, 12),
            ("voice, long prompt", 6.0, 12000, 250, 12)):
        gp, s = best_split(rate, p, o, g)
        for label, pool in (("one/" + str(g), colocated(rate, p, o, g)),
                            (f"{gp}+{g - gp}", s)):
            call = pool.ttft_s + (o - 1) * pool.itl_mean_s
            emit(f"  {name:<21}{label:<7}{pool.ttft_s:>5.2f}s"
                 f"{pool.itl_mean_s * 1000:>5.0f}ms"
                 f"{pool.itl_p95_s * 1000:>4.0f}ms{call:>6.2f}s"
                 f"{pool.decode_batch:>6.1f}")
            name = f"  in {p:,}, out {o}"


def part_tco(seed: int, gpu_hour: float) -> None:
    r = replay(day(seed), "stable-first")
    per_call = {k: r["bill"].usd(k) / r["calls"]
                for k in ("contract", "small")}
    month = round(APRIL_TASKS * CALLS)
    emit(f"cost a month, April volume: {month:,} calls")
    emit(f"  API frontier, contract, 78% hit"
         f"  ${month * per_call['contract']:>8,.0f}")
    emit(f"  API small model, 78% hit"
         f"         ${month * per_call['small']:>8,.0f}")
    small = fleet(2, gpu_hour)
    big = fleet(16, gpu_hour, sre_share=1.0)
    emit(f"  self-host 8B-class, 2 GPUs"
         f"       ${small.monthly:>8,.0f}  (GPUs ${small.gpu_usd:,.0f})")
    u = utilization(month, 2, round(PROMPT * 0.22), OUTPUT)
    emit(f"    busy {u:.1%} of its hours at April volume")
    emit(f"  self-host frontier-class, 16"
         f"     ${big.monthly:>8,.0f}  (GPUs ${big.gpu_usd:,.0f})")
    for label, f in (("2 GPUs", small), ("16 GPUs", big)):
        be = break_even_calls(f, per_call["contract"]) / CALLS
        emit(f"  {label} match the frontier bill at"
             f" {be:>9,.0f} tasks/month")
    be = break_even_calls(small, per_call["small"]) / CALLS
    emit(f"  2 GPUs match the small-model bill at {be:>9,.0f}")
    emit(f"  GPU-hour ${gpu_hour:.2f}; staff $16,000 a month,"
         f" half for 2 GPUs")


def part_card() -> None:
    emit("serving card, April 28, 2026 (lab values)")
    for k, v in (("engines compared", "2 open engines and the API"),
                 ("frontier steps", "provider API, pinned model"),
                 ("prompt layout", "stable-first, serving.layout"),
                 ("cache hit", "9% before, 78% after; alert < 60%"),
                 ("cost per task", "$0.147 to $0.068, down 54%"),
                 ("cache scope", "public prefix shared; traveler salt"),
                 ("clocks", "TTFT, ITL, end to end, per step"),
                 ("self-hosting", "deferred; see serving.tco"),
                 ("disaggregation", "not at this scale; revisit")):
        emit(f"  {k:<18}{v}")


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
