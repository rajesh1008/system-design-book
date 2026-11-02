"""Wednesday, July 8, 2026: the model update with no deploy.

At about 1:15 a.m. CDT the vendor behind the schedule-change intake
classifier moved the alias Lakeshore called to a new model. Nothing
in Lakeshore's deploy log or configuration changed. The new model
coded a message that both retimed a flight and changed its number as
a retime only, so the rebooking step reissued the ticket on the old
flight number, and the reconciler, reading the airline's record,
found the mismatch and left the task unverified. That morning a
partner carrier filed a batch of changes that retimed and renumbered
flights, which is why July 8 was the day it showed.

The replay generates the window from 1:15 a.m. to the tier one pull
at 2:52 p.m. from fixed hourly counts (seed 37), and reads it three
ways: the uptime objective Lakeshore had, the five objectives it
adopted on July 20, and the deterministic code check the review
added. Every identifier and count is synthetic; Lakeshore figures are
illustrative.
"""
from __future__ import annotations

import re
from datetime import timedelta

from common.rand import seeded

from .records import Records, Task, at

DAY = "2026-07-08"
MOVED = at(DAY, "01:15")
STOPPED = at(DAY, "14:52", 10)
DESK_SAW = at(DAY, "14:41")
# hour: (agent tasks, combined-message failures, ordinary failures)
HOURS = {1: (12, 0, 0), 2: (10, 0, 0), 3: (8, 0, 0), 4: (11, 0, 0),
         5: (24, 0, 1), 6: (52, 0, 0), 7: (90, 1, 0), 8: (124, 4, 1),
         9: (142, 8, 0), 10: (150, 7, 1), 11: (148, 6, 1),
         12: (136, 5, 1), 13: (138, 5, 1), 14: (135, 4, 1)}
KINDS = ("rebooking", "refund", "cancellation", "credit")
SHARE = (0.36, 0.30, 0.20, 0.14)
FRONT_DOOR_ERRORS = 2

OLD_CODES = {"retime": ("RETIME",), "renumber": ("FLT_NUMBER_CHANGE",),
             "combined": ("RETIME", "FLT_NUMBER_CHANGE"),
             "cancel": ("CANCEL",)}
NEW_CODES = dict(OLD_CODES, combined=("RETIME",))


def message(rng, shape: str) -> str:
    fl = f"PK {rng.randrange(1100, 1999)}"
    dep = f"{rng.randrange(6, 21):02d}:{rng.choice(('05', '20', '40'))}"
    new = f"PK {rng.randrange(2100, 2999)}"
    if shape == "retime":
        return f"Flight {fl} on July 9 now departs {dep}."
    if shape == "renumber":
        return f"Flight {fl} on July 9 now operates as {new}."
    if shape == "cancel":
        return f"Flight {fl} on July 9 is canceled."
    return (f"Flight {fl} on July 9 now departs {dep} and operates "
            f"as {new}.")


NUMBER = re.compile(r"operates as ([A-Z]{2} \d{3,4})")


def code_check(msg: str, codes: tuple) -> str:
    """The check the review added: a code the message's own text
    contradicts holds the case. It reads the raw message, which the
    classifier does not write."""
    if NUMBER.search(msg) and "FLT_NUMBER_CHANGE" not in codes:
        return "number change in text, not in codes"
    if "now departs" in msg and "RETIME" not in codes:
        return "retime in text, not in codes"
    return ""


def build(seed: int = 37, pinned: bool = False) -> Records:
    """The window as it ran (`pinned=False`) or with the classifier
    pinned to the dated model it had answered with in June."""
    rng = seeded(seed, "july8")
    rec = Records()
    n = 0
    for hour, (count, combined_bad, ordinary_bad) in HOURS.items():
        lo = MOVED if hour == 1 else at(DAY, f"{hour:02d}:00")
        hi = STOPPED if hour == 14 else at(DAY, f"{hour:02d}:59", 59)
        span = (hi - lo).total_seconds()
        ends = sorted(lo + timedelta(seconds=rng.uniform(0, span))
                      for _ in range(count))
        bad_combined = set(rng.sample(range(count), combined_bad))
        rest = [i for i in range(count) if i not in bad_combined]
        bad_ordinary = set(rng.sample(rest, ordinary_bad))
        for i, end in enumerate(ends):
            n += 1
            if i in bad_combined:
                kind, shape = "rebooking", "combined"
            else:
                kind = rng.choices(KINDS, SHARE)[0]
                shape = (rng.choice(("retime", "retime", "renumber",
                                     "cancel"))
                         if kind == "rebooking" else "")
            secs = rng.lognormvariate(2.75, 0.42)
            msg = message(rng, shape) if shape else ""
            table = OLD_CODES if pinned else NEW_CODES
            codes = table[shape] if shape else ()
            wrong = i in bad_combined and not pinned
            ok = not wrong and i not in bad_ordinary
            cause = ("dropped number code" if wrong else
                     "ordinary" if i in bad_ordinary else "")
            rec.tasks.append(Task(
                f"T08-{n:04d}", kind, end - timedelta(seconds=secs),
                end, ok, end + timedelta(minutes=rng.uniform(3, 9)),
                cost_usd=round(rng.uniform(0.9, 1.9), 2),
                requests=rng.randrange(6, 11), codes=codes,
                message=msg, cause=cause))
    for t in rng.sample(rec.tasks, FRONT_DOOR_ERRORS):
        t.errors = 1
    return rec


def summary(rec: Records) -> dict:
    ts = rec.tasks
    req = sum(t.requests for t in ts)
    err = sum(t.errors for t in ts)
    reb = [t for t in ts if t.kind == "rebooking"]
    return {
        "tasks": len(ts),
        "verified": sum(bool(t.verified) for t in ts),
        "dropped": sum(t.cause == "dropped number code" for t in ts),
        "ordinary": sum(t.cause == "ordinary" for t in ts),
        "requests": req, "errors": err,
        "uptime": 1 - err / req,
        "rebookings": len(reb),
        "rebook_verified": sum(bool(t.verified) for t in reb),
        "p95": sorted(t.seconds for t in ts)[int(0.95 * len(ts)) - 1],
    }


def first_code_flag(rec: Records):
    for t in sorted(rec.tasks, key=lambda t: t.ended):
        why = code_check(t.message, t.codes) if t.message else ""
        if why:
            return t, why
    return None, ""
