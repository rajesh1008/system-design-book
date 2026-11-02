"""Chapter 34 live check: the small model as a wording judge.

Thirty held-out messages that people on the desk labeled, sent to the
small model twice: once with the wording rubric (PASS or FAIL), and
once asking whether the refund reached the right card, a question a
message cannot answer. A judge that reads only the message should say
UNKNOWN; one that answers YES or NO is guessing about an effect.
Reads ANTHROPIC_API_KEY from the environment through common.client and
never prints it. Sixty short calls; the meter caps spend at $0.50.

    python3 -m evals.live            # live, records fixtures
    python3 -m evals.live --replay   # offline, from fixtures/live
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from common.client import FixtureTransport
from common.spend import SpendMeter
from common.text import emit
from knowops.live import LowEffortClient

from . import gate as GT
from . import judge as J

FIXTURES = Path(__file__).parent / "fixtures" / "live"
CAP_USD = 0.50
N = 30

RUBRIC = ("You grade one customer message from an airline refund agent. "
          "PASS only if it states the outcome, says what happens next "
          "(such as when money arrives or who calls), and promises "
          "nothing beyond the refund itself. Otherwise FAIL. Reply with "
          "one word: PASS or FAIL.")
EFFECT = ("You read one customer message from an airline refund agent. "
          "Question: did the refund go to the correct card? You see only "
          "the message, not the booking or the payment ledger. Reply "
          "with one word: YES, NO, or UNKNOWN.")


def items(n: int = N) -> list[tuple[str, dict, bool]]:
    """Every failing label in the held-out set first, then passes, so
    the thirty include all kinds of failure the desk marked."""
    pool = GT.held_out()
    bad = [(k, m, w) for k, m, w, _ in pool if not w]
    wrong_card = [(k, m, w) for k, m, w, _ in pool
                  if w and m.get("explains")]
    good = [(k, m, w) for k, m, w, _ in pool
            if w and not m.get("explains")]
    pick = bad[:12] + wrong_card[:3]
    return pick + good[:n - len(pick)]


def why(m: dict) -> str:
    if m.get("overpromise"):
        return "overpromise"
    if m.get("terse"):
        return "terse"
    if not m.get("timeline"):
        return "no next step"
    return ("decline offering credit" if m["kind"] == "declined"
            else "complete")


def word(text: str, allowed: tuple[str, ...]) -> str:
    t = text.strip().upper().strip(".")
    return next((a for a in allowed if t.startswith(a)), "OTHER")


def run(transport=None, record: bool = True) -> list[str]:
    meter = SpendMeter(cap_usd=CAP_USD)
    rec = FIXTURES if record else None
    cl = LowEffortClient("small", meter=meter, transport=transport,
                     record_dir=rec)
    its = items()
    got, eff, model = [], [], ""
    for _, m, _ in its:
        text = J.render(m)
        a = cl.complete(f"Message:\n{text}", system=RUBRIC, max_tokens=16)
        b = cl.complete(f"Message:\n{text}", system=EFFECT, max_tokens=16)
        model = a.model
        got.append(word(a.text, ("PASS", "FAIL")) == "PASS")
        eff.append(word(b.text, ("YES", "NO", "UNKNOWN")))
    people = [w for _, _, w in its]
    agree = sum(g == p for g, p in zip(got, people))
    k = J.kappa(got, people)
    off = Counter(why(m) for (_, m, w), g in zip(its, got) if g != w)
    wc = [i for i, (_, m, _) in enumerate(its) if m.get("explains")]
    out = [f"live judge {model}, {len(its)} labeled messages "
           f"({sum(people)} pass, {len(people) - sum(people)} fail)",
           f"wording agreement {agree} of {len(its)}, kappa {k:.2f} "
           f"(bar {J.KAPPA_MIN:.2f})",
           "judge and desk differ: " + (", ".join(f"{k} {v}" for k, v in
                                    off.most_common()) or "none"),
           f"wrong-card messages passed on wording "
           f"{sum(got[i] for i in wc)} of {len(wc)}",
           "right card? " + ", ".join(
               f"{a} {eff.count(a)}" for a in ("UNKNOWN", "YES", "NO",
                                               "OTHER") if eff.count(a)),
           f"model calls {meter.calls}, spent ${meter.spent_usd:.4f} "
           f"(cap ${CAP_USD:.2f})"]
    return out


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--replay", action="store_true")
    a = p.parse_args(argv)
    if a.replay:
        out = run(FixtureTransport(FIXTURES), record=False)
    else:
        out = run()
    for line in out:
        emit(line)


if __name__ == "__main__":
    main()
