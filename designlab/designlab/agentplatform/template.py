"""The golden path's template: what a use case declares, and what it
may not.

A manifest has two kinds of keys. The ones a team owns (prompts,
retrieval, models, its own tool servers, the business result it is
measured on) are declared and left alone. The ones the platform owns
(the gateway, credentials, policy evaluation, the trail, dashboards)
are refused if a manifest tries to bring its own, because a use case
that brings its own gateway is a second control plane.
"""
from __future__ import annotations

import tomllib
from pathlib import Path

from evals.passk import pass_hat_k

HERE = Path(__file__).parent / "usecases"
USE_CASES = ("servicing", "desk", "loyalty")

REQUIRED = {
    "use_case": ("name", "owner", "team", "business_unit", "identity",
                 "caller_key", "harness", "resource"),
    "evaluation": ("golden_set", "trials", "k", "threshold",
                   "successes"),
    "verify": ("source", "reads_through", "owner"),
    "result": ("measure", "owner"),
}
TEAM_OWNED = ("prompts", "retrieval", "models", "tool_servers")
PLATFORM_OWNED = {
    "gateway": "the shared gateway",
    "proxy": "the shared gateway",
    "provider_key": "identity: keys are issued per run",
    "service_account": "identity: keys are issued per run",
    "policy_engine": "the policy engine",
    "limits_in_prompt": "the policy engine",
    "trail": "the trail",
    "dashboards": "the dashboards",
}
RESOURCES = {"itinerary": ("itinerary_id", "booking_ref"),
             "member": ("member_id",)}
MIN_TASKS = 30


def load(name: str) -> dict:
    with open(HERE / f"{name}.toml", "rb") as f:
        return tomllib.load(f)


def load_all() -> dict[str, dict]:
    return {n: load(n) for n in USE_CASES}


def pass_k(ev: dict) -> float:
    s = ev["successes"]
    return sum(pass_hat_k(ev["trials"], c, ev["k"]) for c in s) / len(s)


def check(m: dict, known_rules: list[dict] | None = None) -> list[str]:
    """Problems with a manifest, in the order a reviewer reads them.
    `known_rules` are the active bundle's rules, which a use case
    built on existing tools may rely on. A new effect tool needs a
    limit or an approval as well as an allow rule; an existing one
    keeps the rules its bundle already has."""
    out = []
    for sect, keys in REQUIRED.items():
        d = m.get(sect)
        if not isinstance(d, dict):
            out.append(f"missing section [{sect}]")
            continue
        for k in keys:
            if d.get(k) in (None, "", []):
                out.append(f"[{sect}] needs {k}")
    for sect in ("use_case", "team_owned"):
        for k in m.get(sect, {}):
            if k in PLATFORM_OWNED:
                out.append(f"platform-owned: {k} ({PLATFORM_OWNED[k]})")
    for k in m:
        if k in PLATFORM_OWNED:
            out.append(f"platform-owned: {k} ({PLATFORM_OWNED[k]})")
    res = m.get("use_case", {}).get("resource")
    if res and res not in RESOURCES:
        out.append(f"resource '{res}' has no binding field")
    tools = m.get("tools", [])
    if not tools:
        out.append("no tools declared")
    rules = list(known_rules or []) + list(
        m.get("policy", {}).get("rules", []))
    for t in tools:
        if t.get("kind") == "effect":
            cover = {r["type"] for r in rules
                     if t["name"] in r.get("tools", [])}
            if not cover & {"allow", "approval"}:
                out.append(f"effect {t['name']} has no allow rule")
            new = "input_schema" in t or "description" in t
            if new and not cover & {"limit", "approval"}:
                out.append(f"effect {t['name']} has no limit")
    ev = m.get("evaluation", {})
    if ev.get("successes"):
        n = len(ev["successes"])
        if n < MIN_TASKS:
            out.append(f"golden set has {n} tasks, needs {MIN_TASKS}")
    v, u = m.get("verify", {}), m.get("use_case", {})
    if v and v.get("owner") and v.get("owner") == u.get("owner"):
        out.append("verifier owner is the use case owner")
    return out


def as_built_aug10() -> dict:
    """The loyalty assistant as it was demonstrated on Monday,
    August 10, 2026: its own proxy, its own keys, a limit in the
    prompt, no golden set, no verifier, no declared result."""
    return {
        "use_case": {"name": "loyalty", "owner": "Arjun Mehta",
                     "team": "Loyalty engineering",
                     "business_unit": "Loyalty",
                     "identity": "", "caller_key": "",
                     "harness": "points assistant 0.4",
                     "resource": "member",
                     "gateway": "loyalty-proxy",
                     "provider_key": "loyalty team key",
                     "service_account": "ledger-svc (direct)",
                     "limits_in_prompt": "never more than 5,000 points"},
        "team_owned": {"prompts": "points assistant repository"},
        "tools": [{"server": "loyalty-points", "name": "points_credit",
                   "kind": "effect",
                   "description": "Post points to a member."}],
        "evaluation": {"golden_set": "", "trials": 0, "k": 0,
                       "threshold": 0, "successes": [8] * 12},
    }
