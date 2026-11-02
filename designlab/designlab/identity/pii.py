"""Data classes: what may reach the context, the trail, and the trace.

Four classes on a servicing case, each with one rule:

  card               tokenized before context; the trail keeps the
                     vault reference; the raw number stays in the
                     payment vault
  identity document  omitted from context (the model gets "on file"
                     and the expiry); the trail keeps a reference
  contact            never in context; the notify tool's server reads
                     it from the profile system through the broker
  preference         allowed (seat, meal)

Free text (a customer's message, a case note) is scanned for card and
document shapes as well, because customers type card numbers into
chat. `find_everywhere` is the seeded-value search: plant a known
value and look in every durable store for it, normalized, so a format
the scanner missed still shows up.
"""
from __future__ import annotations

import hashlib
import json
import re

from common.rand import seeded

PAN = re.compile(r"\b(?:\d[ -]?){13,19}\b")
PASSPORT = re.compile(r"\b[A-Z][0-9]{8}\b")
# June 26 fix: the same shape with spaces or dashes between digits
PASSPORT_LOOSE = re.compile(r"\b[A-Z](?:[ -]?[0-9]){8}\b")
RETENTION_DAYS = {"card": 0, "identity_document": 30, "contact": 0,
                  "preference": 180}


def luhn_ok(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
        alt = not alt
    return total % 10 == 0


def luhn_pan(rng, prefix: str = "4", n: int = 16) -> str:
    body = prefix + "".join(str(rng.randrange(10))
                            for _ in range(n - len(prefix) - 1))
    for check in "0123456789":
        if luhn_ok(body + check):
            return body + check
    raise AssertionError


class Vault:
    """Holds raw values; hands out references that resolve only here."""

    def __init__(self):
        self.store: dict[str, tuple[str, str]] = {}

    def tokenize(self, cls: str, value: str) -> str:
        h = hashlib.sha256(f"{cls}|{value}".encode()).hexdigest()[:10]
        ref = f"ref:{cls}/{h}"
        self.store[ref] = (cls, value)
        return ref

    def resolve(self, ref: str, purpose: str) -> str | None:
        cls, value = self.store.get(ref, ("", ""))
        allowed = {"card": {"processor_refund"},
                   "identity_document": {"check_in_apis"}}
        return value if purpose in allowed.get(cls, set()) else None


def case_record(i: int, seed: int = 32) -> tuple[dict, dict]:
    """A servicing case and the sensitive values planted in it."""
    rng = seeded(seed, "identity", "case", str(i))
    pan = luhn_pan(rng)
    passport = f"{rng.choice('KLMNPRX')}{rng.randrange(10**8):08d}"
    rec = {"case": f"CS-{620000 + i}", "customer": f"C-{118000 + i}",
           "contact": {"email": f"traveler{i}@example.com",
                       "phone": f"+1 312 555 {rng.randrange(10**4):04d}"},
           "payment": {"pan": pan, "last4": pan[-4:]},
           "preference": {"seat": rng.choice(["aisle", "window"]),
                          "meal": rng.choice(["none", "vegetarian"])},
           "note": "Customer asked for a refund to the original card."}
    if rng.random() < 0.30:
        rec["document"] = {"passport": passport, "expires": "2027-03"}
    planted = {"pan": pan}
    if "document" in rec:
        planted["passport"] = passport
    r = rng.random()
    if r < 0.05:
        rec["note"] = f"Customer typed card {pan} in chat to confirm."
    elif r < 0.08:
        rec["note"] = f"Passport {passport} per customer message."
        planted["passport"] = passport
    elif r < 0.09:
        spaced = f"{passport[0]} {passport[1:5]} {passport[5:]}"
        rec["note"] = f"Passport no. {spaced} (customer typed it)."
        planted["passport"] = passport
    return rec, planted


def scrub_text(text: str, vault: Vault, loose: bool = False) -> str:
    def card(m):
        digits = re.sub(r"[ -]", "", m.group(0))
        if 13 <= len(digits) <= 19 and luhn_ok(digits):
            return vault.tokenize("card", digits)
        return m.group(0)
    text = PAN.sub(card, text)
    shape = PASSPORT_LOOSE if loose else PASSPORT
    return shape.sub(lambda m: vault.tokenize("identity_document",
                                              norm(m.group(0))), text)


def as_found_context(rec: dict) -> dict:
    """June 16: the booking record went into context whole."""
    return json.loads(json.dumps(rec))


def assemble_context(rec: dict, vault: Vault,
                     loose: bool = False) -> dict:
    ctx = {"case": rec["case"], "customer": rec["customer"],
           "payment": {"card": vault.tokenize("card",
                                              rec["payment"]["pan"]),
                       "last4": rec["payment"]["last4"]},
           "preference": rec["preference"],
           "note": scrub_text(rec["note"], vault, loose)}
    if "document" in rec:
        ctx["document"] = {"passport": "on file",
                           "expires": rec["document"]["expires"]}
    return ctx


def norm(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", text)


def find_everywhere(value: str, stores: dict[str, list[str]]) -> list:
    """Every store holding the value, however it was formatted."""
    v = norm(value)
    return sorted(name for name, docs in stores.items()
                  if any(v in norm(d) for d in docs))


def replay(n: int = 200, fixed: bool = True, seed: int = 32,
           loose: bool = False) -> dict:
    """Count raw sensitive values that reached context and trace."""
    vault = Vault()
    hits = {"card": 0, "identity_document": 0, "contact": 0}
    missed = []
    for i in range(n):
        rec, planted = case_record(i, seed)
        ctx = assemble_context(rec, vault, loose) if fixed else \
            as_found_context(rec)
        blob = json.dumps(ctx)
        # the trace store keeps what the context held
        stores = {"context": [blob], "trace": [blob]}
        if find_everywhere(planted["pan"], stores):
            hits["card"] += 1
        if "passport" in planted:
            if find_everywhere(planted["passport"], stores):
                hits["identity_document"] += 1
                if fixed:
                    missed.append(rec["case"])
        if rec["contact"]["email"] in blob:
            hits["contact"] += 1
    return {"cases": n, "hits": hits, "missed": missed}
