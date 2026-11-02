"""Chapter 21: a free summary prompt against a structured one.

    python3 -m models.compaction            # replay recorded fixtures
    python3 -m models.compaction --record   # six live calls, cap $0.50

Three seeded run histories of about 6,000 tokens each are compacted
twice by the small model: once with a free prompt ("summarize so
far"), once with a structured prompt that names the sections and
asks for identifiers verbatim. Each summary goes through the same
verifier the lab uses (context.compact.verify_summary), plus a check
that the customer's constraint survived.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common.client import FixtureTransport, HttpTransport, ModelClient  # noqa: F401
from common.live import live_available
from common.spend import SpendMeter
from common.text import emit
from context.compact import verify_summary
from context.live import LowEffortClient
from context.transcript import facts, transcript

SEED = 2105
CASES = (0, 1, 2)
TOKENS = 6_000
CAP_USD = 0.50
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "compaction"

FREE = ("Summarize the conversation so far so the agent can continue "
        "the task.")
STRUCTURED = (
    "Compact this run history so the agent can resume from it. Use "
    "exactly these sections:\n"
    "GOAL: one line.\n"
    "CUSTOMER CONSTRAINTS: quote each one verbatim.\n"
    "PENDING ACTIONS: every approval, refund, or request not yet "
    "complete, with its ID, amount, and idempotency key copied "
    "character for character.\n"
    "CLOSED: IDs that were canceled or superseded, marked closed.\n"
    "DONE SO FAR: at most three lines.\n"
    "NEXT STEP: one line.\n"
    "Do not write any ID, amount, or key that is not in the history.")
PROMPTS = {"free": FREE, "structured": STRUCTURED}


def check(summary: str, f, trail: str,
          stop_reason: str | None = None) -> list[str]:
    """The lab's verifier, plus two checks a live summary needs: the
    customer's constraint must survive word for word (a paraphrase can
    change its meaning), and the summary must not be cut off."""
    found = verify_summary(summary, f.pinned(), trail)
    if f.constraint.lower() not in summary.lower():
        found.append("constraint not verbatim")
    if stop_reason == "max_tokens":
        found.append("cut off")
    return found


def run(client: ModelClient) -> list[dict]:
    rows = []
    for i in CASES:
        f = facts(SEED, i)
        trail = transcript(f, SEED, i, TOKENS)
        for name, instr in PROMPTS.items():
            c = client.complete(trail + "\n\n" + instr, max_tokens=1500)
            rows.append({"case": i, "prompt": name,
                         "findings": check(c.text, f, trail, c.stop_reason),
                         "summary_tokens": c.output_tokens,
                         "input_tokens": c.input_tokens})
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="store_true")
    a = ap.parse_args(argv)
    if a.record and not live_available():
        emit("live run needs ANTHROPIC_API_KEY; replaying fixtures")
        a.record = False
    meter = SpendMeter(cap_usd=CAP_USD)
    if a.record:
        cl = LowEffortClient("small", meter, HttpTransport(timeout=120.0),
                         record_dir=FIXTURES)
    else:
        cl = LowEffortClient("small", meter, FixtureTransport(FIXTURES))
    rows = run(cl)
    emit(f"compaction prompts, {cl.pin.id}, "
         f"{'live' if a.record else 'replayed'}")
    for r in rows:
        emit(f"  case {r['case']} {r['prompt']:<10} "
             f"{r['summary_tokens']:>4} tok  "
             + ("passes" if not r["findings"] else
                ", ".join(r["findings"])[:40]))
    if a.record:
        emit(f"spent ${meter.spent_usd:.4f} of ${CAP_USD:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
