"""What recurs across the worked designs, read from the specs.

Each pattern is a predicate over a spec. A pattern that holds in every
design is the method's; one that holds in some is the industry's. The
chapter's Section 7 reads this table.
"""
from __future__ import annotations

from .lint import cus_1, cus_2, ind_1, reg_1
from .templates import derived_tier

SHORT = {"telecom-care": "tel", "lakeshore-rebooking": "rbk",
         "lakeshore-refunds": "rfd", "bank-payments": "bnk",
         "insurer-claims": "clm", "lender-collections": "col"}


def _gate_outside(s):
    return bool(s.get("gaps", {}).get("G2", {}).get("answer"))


def _independent(s):
    return not ind_1(s) and all(v.get("written_by")
                                for v in s.get("verifiers", []))


def _ladder(s):
    return any(derived_tier(e) for e in s.get("effects", []))


def _never(s):
    return any(e.get("tier") == "never" for e in s.get("effects", []))


def _reserved(s):
    return any(e.get("reserved") for e in s.get("effects", []))


def _promise(s):
    return bool(s.get("human_gate", {}).get("promise_minutes"))


def _status(s):
    return not cus_1(s) and not cus_2(s)


def _rules_outside(s):
    return bool(s.get("obligations")) and not reg_1(s)


def _surge(s):
    return "surge" in s


PATTERNS = (
    ("permission outside the loop", _gate_outside),
    ("verifier reads what it cannot write", _independent),
    ("customer status from the chain", _status),
    ("promised time on every hand-off", _promise),
    ("obligations in control or trail", _rules_outside),
    ("tier set by the amount", _ladder),
    ("a decision kept for a person", _reserved),
    ("an effect the agent never takes", _never),
    ("surge rule signed in advance", _surge),
)


def table(specs: dict[str, dict]) -> list[tuple[str, list[bool]]]:
    return [(name, [fn(s) for s in specs.values()])
            for name, fn in PATTERNS]
