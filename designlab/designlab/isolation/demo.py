"""Chapter 11 lab: session isolation, the sandbox runner, egress policy,
and blast radius, on seeded March 2026 pilot work.

    python3 -m isolation.demo                       # everything, seed 11
    python3 -m isolation.demo --part egress         # one part
    python3 -m isolation.demo --inject shared-dir   # the injected failure
    python3 -m isolation.demo --inject shared-cache

Offline. No model is called and no network request leaves the box.
"""
from __future__ import annotations

import argparse
import json
import statistics
import tempfile
import time
from collections import Counter
from pathlib import Path

from common.clock import FixedClock
from common.rand import seeded
from common.text import emit
from common.trail import check_trail

from .blast import (blast_radius, build_world, by_locator, by_tenant,
                    design, probe_design, warm_pool)
from .egress import EgressPolicy, load_policy
from .sandbox import run_in_sandbox, runner_name
from .session import SessionStore, cross_read_suite

PARTS = ("suite", "sandbox", "egress", "blast", "pool", "cost")
CLOCK0 = "2026-03-16T09:00:00-05:00"     # Monday, CDT


def part_suite(seed: int, shared: bool, runs: int) -> bool:
    label = "one shared scratch dir" if shared else "one dir per session"
    emit(f"cross-read suite: {runs:,} runs, {label}")
    r = cross_read_suite(runs=runs, seed=seed, shared=shared)
    emit(f"  sessions opened        {r.reads:>7,}")
    emit(f"  cross-session reads    {r.cross_reads:>7,}")
    emit(f"  runs with shared path  {r.shared_paths_seen:>7,}")
    emit(f"  scans left after close {r.leftovers:>7,}")
    for mine, got in r.examples[:2]:
        emit(f"  e.g. {mine} read the scan of {got}")
    emit(f"isolation test: {'PASS' if r.ok else 'FAIL'}")
    return r.ok


TOOLS = {
    "proration": "v = round(1184.00 * 9 / 14, 2)\n"
                 "open('out.txt', 'w').write(str(v))\nprint(v)",
    "write-out": "open({target!r}, 'w').write('x')\nprint('wrote')",
    "connect": "import socket\n"
               "socket.create_connection(('203.0.113.9', 443), 2)\n"
               "print('connected')",
}


def part_sandbox(prefer: str = "auto") -> None:
    name = runner_name(prefer)
    emit(f"sandbox runner: {name}")
    with tempfile.TemporaryDirectory(prefix="designlab-sbx-") as root:
        store = SessionStore(Path(root))
        me = store.open("s-000101", "LTG-4400000")
        other = store.open("s-000102", "LTG-4400001")
        target = str(other.workdir / "planted.txt")
        for tool, code in TOOLS.items():
            code = code.format(target=target)
            r = run_in_sandbox(me.workdir, ["python3", "-c", code],
                               prefer=prefer)
            last = (r.stdout.strip() or r.stderr.strip()).splitlines()
            msg = last[-1] if last else ""
            if "Error" in msg:
                kind, _, why = msg.partition(":")
                msg = f"{kind}:{why.split(']')[-1]}"
            emit(f"  {tool:<10} exit {r.code:<3} {msg[:44]}")
        planted = Path(target).exists()
        emit(f"  file in other session: {'yes' if planted else 'no'}")
        emit(f"  out.txt in own session: "
             f"{(me.workdir / 'out.txt').read_text()}")
        store.close(me)
        store.close(other)


LISTED = [("loop", "https://model.lakeshore.internal/v1/messages"),
          ("loop", "https://control.lakeshore.internal/propose"),
          ("loop", "https://trail.lakeshore.internal/append"),
          ("booking_read", "https://knowledge.lakeshore.internal/ctx"),
          ("policy_read", "https://knowledge.lakeshore.internal/pol"),
          ("refund", "https://gateway.lakeshore.internal/refund"),
          ("rebook", "https://gateway.lakeshore.internal/rebook"),
          ("doc_intake", "https://docs.lakeshore.internal/u/1"),
          ("doc_intake", "https://ocr.lakeshore.internal/read"),
          ("flight_status", "https://status.lakeshore.internal/f"),
          ("fare_calc", "https://fares.lakeshore.internal/rules"),
          ("code_run", "https://pkgs.lakeshore.internal/simple/"),
          ("notice_read", "https://notices.lakeshore.internal/n")]
ATTEMPTS = [("code_run", "https://pypi.org/simple/requests/"),
            ("doc_intake", "https://paste.example.net/api/new"),
            ("notice_read", "http://169.254.169.254/latest/"),
            ("fare_calc", "https://198.51.100.7/rules"),
            ("booking_read", "https://gateway.lakeshore.internal/refund"),
            ("doc_intake",
             "https://docs.lakeshore.internal@paste.example.net/x")]


