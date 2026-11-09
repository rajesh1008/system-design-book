"""INC-7, the incident record, rebuilt as spans from the replay.

Ben Carter's record is a timeline of decisions, each with who asked,
who acted, and what the decision bound. Rebuilding it as spans puts
it in the same store as the agent's own traces, so a reviewer can
join a decision to the queue it changed. Times come from the as-run
replay where the replay decides them (the page, the budget, the
peak, the clear) and from the record where a person decided them.
"""
from __future__ import annotations

from dataclasses import dataclass

from tracing.spans import Span, digest

from .day import clock, stamp
from .replay import Result, latency_at, run, t

INCIDENT = "INC-7"
BUNDLE = "pb-2026.09.10.1"


@dataclass(frozen=True)
class Entry:
    at: int
    what: str
    by: str
    binds: str = ""


def timeline(r: Result | None = None) -> list[Entry]:
    r = r or run("as-run")
    s = r.scenario
    e = [
        Entry(t(11, 0), "O'Hare ground stop; changes climb", "FAA, carriers"),
        Entry(int(r.voucher_spent_at), "voucher day spent; vouchers to "
              "people", "budget engine", "voucher-day $5,000"),
        Entry(s.declare_at, f"{INCIDENT} declared, weather", "Ben Carter"),
        Entry(int(r.paged_at), "fleet day at 80%; page", "budget engine",
              "fleet-day $600"),
        Entry(int(r.budget_spent_at), "fleet day spent; new chats to "
              "people at intake", "budget engine"),
        Entry(r.oldest_alert_at, "oldest card past one hour",
              "queue alert",
              "Marcus's objective"),
        Entry(s.emergency_at, "emergency budget +$2,500 to midnight",
              "Sarah Whitfield", "fleet-day $3,100"),
        Entry(s.switch_at, "desk order: departure time", "Marcus Bell",
              "desk config"),
        Entry(r.peak_at, f"queue peak {r.peak_depth:,}", "dashboard"),
        Entry(s.tier2_at, "tier two on refund_vol, credit",
              "Keisha Navarro asked; Lena Okafor pulled", "kill/servicing"),
        Entry(t(14, 52), "rule signed: involuntary refunds to $500",
              "Rachel Morgan", "rule digest, 12 h expiry"),
        Entry(t(14, 55), f"{BUNDLE} in shadow", "policy engine"),
        Entry(s.surge_at, f"{BUNDLE} active; expires 3:05 a.m.",
              "policy engine", BUNDLE),
        Entry(t(17, 0), "O'Hare reopens; day shift leaves", "rota"),
        Entry(r.cleared_at, "queue under 50", "dashboard"),
        Entry(s.tier2_release_at, "tier two released; held work runs",
              "Ben Carter", "checklist"),
        Entry(int(s.surge_at + s.surge_hours * 60), f"{BUNDLE} expired",
              "policy engine"),
    ]
    e.sort(key=lambda x: x.at)
    return e


def spans(r: Result | None = None) -> list[Span]:
    """The record as one trace: a root span for the incident and a
    child span per entry, each carrying who and what it bound."""
    r = r or run("as-run")
    tl = timeline(r)
    trace = digest({"incident": INCIDENT})
    root = Span(trace, digest("root"), None, f"step {INCIDENT}",
                start_ms=tl[0].at * 60_000,
                end_ms=tl[-1].at * 60_000,
                attrs={"incident.id": INCIDENT,
                       "incident.peak": r.peak_depth,
                       "incident.cleared": stamp(r.cleared_at)})
    out = [root]
    for i, x in enumerate(tl):
        out.append(Span(trace, digest([i, x.what]), root.span_id,
                        f"step {x.what[:40]}", start_ms=x.at * 60_000,
                        end_ms=x.at * 60_000,
                        attrs={"at": stamp(x.at), "by": x.by,
                               "binds": x.binds}))
    return out


def lines(r: Result | None = None) -> list[str]:
    r = r or run("as-run")
    out = [f"{INCIDENT}  Thursday, September 10, 2026 (CDT)"]
    for x in timeline(r):
        out.append(f"{clock(x.at):>14}  {x.what}"[:70])
    out.append(f"latency read {latency_at(r, t(14)):.0f} min at 2:00 p.m.;"
               f" oldest card {r.oldest_at_peak:.0f} min at the peak")
    return out
