"""The portability check and the migration test (Chapter 30).

check()    the same resolved Harness Manifest on both adapters: one
           hash, zero diffs, and no runtime-native field anywhere in
           the manifest. A manifest that names a thread id or a session
           id is tied to one runtime's session model.
migrate()  run cases on one adapter, kill some workers mid-run, and
           finish the in-flight runs on the other adapter, either from
           the runtime's own checkpoints or from Lakeshore's run store.
"""
from __future__ import annotations

import random
import sqlite3
from collections import Counter
from dataclasses import dataclass

from durable.store import RunStore
from harness import manifest as M
from harness.world import World, cases

from .adapters import ADAPTERS, NotPortable

STEPS = ("booking_read", "fare_calc", "request_permission",
         "refund_ticket", "verify", "close")


def native_refs(m, adapters, prefix=""):
    """Dotted paths in the manifest whose key or value names a field
    that only one runtime has."""
    fields = {f: a.name for a in adapters for f in a.native_fields}
    out = []
    if isinstance(m, dict):
        for k, v in m.items():
            path = f"{prefix}.{k}" if prefix else k
            if k in fields:
                out.append(f"{path} names {k} ({fields[k]})")
            out += native_refs(v, adapters, path)
    elif isinstance(m, list):
        for i, v in enumerate(m):
            out += native_refs(v, adapters, f"{prefix}[{i}]")
    elif isinstance(m, str) and m in fields:
        out.append(f"{prefix} names {m} ({fields[m]})")
    return out


@dataclass
class Check:
    hashes: dict
    diffs: list
    tied: list

    @property
    def ok(self) -> bool:
        return (len(set(self.hashes.values())) == 1 and not self.diffs
                and not self.tied)


def check(name: str = "servicing-1.0.0", overrides: dict | None = None,
          adapter_names=("threads", "sessions")) -> Check:
    base = M.resolve(M.load(name))
    if overrides:
        base = M.apply_overrides(base, overrides)
    adapters = [ADAPTERS[n]() for n in adapter_names]
    deployed = {a.name: M.resolve(M.load(name)) for a in adapters}
    if overrides:
        deployed = {k: M.apply_overrides(v, overrides)
                    for k, v in deployed.items()}
    hashes = {k: M.short(M.manifest_hash(v)) for k, v in deployed.items()}
    first, *rest = deployed.values()
    diffs = [d for v in rest for d in M.diff(first, v)]
    return Check(hashes, diffs, native_refs(base, adapters))


class Harness:
    """The runtime-neutral step function. Its keys come from its own
    run id; `key_from="handle"` is the tied variant that keys effects
    on whatever id the runtime hands it."""

    def __init__(self, world, store, by_id, key_from="run"):
        self.world, self.store, self.by_id = world, store, by_id
        self.key_from = key_from
        self.asked = Counter()
        self.answers = Counter()

    def fresh(self, cid):
        return {"run_id": cid, "at": 0, "amount": "0.00",
                "permit": None, "closed": False, "outcome": None}

    def advance(self, state, handle):
        s = dict(state)
        case = self.by_id[s["run_id"]]
        step = STEPS[s["at"]]
        if step == "booking_read":
            self.world.booking_read(case)
        elif step == "fare_calc":
            s["amount"] = str(self.world.fare_calc(case))
            if s["amount"] == "0.00":
                s["outcome"], s["at"] = "handoff", STEPS.index("close") - 1
        elif step == "request_permission":
            self.asked[case.cid] += 1
            if case.approve:
                s["permit"] = f"PRM-{case.cid}"
            else:
                s["outcome"], s["at"] = "declined", STEPS.index("close") - 1
        elif step == "refund_ticket":
            key = (f"{case.cid}:refund:1" if self.key_from == "run"
                   else f"{case.cid}:{handle}:refund")
            from decimal import Decimal
            r = self.world.refund(case, Decimal(s["amount"]),
                                  s["permit"], key)
            self.answers[r.split(":")[0]] += 1
        elif step == "verify":
            from decimal import Decimal
            got = self.world.reconcile(case)
            s["outcome"] = ("verified" if got == Decimal(s["amount"])
                            else "mismatch")
        elif step == "close":
            s["closed"] = True
        s["at"] += 1
        if self.store is not None:
            self.store.save(case.cid, s)
        return s


@dataclass
class Migration:
    runs: int
    moved: int
    lost: int
    reasked: int
    duplicates: int
    refused_dupes: int
    outcomes: Counter


def migrate(n=200, killed=40, record="store", key_from="run",
            src="threads", dst="sessions", seed=30) -> Migration:
    rng = random.Random(seed)
    cs = cases(n, seed=seed)
    by_id = {c.cid: c for c in cs}
    world = World()
    store = RunStore(sqlite3.connect(":memory:"))
    h = Harness(world, store if record == "store" else None, by_id,
                key_from)
    a, b = ADAPTERS[src](), ADAPTERS[dst]()
    kill = {c.cid: rng.randint(1, len(STEPS) - 1)
            for c in rng.sample(cs, killed)}
    done, in_flight = {}, []
    for c in cs:
        st, was_killed = a.run(c.cid, h.fresh(c.cid), h.advance,
                               kill.get(c.cid))
        if was_killed:
            in_flight.append(c.cid)
        else:
            done[c.cid] = st
    lost = 0
    for cid in in_flight:
        if record == "store":
            state = store.latest(cid)[1]
        else:
            try:
                state = b.import_native(a.export(cid))
            except NotPortable:
                lost += 1
                state = h.fresh(cid)
        done[cid], _ = b.run(cid, state, h.advance)
    dupes = sum(1 for c in cs
                if sum(k.startswith(c.cid + ":") for k in world.refunds) > 1)
    return Migration(n, len(in_flight), lost,
                     sum(v - 1 for v in h.asked.values() if v > 1),
                     dupes, h.answers["duplicate"],
                     Counter(s["outcome"] for s in done.values()))
