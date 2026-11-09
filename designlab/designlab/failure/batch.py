"""The batch refund path, as injected and as fixed (Chapter 12, lab).

Injected (April 14): the involuntary-refund batch calls the processor
through a framework payments adapter with its own credential. The
adapter's retry wrapper mints a fresh key for every attempt, so a
late answer followed by a retry is two refunds. The agent path, the
same afternoon, goes through the gateway: one key per permission,
minted before the first attempt, and the ledger.

Fixed (April 28): every refund, batch or agent, gets its key from the
control plane at grant, is written to the ledger, and reaches the
processor only through the guarded client, which refuses anything
else. Optionally a breaker holds effects while the processor is slow.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from chain.record import Permission
from corpus.fall1 import TIMEOUT_S, BACKOFF_S, probe_latency
from corpus.tools import TOOLS, SupplierSim, SupplierTimeout
from effects import KeyIssuer, KeyRefused, Ledger
from effects.guard import GATEWAY, GuardedClient

TOOL = "processor-refund"
SPEC = next(t for t in TOOLS if t.name == TOOL)
BATCH_CREDENTIAL = "int-fin-02"
PROBE_GAP_S = 5.0


def request(r: dict) -> dict:
    return {"target": r["charge_id"], "amount_usd": r["amount_usd"],
            "permission": r["permission_id"]}


def permission(r: dict) -> Permission:
    return Permission(r["permission_id"], "approver-desk", "refunds-v3",
                      1500.0)


def attempt_key(refund_id: str, n: int) -> str:
    """What the framework wrapper sent: a new key per attempt."""
    raw = f"{refund_id}|attempt|{n}".encode()
    return "fw-" + hashlib.sha256(raw).hexdigest()[:20]


@dataclass
class Run:
    name: str
    sim: SupplierSim = field(default_factory=lambda: SupplierSim(SPEC))
    ledger: Ledger = field(default_factory=Ledger)
    issuer: KeyIssuer = field(default_factory=KeyIssuer)
    credential: dict[str, str] = field(default_factory=dict)
    starts: list[float] = field(default_factory=list)
    to_people: int = 0
    refused: int = 0
    held: int = 0
    breaker: Optional[object] = None
    queue: Optional[object] = None
    drained_at: Optional[float] = None

    def lines(self) -> list[dict]:
        return [{"credit_id": rec["effect_id"],
                 "charge_id": rec["target"],
                 "amount_usd": rec["request"]["amount_usd"],
                 "at": rec["at"], "ref": rec["ref"],
                 "credential": self.credential.get(rec["ref"], GATEWAY)}
                for rec in self.sim.records]

    def owed(self, refunds: list[dict]) -> dict[str, float]:
        return {r["charge_id"]: r["amount_usd"] for r in refunds}

    def calls(self) -> int:
        return len(self.starts)


def _latency(a: dict) -> float:
    return a["latency_s"] if a["outcome"] != "lost" else 0.0


def _wrapper(run: Run, r: dict, plan: list[dict], cred: str) -> None:
    """The framework adapter: three tries, a new key every time."""
    ref = f"BAT-{r['refund_id']}"
    run.credential[ref] = cred
    for a in plan:
        run.starts.append(a["start"])
        if a["outcome"] != "ok":
            run.sim.faults[run.sim.calls + 1] = a["outcome"]
        try:
            run.sim.call(request(r), key=attempt_key(r["refund_id"],
                                                     a["attempt"]),
                         ref=ref, at=a["start"] + _latency(a))
            return
        except SupplierTimeout:
            continue
    run.to_people += 1


def _gateway(run: Run, r: dict, plan: list[dict], client,
             mint: str = "action") -> str:
    """One refund through key, ledger and guarded client. Returns
    'committed', 'held' or 'escalated'."""
    req = request(r)
    try:
        ek = run.issuer.mint(permission(r), TOOL,
                             req if mint == "action" else
                             {**req, "attempt": 1}, plan[0]["start"])
    except KeyRefused:
        run.refused += 1
        run.to_people += 1
        return "escalated"
    e, _ = run.ledger.reserve(ek, plan[0]["start"])
    if e.state == "committed":
        return "committed"
    for a in plan:
        t = a["start"]
        if run.breaker is not None and not run.breaker.allows_effect(t):
            run.queue.hold(t, r)
            run.held += 1
            return "held"
        if mint == "attempt" and a["attempt"] > 1:
            try:
                run.issuer.mint(permission(r), TOOL,
                                {**req, "attempt": a["attempt"]}, t)
            except KeyRefused:
                run.refused += 1
                run.to_people += 1
                run.ledger.move(ek.key, "escalated", t, "key refused")
                return "escalated"
        token = run.ledger.acquire(ek.key, "gateway", t)
        run.ledger.move(ek.key, "attempting", t, "", token)
        run.starts.append(t)
        if a["outcome"] != "ok":
            run.sim.faults[run.sim.calls + 1] = a["outcome"]
        lat = a["latency_s"]
        try:
            client.call(req, key=ek.key, ref=ek.key, at=t + _latency(a))
        except SupplierTimeout:
            run.ledger.move(ek.key, "unknown", t + TIMEOUT_S, "timeout",
                            token)
            if run.breaker is not None:
                run.breaker.record(t + TIMEOUT_S, TIMEOUT_S, False)
            continue
        run.ledger.move(ek.key, "committed", t + lat, "", token)
        if run.breaker is not None:
            run.breaker.record(t + lat, lat, True)
        return "committed"
    run.ledger.move(ek.key, "escalated", plan[-1]["start"], "attempts")
    run.to_people += 1
    return "escalated"


def _plans(fall: dict) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    for a in fall["fall1_attempts"]:
        out[a["refund_id"]].append(a)
    return out


def replay_injected(fall: dict) -> Run:
    run = Run("injected")
    gw = GuardedClient(run.sim, run.ledger)
    plans = _plans(fall)
    for r in fall["fall1_refunds"]:
        if r["path"] == "batch":
            _wrapper(run, r, plans[r["refund_id"]], BATCH_CREDENTIAL)
        else:
            _gateway(run, r, plans[r["refund_id"]], gw)
    return run


def _tick(run: Run, client, now: float, per_s: float,
          next_probe: list) -> None:
    """Advance the breaker's probes to `now`; drain on close."""
    b = run.breaker
    while b.state != "closed":
        due = b.opened_at + b.open_s if b.state == "open" \
            else next_probe[0]
        if due > now:
            return
        b.due_probe(due)
        b.probe(due, probe_latency(due))
        next_probe[0] = due + PROBE_GAP_S
        if b.state == "closed":
            for t, r in run.queue.release(due, per_s):
                plan = [{"attempt": 1, "outcome": "ok", "start": t,
                         "latency_s": probe_latency(t)}]
                _gateway(run, r, plan, client)
                run.drained_at = t


