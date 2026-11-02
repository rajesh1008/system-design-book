"""The controls this chapter adds, and a stand-in for the policy check.

- `bound`: the session binding. The session token names one tenant and
  one itinerary (Chapter 11's blast radius of one itinerary); a call
  that names any other itinerary is refused before the gateway, and the
  trail line records both identities, the agent and the customer it
  acts for.
- `decide`: the control plane's answer to an effect proposal, reduced
  to the rules the battery touches (refunds-v3, vouchers-v1, and
  memory is not authority). Chapter 31's engine replaces it.
- `reply_problems`: the chat widget renders text, links only to
  Lakeshore's own pages, and no remote images.
- `code_urls`: the URLs a code run will ask the proxy for.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from memory.policy import grounds_problems

REFUND_CAP_USD = 1500.00        # refunds-v3
REBOOK_CAP_USD = 250.00         # rebook-v2
VOUCHER_CAP_USD = 100.00        # vouchers-v1
REPLY_LINK_HOSTS = ("www.lakeshore.com", "help.lakeshore.com")
OBJECT_FIELDS = ("itinerary_id", "booking_ref")


@dataclass(frozen=True)
class Session:
    """Issued at sign-in; never built from conversation text."""
    session_id: str
    tenant: str
    itinerary: str
    agent: str = "agent:servicing"


def bound(session: Session, tool: str, args: dict, trail) -> str:
    """Empty when every object the call names is the session's own."""
    for f in OBJECT_FIELDS:
        v = args.get(f)
        if v is not None and v != session.itinerary:
            trail.append({"event": "session_refused", "tool": tool,
                          "agent": session.agent,
                          "on_behalf_of": session.tenant,
                          "session_itinerary": session.itinerary,
                          "asked": v})
            return "not_this_session"
    return ""


@dataclass
class Facts:
    """What code read from systems of record for this case."""
    refundable: dict             # ticket -> refundable fare, USD
    quote: dict = None           # flight -> fare difference, USD
    flight_canceled: bool = True
    facts: dict | None = None    # for memory.policy.grounds_problems


def decide(tool: str, args: dict, facts: Facts,
           grounds: list[str]) -> tuple[bool, str]:
    """(permit, reason). A permit is a permission for one exact call."""
    problems = grounds_problems(facts, grounds)
    if problems:
        return False, "memory is not authority"
    if tool == "refund_ticket":
        amt = float(args["amount_usd"])
        fare = facts.refundable.get(args["ticket_number"], 0.0)
        if args["reason"] == "goodwill":
            return False, "goodwill needs a person"
        if amt > REFUND_CAP_USD:
            return False, "over refunds-v3 cap 1500.00"
        if amt > fare:
            return False, f"over refundable fare {fare:.2f}"
        if args["reason"] == "canceled_by_carrier" and not \
                facts.flight_canceled:
            return False, "flight not canceled"
        return True, "refunds-v3, approver desk"
    if tool == "voucher_issue":
        if float(args["amount_usd"]) > VOUCHER_CAP_USD:
            return False, "over vouchers-v1 cap 100.00"
        return True, "vouchers-v1"
    if tool == "rebook_ticket":
        q = (facts.quote or {}).get(args["new_flight_id"])
        asked = float(args["fare_difference_usd"])
        if q is None or abs(asked - q) > 0.005:
            return False, "fare difference is code's"
        if q > REBOOK_CAP_USD:
            return False, "over rebook-v2 cap 250.00"
        return True, "rebook-v2"
    return True, "within policy"


IMG = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)|(https?://\S+)")


def reply_problems(text: str) -> list[str]:
    out = []
    for m in IMG.finditer(text):
        out.append(f"remote image {urlsplit(m.group(1)).hostname}")
    stripped = IMG.sub("", text)
    for m in LINK.finditer(stripped):
        url = (m.group(1) or m.group(2)).rstrip(").,")
        host = urlsplit(url).hostname or ""
        if host not in REPLY_LINK_HOSTS:
            out.append(f"link to {host}")
    return out


URL = re.compile(r"https?://[^\s'\")]+")


def code_urls(code: str) -> list[str]:
    return URL.findall(code)
