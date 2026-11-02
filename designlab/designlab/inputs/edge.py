"""The edge: where every input becomes an envelope tagged untrusted.

admit() is the only way an input reaches the agent. It hashes the raw
layers, records provenance, keeps only the contract's fields, checks
identifiers against records Lakeshore controls, raises signals, and
routes each field. The assembler gate refuses anything that is not an
envelope, so an adapter that skips admit() fails loudly.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field

from .contract import CONTRACTS, READ_BACK, TRUST, Contract
from .samples import PNR, PROFILE, SUPPLIERS, RawInput

ACCEPT, REVIEW, ASK, REJECT = "accept", "review", "ask", "reject"

# Instruction-like phrasing: a sensor, not a judge. A hit is recorded
# and shown to the reviewer; a miss grants nothing.
IMPERATIVE = re.compile(
    r"\b(ignore (all|prior|previous)|supersedes?|approve\b|without "
    r"(review|further checks)|note (for|to) (automated )?(assistants?|"
    r"ai|agents?)|agent(s)?:|assistant:|system:|you (must|should)|"
    r"your agent should|send the refund to|skip approval|upgrade this"
    r"|do not tell|forward (the|this))", re.I)


@dataclass(frozen=True)
class Provenance:
    input_id: str
    channel: str
    sender: str
    received_at: str
    sha256: str
    extractor: str
    contract: str


@dataclass
class FieldValue:
    name: str
    value: str
    confidence: float
    where: str
    route: str = ""
    reasons: list[str] = field(default_factory=list)


@dataclass
class Envelope:
    trust: str
    provenance: Provenance
    fields: dict[str, FieldValue]
    signals: dict[str, list[str]]
    quarantined: int          # characters kept out of the agent's view
    read_back: list[str]

    @property
    def route(self) -> str:
        order = (REJECT, ASK, REVIEW, ACCEPT)
        routes = [f.route for f in self.fields.values()] or [REVIEW]
        if self.signals["instruction_like"] or self.signals["hidden_text"]:
            routes.append(REVIEW)
        return next(r for r in order if r in routes)


def digest(raw: RawInput) -> str:
    body = json.dumps([[l.text, l.visible, l.where] for l in raw.layers])
    return hashlib.sha256(body.encode()).hexdigest()


def _check(name: str, kind: str | None, value: str,
           env_fields: dict) -> str | None:
    """Return a reason if the value disagrees with a record we control."""
    if kind is None:
        return None
    if kind == "pnr":
        loc = env_fields.get("locator")
        rec = PNR.get(loc.value) if loc else None
        if rec is None:
            return "locator not found"
        if name != "locator" and rec.get(name) != value:
            return f"{name} does not match the booking"
    if kind == "profile":
        sur = env_fields.get("surname"); giv = env_fields.get("given")
        key = f"{sur.value}/{giv.value}" if sur and giv else ""
        rec = PROFILE.get(key)
        if rec is None:
            return "traveler not on file"
        if name == "number" and rec["number"] != value:
            return "number does not match the profile"
    if kind == "supplier" and value not in SUPPLIERS:
        return "supplier not under contract"
    return None


def _route(f, conf: float, valid: bool, mismatch: str | None) -> str:
    if not valid:
        return REJECT
    if conf < f.review_at:
        return ASK
    if mismatch or conf < f.accept_at:
        return REVIEW
    return ACCEPT


def admit(raw: RawInput, contract: Contract | None = None,
          accept_shift: float = 0.0) -> Envelope:
    c = contract or CONTRACTS[raw.contract]
    prov = Provenance(raw.input_id, raw.channel, raw.sender,
                      raw.received_at, digest(raw), raw.extractor,
                      f"{c.name}/{c.version}")
    fields: dict[str, FieldValue] = {}
    for f in c.fields:                         # contract fields only
        if f.name in raw.extracted:
            v, conf, where = raw.extracted[f.name]
            fields[f.name] = FieldValue(f.name, v, conf, where)
    for f in c.fields:
        fv = fields.get(f.name)
        if fv is None:
            continue
        valid = f.valid(fv.value)
        mismatch = _check(f.name, f.check, fv.value, fields)
        fv.route = _route(f, fv.confidence + accept_shift, valid, mismatch)
        if not valid:
            fv.reasons.append("value outside the contract")
        if mismatch:
            fv.reasons.append(mismatch)
    signals = {"instruction_like": [], "hidden_text": []}
    for layer in raw.layers:
        if IMPERATIVE.search(layer.text):
            signals["instruction_like"].append(layer.where)
        if not layer.visible:
            signals["hidden_text"].append(layer.where)
    kept = sum(len(fv.value) for fv in fields.values())
    total = sum(len(l.text) for l in raw.layers)
    rb = [n for n in READ_BACK if n in fields] if c.modality == "voice" \
        else []
    return Envelope(TRUST, prov, fields, signals, total - kept, rb)


class NotAdmitted(TypeError):
    pass


def for_context(item) -> str:
    """The assembler gate: only envelopes, rendered as quoted data."""
    if not isinstance(item, Envelope) or item.trust != TRUST:
        raise NotAdmitted("input did not cross the edge")
    p = item.provenance
    lines = [f"input {p.input_id}  {p.contract}  via {p.channel}",
             f"  trust {item.trust}  route {item.route}"]
    for fv in item.fields.values():
        lines.append(f"  {fv.name:<14} {fv.value:<15} "
                     f"{fv.confidence:.2f}  {fv.route}")
    for k, v in item.signals.items():
        if v:
            lines.append(f"  signal {k}: {len(v)}")
    return "\n".join(lines)


def to_context_item(env: Envelope):
    """A context.slots Item for the task slot, if Chapter 14's package
    is installed. The item carries the envelope's rendering, never the
    raw text."""
    from context.slots import Item      # soft: optional package
    text = for_context(env)
    return Item(slot="task", key=env.provenance.input_id,
                tokens=max(1, len(text) // 4), text=text)


# Every path by which outside content reaches Lakeshore's agent, and the
# adapter that carries it. The edge test walks this list.
INTAKE_PATHS = {
    "docs": "docs.lakeshore.internal upload extractor",
    "ocr": "ocr.lakeshore.internal image extractor",
    "email-attachment": "mail intake, attachments to docs or ocr",
    "chat-upload": "chat widget uploads to ocr",
    "voicemail": "voicemail transcripts from the telephony vendor",
    "notices": "notice_read over notices.lakeshore.internal",
}


def adapter(path: str):
    """Each intake adapter is admit() bound to its channel."""
    if path not in INTAKE_PATHS:
        raise KeyError(path)

    def run(raw: RawInput) -> Envelope:
        if raw.channel != path:
            raise ValueError("input arrived on another path")
        return admit(raw)
    return run
