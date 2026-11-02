"""Chapter 16 live lab: twenty argument cases against the small model.

Each case gives the model one case packet, one customer message and one
tool with strict tool use on. The proposed arguments go through the
same intake as the demo. A rejected call goes back as a tool result
with the structured reason, at most twice; the model may also stop
and say why, which sends the case to a person.
Reads ANTHROPIC_API_KEY from the environment through common.client and
never prints it. About 60 short calls; the meter caps spend at $0.05.

    python3 -m toolargs.live
"""
from __future__ import annotations

import json

from common.client import ModelClient
from common.clock import FixedClock
from common.spend import SpendMeter
from common.text import emit
from common.trail import TrailWriter

from . import schema, world
from .cases import LIVE_CASES, OFFERS, PACKET
from .layer import Intake
from .tools import TOOLS, api_tool

SYSTEM = ("You are Lakeshore Travel Group's servicing agent. Act only "
          "by calling the tool. Use only identifiers that belong to "
          "this case's itinerary. If a tool result reports an error, "
          "fix the named field from the packet or stop and say why.")


class ToolClient(ModelClient):
    """ModelClient with a tools field. Same meter, same transport."""

    def call(self, messages: list, tool: dict, force: bool,
             max_tokens: int = 400) -> dict:
        body = {"model": self.pin.id, "max_tokens": max_tokens,
                "system": SYSTEM, "messages": messages,
                "tools": [api_tool(tool)],
                "tool_choice": ({"type": "tool", "name": tool["name"]}
                                if force else {"type": "auto"})}
        chars = len(json.dumps(body))
        self.meter.check(self.pin, chars, max_tokens)
        resp = self.transport(body)
        self.meter.record(self.pin, resp.get("usage", {}))
        resp["_pinned"] = self.pin.id
        return resp


def tool_use(resp: dict):
    for b in resp.get("content", []):
        if b.get("type") == "tool_use":
            return b
    return None


def run_case(client: ToolClient, case, intake: Intake,
             budget: int = 2) -> dict:
    tool = TOOLS[case.tool]
    user = f"{PACKET[case.session]} {OFFERS}\nCustomer: {case.message}"
    messages = [{"role": "user", "content": user}]
    out = {"name": case.name, "trap": case.trap, "attempts": [],
           "status": None, "drift": False}
    force, repairs = True, 0
    while True:
        resp = client.call(messages, tool, force)
        out["drift"] |= resp.get("model") != resp["_pinned"]
        block = tool_use(resp)
        if block is None:
            # The model stopped and said why: a person takes the case.
            out["status"] = "stopped" if out["attempts"] else "declined"
            return out
        args = block["input"]
        shape = not schema.validate(args, tool["input_schema"])
        v = intake.check(case.session, case.tool, args)
        reason = v.errors[0].get("reason") if v.errors else None
        out["attempts"].append({"shape": shape, "ok": v.ok,
                                "reason": reason, "args": args,
                                "errors": v.errors,
                                "stop": resp.get("stop_reason")})
        if v.ok:
            out["status"] = "repaired" if repairs else "passed"
            return out
        if repairs >= budget:
            out["status"] = "handed_off"
            return out
        repairs += 1
        messages += [
            {"role": "assistant", "content": resp["content"]},
            {"role": "user", "content": [{
                "type": "tool_result", "tool_use_id": block["id"],
                "is_error": True,
                "content": json.dumps(v.for_model(budget - repairs))}]}]
        force = False


def run(client: ToolClient | None = None) -> list[dict]:
    client = client or ToolClient("small", meter=SpendMeter(cap_usd=0.05))
    w = world.build()
    trail = TrailWriter(clock=FixedClock(
        start="2026-05-18T09:00:00-05:00"))
    intake = Intake(w, trail)
    results = [run_case(client, c, intake) for c in LIVE_CASES]
    results.append({"spent": client.meter.spent_usd,
                    "calls": client.meter.calls})
    return results


def summarize(results: list[dict]) -> list[str]:
    cases = [r for r in results if "name" in r]
    meta = results[-1]
    first = [r["attempts"][0] for r in cases if r["attempts"]]
    lines = [f"cases {len(cases)}  model calls {meta['calls']}  "
             f"spent ${meta['spent']:.4f}"]
    lines.append(f"schema-valid first proposals  "
                 f"{sum(a['shape'] for a in first)} of {len(first)}")
    lines.append(f"world-rejected first proposals "
                 f"{sum(not a['ok'] for a in first)} of {len(first)}")
    for s in ("passed", "repaired", "handed_off", "stopped"):
        lines.append(f"  {s:12} {sum(r['status'] == s for r in cases)}")
    attempts = [a for r in cases for a in r["attempts"]]
    bad = [a for a in attempts if not a["shape"]]
    lines.append(f"proposals {len(attempts)}, malformed {len(bad)}, "
                 f"stop reasons {sorted({a['stop'] for a in bad})}"[:70])
    lines.append(f"drift from pinned model: "
                 f"{sum(r['drift'] for r in cases)}")
    for r in cases:
        path = ",".join("ok" if a["ok"] else (a["reason"] or "schema")
                        for a in r["attempts"]) or "-"
        lines.append(f"{r['name'][:24]:24} {r['status']:10} {path}"[:70])
    return lines


if __name__ == "__main__":
    for line in summarize(run()):
        emit(line)
