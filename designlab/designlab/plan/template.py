"""The five-year plan as a decision record, and its linter.

A plan has commitments, which sit on the four links that stay and must
not wait on a model release, and bets, which are dated predictions
about models, runtimes, protocols, and the role, each with a test."""
import datetime as dt
import re

from designs import records
from plan.core import LINKS, load

TEMPLATE = """\
[plan]       id, record, date, year_two_end, horizon,
             owner, signer (not the owner), reviewers
[targets]    the split and the blended cost, as decisions
[[commitment]]  link (effect | permission | verification
             | trail), text, measure, owner
[[bet]]      area, claim, made, due, test, if_true,
             if_false, owner, revisit (before due), models"""

ROADMAP = re.compile(r"\b(next model|model will|smarter model|"
                     r"model release|future model)\b", re.I)
BET_FIELDS = ("claim", "made", "due", "test", "if_true", "if_false",
              "owner", "revisit")


def _d(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def check(plan: dict, status: dict | None = None) -> list[str]:
    status = status or load("model_status.toml")
    P, out = plan["plan"], []
    if P["owner"] == P["signer"]:
        out.append("PLN-1 owner signs own plan")
    links = {c["link"] for c in plan.get("commitment", [])}
    for k in LINKS:
        if k not in links:
            out.append(f"PLN-2 no commitment on the {k}")
    for c in plan.get("commitment", []):
        if ROADMAP.search(c["text"] + " " + c["measure"]):
            out.append(f"PLN-3 {c['id']} waits on the model roadmap")
    t = plan["targets"]
    if t["agent"] + t["assisted"] + t["self_service"] + t["person"] != 100:
        out.append("PLN-4 split does not sum to 100")
    month_full = records.due_by_month()
    mine: dict[str, int] = {}
    retired = {m["id"]: m for m in status["model"]
               if m["state"] in ("retired", "deprecated")}
    earliest = {m["id"]: m.get("earliest") for m in status["model"]}
    for b in plan.get("bet", []):
        miss = [f for f in BET_FIELDS if not str(b.get(f, "")).strip()]
        if miss:
            out.append(f"PLN-5 {b['id']} missing {', '.join(miss)}")
            continue
        if not _d(b["made"]) <= _d(b["revisit"]) <= _d(b["due"]):
            out.append(f"PLN-6 {b['id']} revisit not between made, due")
        if _d(b["due"]) > _d(P["horizon"]):
            out.append(f"PLN-7 {b['id']} due past the horizon")
        m = b["revisit"][:7]
        mine[m] = mine.get(m, 0) + 1
        if month_full[m] + mine[m] > records.MONTH_FULL:
            out.append(f"PLN-8 {b['id']} revisit in a full month {m}")
        for mid in b.get("models", []):
            if mid in retired:
                r = retired[mid]
                when = r.get("retired") or r.get("retires")
                out.append(f"PLN-9 {b['id']} names {mid}, "
                           f"{r['state']} {when}")
            elif mid not in earliest:
                out.append(f"PLN-9 {b['id']} names unknown {mid}")
    return out


def window(plan: dict, status: dict | None = None) -> list[tuple]:
    """Each pinned model in the plan, with its earliest retirement and
    the days from the plan's date to it."""
    status = status or load("model_status.toml")
    start = _d(plan["plan"]["date"])
    rows = []
    for m in status["model"]:
        ids = {x for b in plan.get("bet", []) for x in b.get("models", [])}
        if m["id"] in ids and m.get("earliest"):
            rows.append((m["id"], m["earliest"],
                         (_d(m["earliest"]) - start).days))
    return rows
