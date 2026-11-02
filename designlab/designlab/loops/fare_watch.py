"""The fare watch: actor, control, and verifier, one hour at a time.

`Design` switches between the fare watch as it went live on Friday,
June 12, 2026 (1.0.0), the build of Monday, June 15 (1.0.1: reads
fixed, verifier added), and the redesign of Friday, June 19 (1.1.0:
verdicts persisted, run keys, stall detector, loop-day budget).
Every tool call goes through Chapter 26's gateway. The model's
comparability judgment is simulated: a basic-economy fare is not
comparable to the main-cabin fare the traveler bought. Lakeshore
figures are illustrative.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from cost.budget import BudgetStop

from . import stall
from .budget import LoopEnforcer, judge_usd, judge_worst
from .state import Memory, Persisted, progress_digest
from .world import ACTOR, VERIFIER, FareWorld, Watch, at, day_of

LOOP = "fare-watch"
MIN_DROP = 5.00         # a drop smaller than this is not worth a voucher
CAP, DAY_CAP = 100.00, 5000.00          # vouchers-v1


@dataclass(frozen=True)
class Design:
    version: str
    segment_bug: bool = False       # 1.0.0 sent the segment as text
    refusal_is_empty: bool = False  # 1.0.0 read a refusal as no fare
    persist_verdicts: bool = True
    detector: bool = True
    self_report: bool = False       # the model writes the hour's report
    verdict_slots: int = 0          # injection: a cache of N verdicts


V100 = Design("1.0.0", segment_bug=True, refusal_is_empty=True,
              persist_verdicts=False, detector=False, self_report=True)
V101 = Design("1.0.1", persist_verdicts=False, detector=False)
V110 = Design("1.1.0")


@dataclass
class Hour:
    hour: int
    claimed: int = 0           # what the actor says it checked
    reads_ok: int = 0          # allowed reads, by the actor's count
    refused: int = 0
    model_calls: int = 0
    spend: float = 0.0
    vouchers: list = field(default_factory=list)
    handoffs: list = field(default_factory=list)
    stalls: list = field(default_factory=list)
    budget_stops: list = field(default_factory=list)
    report: str = ""


def offer_digest(o: dict) -> str:
    raw = json.dumps(o, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()[:12]


class Control:
    """The control plane's voucher check: cap per action, budget per
    day. It grants a single-use permission; the gateway spends it."""

    def __init__(self, fw: FareWorld):
        self.fw, self.day = fw, {}
        self.n = 0
        self.alerts: list[tuple[str, str]] = []   # (day, time)

    def permit(self, tool: str, args: dict) -> str:
        self.n += 1
        pid = f"PRM-FW-{self.n:06d}"
        self.fw.w.policy.issue(pid, tool, args)
        return pid

    def voucher(self, day: str, amount: float) -> str:
        if amount > CAP:
            return "over-cap"
        if self.day.get(day, 0.0) + amount > DAY_CAP:
            return "over-day"
        was = self.day.get(day, 0.0)
        self.day[day] = was + amount
        if was < 0.8 * DAY_CAP <= self.day[day]:
            self.alerts.append((day, self.fw.clock.peek().strftime(
                "%H:%M")))
        return ""


class Actor:
    def __init__(self, fw: FareWorld, design: Design, store=None,
                 enforcer: LoopEnforcer | None = None,
                 control: Control | None = None):
        self.fw, self.d = fw, design
        self.store = store if store is not None else Persisted()
        self.enf = enforcer
        self.control = control or Control(fw)

    # one read through the gateway
    def read(self, w: Watch):
        # the enrollment export stored the segment as text
        seg = str(w.segment) if self.d.segment_bug else w.segment
        return self.fw.w.gateway.call(
            ACTOR, "offers", "offers_search",
            {"booking_ref": w.booking, "segment": seg,
             "kind": "flight"})

    def judge(self, run: str, day: str, offer: dict, h: Hour) -> str:
        """One comparability call, reserved and settled."""
        if self.enf is not None:
            rid = self.enf.reserve(run, LOOP, day, judge_worst())
            self.enf.settle(rid, judge_usd())
        h.model_calls += 1
        h.spend += judge_usd()
        return "comparable" if offer["cabin"] == "main" else \
            "not comparable"

    def check(self, w: Watch, hour: int, h: Hour, run: str) -> None:
        st = self.store.load(w.wid, w.booked)
        if st["status"] != "active":
            return
        day = day_of(hour)
        r = self.read(w)
        if not r.ok:
            h.refused += 1
            if self.d.refusal_is_empty:
                h.claimed += 1          # "checked": nothing found
            return
        h.claimed += 1
        h.reads_ok += 1
        o = r.output["offers"][0]
        fare = float(o["fare_usd"])
        dg = offer_digest(o)
        changed = st["last_digest"] != dg
        st["last_digest"], st["last_fare"] = dg, fare
        if fare > st["floor_usd"] - MIN_DROP:
            if changed:
                self.store.save(w.wid, st)
            return
        verdicts = st["verdicts"]
        if dg in verdicts:              # decided before; nothing to do
            if changed:
                self.store.save(w.wid, st)
            return
        before = progress_digest(st)
        try:
            v = self.judge(run, day, o, h)
        except BudgetStop as e:
            h.budget_stops.append((w.wid, e.scope))
            self.store.save(w.wid, st)
            return
        if self.d.persist_verdicts:
            verdicts[dg] = v
        if v == "comparable":
            self.effect(w, st, fare, day, h)
            verdicts[dg] = v
        if self.d.verdict_slots and len(verdicts) > self.d.verdict_slots:
            for k in list(verdicts)[:-self.d.verdict_slots]:
                del verdicts[k]
        if self.d.detector:
            stop = stall.after_step(st, before)
            if stop:
                st["status"] = "paused"
                h.stalls.append((w.wid, stop))
                self.fw.w.trail.append({"event": "stall",
                                        "loop": LOOP, "watch": w.wid,
                                        "stop": stop,
                                        "steps": st["no_progress"]})
        self.store.save(w.wid, st)

    def effect(self, w: Watch, st: dict, fare: float, day: str,
               h: Hour) -> None:
        amount = round(st["floor_usd"] - fare, 2)
        why = self.control.voucher(day, amount)
        if why:
            h.handoffs.append((w.wid, why, amount))
            st["floor_usd"] = fare
            return
        args = {"itinerary_id": w.booking,
                "amount_usd": f"{amount:.2f}", "reason": "service"}
        pid = self.control.permit("voucher_issue", args)
        r = self.fw.w.gateway.call(ACTOR, "payments", "voucher_issue",
                                   args, permission=pid)
        if not r.ok:
            h.handoffs.append((w.wid, r.reason, amount))
            return
        note = {"itinerary_id": w.booking, "template": "update"}
        self.fw.w.gateway.call(ACTOR, "messaging", "customer_notify",
                               note, permission=self.control.permit(
                                   "customer_notify", note))
        st["floor_usd"] = fare
        st["vouchers_usd"] = round(st["vouchers_usd"] + amount, 2)
        h.vouchers.append((w.wid, amount, fare))

    def run_hour(self, hour: int, minutes: float = 59.0) -> Hour:
        h = Hour(hour)
        ws = self.fw.list
        for i, w in enumerate(ws):
            self.fw.clock.set(at(hour, minutes * i / len(ws)))
            self.check(w, hour, h, f"{w.wid}@{hour}")
        n = len(ws)
        if self.d.self_report:
            # the model summarizes the hour from the actor's counters
            h.report = (f"All fares checked: {h.claimed:,} watches, "
                        f"{len(h.vouchers)} drops.")
        else:
            h.report = (f"checked {h.reads_ok:,} of {n:,} by the "
                        f"trail, vouchers {len(h.vouchers)}")
        return h


class Verifier:
    """Did not act. Reads the gateway trail, re-reads a sample of
    fares under its own identity, and re-derives every voucher from
    the ledger and its own read."""

    def __init__(self, fw: FareWorld, sample: float = 0.02):
        self.fw = fw
        self.every = max(1, round(1 / sample))
        self.floor = {w.wid: w.booked for w in fw.list}
        self.mark = 0
        self.seen = 0

    def _fare(self, w: Watch) -> float | None:
        r = self.fw.w.gateway.call(VERIFIER, "offers", "offers_search",
                                   {"booking_ref": w.booking,
                                    "segment": w.segment,
                                    "kind": "flight"})
        return float(r.output["offers"][0]["fare_usd"]) if r.ok \
            else None

    def check_hour(self, hour: int, h: Hour, store) -> dict:
        lines = self.fw.w.trail.lines[self.mark:]
        self.mark = len(self.fw.w.trail.lines)
        reads = sum(1 for ln in lines
                    if '"loop:fare-watch"' in ln
                    and '"offers_search"' in ln
                    and '"allowed"' in ln)
        self.fw.clock.set(at(hour, 59.5))
        bad = []
        if reads != h.claimed:
            bad.append(f"claimed {h.claimed:,}, trail {reads:,}")
        sample = self.fw.list[hour % self.every::self.every]
        off = 0
        for w in sample:
            st = store.load(w.wid, w.booked)
            if st.get("last_fare") is None or \
                    abs(st["last_fare"] - (self._fare(w) or -1)) > .005:
                off += 1
        if off:
            bad.append(f"sample {off} of {len(sample)} differ")
        by = {x.booking: x for x in self.fw.list}
        new = self.fw.ledger.vouchers[self.seen:]
        self.seen = len(self.fw.ledger.vouchers)
        wrong = 0
        for v in new:
            w = by[v["itinerary_id"]]
            f = self._fare(w)
            want = round(self.floor[w.wid] - f, 2)
            if abs(want - float(v["amount_usd"])) > .005:
                wrong += 1
            self.floor[w.wid] = f
        if wrong:
            bad.append(f"vouchers {wrong} of {len(new)} wrong")
        return {"hour": hour, "trail_reads": reads,
                "sample": len(sample), "vouchers": len(new),
                "green": not bad, "why": bad}

    def handed_off(self, w: Watch, fare: float) -> None:
        self.floor[w.wid] = fare


class SelfCheck:
    """The actor checking its own work: its report against its own
    counters, its state against its own state. Always agrees."""

    def __init__(self, fw: FareWorld):
        self.fw = fw

    def check_hour(self, hour: int, h: Hour, store) -> dict:
        said = int(h.report.split(": ")[1].split(" ")[0]
                   .replace(",", "")) if ": " in h.report else h.reads_ok
        bad = [] if said == h.claimed else ["report differs"]
        return {"hour": hour, "trail_reads": None, "sample": 0,
                "vouchers": len(h.vouchers), "green": not bad,
                "why": bad}
