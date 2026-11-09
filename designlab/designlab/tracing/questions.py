"""The eleven questions an auditor asks of one refund, answered from
its trace and the gateway trail alone. An answer of None means the
trace cannot answer it: someone has to go and find out."""
from __future__ import annotations

import json
from decimal import Decimal

from . import conventions as c
from .spans import Span


def _first(spans, prefix):
    return next((s for s in spans if s.name.startswith(prefix)), None)


def _tool(spans, name):
    return next((s for s in spans
                 if s.attrs.get(c.TOOL_NAME) == name), None)


def answers(spans: list[Span], evidence: dict,
            trail: list[str]) -> list[tuple[str, str | None]]:
    root = spans[0]
    pol = _first(spans, "policy ")
    ref = _tool(spans, "refund_ticket")
    if ref is not None and ref.attrs.get(c.VERDICT) != "allowed":
        ref = next((s for s in spans if s.attrs.get(c.TOOL_NAME)
                    == "refund_ticket"
                    and s.attrs.get(c.VERDICT) == "allowed"), ref)
    ver = _first(spans, "verify ")
    fare = _tool(spans, "fare_calc")
    hashes = {json.loads(x)["call"]: x for x in trail}
    before = [s.attrs[c.TOOL_NAME] for s in spans
              if s.name.startswith("execute_tool ")
              and (pol is None or s.start_ms <= pol.start_ms)]
    models = sorted({s.attrs[c.MODEL] for s in spans
                     if s.name.startswith("chat ")})
    cost = sum(Decimal(s.attrs[c.COST]) for s in spans
               if s.name.startswith("chat "))

    def amount_source():
        if pol is None or fare is None:
            return None
        got = evidence[fare.span_id]["out"]["result"]
        if got != pol.attrs[c.AMOUNT]:
            return None
        return f"{got} from {fare.attrs[c.TOOL_CALL]}"

    def trail_link():
        if ref is None:
            return None
        line = hashes.get(ref.attrs[c.TOOL_CALL])
        if line is None:
            return None
        from common.trail import line_hash
        ok = line_hash(line)[:16] == ref.attrs.get(c.TRAIL)
        return "matches gateway line" if ok else "MISMATCH"

    return [
        ("whose case", root.attrs.get(c.CONVERSATION)),
        ("which harness", root.attrs.get(c.HARNESS_HASH)),
        ("which models", ", ".join(m.split("-")[1] for m in models)),
        ("read before deciding",
         f"{len(before)} reads, last {before[-1]}" if pol and before
         else None),
        ("amount and its source", amount_source()),
        ("policy and verdict",
         f"{pol.attrs[c.POLICY]} {pol.attrs[c.POLICY_VERDICT]}"
         if pol else None),
        ("approval wait",
         f"{pol.attrs['lakeshore.approval.wait_s']} s at the desk"
         if pol and "lakeshore.approval.wait_s" in pol.attrs else None),
        ("permit on the effect",
         ref.attrs.get(c.PERMIT) if ref and pol else None),
        ("effect vs trail", trail_link()),
        ("verified, by whom",
         f"{ver.attrs[c.VERIFY_RESULT]}, {ver.attrs[c.VERIFY_BY]}"
         if ver else None),
        ("cost of the run", f"${cost:.4f}"),
    ]
