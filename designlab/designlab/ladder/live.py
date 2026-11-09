"""A model scores the 24 calibration answers against the rubric.

    RUN_LIVE=1 python3 -m ladder.live --record   # real calls, recorded
    python3 -m ladder.demo --part model          # replay, offline

The live run needs RUN_LIVE=1 and ANTHROPIC_API_KEY in the
environment. The key is read by the shared transport and nowhere
else. Every call is priced by the spend meter and stops at its cap.
Recorded fixtures live in ladder/fixtures/scoring/; offline runs
replay them through the same client code.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from common.client import FixtureTransport, HttpTransport, ModelClient
from common.spend import SpendMeter

from . import notes
from .prompts import PROMPTS
from .rubric import CRITERIA

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "scoring"
CAP_USD = 0.50

SYSTEM = """You score one answer from a 45-minute system design \
interview about an AI agent that acts. You are given the prompt and \
the interviewer's minute-by-minute note. Score seven criteria, each \
0, 1, or 2:
framing: 2 if the effect the agent may cause is named first, with an \
owner, by minute 5; 1 if named later or without an owner; 0 if never.
estimation: 2 if a number with a stated source changes the design; \
1 if a number without a source or that changes nothing; 0 if none.
chain: 2 if the drawing puts permission before the effect and a \
verifier that did not act after it; 1 if only one; 0 if no drawing.
gaps: the five gaps (G1 output to proposal, G2 proposal to \
permission, G3 permission to execution, G4 execution to verified \
outcome, G5 verified outcome to business result). 2 if all five are \
closed correctly with an owner; 1 if three or four; 0 otherwise. A \
gap closed with a wrong answer does not count.
tradeoffs: 2 if two or more options are weighed and the losers' \
reasons are given; 1 if options without reasons; 0 if none.
cost: 2 if cost is per verified outcome; 1 if per token, per month, \
or vague; 0 if none.
communication: 2 if the answer frames by 5, draws by 15, closes the \
gaps by 30, and ends with a decision and what would reverse it; 1 if \
partly; 0 if not.
Reply with JSON only, keys in this order: framing, estimation, chain, \
gaps, tradeoffs, cost, communication."""


class LowEffortClient(ModelClient):
    """Sends effort "low", as Chapters 21 and 23 do, so scoring does not
    spend its output budget thinking. The first recording, with
    max_tokens 120 and the default effort, came back with 24 replies
    of thinking and no JSON. The effort is in the request body, so it
    is in the request hash and the fixture."""

    def request_body(self, prompt, system, max_tokens, temperature):
        body = super().request_body(prompt, system, max_tokens,
                                    temperature)
        body["output_config"] = {"effort": "low"}
        return body


def user_prompt(note: dict) -> str:
    p = PROMPTS[note["answer"]["prompt"]]
    return (f"Prompt ({p['level']}): {p['text']}\n\n"
            f"Interviewer's note:\n{notes.as_text(note)}")


def parse(text: str) -> list[int] | None:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
        row = [int(d[c]) for c in CRITERIA]
    except (ValueError, KeyError, TypeError):
        return None
    return row if all(v in (0, 1, 2) for v in row) else None


def client(transport, meter: SpendMeter | None = None,
           record: bool = False, model: str = "small") -> ModelClient:
    return LowEffortClient(model, meter or SpendMeter(cap_usd=CAP_USD),
                           transport,
                           record_dir=FIXTURES if record else None)


def score_all(cl: ModelClient) -> tuple[dict[str, list[int]], dict]:
    out, info = {}, {"bad": [], "model": "", "in": 0, "out": 0}
    for aid, note in notes.load_all().items():
        c = cl.complete(user_prompt(note), system=SYSTEM,
                        max_tokens=2000)
        info["model"] = c.model
        info["in"] += c.input_tokens
        info["out"] += c.output_tokens
        row = parse(c.text)
        if row is None:
            info["bad"].append(aid)
            continue
        out[aid] = row
    return out, info


def replay() -> tuple[dict[str, list[int]], dict]:
    return score_all(client(FixtureTransport(FIXTURES)))


def live_allowed() -> bool:
    return (os.environ.get("RUN_LIVE") == "1"
            and os.environ.get("DESIGNLAB_OFFLINE") != "1"
            and bool(os.environ.get("ANTHROPIC_API_KEY", "").strip()))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="store_true")
    a = ap.parse_args(argv)
    if not a.record:
        rows, info = replay()
    else:
        if not live_allowed():
            print("live run needs RUN_LIVE=1 and ANTHROPIC_API_KEY")
            return 2
        meter = SpendMeter(cap_usd=CAP_USD)
        rows, info = score_all(client(HttpTransport(), meter, True))
        print(f"spent ${meter.spent_usd:.4f} in {meter.calls} calls")
    print(f"model {info['model']}: scored {len(rows)} of 24, "
          f"unparsed {len(info['bad'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
