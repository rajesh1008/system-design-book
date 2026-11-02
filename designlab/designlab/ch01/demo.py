"""designlab v0, the Chapter 1 lab. Offline, seeded, the same every run.

    python3 -m ch01.demo                      # the whole lab
    python3 -m ch01.demo --no-permission-check
    python3 -m ch01.demo --timeout-rate 0.10
    python3 -m ch01.demo --action hotel_cancel
    python3 -m ch01.demo --live               # one live model output
"""
from __future__ import annotations

import argparse
import json

from chain.record import ChainRecord, Proposal, Refused
from common.clock import FixedClock
from common.rand import seeded  # noqa: F401 (tests use it)
from common.text import emit
from common.trail import TrailWriter

from .checker import QUESTIONS, audit
from .v0 import ACTIONS, Network, V0Loop, demo_shape

SEED = 7
REFUND = ('{"action": "refund", "itinerary": "LTG-4471902", '
          '"amount_usd": 412.60, "reason": "flight canceled by carrier"}')
REBOOK = ('{"action": "rebook", "itinerary": "LTG-4380117", '
          '"amount_usd": 86.00, "reason": "missed connection"}')
ANSWER = "Your new flight leaves at 6:40 p.m. from gate B7."


# Lab clocks run in Lakeshore's local time, America/Chicago, with the
# offset that applied on the day: CST (-06:00) in December, CDT (-05:00)
# on October 6. test_ch01 checks both against the time-zone database.
INCIDENT_START = "2025-12-04T14:32:07-06:00"
OCTOBER_START = "2025-10-06T15:12:40-05:00"


def trail(start: str = INCIDENT_START) -> TrailWriter:
    return TrailWriter(clock=FixedClock(start, step_seconds=1.0))


def render(line: str) -> str:
    """One trail line, shortened to fit the page."""
    e = json.loads(line)
    ev, n = e["event"], e["seq"]
    if ev == "output":
        rest = f"class={e['class']}"
    elif ev == "proposal":
        rest = f"{e['action']} {e['ref']} ${e['usd']:,.2f}"
    elif ev == "permission":
        rest = f"{e['id']} by {e['by']} {e['policy']}"
    elif ev == "execution":
        rest = (f"{e['effect']} status={e['status']} "
                f"attempts={e['attempts']} key={str(e['key'])[:13]}")
    elif ev == "verification":
        rest = f"by {e['verified_by']} found={e['found']} ok={e['ok']}"
    elif ev == "closed":
        rest = f"state={e['state']} prev={e['prev'][:10]}"
    elif ev == "refused":
        rest = f"by {e['by']}\n{'':>16}missing={', '.join(e['missing'])}"
    elif ev == "denied":
        rest = f"by {e['by']} to={e['to']}"
    elif ev == "tool_call":
        rest = f"tool={e['tool']} status={e['status']}"
    else:
        rest = ""
    out = f"  {n:>2} {ev:<12} {rest}"
    return "\n".join(ln[:70] for ln in out.split("\n"))


def show(line: str) -> None:
    for part in render(line).split("\n"):
        emit(part)


def october_demo() -> None:
    emit("1. The October 6 demo, replayed (one rebooking)")
    t, world = trail(OCTOBER_START), Network()
    demo_shape(world, t, "demo-1", REBOOK)
    for line in t.lines:
        show(line)
    a = audit(t.lines)
    gaps = [q for q in QUESTIONS if a["unanswered"][q]]
    emit(f"  trail cannot answer: {', '.join(gaps)}")


def one_refund() -> None:
    emit("")
    emit("2. v0, one refund end to end (first answer arrives late)")
    t, world = trail(), Network(slow_calls={1})
    rec = V0Loop(world, t).run("req-1", REFUND)
    for line in t.lines:
        show(line)
    emit(f"  effects in the world: {len(world.effects)}"
         f"  notes: {len(rec.notes)}")


def injection() -> None:
    emit("")
    emit("3. Failure injection: execute with no permission record")
    t, world = trail(), Network()
    loop = V0Loop(world, t)
    rec = ChainRecord(proposal=Proposal("refund", "LTG-4471902", 412.60,
                                        "flight canceled by carrier"))
    try:
        loop.execute("req-2", rec)
        emit("  executed (this should not happen)")
    except Refused as exc:
        emit(f"  Refused: {', '.join(exc.missing)}")
    for line in t.lines:
        show(line)
    emit(f"  effects in the world: {len(world.effects)}")


