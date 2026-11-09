"""The loops linter: seven properties, each a check on the spec.

A property passes when the spec declares it in a form a machine can
act on. The linter cannot tell whether the code honors the spec;
the run's tests and the verifier do that. It can tell whether there
is anything for them to honor.
"""
from __future__ import annotations

from dataclasses import dataclass

PROPS = ("trigger", "stop", "state", "verify", "budget", "change",
         "human")
TRIGGER_KINDS = {"schedule", "event", "threshold"}
MACHINE = {"trail", "state", "enforcer", "verifier", "clock"}
EFFECT_TOOLS = {"voucher_issue", "customer_notify", "refund_ticket",
                "rebook_ticket", "credit_issue"}


@dataclass
class Finding:
    prop: str
    ok: bool
    why: str


def _trigger(s) -> str:
    t = s.get("trigger", {})
    kinds = set(t.get("kinds", []))
    if not kinds or not kinds <= TRIGGER_KINDS:
        return "no declared trigger kind"
    if not t.get("run_key"):
        return "no run key: two triggers make two runs"
    if not t.get("max_runs_per_watch_hour"):
        return "no ceiling on how often it runs"
    return ""


def _stop(s) -> str:
    stops = s.get("stops", [])
    for x in stops:
        if x.get("check") not in MACHINE:
            return f"'{x['id']}' is checked by the {x.get('check')}"
    ids = {x["id"] for x in stops}
    if "no-progress" not in ids:
        return "no stop for a run that makes no progress"
    if "budget" not in ids:
        return "no stop when the budget refuses"
    return ""


def _state(s) -> str:
    st = s.get("state", {})
    if st.get("store") != "run_store":
        return f"state lives in {st.get('store')}"
    if not st.get("schema"):
        return "state has no schema version"
    if not st.get("progress"):
        return "progress is not defined over persisted fields"
    missing = set(st["progress"]) - set(st.get("fields", []))
    if missing:
        return f"progress names unknown fields {sorted(missing)}"
    return ""


def _verify(s) -> str:
    v = s.get("verify", {})
    if not v.get("verifier") or v["verifier"] == s.get("actor"):
        return "the actor verifies itself"
    if v.get("effects"):
        return "the verifier can act"
    reads = " ".join(v.get("reads", []))
    if "report" in reads or not reads:
        return "the verifier reads the actor's report"
    return ""


def _budget(s) -> str:
    b = s.get("budget", {})
    if b.get("enforced_by") != "budget enforcer":
        return f"enforced by the {b.get('enforced_by')}"
    for k in ("run_usd", "run_steps", "loop_day_usd"):
        if not b.get(k):
            return f"no {k.replace('_', ' ')}"
    if not 0 < b.get("alert", 0) < 1:
        return "no alert before the stop"
    return ""


def _change(s) -> str:
    c = s.get("change", {})
    grant = set(c.get("grant", []))
    if not grant:
        return "no tool grant"
    # A spec may name its own effect tools (Chapter 45's internal
    # designs); the fare-watch and waiver-watch specs use the default.
    effects = grant & (EFFECT_TOOLS | set(c.get("effect_tools", [])))
    for e in sorted(effects):
        lim = c.get("effects", {}).get(e)
        if not lim:
            return f"effect {e} has no limit"
        if e == "voucher_issue" and not (lim.get("per_action_usd")
                                         and lim.get("per_day_usd")):
            return "voucher without per-action and daily caps"
    return ""


def _human(s) -> str:
    h = s.get("human", {})
    for k in ("owner", "pages", "hand_off", "kill_switch", "review"):
        if not h.get(k):
            return f"no {k.replace('_', ' ')}"
    return ""


CHECKS = dict(zip(PROPS, (_trigger, _stop, _state, _verify, _budget,
                          _change, _human)))


def lint(spec: dict) -> list[Finding]:
    out = []
    for p in PROPS:
        why = CHECKS[p](spec)
        out.append(Finding(p, not why, why))
    return out


def passed(spec: dict) -> int:
    return sum(f.ok for f in lint(spec))
