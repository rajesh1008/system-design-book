"""Expand a compact worked-design spec into the method's eight artifacts.

A spec names the effects, their limits and tiers, the executor, the
verifiers and what each reads, the person gate, the customer states,
the obligations, the estimate inputs, one decision, one deep dive, one
decision record, and the five gap answers. This module derives the
rest: the answers the bank questions can take from the effects, the
derived estimate lines, and the diagram in Chapter 5's grammar. The
method linter then reads the result exactly as it reads a design a
person wrote by hand.
"""
from __future__ import annotations

import copy

# Autonomy tiers, least to most autonomous.
TIERS = ("never", "suggest", "approve", "notify", "act")
TIER_WORDS = {"never": "never by the agent", "suggest": "suggest only",
              "approve": "with approval", "notify": "act and notify",
              "act": "act alone"}

# The six states a customer sees. Each is computed from the chain;
# the model never writes one.
STATES = ("received", "waiting for approval", "with a person",
          "in progress", "done", "declined")
STATE_KEYS = ("received", "waiting", "person", "progress", "done",
              "declined")
SUMMARY_FIELDS = ("asked", "proposed", "stopped because", "evidence",
                  "deadline")

# Estimate inputs every worked design states, and what derives.
INPUTS = ("cases_per_year", "worst_day_factor", "window_hours",
          "calls_per_case", "tools_per_case", "gate_share",
          "reviews_per_hour")
DERIVED = (
    ("avg_per_day", "cases_per_year / 365", "cases a day"),
    ("peak_per_hour", "avg_per_day * worst_day_factor / window_hours",
     "cases an hour"),
    ("peak_requests_per_s",
     "peak_per_hour / 3600 * (calls_per_case + tools_per_case)",
     "requests a second"),
    ("gate_items_per_hour", "peak_per_hour * gate_share",
     "gate items an hour"),
    ("reviewers_needed", "gate_items_per_hour / reviews_per_hour",
     "people at the gate"),
)


def rank(tier: str) -> int:
    return TIERS.index(tier) if tier in TIERS else -1


def derived_tier(effect: dict) -> str | None:
    """The most autonomous tier the effect's limit allows.

    The ladder is a list of [ceiling in USD, tier]: the first rung whose
    ceiling is at or above the limit names the tier. Above the last
    rung, a person decides (suggest). No ladder means no amount rule.
    """
    ladder = effect.get("ladder")
    if not ladder:
        return None
    amount = float(effect.get("limit_usd", 0))
    for ceiling, tier in ladder:
        if amount <= float(ceiling):
            return tier
    return "suggest"


def _systems(spec: dict) -> list[str]:
    seen: list[str] = []
    for e in spec.get("effects", []):
        s = e.get("system")
        if s and s not in seen:
            seen.append(s)
    return seen


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in text.lower())


def _derived_answers(spec: dict) -> dict:
    eff = spec.get("effects", [])
    gate = spec.get("human_gate", {})
    vers = spec.get("verifiers", [])
    money = [e for e in eff if e.get("limit_usd")]
    out = {}
    if eff:
        out["A1"] = {"answer": ", ".join(e["label"] for e in eff),
                     "source": "doc:scope-card"}
        out["A2"] = {"answer": "; ".join(
            f"{e['name']}: {e.get('undo', 'not stated')}" for e in eff),
            "source": "doc:effects"}
        out["C2"] = {"answer": "; ".join(
            f"{e['name']} {TIER_WORDS.get(e.get('tier'), '?')}"
            for e in eff), "source": "doc:autonomy-table"}
    if money:
        top = max(money, key=lambda e: e["limit_usd"])
        out["A3"] = {"answer": f"{top['name']} up to "
                     f"${top['limit_usd']:,.0f}", "source": "doc:limits"}
    if _systems(spec):
        out["A4"] = {"answer": ", ".join(_systems(spec)),
                     "source": "doc:integration-list"}
    out["C1"] = {"answer": "the policy engine, outside the loop; records "
                 "bound to the argument digest, 15-minute expiry",
                 "source": "doc:permission-store"}
    if gate.get("promise_minutes"):
        out["C3"] = {"answer": f"{gate['promise_minutes']} minutes "
                     "promised; no answer is no, never yes by timeout",
                     "source": "doc:desk"}
    if vers:
        out["T2"] = {"answer": "; ".join(v["reads"] for v in vers),
                     "source": "doc:integration-list"}
        out["T3"] = {"answer": ", ".join(v["id"] for v in vers)
                     + "; none of them acts", "source": "doc:verifiers"}
    return out


def _estimate(spec: dict) -> list[dict]:
    lines = [dict(ln) for ln in spec.get("estimate", [])]
    have = {ln.get("name") for ln in lines}
    for name, formula, unit in DERIVED:
        if name not in have:
            lines.append({"name": name, "formula": formula, "unit": unit})
    return lines