def requests(n: int, seed: int, action: str) -> list[tuple[str, str]]:
    """n customer turns: about one in ten is a question, not an action."""
    rng = seeded(seed, "ch01", "requests")
    out = []
    for i in range(n):
        if rng.random() < 0.10:
            out.append((f"req-{i + 1:04d}", ANSWER))
            continue
        amount = round(rng.uniform(60, 1800), 2)
        out.append((f"req-{i + 1:04d}", json.dumps(
            {"action": action, "itinerary": f"LTG-{5000000 + i}",
             "amount_usd": amount, "reason": "schedule change"})))
    return out


def batch(n: int, seed: int, rate: float, action: str,
          check: bool) -> None:
    emit("")
    emit(f"4. {n:,} requests, seed {seed}, {rate:.0%} answered after"
         f" the timeout")
    if action != "refund":
        emit(f"   action={action} limit=${ACTIONS[action]['limit']:,.0f}")
    reqs = requests(n, seed, action)
    rng = seeded(seed, "ch01", "slow")
    slow = {i for i in range(1, 4 * n) if rng.random() < rate}
    rows = []
    for label in ("demo shape", "v0" if check else "v0, no check"):
        world, t = Network(slow_calls=set(slow)), trail()
        if label == "demo shape":
            for rid, out in reqs:
                t.append({"event": "output", "req": rid,
                          "class": "action" if out.startswith("{")
                          else "answer"})
                demo_shape(world, t, rid, out)
        else:
            loop = V0Loop(world, t, check_permission=check)
            for rid, out in reqs:
                loop.run(rid, out)
        a = audit(t.lines)
        dupes = sum(1 for rid, out in reqs if out.startswith("{")
                    and len(world.found(action, json.loads(out)
                                        ["itinerary"])) > 1)
        rows.append((label, a, dupes, len(t.lines)))
    emit(f"   {'':<26}{rows[0][0]:>12}{rows[1][0]:>14}")
    def row(name, f):
        emit(f"   {name:<26}{f(rows[0]):>12,}{f(rows[1]):>14,}")
    row("answers, nothing to do", lambda r: r[1]["answers"])
    row("sent to a person", lambda r: r[1]["denied"])
    row("reached the world", lambda r: r[1]["acted"])
    row("  no permission record", lambda r: r[1]["unanswered"]["allowed"])
    row("  no policy named", lambda r: r[1]["unanswered"]["policy"])
    row("  no key for retries", lambda r: r[1]["unanswered"]["once"])
    row("  not verified by another", lambda r: r[1]["unanswered"]
        ["verified"])
    row("duplicate effects", lambda r: r[2])
    row("trail lines", lambda r: r[3])
    row("broken trail links", lambda r: len(r[1]["links"]))


def live(transport=None) -> None:
    """One live call: the small model writes the output, v0 does the rest.

    `transport` lets the offline tests replay a scripted response down
    the same code path; by default the call goes to the provider.
    """
    from common.client import ModelClient
    from common.spend import SpendMeter
    emit("")
    emit("5. Live: the small model writes the output")
    c = ModelClient("small", meter=SpendMeter(cap_usd=0.05),
                    transport=transport)
    r = c.complete(LIVE_PROMPT, system=LIVE_SYSTEM, max_tokens=160)
    t, world = trail(), Network()
    V0Loop(world, t).run("live-1", r.text)
    emit(f"  model={r.model} tokens={r.input_tokens}+{r.output_tokens}"
         f" usd={r.cost_usd:.6f}")
    for line in t.lines:
        show(line)


LIVE_SYSTEM = ("You turn a travel customer's message into one JSON object "
               "with keys action (refund, rebook or hotel_cancel), "
               "itinerary, amount_usd (a number) and reason (under eight "
               "words). Reply with the JSON object only.")
LIVE_PROMPT = ("Itinerary LTG-4471902. The airline canceled my Boston "
               "flight. Please refund the $412.60 fare.")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--timeout-rate", type=float, default=0.02)
    ap.add_argument("--action", choices=sorted(ACTIONS), default="refund")
    ap.add_argument("--no-permission-check", action="store_true")
    ap.add_argument("--live", action="store_true")
    a = ap.parse_args(argv)
    october_demo()
    one_refund()
    injection()
    batch(a.n, a.seed, a.timeout_rate, a.action,
          check=not a.no_permission_check)
    if a.live:
        live()


if __name__ == "__main__":
    main()
