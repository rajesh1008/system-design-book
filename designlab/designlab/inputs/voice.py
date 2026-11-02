"""A voice turn and its latency budget, simulated.

A turn is the time from the caller's last word to the agent's first
audio. Two pipelines are simulated over the same seeded calls: a batch
one (wait for silence, transcribe the whole utterance, generate the
whole reply, synthesize it) and a streaming one (semantic endpointing,
streaming transcription, speak the first sentence while the rest is
generated, and a fixed holding phrase when a tool call would run past
the budget). Stage times are drawn from ranges, not measured; the
point is the shape of the budget, not any vendor's numbers.

Read-back: any amount or date a proposal would use is spoken back and
confirmed before the proposal exists. The simulation counts how many
misheard values reach a proposal with and without it.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass

from common.rand import seeded

BUDGET_S = 2.0          # first audio within two seconds of end of speech
HOLD_AT_S = 1.2         # say a holding phrase if the reply is not ready


@dataclass(frozen=True)
class Turn:
    endpoint: float
    asr: float
    model: float
    tool: float          # 0 when the turn needs no tool
    tts: float
    held: bool = False   # a holding phrase was spoken first

    @property
    def total(self) -> float:
        if self.held:
            return self.endpoint + HOLD_AT_S
        return self.endpoint + self.asr + self.model + self.tool + self.tts


def _tri(rng, lo, mode, hi):
    return rng.triangular(lo, hi, mode)


def batch_turn(rng, needs_tool: bool) -> Turn:
    return Turn(endpoint=_tri(rng, 0.8, 1.0, 1.5),
                asr=_tri(rng, 0.4, 0.7, 1.4),
                model=_tri(rng, 1.0, 1.6, 3.2),
                tool=_tri(rng, 0.6, 1.2, 2.6) if needs_tool else 0.0,
                tts=_tri(rng, 0.4, 0.6, 1.1))


def stream_turn(rng, needs_tool: bool) -> Turn:
    t = Turn(endpoint=_tri(rng, 0.25, 0.4, 0.75),
             asr=_tri(rng, 0.08, 0.12, 0.25),
             model=_tri(rng, 0.35, 0.55, 1.1),   # to the first sentence
             tool=_tri(rng, 0.6, 1.2, 2.6) if needs_tool else 0.0,
             tts=_tri(rng, 0.12, 0.18, 0.3))     # first audio chunk
    if t.asr + t.model + t.tool + t.tts > HOLD_AT_S:
        # holding phrase: canned audio at a fixed time, nothing generated
        return Turn(t.endpoint, t.asr, t.model, t.tool, t.tts, held=True)
    return t


def simulate(n: int = 2_000, seed: int = 23, tool_share: float = 0.35,
             streaming: bool = True) -> list[Turn]:
    rng = seeded(seed, "voice", "turns")
    make = stream_turn if streaming else batch_turn
    return [make(rng, rng.random() < tool_share) for _ in range(n)]


def pct(xs: list[float], p: float) -> float:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p * (len(xs) - 1))))]


def summary(turns: list[Turn]) -> dict:
    tot = [t.total for t in turns]
    return {"p50": statistics.median(tot), "p95": pct(tot, 0.95),
            "max": max(tot), "over": sum(x > BUDGET_S for x in tot),
            "held": sum(t.held for t in turns), "n": len(tot)}


def stage_means(turns: list[Turn]) -> dict:
    keys = ("endpoint", "asr", "model", "tool", "tts")
    return {k: statistics.fmean(getattr(t, k) for t in turns) for k in keys}


def read_back(n: int = 1_000, seed: int = 23, mishear: float = 0.04,
              caught: float = 0.97, enabled: bool = True) -> dict:
    """Spoken amounts and dates: how many wrong values reach a proposal.

    mishear: share of spoken values transcribed wrong. caught: share of
    wrong read-backs the caller corrects. A correction is transcribed
    again and read back again, up to twice, then the call goes to a
    person."""
    rng = seeded(seed, "voice", "readback")
    first = seeded(seed, "voice", "heard")
    wrong_in = wrong_out = to_person = confirmations = 0
    for _ in range(n):
        wrong = first.random() < mishear
        wrong_in += wrong
        if not enabled:
            wrong_out += wrong
            continue
        tries = 0
        while True:
            confirmations += 1
            if not wrong:
                break
            if rng.random() < caught:
                tries += 1
                if tries > 2:
                    to_person += 1
                    break
                wrong = rng.random() < mishear
                continue
            wrong_out += 1
            break
    return {"values": n, "misheard": wrong_in, "reached": wrong_out,
            "to_person": to_person, "read_backs": confirmations}
