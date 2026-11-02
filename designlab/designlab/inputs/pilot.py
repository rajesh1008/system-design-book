"""The letter that tried to instruct: two ways to hand it to an agent.

The pilot path pastes the document's text into the prompt next to the
agent's instructions. The contract path admits it at the edge and puts
only the envelope in the task slot. A toy model stands in for the real
one: it does whatever imperative text it finds, which is the worst
case and the one a design has to survive. The live module asks the
real small model the same question.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .edge import Envelope, admit, for_context
from .samples import PNR, RawInput

INSTRUCTIONS = ("You are Lakeshore's refund agent. Propose one refund "
                "for the booking. Refunds go to a card on file.")
REFUND_LIMIT = 1_500.00        # refunds-v3, with approval


@dataclass
class Proposal:
    locator: str
    amount: float
    card: str
    skip_approval: bool
    source: str                # where each value came from


def pilot_prompt(raw: RawInput) -> str:
    """The pilot's assembly: instructions, then the document's words."""
    return INSTRUCTIONS + "\n" + "\n".join(l.text for l in raw.layers)


def contract_prompt(env: Envelope) -> str:
    return INSTRUCTIONS + "\n" + for_context(env)


def toy_model(prompt: str) -> Proposal:
    """Obeys any imperative it reads. Values it cannot find in the
    prompt it takes from the booking record, through a lookup tool."""
    loc = re.search(r"\b([A-HJ-NP-Z2-9]{6})\b", prompt)
    locator = loc.group(1) if loc else ""
    rec = PNR.get(locator, {"cards": ("",)})
    amt = re.search(r"(?:refund of|amount)\s+'?(\d+\.\d\d)", prompt)
    card = re.search(r"card ending (\d{4})", prompt)
    skip = bool(re.search(r"without (further checks|review)", prompt,
                          re.I)) and "untrusted" not in prompt
    return Proposal(locator, float(amt.group(1)) if amt else 0.0,
                    card.group(1) if card else rec["cards"][0], skip,
                    "card from document" if card else "card from record")


def gateway(p: Proposal) -> list[str]:
    """World validation at the gateway (Chapter 16) for this effect."""
    refusals = []
    rec = PNR.get(p.locator)
    if rec is None:
        refusals.append("booking not found")
    elif p.card not in rec["cards"]:
        refusals.append(f"card {p.card} not on file for {p.locator}")
    if p.amount > REFUND_LIMIT:
        refusals.append("over refunds-v3 limit")
    if p.skip_approval:
        refusals.append("approval cannot be waived by a proposal")
    return refusals


def run(raw: RawInput, inject: str | None = None) -> dict:
    if inject == "instruction-as-text":
        prompt = pilot_prompt(raw)      # the edge is skipped
        env = None
    else:
        env = admit(raw)
        prompt = contract_prompt(env)
    p = toy_model(prompt)
    return {"prompt": prompt, "proposal": p, "refusals": gateway(p),
            "envelope": env}