def part_egress(seed: int) -> None:
    clock = FixedClock(CLOCK0, step_seconds=97.0)
    pol = EgressPolicy(clock=clock)
    emit(f"egress policy: {pol.host_count()} hosts, owner {pol.owner}")
    r = seeded(seed, "isolation", "egress")
    calls = 5_000
    for i in range(calls):
        if r.random() < 0.006:
            tool, url = r.choice(ATTEMPTS)
        else:
            tool, url = r.choice(LISTED)
        clock.now()
        pol.check(tool, url, session=f"s-{i:06d}")
    chain = ["https://notices.lakeshore.internal/n/77",
             "https://cdn.carrier.example/n/77"]
    v = pol.follow("notice_read", chain, session="s-redirect")
    emit(f"  calls checked          {calls + len(chain):>6,}")
    emit(f"  allowed                {pol.allowed:>6,}")
    emit(f"  denied                 {pol.denied:>6,}")
    reasons = Counter()
    hosts = Counter()
    for line in pol.trail.lines:
        e = json.loads(line)
        reasons[e["reason"]] += 1
        hosts[e["host"]] += 1
    for why, n in reasons.most_common():
        emit(f"    {why:<26}{n:>4}")
    listed = {h["name"] for h in load_policy()["host"]}
    leaks = sum(n for h, n in pol.allowed_hosts.items()
                if h not in listed)
    emit(f"  unlisted calls allowed {leaks:>6}")
    emit(f"  redirect hop 2: {v.host} -> {v.reason}")
    first = json.loads(pol.trail.lines[0])
    emit(f"  first denial at {first['at']}")
    emit(f"  trail lines {len(pol.trail.lines)}, "
         f"chain intact: {check_trail(pol.trail.lines) == []}")


def _its(n: int) -> str:
    return "itinerary" if n == 1 else "itineraries"


def part_blast(seed: int, shared_dir: bool, shared_cache: bool) -> int:
    w = build_world(seed)
    me = w.itineraries[0]
    res = design(w, me, shared_dir=shared_dir,
                 cache_key=by_locator if shared_cache else by_tenant)
    reach = probe_design(w, res)
    emit(f"blast radius for one session ({len(w.itineraries):,} "
         f"itineraries probed)")
    for name, s in reach.items():
        emit(f"  {name:<18}{len(s):>6} {_its(len(s))}")
    n = blast_radius(reach)
    emit(f"  {'union':<18}{n:>6} {_its(n)}")
    return n


def part_pool() -> None:
    emit("warm sandbox pool, Little's law L = lambda * W")
    for label, lam, hold in (("March pilot", 0.03, 31.0),
                             ("storm, full scale", 3.1, 31.0)):
        in_use, pool = warm_pool(lam, hold)
        emit(f"  {label:<18} {lam:>4} /s x {hold:.0f} s = "
             f"{in_use:5.1f} -> pool {pool}")


def part_cost(prefer: str = "auto", n: int = 15) -> None:
    import subprocess
    import sys
    emit(f"start cost, median of {n} starts of python3 -c pass")
    with tempfile.TemporaryDirectory(prefix="designlab-cost-") as root:
        def med(fn) -> float:
            ts = []
            for _ in range(n):
                t = time.perf_counter()
                fn()
                ts.append((time.perf_counter() - t) * 1000)
            return statistics.median(ts)
        plain = med(lambda: subprocess.run([sys.executable, "-c", "pass"],
                                           cwd=root))
        boxed = med(lambda: run_in_sandbox(Path(root),
                                           ["python3", "-c", "pass"],
                                           prefer=prefer))
    emit(f"  plain subprocess      {plain:7.1f} ms")
    label = f"{runner_name(prefer)} sandbox"
    emit(f"  {label:<22}{boxed:7.1f} ms")
    emit(f"  added per session     {boxed - plain:7.1f} ms")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--part", choices=PARTS)
    ap.add_argument("--inject", choices=("shared-dir", "shared-cache"))
    ap.add_argument("--runs", type=int, default=10_000)
    ap.add_argument("--runner", choices=("auto", "subprocess"),
                    default="auto")
    a = ap.parse_args(argv)
    shared_dir = a.inject == "shared-dir"
    shared_cache = a.inject == "shared-cache"
    parts = [a.part] if a.part else list(PARTS)
    for i, p in enumerate(parts):
        if i:
            emit()
        if p == "suite":
            part_suite(a.seed, shared_dir, a.runs)
        elif p == "sandbox":
            part_sandbox(a.runner)
        elif p == "egress":
            part_egress(a.seed)
        elif p == "blast":
            part_blast(a.seed, shared_dir, shared_cache)
        elif p == "pool":
            part_pool()
        elif p == "cost":
            part_cost(a.runner)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
