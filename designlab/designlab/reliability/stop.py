"""Time to stop, from the decision to the safe state observed.

The kill switch is Chapter 12's and Chapter 31's: `policy.kill`,
three tiers, a flag each gateway replica polls every 5 seconds. A
stop is four facts, plus two for tier three, and time to stop is
the last of them minus the moment someone decided to stop:

  received            the switch recorded the pull
  no new commands     the slowest replica has polled since the pull
  in-flight settled   the longest call already sent has finished
  safe state          the far end's own count stayed flat for 20 s

What the far end is depends on what has to stop. For a tool's
effects it is the system of record's count of writes; for spend it
is the provider's count of calls, because tier two holds effects at
the gateway and lets model calls through by design.

Times here are the incident logs' (Lakeshore figures are
illustrative); the poll lags are the four replicas' in the drill.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from policy.kill import KillSwitch

from .records import at, hms

LAGS = (1.2, 2.9, 4.1, 4.8)     # seconds since each replica polled
QUIET = 20.0


@dataclass
class Stop:
    name: str
    decided: datetime
    facts: dict = field(default_factory=dict)
    blocked: dict = field(default_factory=dict)

    @property
    def safe(self) -> datetime | None:
        return self.facts.get("safe state")

    @property
    def seconds(self) -> float | None:
        s = self.safe
        return None if s is None else (s - self.decided).total_seconds()


def run_stop(name: str, decided: datetime, pulls: list[tuple],
             sub: str, tool: str, kind: str, inflight_s: float,
             key: str) -> Stop:
    """`pulls` is [(seconds after the decision, tier, by, tool)]. The
    stop is safe only once a pull blocks calls of `kind` from `sub`."""
    ks = KillSwitch(write_key=key, read_key=key)
    st = Stop(name, decided)
    for off, tier, by, tl in pulls:
        t = decided + timedelta(seconds=off)
        ks.pull(t, tier, by, name, tool=tl)
        st.facts.setdefault("received", t)
        after = t + timedelta(seconds=max(LAGS))
        why = ks.blocks(sub, tool, kind, after, lag_s=0.0)
        st.blocked[f"tier {tier}"] = why or "not blocked"
        if why:
            st.facts["no new commands"] = after
            settled = after + timedelta(seconds=inflight_s)
            st.facts["in-flight settled"] = settled
            if tier == 3:
                st.facts["runs stopped"] = after + timedelta(seconds=11)
                st.facts["token refused"] = after + timedelta(seconds=6)
            st.facts["safe state"] = settled + timedelta(seconds=QUIET)
            break
    return st


def july8(pulls=None) -> Stop:
    """Ben Carter, tier one on rebook_ticket. A ticket reissue at the
    airline can take 25 s; the bookings system's count is the far
    end."""
    return run_stop(
        "rebook_ticket reissues on wrong numbers",
        at("2026-07-08", "14:52", 10),
        pulls or [(14, 1, "ben.carter", "rebook_ticket")],
        "agent:servicing", "rebook_ticket", "effect", 25.0,
        "kill/servicing")


def storm(pulls=None) -> Stop:
    """Lena Okafor pulled tier two on the waiver watch, saw the loop's
    model calls still flowing at the model gateway, and pulled tier
    three. The provider finishes a long call it has started, up to
    38 s; its count of the loop's calls is the far end."""
    return run_stop(
        "waiver watch retry storm",
        at("2026-07-26", "19:36", 0),
        pulls or [(9, 2, "lena.okafor", ""),
                  (53, 3, "lena.okafor", "")],
        "agent:waiver-watch", "model_call", "model", 38.0,
        "kill/waiver-watch")


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def lines(st: Stop) -> list[str]:
    out = [f"decided            {hms(st.decided)}"]
    for k, v in st.facts.items():
        out.append(f"{k:<18} {hms(v)}")
    for k, v in st.blocked.items():
        out.append(f"{k} blocks model and effect calls? {v}")
    out.append(f"time to stop       {st.seconds:.0f} s")
    return out