def replay_fixed(fall: dict, breaker=None, mint: str = "action",
                 enforce: bool = True, per_s: float = 4.0) -> Run:
    from .degrade import HoldQueue
    run = Run("fixed")
    run.breaker = breaker
    run.queue = HoldQueue()
    client = GuardedClient(run.sim, run.ledger) if enforce else run.sim
    plans = _plans(fall)
    nxt = [0.0]
    for r in fall["fall1_refunds"]:
        plan = plans[r["refund_id"]]
        if breaker is not None:
            _tick(run, client, plan[0]["start"], per_s, nxt)
        if mint == "attempt" and not enforce and r["path"] == "batch":
            _wrapper(run, r, plan, GATEWAY)   # convention only
        else:
            _gateway(run, r, plan, client,
                     mint if enforce else "action")
    if breaker is not None:
        _tick(run, client, 24 * 3600.0, per_s, nxt)
    return run


def open_intervals(transitions: list[tuple[float, str]]) -> list[tuple]:
    out, since = [], None
    for t, s in transitions:
        if s == "open" and since is None:
            since = t
        if s == "closed" and since is not None:
            out.append((since, t))
            since = None
    if since is not None:
        out.append((since, float("inf")))
    return out


def starts_while_open(run: Run) -> int:
    iv = open_intervals(run.breaker.transitions)
    return sum(1 for s in run.starts if any(a <= s < b for a, b in iv))
