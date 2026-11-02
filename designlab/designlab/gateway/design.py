"""Writing tools an agent can use well: the checks and the evidence.

Five properties, each checkable: a narrow purpose, a clear name,
typed identifiers, a small output, and errors the model can act on.
The before and after are booking_read 1.3 and 1.4, and the read
tools' error catalogs before and after the rewrite of late May 2026.
Lakeshore figures are illustrative.
"""
from __future__ import annotations

import re

from .core import tokens_of
from .servers import booking_history, booking_summary

NAME = re.compile(r"^[a-z]+(_[a-z]+)+$")
ID_FIELDS = re.compile(r"(_ref|_id|_number)$")

# What the read tools returned on failure before the rewrite.
ERRORS_BEFORE = {
    "booking_read": [{"error": "404"}, {"error": "timeout"}],
    "fare_calc": [{"error": "invalid request"}, {"error": "null"}],
    "fare_rules_search": [{"error": "no results"}],
    "flight_status": [{"error": "upstream 503"}],
    "offers_search": [{"error": "invalid request"},
                      {"error": "sold out"}],
    "notice_read": [{"error": "not found"}],
}

# The same failures after: what went wrong, which field, what to do.
ERRORS_AFTER = {
    "booking_read": [
        {"error": "booking_not_found", "field": "booking_ref",
         "fix": "use the reference in the case packet",
         "retryable": False},
        {"error": "source_slow", "field": "",
         "fix": "retry once after 2 s, then hand off",
         "retryable": True}],
    "fare_calc": [
        {"error": "ticket_not_on_booking", "field": "ticket_number",
         "fix": "take ticket numbers from booking_read",
         "retryable": False},
        {"error": "fare_not_refundable", "field": "ticket_number",
         "fix": "check credit_issue; the fare allows a credit",
         "retryable": False}],
    "fare_rules_search": [
        {"error": "no_rule_for_product", "field": "fare_product",
         "fix": "search by carrier only, then read the rule",
         "retryable": False}],
    "flight_status": [
        {"error": "status_feed_down", "field": "",
         "fix": "use notice_read for the waiver, or hand off",
         "retryable": True}],
    "offers_search": [
        {"error": "segment_out_of_range", "field": "segment",
         "fix": "segments are numbered from 1 in booking_read",
         "retryable": False},
        {"error": "no_seats_left", "field": "",
         "fix": "search the next day, or hand off",
         "retryable": False}],
    "notice_read": [
        {"error": "notice_not_found", "field": "notice_id",
         "fix": "take the notice id from flight_status",
         "retryable": False}],
}


def actionable(err: dict) -> bool:
    """The model can act on it: a reason, a fix, and whether to retry."""
    return bool(err.get("error")) and bool(err.get("fix")) and \
        "retryable" in err


def share_actionable(catalog: dict) -> tuple[int, int]:
    errs = [e for v in catalog.values() for e in v]
    return sum(actionable(e) for e in errs), len(errs)


def check_tool(spec: dict, sample_output: dict | list) -> dict:
    props = spec["input_schema"].get("properties", {})
    ids = [n for n in props if ID_FIELDS.search(n)]
    untyped = [n for n in ids if "pattern" not in props[n]]
    words = len(spec["description"].split())
    return {"name": bool(NAME.match(spec["name"])),
            "purpose_words": words,
            "ids_typed": not untyped,
            "out_tokens": tokens_of(sample_output)}


def booking_read_before_after(ref: str = "LTG-5208877") -> dict:
    hist = booking_history(ref)
    return {"v1.3_lines": len(hist),
            "v1.3_tokens": tokens_of("\n".join(hist)),
            "v1.4_tokens": tokens_of(booking_summary(ref))}
