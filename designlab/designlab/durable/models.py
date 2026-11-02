"""Model fixtures. No live API: each returns a fixed answer.

fixture-a picks the earliest departure. fixture-b, a later model,
picks the lowest fare. Sampled wraps fixture-a and answers a second
call for the same step differently on some runs, the way a sampled
model can when it is asked again after a restart.
"""
from __future__ import annotations

import hashlib


class FixtureA:
    name = "fixture-a"

    def __init__(self):
        self.calls = 0

    def call(self, run_id: str, step: str, payload: dict) -> dict:
        self.calls += 1
        if step == "model_plan":
            plan = "rebook+refund" if payload["kind"] == "refund" \
                else "rebook"
            return {"plan": plan, "model": self.name}
        opts = payload["options"]
        return {"flight": self.pick(opts)["flight"], "model": self.name}

    def pick(self, opts):
        return min(opts, key=lambda o: (o["dep"], o["fare"]))


class FixtureB(FixtureA):
    name = "fixture-b"

    def pick(self, opts):
        return min(opts, key=lambda o: (o["fare"], o["dep"]))


class Sampled(FixtureA):
    """Second and later calls for a step pick another flight on runs
    whose id hashes into the given share."""
    name = "fixture-a-sampled"

    def __init__(self, share: float = 0.5):
        super().__init__()
        self.share = share
        self.seen: dict[tuple, int] = {}

    def call(self, run_id, step, payload):
        k = (run_id, step)
        self.seen[k] = self.seen.get(k, 0) + 1
        out = super().call(run_id, step, payload)
        h = int(hashlib.sha256(run_id.encode()).hexdigest()[:4], 16)
        if step == "model_choose" and self.seen[k] > 1 \
                and h / 0xFFFF < self.share:
            opts = sorted(payload["options"], key=lambda o: o["dep"])
            out["flight"] = opts[-1]["flight"]
        return out
