"""One rebooking run as twelve steps, and three ways to keep its state.

    1 read_request   2 model_plan     3 fetch_fares    4 model_choose
    5 propose        6 request_approval                7 wait_approval
    8 permission     9 rebook        10 refund        11 verify
   12 close

strategy="memory"     the pilot loop: run state lives in the process.
strategy="framework"  February 2026: a checkpoint of position and
                      messages after each step; the pending approval,
                      permission, and keys stay in the process, and an
                      interrupted approval node re-runs from its top.
strategy="durable"    the run store: an intent row before each step,
                      the result and a schema 2 checkpoint in one
                      commit after it, durable timers, and a permission
                      re-read before every effect.

A Kill raises Crash at a named step and phase ("work": the step did
its work but nothing was committed; "commit": just after the commit)
or at a simulated time. The caller then builds a new Engine on the
same files, which is what a restarted process has.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from chain.record import ChainRecord, Permission, Proposal, Refused
from common.trail import TrailWriter

from .store import SCHEMA_VERSION, RunStore
from .world import World, pay_key

STEPS = ["read_request", "model_plan", "fetch_fares", "model_choose",
         "propose", "request_approval", "wait_approval", "permission",
         "rebook", "refund", "verify", "close"]
IDX = {s: i for i, s in enumerate(STEPS)}
MESSAGE_STEPS = {"read_request", "model_plan", "fetch_fares",
                 "model_choose", "propose", "verify", "close"}
DURATION = {"read_request": 2, "model_plan": 6, "fetch_fares": 3,
            "model_choose": 7, "propose": 1, "request_approval": 1,
            "wait_approval": 0, "permission": 1, "rebook": 4,
            "refund": 3, "verify": 2, "close": 1}
AGENT = "rebooking-agent"
POLL_S = 60


class Crash(Exception):
    pass


class SimClock:
    """Simulated time owned by the world, not the process: it carries
    on across a crash. Reading does not move it; steps and polls do."""

    def __init__(self, start: str):
        self.t = datetime.fromisoformat(start)

    def now(self) -> datetime:
        return self.t

    def peek(self) -> datetime:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += timedelta(seconds=seconds)


@dataclass
class Kill:
    step: str | None = None
    phase: str | None = None
    at: datetime | None = None
    spent: bool = False

    def check(self, step: str, phase: str, now: datetime) -> None:
        if self.spent:
            return
        hit = (self.at is not None and now >= self.at) or \
              (self.step == step and self.phase == phase)
        if hit:
            self.spent = True
            raise Crash(f"{step}/{phase}")


@dataclass
class Spec:
    run_id: str
    itinerary: str
    kind: str                      # "refund" or "rebook" or "waiver"
    old_fare: float
    options: list[dict]
    grant_after_s: float | None = 360
    regrant: bool = True
    poll_s: float = POLL_S
    timers: list[tuple[str, float]] = field(default_factory=lambda: [
        ("escalate", 45 * 60), ("deadline", 60 * 60)])

    def to_json(self) -> str:
        return json.dumps(self.__dict__, sort_keys=True)

    @classmethod
    def from_json(cls, s: str) -> "Spec":
        d = json.loads(s)
        d["timers"] = [tuple(t) for t in d["timers"]]
        return cls(**d)


def propose_v1(spec: Spec, choice: dict) -> dict:
    """The pure step: the proposal follows from the chosen option."""
    opt = next(o for o in spec.options if o["flight"] == choice["flight"])
    diff = round(spec.old_fare - opt["fare"], 2)
    refund = diff if spec.kind in ("refund", "waiver") and diff > 0 else 0.0
    body = {"flight": opt["flight"], "refund_usd": refund}
    body["hash"] = hashlib.sha256(json.dumps(body, sort_keys=True)
                                  .encode()).hexdigest()[:12]
    return body


@dataclass
class Ctx:
    spec: Spec
    pos: int = 0
    out: dict = field(default_factory=dict)
    request_id: str | None = None
    permission_id: str | None = None
    keys: dict = field(default_factory=dict)
    status: str = "running"
    events: list[str] = field(default_factory=list)
    resumed_from: int | None = None


class Engine:
    def __init__(self, base: Path, strategy: str, model, clock,
                 kill: Kill | None = None, propose=propose_v1):
        self.base = Path(base)
        self.strategy = strategy
        self.model = model
        self.clock = clock
        self.kill = kill or Kill()
        self.propose = propose
        self.conn = sqlite3.connect(self.base / "lab.db")
        self.conn.execute("pragma journal_mode=wal")
        self.conn.execute("pragma synchronous=normal")
        self.world = World(self.conn)
        self.store = RunStore(self.conn)
        self.conn.execute("create table if not exists inbound("
                          "run_id text primary key, spec text)")
        self.conn.commit()
        self.trail = TrailWriter(self.base / "trail.jsonl", clock=_Fixed(
            self.clock))
        self.mem: dict[str, Ctx] = {}
        self.mem_timers: dict[str, list] = {}

    def close(self) -> None:
        self.conn.close()

    # ---------------------------------------------------------- intake
    def submit(self, spec: Spec) -> None:
        self.conn.execute("insert or ignore into inbound values(?,?)",
                          (spec.run_id, spec.to_json()))
        self.conn.commit()

    def spec(self, run_id: str) -> Spec:
        row = self.conn.execute("select spec from inbound where run_id=?",
                                (run_id,)).fetchone()
        return Spec.from_json(row[0])

    # ------------------------------------------------------------ load
    def load(self, run_id: str) -> Ctx:
        spec = self.spec(run_id)
        if self.strategy == "memory":
            return self.mem.get(run_id) or Ctx(spec)
        latest = self.store.latest(run_id)
        if latest is None:
            return Ctx(spec)
        schema, body = latest
        ctx = Ctx(spec, pos=body["pos"], out=body["out"])
        ctx.resumed_from = ctx.pos
        if self.strategy == "framework":
            held = self.mem.get(run_id)
            if held:
                ctx.request_id, ctx.permission_id = \
                    held.request_id, held.permission_id
                ctx.keys = held.keys
            if ctx.pos < len(STEPS) and \
                    STEPS[ctx.pos] in ("request_approval", "wait_approval"):
                ctx.pos = IDX["request_approval"]   # node re-runs
            return ctx
        ctx.request_id = body.get("request_id")
        ctx.permission_id = body.get("permission_id")
        ctx.keys = body.get("keys", {})
        if schema < SCHEMA_VERSION:
            ctx.events.append(f"checkpoint schema {schema}: no pending "
                              f"permission")
        return ctx

    # ------------------------------------------------------------- run
    def run(self, run_id: str, horizon: datetime | None = None) -> Ctx:
        ctx = self.load(run_id)
        if self.strategy == "durable":
            self.sweep(ctx)
        try:
            while ctx.pos < len(STEPS) and ctx.status == "running":
                self.step(ctx, horizon)
        except (Held, Refused) as e:
            ctx.status = "held for a person"
            ctx.events.append(str(e))
        if ctx.pos == len(STEPS):
            ctx.status = "done"
        return ctx

    def step(self, ctx: Ctx, horizon) -> None:
        step = STEPS[ctx.pos]
        seq = ctx.pos + 1
        rid = ctx.spec.run_id
        skey = f"{rid}:{seq}"
        if self.strategy == "durable":
            done = self.store.result(rid, seq)
            if done is not None:            # result made it, checkpoint
                ctx.out[step] = done        # did not: journal wins
                self.apply(ctx, step, done)
                self.commit(ctx, step, seq, skey, done, journal=False)
                return
            redo = self.store.begun(rid, seq)
            if step in ("rebook", "refund") or (
                    step == "permission" and self.needs_person(ctx)):
                self.gate(ctx)
            self.store.begin(rid, seq, step, kind(step), skey,
                             self.clock.now())
        else:
            redo = False
            if step in ("permission", "rebook", "refund") and \
                    not self.has_permission(ctx, step):
                return
        output = self.do(ctx, step, skey, redo, horizon)
        if ctx.status != "running" and output is None:
            return
        self.kill.check(step, "work", self.clock.now())
        ctx.out[step] = output
        self.apply(ctx, step, output)
        self.commit(ctx, step, seq, skey, output)
        self.kill.check(step, "commit", self.clock.now())

    def apply(self, ctx, step, output):
        if step == "request_approval" and output.get("request_id"):
            ctx.request_id = output["request_id"]
        if step in ("wait_approval", "permission") and \
                output.get("permission_id"):
            ctx.permission_id = output["permission_id"]
        if step == "wait_approval" and output.get("decision") == "expired":
            ctx.events.append("deadline: refund not paid, rebooking "
                              "offered alone")

    def commit(self, ctx, step, seq, skey, output, journal=True):
        ctx.pos += 1
        rid = ctx.spec.run_id
        if self.strategy == "memory":
            self.mem[rid] = ctx
            return
        if self.strategy == "framework":
            msgs = {k: v for k, v in ctx.out.items() if k in MESSAGE_STEPS}
            if "wait_approval" in ctx.out:
                msgs["wait_approval"] = {"decision": ctx.out[
                    "wait_approval"].get("decision")}
            self.mem[rid] = ctx
            self.store.save(rid, {"pos": ctx.pos, "out": msgs}, schema=1)
            return
        if journal:
            self.store.done(rid, seq, step, kind(step), skey, output,
                            self.clock.now(), commit=False)
        body = {"pos": ctx.pos, "out": ctx.out,
                "request_id": ctx.request_id,
                "permission_id": ctx.permission_id, "keys": ctx.keys}
        self.store.save(rid, body, commit=False)
        self.conn.commit()                    # result and checkpoint

    # ------------------------------------------------- permission gate
    def needs_person(self, ctx: Ctx) -> bool:
        return ctx.spec.kind != "rebook" and \
            ctx.out.get("propose", {}).get("refund_usd", 0) > 0 and \
            ctx.out.get("wait_approval", {}).get("decision") != "expired"

    def has_permission(self, ctx: Ctx, step: str) -> bool:
        """memory and framework: no permission in hand sends the run
        back to ask for one, as the vendor's error path did."""
        if ctx.permission_id or (step == "permission"
                                 and not self.needs_person(ctx)):
            return True
        ctx.events.append(f"{step}: no permission in hand, asked again")
        ctx.pos = IDX["request_approval"] if self.needs_person(ctx) \
            else IDX["permission"]
        return False

    def gate(self, ctx: Ctx) -> None:
        """durable: re-read the permission before any effect."""
        if ctx.permission_id is None:
            missing = ["permission (not in checkpoint)"]
            ctx.events.append("refused to act: " + ", ".join(missing))
            ctx.permission_id = self.reread(ctx)
            ctx.events.append(f"re-read {ctx.permission_id} from "
                              f"{ctx.request_id or 'policy engine'}")
        p = self.world.permission(ctx.permission_id)
        rec = ChainRecord(
            proposal=Proposal("refund", ctx.spec.itinerary,
                              ctx.out["propose"]["refund_usd"],
                              "fare difference"),
            permission=None if p is None else Permission(
                p["permission_id"], p["granted_by"], p["policy"],
                p["max_amount_usd"]),
            idempotency_key=pay_key(ctx.permission_id, "refund"))
        missing = rec.missing_before_effect(AGENT)
        if p and datetime.fromisoformat(p["valid_until"]) < \
                self.clock.now():
            missing.append("permission still valid")
        if missing:
            ctx.status = "held for a person"
            raise Refused(missing)

    def reread(self, ctx: Ctx) -> str:
        if not self.needs_person(ctx):
            return self.world.policy_grant(ctx.spec.run_id, self.clock.now(),
                                           f"{ctx.spec.run_id}:8")
        rid = ctx.spec.run_id
        req = ctx.request_id or (self.store.result(rid, 6) or {}).get(
            "request_id") or self.world.find_request(f"{rid}:6")
        if req is None:
            raise Held(["no approval request on record"])
        ctx.request_id = req
        status, pid = self.world.status(req, self.clock.now())
        if pid is None:
            ctx.status = "held for a person"
            raise Held([f"{ctx.request_id} is {status}"])
        return pid

    # ------------------------------------------------------- the steps
    def do(self, ctx: Ctx, step: str, skey: str, redo: bool, horizon):
        s, now = ctx.spec, self.clock
        now.advance(DURATION[step])
        rid = s.run_id
        if step == "read_request":
            return {"itinerary": s.itinerary, "ask": "missed connection"}
        if step == "model_plan":
            return self.model.call(rid, step, {"kind": s.kind})
        if step == "fetch_fares":
            return {"options": s.options}
        if step == "model_choose":
            out = self.model.call(rid, step, {"options": s.options})
            if self.strategy != "durable":     # streamed as it came
                self.world.notice(rid, "offer:" + out["flight"], now.now())
            return out
        if step == "propose":
            body = self.propose(s, ctx.out["model_choose"])
            if self.strategy == "durable":     # sent once journaled
                self.world.notice(rid, "offer:" + body["flight"], now.now(),
                                  key=skey)
            return body
        needs_person = self.needs_person(ctx)
        if step == "request_approval":
            if not needs_person:
                return {"skipped": True}
            key = skey if self.strategy == "durable" else None
            req = self.world.file(rid, s.itinerary,
                                  ctx.out["propose"]["refund_usd"],
                                  now.now(), s.grant_after_s, req_key=key,
                                  regrant=s.regrant)
            self.set_timers(ctx, req)
            return {"request_id": req}
        if step == "wait_approval":
            if not needs_person:
                return {"skipped": True}
            return self.wait(ctx, horizon)
        if step == "permission":
            if needs_person:
                return {"permission_id": ctx.permission_id}
            if ctx.permission_id and self.strategy != "durable":
                return {"permission_id": ctx.permission_id}
            key = f"{rid}:8" if self.strategy == "durable" else None
            return {"permission_id": self.world.policy_grant(
                rid, now.now(), key)}
        if step == "rebook":
            if redo:
                found = self.world.tickets(s.itinerary)
                if found:
                    ctx.events.append(f"rebook found by lookup: {found[-1]}")
                    return {"ticket": found[-1], "found": True}
            return {"ticket": self.world.rebook(
                s.itinerary, ctx.out["propose"]["flight"], now.now())}
        if step == "refund":
            amount = ctx.out["propose"]["refund_usd"]
            if amount <= 0 or ctx.out.get("wait_approval", {}).get(
                    "decision") == "expired":
                return {"skipped": True}
            k = pay_key(ctx.permission_id, "refund")
            ctx.keys["refund"] = k
            r = self.world.refund(k, s.itinerary, amount, now.now())
            if r["replayed"]:
                ctx.events.append(f"refund key {k} seen: no new credit")
            return dict(r, key=k)
        if step == "verify":
            t = len(self.world.tickets(s.itinerary))
            c = self.world.credits(s.itinerary)
            want = 1 if ctx.out.get("refund", {}).get("credit") else 0
            return {"tickets": t, "credits": c,
                    "verified": t == 1 and c == want}
        if step == "close":
            mine = [ln for ln in self.trail.lines if f'"{rid}"' in ln
                    and '"close"' in ln]
            if mine:
                return {"trail": "already closed"}
            self.trail.append({"run_id": rid, "event": "close",
                               "verified": ctx.out["verify"]["verified"]})
            return {"trail": len(self.trail.lines)}
        raise ValueError(step)

    # ---------------------------------------------------- waits, timers
    def set_timers(self, ctx: Ctx, req: str) -> None:
        now = self.clock.now()
        for name, after in ctx.spec.timers:
            at = now + timedelta(seconds=after)
            if self.strategy == "durable":
                self.store.set_timer(ctx.spec.run_id, name, at)
            else:
                self.mem_timers.setdefault(ctx.spec.run_id, []).append(
                    [name, at, False])

    def sweep(self, ctx: Ctx) -> list[str]:
        fired = []
        if self.strategy == "durable":
            for run_id, name, _ in self.store.due(self.clock.now(),
                                                  ctx.spec.run_id):
                if self.store.fire(run_id, name):
                    fired.append(name)
        else:
            for t in self.mem_timers.get(ctx.spec.run_id, []):
                if not t[2] and t[1] <= self.clock.now():
                    t[2] = True
                    fired.append(t[0])
        for name in fired:
            ctx.events.append(f"timer {name} fired at "
                              f"{self.clock.now():%m-%d %H:%M}")
            if name != "deadline" and ctx.request_id:
                self.world.escalate(ctx.request_id)
                self.world.notice(ctx.spec.run_id, name, self.clock.now())
        return fired

    def deadline_fired(self, ctx: Ctx) -> bool:
        if self.strategy == "durable":
            return self.store.c.execute(
                "select 1 from timers where run_id=? and name='deadline' "
                "and state='fired'", (ctx.spec.run_id,)).fetchone() \
                is not None
        return any(t[0] == "deadline" and t[2]
                   for t in self.mem_timers.get(ctx.spec.run_id, []))

    def wait(self, ctx: Ctx, horizon):
        req = ctx.request_id or ctx.out["request_approval"]["request_id"]
        while True:
            now = self.clock.now()
            status, pid = self.world.status(req, now)
            if status == "granted":
                if self.strategy == "durable":
                    self.store.cancel_timers(ctx.spec.run_id)
                return {"decision": "approved", "permission_id": pid}
            fired = self.sweep(ctx)
            if "deadline" in fired or self.deadline_fired(ctx):
                self.world.close_request(req, "expired")
                return {"decision": "expired"}
            if horizon is not None and now >= horizon:
                ctx.status = "waiting"
                return None
            self.kill.check("wait_approval", "poll", now)
            self.clock.advance(ctx.spec.poll_s)


class Held(Exception):
    def __init__(self, missing):
        self.missing = missing
        super().__init__("held: " + ", ".join(missing))


class _Fixed:
    """Trail timestamps from the shared simulated clock, no advance."""

    def __init__(self, clock):
        self.c = clock

    def now(self):
        return self.c.peek()


def kind(step: str) -> str:
    return {"model_plan": "model", "model_choose": "model",
            "propose": "pure", "request_approval": "desk",
            "wait_approval": "wait", "permission": "permission",
            "rebook": "effect", "refund": "effect"}.get(step, "read")
