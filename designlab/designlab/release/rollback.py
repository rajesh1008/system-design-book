"""Rollback: the unit is the bundle, and the runs in flight decide
what rolling back means.

Rolling back sets the active pointer to the parent bundle for new
runs. Every run already started was started on the candidate, and its
state was written by the candidate, so each one needs a rule by where
it is in its life: queued, started with no effect, waiting on an
approval bound to the candidate's proposal, effect sent and waiting
for its verdict, or done. State the candidate wrote is kept, tagged
with its bundle hash, and read by the reconciler, never deleted.
Lakeshore figures are illustrative.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from .bundle import Bundle, trail_line

STATES = ("queued", "started", "awaiting_approval", "awaiting_verdict",
          "done")
RULE = {
    "queued": "re-route to the parent bundle",
    "started": "abandon checkpoint; restart on the parent",
    "awaiting_approval": "cancel the card; re-propose on the parent",
    "awaiting_verdict": "no agent step left; reconciler verifies",
    "done": "keep; audit by bundle hash",
}


@dataclass
class InFlight:
    run_id: str
    state: str
    bundle: str


def rollback(active: Bundle, parent: Bundle, runs: list[InFlight],
             stamp: str) -> dict:
    """Plan the rollback. Returns per-state actions and trail lines."""
    plan: dict[str, list[str]] = {s: [] for s in STATES}
    for r in runs:
        if r.bundle and r.bundle != active.hash:
            continue
        plan[r.state].append(r.run_id)
    trail = [f"{stamp} rollback {active.hash} -> {parent.hash}"]
    for s in STATES:
        for rid in plan[s]:
            if s in ("queued", "started", "awaiting_approval"):
                t = trail_line(rid, parent, "rerouted")
                trail.append(f"{rid} -> {t['bundle']} {t['harness']}")
    return {"plan": plan, "trail": trail}


def inflight(seed: int = 723) -> list[InFlight]:
    """The 1.1.0 refund canary at 08:40 CDT on Thursday, July 30:
    the morning's queue, plus the runs whose refunds went out after
    the last settlement file closed."""
    rng = random.Random(seed)
    want = {"queued": 4, "started": 7, "awaiting_approval": 6,
            "awaiting_verdict": 23, "done": 59}
    out = []
    n = 0
    for s, k in want.items():
        for _ in range(k):
            n += 1
            out.append(InFlight(f"run-0730-{n:03d}", s, ""))
    rng.shuffle(out)
    return out


# ---- memory written by a canary --------------------------------------

@dataclass
class MemRecord:
    rid: str
    schema: int
    fields: dict


V2_FIELDS = ("seat", "meal", "assist", "contact")


def downcast(rec: MemRecord) -> MemRecord | None:
    """v3 to v2 if no v3-only field carries a value, else None."""
    extra = {k: v for k, v in rec.fields.items() if k not in V2_FIELDS}
    if any(v not in (None, "", []) for v in extra.values()):
        return None
    return MemRecord(rec.rid, 2, {k: rec.fields.get(k)
                                  for k in V2_FIELDS})


def schema3_writes(seed: int = 819) -> list[MemRecord]:
    """Traveler records written by the 5% rebooking canary of memory
    schema 3, August 19 to 20. Schema 3 split `assist` into
    `assist_need` and `assist_window`."""
    rng = random.Random(seed)
    out = []
    for i in range(41):
        f = {"seat": rng.choice(["aisle", "window", None]),
             "meal": rng.choice(["vgml", None, None]),
             "contact": "sms"}
        if rng.random() < 0.3:
            f["assist_need"] = rng.choice(["wchr", "blnd", "deaf"])
            f["assist_window"] = "45m"
        else:
            f["assist"] = None
            f["assist_need"] = None
            f["assist_window"] = None
        out.append(MemRecord(f"tm-{i:04d}", 3, f))
    return out


def read_v2(rec: MemRecord) -> dict | None:
    """The v2 reader in the packet gate: unknown schema is skipped,
    silently, which is what the canary taught us not to do."""
    return rec.fields if rec.schema == 2 else None
