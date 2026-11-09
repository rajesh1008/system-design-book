"""A mock interviewer for the Chapter 46 drill, against a pinned model.

The drill (ladder.drill) decides what to ask about; the model only
words it. Given the prompt, the minute, and the first gap the answer
has not closed, the model asks one question. The reply must meet a
small contract: one question, at most thirty words, ending with a
question mark, from the pinned model.

Live calls need RUN_LIVE=1 and ANTHROPIC_API_KEY; the key is read only
by the shared transport. Recorded replies in fixtures/interviewer/ let
the tests and the demo run offline through the same client code.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from common.client import FixtureTransport, HttpTransport, ModelClient
from common.spend import SpendMeter

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "interviewer"
MAX_WORDS = 30

GAP_QUESTIONS = {
    "G1": "Is every action a typed proposal?",
    "G2": "Is permission granted outside the loop?",
    "G3": "Does a retry stay the same request?",
    "G4": "Does something that did not act verify?",
    "G5": "Is the business result counted?",
}

SYSTEM = """You are the interviewer in a 45-minute system design \
interview about an AI agent that acts in the world. Ask the candidate \
exactly one short question that makes them answer the gap you are \
given, in terms of their own design. Do not explain, do not answer, \
do not mention models, prompts, or temperature. Reply with the \
question only."""


@dataclass
class Asked:
    question: str
    model: str
    pinned: str
    problems: list[str]
    first: str = ""
    first_problems: list[str] | None = None
    source: str = "model"      # model, repair, or checklist


def user_prompt(prompt_text: str, minute: int, gap: str,
                drawn: str) -> str:
    return (f"Prompt: {prompt_text}\nMinute: {minute} of 45\n"
            f"What the candidate has drawn: {drawn}\n"
            f"Gap not yet closed: {gap}, {GAP_QUESTIONS[gap]}")


def check(text: str, model: str, pinned: str) -> list[str]:
    t = text.strip()
    out = []
    if model != pinned:
        out.append(f"answered by {model}, pinned {pinned}")
    if not t.endswith("?"):
        out.append("not a question")
    if t.count("?") != 1:
        out.append("more than one question")
    if "\n" in t:
        out.append("more than one line")
    if len(t.split()) > MAX_WORDS:
        out.append(f"{len(t.split())} words, over {MAX_WORDS}")
    return out


class LowEffortClient(ModelClient):
    """Effort "low" in the request body, so a one-line question does not
    spend its output budget thinking (the body is in the fixture hash)."""

    def request_body(self, prompt, system, max_tokens, temperature):
        body = super().request_body(prompt, system, max_tokens,
                                    temperature)
        body["output_config"] = {"effort": "low"}
        return body


def client(live: bool = False, meter: SpendMeter | None = None
           ) -> ModelClient:
    meter = meter or SpendMeter(cap_usd=0.05)
    if live:
        return LowEffortClient("small", meter, HttpTransport(),
                               record_dir=FIXTURES)
    return LowEffortClient("small", meter, FixtureTransport(FIXTURES))


def ask(cl: ModelClient, prompt_text: str, minute: int, gap: str,
        drawn: str) -> Asked:
    """One question. A reply that breaks the contract gets one repair,
    with the problems named; a second failure falls back to the
    checklist's own wording of the gap, which always passes."""
    up = user_prompt(prompt_text, minute, gap, drawn)
    c = cl.complete(up, system=SYSTEM, max_tokens=300)
    q = " ".join(c.text.split())
    probs = check(q, c.model, c.pinned)
    if not probs:
        return Asked(q, c.model, c.pinned, [], q, [])
    fix = (up + "\n\nYour last reply broke the rules: "
           + "; ".join(probs)
           + f". Ask one question of at most {MAX_WORDS} words.")
    c2 = cl.complete(fix, system=SYSTEM, max_tokens=300)
    q2 = " ".join(c2.text.split())
    probs2 = check(q2, c2.model, c2.pinned)
    if not probs2:
        return Asked(q2, c2.model, c2.pinned, [], q, probs, "repair")
    return Asked(GAP_QUESTIONS[gap], c2.model, c2.pinned, [], q, probs,
                 "checklist")


def live_allowed() -> bool:
    return (os.environ.get("RUN_LIVE") == "1"
            and os.environ.get("DESIGNLAB_OFFLINE") != "1"
            and bool(os.environ.get("ANTHROPIC_API_KEY", "").strip()))