def _diagram(spec: dict) -> dict:
    ex = spec.get("executor", {})
    gate = spec.get("human_gate")
    writes = set(ex.get("writes", []))
    nodes = [
        {"id": "customer", "kind": "external", "plane": "action",
         "label": spec["design"].get("customer", "customer")},
        {"id": "loop", "kind": "loop", "plane": "action",
         "label": "agent harness"},
        {"id": "model", "kind": "model", "plane": "action",
         "label": "model"},
        {"id": "facts", "kind": "store", "plane": "knowledge",
         "label": spec["design"].get("knowledge", "records")},
        {"id": "policy", "kind": "gate", "plane": "control",
         "label": "policy engine"},
        {"id": "permits", "kind": "store", "plane": "trail",
         "label": "permission records"},
        {"id": "executor", "kind": "tool", "plane": "action",
         "label": ex.get("label", "executor")},
        {"id": "trail", "kind": "store", "plane": "trail",
         "label": "trail"},
        {"id": "status", "kind": "tool", "plane": "trail",
         "label": "status from the chain"},
    ]
    edges = [
        {"from": "customer", "to": "loop", "kind": "control",
         "label": "request"},
        {"from": "facts", "to": "loop", "kind": "data", "label": "facts"},
        {"from": "loop", "to": "model", "kind": "data", "label": "context"},
        {"from": "model", "to": "loop", "kind": "data", "label": "output"},
        {"from": "loop", "to": "policy", "kind": "control",
         "label": "typed proposal"},
        {"from": "policy", "to": "permits", "kind": "trail",
         "label": "permission record"},
        {"from": "policy", "to": "executor", "kind": "control",
         "label": "permission"},
        {"from": "executor", "to": "trail", "kind": "trail",
         "label": "execution"},
        {"from": "trail", "to": "status", "kind": "data",
         "label": "chain"},
        {"from": "status", "to": "customer", "kind": "data",
         "label": "one of six states"},
    ]
    if gate:
        nodes.append({"id": "desk", "kind": "person", "plane": "control",
                      "label": gate.get("label", "desk")})
        edges += [{"from": "policy", "to": "desk", "kind": "async",
                   "label": "needs a person"},
                  {"from": "desk", "to": "policy", "kind": "control",
                   "label": "decision"}]
    for s in _systems(spec):
        sid = "sys_" + _slug(s)
        nodes.append({"id": sid, "kind": "external", "plane": "action",
                      "label": s})
        edges.append({"from": "executor", "to": sid, "kind": "effect",
                      "label": "effect"})
    for v in spec.get("verifiers", []):
        src = v["reads"]
        sid = "src_" + _slug(src)
        if src in writes:
            # The verifier reads a record the executor writes itself.
            nodes.append({"id": sid, "kind": "store", "plane": "trail",
                          "label": src})
            edges.append({"from": "executor", "to": sid, "kind": "trail",
                          "label": "writes"})
        else:
            nodes.append({"id": sid, "kind": "external", "plane": "trail",
                          "label": src})
            by = v.get("written_by")
            if by:
                edges.append({"from": "sys_" + _slug(by), "to": sid,
                              "kind": "data", "label": "records"})
        nodes.append({"id": v["id"], "kind": "verifier", "plane": "trail",
                      "label": v["id"]})
        edges.append({"from": sid, "to": v["id"], "kind": "data",
                      "label": "reads"})
        edges.append({"from": v["id"], "to": "trail", "kind": "trail",
                      "label": "verified outcome"})
        if v.get("acts"):
            edges.append({"from": v["id"], "to": "sys_" + _slug(
                (_systems(spec) or ["world"])[0]), "kind": "effect",
                "label": "corrects"})
    # De-duplicate nodes that two verifiers share.
    seen, uniq = set(), []
    for n in nodes:
        if n["id"] not in seen:
            seen.add(n["id"])
            uniq.append(n)
    return {"nodes": uniq, "edges": edges}


def expand(spec: dict) -> dict:
    """Return the method's raw design dict for a worked-design spec."""
    spec = copy.deepcopy(spec)
    meta = spec["design"]
    raw: dict = {"design": {k: meta[k] for k in
                            ("id", "version", "as_of", "author", "title",
                             "people") if k in meta}}
    raw["scope"] = {
        "summary": meta.get("summary", ""),
        "effects": [e["name"] for e in spec.get("effects", [])],
        "autonomy": "; ".join(f"{e['name']} {TIER_WORDS.get(e['tier'])}"
                              for e in spec.get("effects", [])),
        "out_of_scope": meta.get("out_of_scope", ""),
        "owner": meta.get("owner", ""),
    }
    reqs = _derived_answers(spec)
    reqs.update(spec.get("requirements", {}))
    raw["requirements"] = reqs
    raw["estimate"] = _estimate(spec)
    raw["diagram"] = _diagram(spec)
    if "decision" in spec:
        raw["decisions"] = [spec["decision"]]
    if "deep_dive" in spec:
        raw["deep_dives"] = [spec["deep_dive"]]
    if "record" in spec:
        raw["records"] = [spec["record"]]
    raw["gaps"] = spec.get("gaps", {})
    return raw
