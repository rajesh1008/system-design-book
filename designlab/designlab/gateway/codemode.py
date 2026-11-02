"""Code mode: the model writes a short program against a typed API.

The program runs in the sandbox (Chapter 11) and every function it
calls is a call through the same gateway, with the same caller, the
same checks and the same trail line, marked via="code". Only read
tools appear in the API; an effect from code is refused. Tokens are
estimated at four characters a token, and the direct path is assumed
to take one model turn per call, rereading the context each turn.
"""
from __future__ import annotations

import inspect
import json

from .core import tokens_of

TOKEN = "wl-servicing-agent"
REF = "LTG-5208877"


def api_stub(registry, caller) -> str:
    """The typed API the model reads instead of fourteen definitions."""
    lines = ["# Lakeshore read API (calls pass the tool gateway)"]
    for e in sorted(registry.approved(), key=lambda e: e.tool):
        if e.kind != "read" or e.tool not in caller.tools:
            continue
        args = ", ".join(e.schema.get("required", []))
        first = e.description.split(". ")[0].rstrip(".")
        lines.append(f"def {e.tool}({args}): ...  # {first}")
    return "\n".join(lines)


def definitions(registry, caller) -> str:
    return json.dumps([{"name": e.tool, "description": e.description,
                        "input_schema": e.schema}
                       for e in registry.approved()
                       if e.tool in caller.tools])


class API:
    """What the sandboxed program sees. Each method is a gateway call."""

    def __init__(self, gw, token: str = TOKEN):
        self._gw = gw
        self._token = token
        self.calls = 0
        self._where = {t: s for s, srv in gw.servers.items()
                       for t in srv.tools()}

    def _call(self, tool: str, **args):
        self.calls += 1
        r = self._gw.call(self._token, self._where[tool], tool, args,
                          via="code")
        if not r.ok:
            raise RuntimeError(f"{tool}: {r.reason}")
        return r.output

    def __getattr__(self, tool: str):
        if tool.startswith("_"):
            raise AttributeError(tool)
        return lambda **a: self._call(tool, **a)


def refund_check(api):
    b = api.booking_read(booking_ref="LTG-5208877")
    out = {"canceled": 0, "refundable": 0.0}
    for s in b["segments"]:
        st = api.flight_status(flight_id=s["flight_id"])
        if st["status"] == "canceled":
            out["canceled"] += 1
            out["waiver"] = api.notice_read(notice_id=st["notice_id"])[
                "waiver"]
    api.fare_rules_search(carrier="XPA", fare_product="economy",
                          query="carrier canceled refund")
    for t in b["tickets"]:
        out["refundable"] += float(api.fare_calc(ticket_number=t)[
            "refundable_usd"])
    return out


def direct_plan() -> list[tuple[str, str, dict]]:
    """The same task as one tool call per model turn."""
    plan = [("booking", "booking_read", {"booking_ref": REF})]
    for f in ("FLT-904417", "FLT-904501"):
        plan += [("status", "flight_status", {"flight_id": f}),
                 ("status", "notice_read", {"notice_id": "NTC-20611"})]
    plan.append(("fares", "fare_rules_search",
                 {"carrier": "XPA", "fare_product": "economy",
                  "query": "carrier canceled refund"}))
    plan += [("fares", "fare_calc", {"ticket_number": f"TKT-402{10 + i}"})
             for i in range(5)]
    return plan


def run_direct(gw, registry, caller, prompt_tokens: int = 600) -> dict:
    ctx = tokens_of(definitions(registry, caller)) + prompt_tokens
    processed = 0
    for server, tool, args in direct_plan():
        processed += ctx
        r = gw.call(TOKEN, server, tool, args)
        ctx += tokens_of({"tool": tool, "args": args}) + r.out_tokens
    processed += ctx
    return {"calls": len(direct_plan()), "final_context": ctx,
            "processed": processed}


def run_code(gw, registry, caller, prompt_tokens: int = 600) -> dict:
    api = API(gw)
    stub = tokens_of(api_stub(registry, caller))
    script = tokens_of(inspect.getsource(refund_check))
    first = stub + prompt_tokens
    result = refund_check(api)
    second = first + script + tokens_of(result)
    return {"calls": api.calls, "final_context": second,
            "processed": first + second, "result": result}


def effect_from_code(gw) -> str:
    api = API(gw)
    try:
        api.refund_ticket(itinerary_id=REF, ticket_number="TKT-40210",
                          amount_usd="250.00",
                          reason="canceled_by_carrier")
    except RuntimeError as e:
        return str(e)
    return "allowed"
