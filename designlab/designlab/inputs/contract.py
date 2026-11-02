"""The input contract: what an input may become once it crosses the edge.

Every contract names a modality, the narrow set of fields an extractor
may return, a confidence floor for each field, and the record each
identifier must match. There is no free-text field. An input's own
words never become an instruction; the contract has no slot for one.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

TRUST = "untrusted"          # the only trust value the edge can assign
MODALITIES = ("document", "image", "voice")


@dataclass(frozen=True)
class Field:
    name: str
    pattern: str             # the value must match this, whole
    accept_at: float         # at or above: accepted, if checks pass
    review_at: float         # at or above: a person reviews; below: ask
    check: str | None = None  # record it must match ("pnr", "card", ...)

    def valid(self, value: str) -> bool:
        return re.fullmatch(self.pattern, value or "") is not None


@dataclass(frozen=True)
class Contract:
    name: str
    version: str
    modality: str
    fields: tuple[Field, ...]
    owner: str
    signals: tuple[str, ...] = ("instruction_like", "hidden_text")
    free_text: bool = False  # never True; a test holds it there

    def field(self, name: str) -> Field:
        return next(f for f in self.fields if f.name == name)


LOCATOR = r"[A-HJ-NP-Z2-9]{6}"
DATE = r"2026-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])"
MONEY = r"\d{1,5}\.\d{2}"

CONTRACTS = {c.name: c for c in (
    Contract("boarding-pass", "v1", "image", (
        Field("passenger", r"[A-Z][A-Z' -]{1,40}/[A-Z][A-Z' -]{1,40}",
              0.90, 0.60, "pnr"),
        Field("locator", LOCATOR, 0.95, 0.60, "pnr"),
        Field("flight", r"[A-Z0-9]{2}\d{1,4}", 0.90, 0.60, "pnr"),
        Field("date", DATE, 0.90, 0.60, "pnr"),
        Field("origin", r"[A-Z]{3}", 0.90, 0.60),
        Field("destination", r"[A-Z]{3}", 0.90, 0.60),
        Field("seat", r"\d{1,2}[A-K]", 0.80, 0.50),
    ), owner="Owen Fletcher"),
    Contract("passport", "v1", "image", (
        Field("surname", r"[A-Z][A-Z' -]{1,40}", 0.95, 0.70, "profile"),
        Field("given", r"[A-Z][A-Z' -]{1,40}", 0.95, 0.70, "profile"),
        Field("number", r"[A-Z0-9]{6,9}", 0.98, 0.70, "profile"),
        Field("expiry", r"20\d\d-\d\d-\d\d", 0.95, 0.70),
    ), owner="Owen Fletcher"),
    Contract("customer-letter", "v1", "document", (
        Field("locator", LOCATOR, 0.95, 0.60, "pnr"),
        Field("request", r"refund|rebook|cancel|other", 0.80, 0.50),
        Field("amount", MONEY, 0.95, 0.70),
    ), owner="Owen Fletcher"),
    Contract("supplier-notice", "v1", "document", (
        Field("supplier", r"[A-Za-z0-9 .&'-]{2,60}", 0.90, 0.60,
              "supplier"),
        Field("effective", DATE, 0.95, 0.70),
        Field("topic", r"schedule|rate|policy|closure|other", 0.80, 0.50),
    ), owner="Owen Fletcher"),
    Contract("voice-note", "v1", "voice", (
        Field("locator", LOCATOR, 0.95, 0.60, "pnr"),
        Field("request", r"refund|rebook|cancel|other", 0.80, 0.50),
        Field("date", DATE, 0.95, 0.60),
        Field("amount", MONEY, 0.95, 0.60),
    ), owner="Owen Fletcher"),
)}

# Fields whose value the customer must hear read back before any
# proposal uses it (voice), or see on screen (chat).
READ_BACK = ("amount", "date")
