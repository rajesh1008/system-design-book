"""Deterministic replay from the step journal.

Strict replay reads every recorded result and calls nothing: not the
model, not the desk, not the airline, not the processor. It recomputes
the pure steps (the proposal) with whatever code it is given and stops
at the first step whose result differs from the record.

Passing a model fixture asks a different question: what would this
model have chosen on the same inputs? The world is still never called.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field

from .store import RunStore
from .workflow import Spec, propose_v1


class NoCalls:
    """Stands in for the model and the world during strict replay."""

    name = "none"

    def call(self, *a, **k):
        raise AssertionError("strict replay called out")


@dataclass
class Replay:
    run_id: str
    steps: int = 0
    model_calls: int = 0
    divergence: dict | None = None
    decision: dict = field(default_factory=dict)

    def line(self) -> str:
        if self.divergence is None:
            return (f"{self.run_id}: {self.steps} steps replayed, "
                    f"model calls {self.model_calls}, no divergence")
        d = self.divergence
        return (f"{self.run_id}: diverged at step {d['seq']} "
                f"{d['step']}\n  recorded {d['recorded']}, "
                f"replay got {d['got']}")


def same(step: str, a: dict, b: dict) -> bool:
    keys = {"model_plan": ("plan",), "model_choose": ("flight",),
            "propose": ("flight", "refund_usd")}.get(step)
    if keys is None:
        return a == b
    return all(a.get(k) == b.get(k) for k in keys)


def replay(conn: sqlite3.Connection, run_id: str, model=None,
           propose=propose_v1) -> Replay:
    store = RunStore(conn)
    spec = Spec.from_json(conn.execute(
        "select spec from inbound where run_id=?", (run_id,)).fetchone()[0])
    model = model or NoCalls()
    rep = Replay(run_id)
    out: dict = {}
    for e in store.entries(run_id):
        if e["status"] != "done":
            continue
        seq, step, kind, recorded = e["seq"], e["step"], e["kind"], \
            e["output"]
        got = recorded
        if kind == "model" and not isinstance(model, NoCalls):
            payload = {"kind": spec.kind} if step == "model_plan" else \
                {"options": spec.options}
            got = model.call(run_id, step, payload)
            rep.model_calls += 1
        elif kind == "pure":
            got = propose(spec, out["model_choose"])
        out[step] = got
        rep.steps += 1
        if not same(step, recorded, got) and rep.divergence is None:
            rep.divergence = {"seq": seq, "step": step,
                              "recorded": _brief(step, recorded),
                              "got": _brief(step, got)}
            break
    rep.decision = out.get("propose", {})
    return rep


def _brief(step, d):
    if step == "model_choose":
        return d.get("flight")
    if step == "propose":
        return f"{d.get('flight')} ${d.get('refund_usd'):.2f}"
    if step == "model_plan":
        return d.get("plan")
    return json.dumps(d, sort_keys=True)
