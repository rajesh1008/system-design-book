"""The ladder as a timed drill: the clock run over one answer note.

    python3 -m ladder.drill --answer A03b           # replay, offline
    RUN_LIVE=1 python3 -m ladder.drill --answer A03b --live

At each mark the drill prints what is on the board. At a mark the
answer misses, the mock interviewer (models.interviewer) asks about
the first gap that is still open and has not been asked about yet.
"""
from __future__ import annotations

import argparse
import sys
import textwrap

from common.spend import SpendMeter
from models import interviewer

from . import clock, notes
from .prompts import PROMPTS


def drawn(note: dict, by: int) -> str:
    ch = notes.events(note, "chain", by)
    if not ch:
        return "nothing yet"
    return ", ".join(ch[-1]["names"])


def run(note: dict, live: bool = False, ask: bool = True
        ) -> list[dict]:
    p = PROMPTS[note["answer"]["prompt"]]
    cl = interviewer.client(live, SpendMeter(cap_usd=0.05)) \
        if ask else None
    asked: set[str] = set()
    out = []
    for minute, task, ok, board in clock.check(note):
        row = {"minute": minute, "task": task, "ok": ok,
               "board": board, "question": None, "gap": None}
        if not ok and cl is not None:
            done = set(clock.closed(note, minute))
            open_ = [g for g in clock.GAPS
                     if g not in done and g not in asked]
            if open_:
                g = open_[0]
                asked.add(g)
                a = interviewer.ask(cl, p["text"], minute, g,
                                    drawn(note, minute))
                row.update(question=a.question, gap=g,
                           first=a.first, first_problems=a.first_problems,
                           source=a.source, model=a.model)
        out.append(row)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--answer", default="A03b")
    ap.add_argument("--live", action="store_true")
    a = ap.parse_args(argv)
    if a.live and not interviewer.live_allowed():
        print("live run needs RUN_LIVE=1 and ANTHROPIC_API_KEY")
        return 2
    for r in run(notes.load(a.answer), live=a.live):
        print(f"{r['minute']:>2} min  {'met ' if r['ok'] else 'MISS'}"
              f"  {r['task']}: {r['board']}")
        if r["question"]:
            if r["first_problems"]:
                print(f"        first reply: "
                      f"{'; '.join(r['first_problems'])}")
            lines = textwrap.wrap(f"ask {r['gap']} ({r['source']}): "
                                  f"{r['question']}", 60)
            for ln in lines:
                print("        " + ln)
    return 0


if __name__ == "__main__":
    sys.exit(main())
