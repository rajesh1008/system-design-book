"""Replay many runs under injected timeouts, keyed and unkeyed (Lab).

Each run is one permitted effect on one of the eighteen tools, chosen
by a fixed weight. Every call times out with probability `rate`; of
those, `late_share` were applied before the answer was lost. The
supplier records are then checked against the ledger.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from chain.record import Permission
from common.rand import DEFAULT_SEED, seeded
from corpus.tools import NATIVE, NONE, TOOLS, SupplierSim
from .check import Report, check
from .execute import Executor, unkeyed
from .keys import KeyIssuer
from .ledger import Ledger

WEIGHTS = {
    "processor-refund": 20, "fare-charge": 6, "voucher-ledger": 8,
    "airline-rebook-a": 8, "airline-rebook-b": 6, "gds-reissue": 6,
    "airline-seat-hold": 4, "airline-void-ticket": 2,
    "airline-cancel-segment": 4, "hotel-cancel-channel": 5,
    "hotel-cancel-aggregator": 5, "hotel-cancel-direct": 3,
    "hotel-modify": 4, "hotel-book": 3, "car-cancel": 3, "car-book": 2,
    "customer-email": 6, "customer-sms": 5,
}


@dataclass
class Result:
    runs: int
    keyed: bool
    rate: float
    calls: int = 0
    keyed_effects: int = 0
    unknowns: int = 0
    resolved: dict[str, int] = field(default_factory=dict)
    max_resolve_s: float = 0.0
    report: Report = field(default_factory=Report)

    def lines(self) -> list[str]:
        shape = "keyed, effect ledger" if self.keyed else \
            "unkeyed, framework retry"
        out = [f"{shape}: {self.runs:,} runs, timeout rate "
               f"{self.rate:.0%}", f"tool calls {self.calls:,}"]
        if self.keyed:
            share = self.keyed_effects / self.runs
            out.append(f"keyed share {share:.1%}")
            out.append(f"unknowns {self.unknowns}, longest open "
                       f"{self.max_resolve_s:.0f} s")
            out.append("left unknown by: " + ", ".join(
                f"{k} {v}" for k, v in sorted(self.resolved.items())))
        return out + self.report.lines()


def _faults(rng, rate: float, late_share: float):
    def f(_: str) -> str:
        if rng.random() < rate:
            return "late" if rng.random() < late_share else "lost"
        return ""
    return f


def run(runs: int = 10_000, rate: float = 0.05, keyed: bool = True,
        seed: int = DEFAULT_SEED, late_share: float = 0.6,
        override: dict[str, str] | None = None,
        inject: str = "") -> Result:
    """`override` maps a tool name to a contract for the try-it labs.
    `inject="no-key"` makes the executor drop the key on retries."""
    rng = seeded(seed, "effects", "replay", str(rate))
    pick = seeded(seed, "effects", "pick")
    names = [t.name for t in TOOLS]
    weights = [WEIGHTS[n] for n in names]
    sims = {}
    for t in TOOLS:
        sim = SupplierSim(t)
        if override and t.name in override:
            sim.honor_keys = {NATIVE: True, NONE: False}.get(
                override[t.name])
        sims[t.name] = sim
    lag_rng = seeded(seed, "effects", "lag")
    lags = (lambda name: lag_rng.uniform(0, sims[name].tool
                                         .visible_within_s))
    faults = _faults(rng, rate, late_share)
    res = Result(runs, keyed, rate)
    ledger, issuer = Ledger(), KeyIssuer()
    ex = Executor(ledger, sims, faults=faults, lags=lags)
    for i in range(runs):
        name = pick.choices(names, weights)[0]
        req = {"intent": f"INT-{i:05d}", "target": f"T-{i:05d}",
               "amount_usd": round(pick.uniform(20, 900), 2)}
        if not keyed:
            res.calls += unkeyed(sims[name], req, faults)
            continue
        perm = Permission(f"PRM-{40000 + i}", "policy-engine",
                          "lab", 1500.00)
        ek = issuer.mint(perm, name, req, at=ex.now)
        if inject == "no-key" and sims[name].support == NATIVE:
            ex.ledger.reserve(ek, ex.now)
            res.calls += unkeyed(sims[name], req, faults)
            continue
        before = ex.calls
        ex.run(ek, req)
        res.calls += ex.calls - before
        res.keyed_effects += 1
    if keyed:
        for e in ledger.entries.values():
            for secs, state in e.resolutions:
                res.unknowns += 1
                label = {"committed": "lookup found",
                         "attempting": "retry same key",
                         "escalated": "person",
                         "abandoned": "not resent"}[state]
                if state == "attempting" and \
                        sims[e.key.tool].support != NATIVE:
                    label = "lookup absent"
                res.resolved[label] = res.resolved.get(label, 0) + 1
                res.max_resolve_s = max(res.max_resolve_s, secs)
    res.report = check(sims, runs, ledger if keyed else None)
    return res


def sweep(rates=(0.0, 0.01, 0.02, 0.05, 0.10), runs: int = 10_000,
          seed: int = DEFAULT_SEED) -> list[tuple[float, int, int]]:
    """Duplicates against timeout rate: (rate, unkeyed, keyed)."""
    out = []
    for r in rates:
        u = run(runs, r, keyed=False, seed=seed).report.duplicates
        k = run(runs, r, keyed=True, seed=seed).report.duplicates
        out.append((r, u, k))
    return out
