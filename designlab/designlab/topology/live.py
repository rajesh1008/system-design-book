"""Live sample: the 24 eligibility tasks on the small model.

    python3 -m topology.live            # replay recorded fixtures
    python3 -m topology.live --record   # about 270 live calls, cap $0.50

Five designs over the same tasks, each task once:

  single        one call
  orchestrator  the lead writes a brief; a facts worker reads the
                record; a rules worker sees the rule card and the
                facts summary only; the lead checks and answers
                (four calls)
  vote          three calls, each with its own "Reviewer n of 3" line
  debate        the vote's three answers, then a second round in
                which each reviewer sees all three
  verifier      the single answer, checked by eligibility.verify; on
                a finding, one repair call with the finding

The reviewer lines matter twice: they make the three requests differ,
so the client's request-hash cache and the fixtures do not collapse
three votes into one, and they are the only difference between the
voters, which is the point of Chapter 27. Every call goes through the
shared client and spend meter; the key is read by the transport and
nowhere else. Fixtures hold redacted request and response bodies.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

from common.client import FixtureTransport, HttpTransport, ModelClient
from common.live import live_available
from common.spend import SpendMeter
from common.text import emit
from context.live import LowEffortClient

from .eligibility import (QUESTION, RULES, TASKS, Answer, Task, outcome,
                          parse, verify)

CAP_USD = 0.50
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "live"
SYSTEM = ("You decide refund eligibility for a travel company's "
          "servicing agent, using only the rule card given.")
DESIGNS = ("single", "orchestrator", "vote", "debate", "verifier")


@dataclass
class Tally:
    design: str
    correct: int = 0
    desk: int = 0
    wrong: int = 0
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    wrong_tasks: list[str] = field(default_factory=list)

    @property
    def tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def add_call(self, c) -> None:
        self.calls += 1
        self.input_tokens += c.input_tokens
        self.output_tokens += c.output_tokens
        self.cost += c.cost_usd

    def score(self, t: Task, a: Answer) -> None:
        o = outcome(t, a)
        setattr(self, o, getattr(self, o) + 1)
        if o == "wrong":
            self.wrong_tasks.append(t.task_id)


def _ask(cl: ModelClient, prompt: str, tally: Tally,
         max_tokens: int = 1200):
    c = cl.complete(prompt, system=SYSTEM, max_tokens=max_tokens)
    tally.add_call(c)
    return c


def card_prompt(t: Task, extra: str = "") -> str:
    head = f"{extra}\n\n" if extra else ""
    return f"{head}{RULES}\nRecord:\n{t.record()}\n\n{QUESTION}"


def majority(answers: list[Answer]) -> Answer:
    vs = [a.eligible for a in answers]
    best = max(set(vs), key=vs.count)
    if vs.count(best) < 2:
        return Answer("desk", "R5")
    return next(a for a in answers if a.eligible == best)


def run(cl: ModelClient, tasks: list[Task] | None = None
        ) -> dict[str, Tally]:
    ts = {d: Tally(d) for d in DESIGNS}
    for t in (TASKS if tasks is None else tasks):
        # single, and the verifier built on the same answer
        c = _ask(cl, card_prompt(t), ts["single"])
        first = parse(c.text)
        ts["single"].score(t, first)
        ts["verifier"].add_call(c)
        finding = verify(t, first)
        final = first
        if finding:
            fix = _ask(cl, card_prompt(
                t, f"Your previous answer was {c.text.strip()}. A "
                   f"checker found: {finding}. Answer again."),
                ts["verifier"])
            final = parse(fix.text)
            if verify(t, final):
                final = Answer("desk", "R5")   # still failing: a person
        ts["verifier"].score(t, final)
        # orchestrator-worker
        ow = ts["orchestrator"]
        brief = _ask(cl, f"{RULES}\nRecord:\n{t.record()}\n\nYou lead two "
                     "workers. Write a brief for the facts worker: the "
                     "facts it must pull from the record so a rules "
                     "worker can decide. At most 60 words.", ow)
        facts = _ask(cl, f"Brief from the lead:\n{brief.text.strip()}\n\n"
                     f"Record:\n{t.record()}\n\nState only the facts the "
                     "brief asks for. At most 80 words.", ow)
        rules = _ask(cl, f"Case {t.task_id}.\n{RULES}\nFacts from the "
                     f"facts worker:\n"
                     f"{facts.text.strip()}\n\n{QUESTION}", ow)
        merged = _ask(cl, f"{RULES}\nRecord:\n{t.record()}\n\nThe rules "
                      f"worker answered: {rules.text.strip()}\nCheck it "
                      f"against the record and give the final answer. "
                      f"{QUESTION}", ow)
        ow.score(t, parse(merged.text))
        # vote, and debate built on the same three answers
        r1 = [_ask(cl, card_prompt(t, f"Reviewer {n} of 3."), ts["vote"])
              for n in (1, 2, 3)]
        a1 = [parse(c.text) for c in r1]
        ts["vote"].score(t, majority(a1))
        for c in r1:
            ts["debate"].add_call(c)
        seen = "\n".join(f"Reviewer {n}: {c.text.strip()}"
                         for n, c in zip((1, 2, 3), r1))
        r2 = [_ask(cl, card_prompt(
            t, f"Reviewer {n} of 3, round two. The three first-round "
               f"answers were:\n{seen}\nConsider them, then give your "
               f"own final answer."), ts["debate"]) for n in (1, 2, 3)]
        ts["debate"].score(t, majority([parse(c.text) for c in r2]))
    return ts


def client(record: bool) -> tuple[ModelClient, SpendMeter]:
    meter = SpendMeter(cap_usd=CAP_USD)
    if record:
        return LowEffortClient("small", meter, HttpTransport(timeout=120.0),
                               record_dir=FIXTURES), meter
    return LowEffortClient("small", meter,
                           FixtureTransport(FIXTURES)), meter


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="store_true")
    a = ap.parse_args(argv)
    if a.record and not live_available():
        emit("live run needs ANTHROPIC_API_KEY; replaying fixtures")
        a.record = False
    cl, meter = client(a.record)
    ts = run(cl)
    base = ts["single"].tokens
    emit(f"eligibility, 24 tasks, {cl.pin.id}, "
         f"{'live' if a.record else 'replayed'}")
    emit("  design        correct  desk  wrong  calls  tokens  x single")
    for d in DESIGNS:
        t = ts[d]
        emit(f"  {d:<12}  {t.correct:>7}  {t.desk:>4}  {t.wrong:>5}  "
             f"{t.calls:>5}  {t.tokens:>6,}  {t.tokens / base:>8.2f}")
    for d in DESIGNS:
        if ts[d].wrong_tasks:
            emit(f"  wrong, {d}: {', '.join(ts[d].wrong_tasks)}"[:70])
    total = sum(t.cost for d, t in ts.items() if d not in ("verifier",
                                                           "debate"))
    total += ts["verifier"].cost - ts["single"].cost
    total += ts["debate"].cost - ts["vote"].cost
    emit(f"model spend for the sample ${total:.4f}"
         + (f"; meter ${meter.spent_usd:.4f} of ${CAP_USD:.2f}"
            if a.record else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
