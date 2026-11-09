"""Six conformance tests a use case passes before it is live.

Each test reads evidence the shared control plane already produces:
the trail, the registry, the policy decisions, the golden-set counts,
and the spans. A test that needed a team to write something new for
it would be a form, not a test.

    K1 identity    every call carried this use case's identity, its
                   grant equals its manifest, and a token for one
                   resource cannot touch another
    K2 gateway     every request its tool servers answered was one
                   the gateway forwarded (the bypass detector)
    K3 registry    every tool approved, served hash matches review
    K4 policy      every effect had a permit; each limit routes
    K5 evaluation  a golden set of 30 or more tasks, pass^k at or
                   above the threshold
    K6 trace       a span for every call, carrying the call id
"""
from __future__ import annotations

from dataclasses import dataclass

from .chain import calls_of, decision_for
from .template import MIN_TASKS, RESOURCES, pass_k

from tracing import conventions as conv

NAMES = ("identity", "gateway", "registry", "policy", "evaluation",
         "trace")


@dataclass
class Check:
    id: str
    name: str
    ok: bool
    detail: str


def _servers(m: dict) -> set[str]:
    return {t["server"] for t in m["tools"]}


def k1_identity(plane, m: dict, lines) -> Check:
    u = m["use_case"]
    caller = plane.gateway.callers.get(u["caller_key"])
    want = {t["name"] for t in m["tools"]}
    if caller is None:
        return Check("K1", "identity", False, "no caller admitted")
    if set(caller.tools) != want:
        extra = len(set(caller.tools) - want)
        return Check("K1", "identity", False,
                     f"grant has {extra} tools beyond the manifest")
    other = [e for e in calls_of(lines, u["identity"])
             if e["server"] not in _servers(m)]
    if other:
        return Check("K1", "identity", False,
                     f"{len(other)} calls outside its servers")
    # probe: a token for one resource, used on another
    s = m["script"][0]
    f = RESOURCES[u["resource"]]
    args = {k: (v.format(n=9001) if isinstance(v, str) else v)
            for k, v in s["args"].items()}
    key = next(k for k in args if k in f)
    token = plane.mint(m, "probe-resource")
    from .plane import Tracer
    r = plane.call(m, token, s["server"], s["tool"], args,
                   Tracer("probe"))
    if r.ok or r.reason != "other_resource":
        return Check("K1", "identity", False,
                     f"cross-resource probe on {key}: {r.reason}")
    return Check("K1", "identity", True,
                 f"{len(want)} tools; cross-resource refused")


def k2_gateway(plane, m: dict, lines) -> Check:
    rec = plane.reconcile()["unmatched"]
    bad = {s: n for s, n in rec.items() if s in _servers(m)}
    if bad:
        s, n = next(iter(bad.items()))
        word = "request" if n == 1 else "requests"
        return Check("K2", "gateway", False,
                     f"{s}: {n} {word} not forwarded")
    return Check("K2", "gateway", True, "server counts match trail")


def k3_registry(plane, m: dict, lines) -> Check:
    for t in m["tools"]:
        srv = plane.world.servers[t["server"]]
        if not plane.registry.check_served(t["server"], t["name"],
                                           srv.describe(t["name"])):
            return Check("K3", "registry", False,
                         f"{t['name']}: not approved or hash differs")
    return Check("K3", "registry", True,
                 f"{len(m['tools'])} approved, hashes match")


def k4_policy(plane, m: dict, lines) -> Check:
    u = m["use_case"]
    effects = [e for e in calls_of(lines, u["identity"])
               if e["verdict"] == "allowed"
               and plane.kind_of(e["server"], e["tool"]) == "effect"]
    for e in effects:
        d = decision_for(lines, e)
        if d is None or not d.get("permission"):
            return Check("K4", "policy", False,
                         f"{e['call']}: effect without a permit")
    probes = 0
    for r in m.get("policy", {}).get("rules", []):
        if r["type"] != "limit":
            continue
        s = next(x for x in m["script"] if x["tool"] in r["tools"])
        args = {k: (v.format(n=9002) if isinstance(v, str) else v)
                for k, v in s["args"].items()}
        args[r["field"]] = r["max"] + 1
        f = RESOURCES[u["resource"]]
        res = next(args[k] for k in args if k in f)
        from .plane import Tracer
        out = plane.call(m, plane.mint(m, res), s["server"], s["tool"],
                         args, Tracer("probe-limit"))
        if out.ok or out.reason != "routed_to_person":
            return Check("K4", "policy", False,
                         f"{r['id']}: over limit was {out.reason or 'ok'}")
        probes += 1
    tail = f"; {probes} limit routes" if probes else ""
    return Check("K4", "policy", True,
                 f"{len(effects)} effects permitted{tail}")


def k5_evaluation(plane, m: dict, lines) -> Check:
    ev = m["evaluation"]
    n = len(ev["successes"])
    p = pass_k(ev)
    if n < MIN_TASKS:
        return Check("K5", "evaluation", False,
                     f"{n} tasks, needs {MIN_TASKS}")
    if p < ev["threshold"]:
        return Check("K5", "evaluation", False,
                     f"pass^{ev['k']} {p:.3f} < {ev['threshold']}")
    return Check("K5", "evaluation", True,
                 f"{n} tasks, pass^{ev['k']} {p:.3f}")


def k6_trace(plane, m: dict, lines) -> Check:
    u = m["use_case"]
    ids = {s.attrs.get(conv.TOOL_CALL) for s in plane.spans}
    calls = calls_of(lines, u["identity"])
    missing = [e["call"] for e in calls if e["call"] not in ids]
    if missing:
        return Check("K6", "trace", False,
                     f"{len(missing)} of {len(calls)} calls, no span")
    return Check("K6", "trace", True, f"{len(calls)} calls, all spanned")


TESTS = (k1_identity, k2_gateway, k3_registry, k4_policy,
         k5_evaluation, k6_trace)


def run(plane, m: dict) -> list[Check]:
    lines = plane.lines()
    out = []
    for t in TESTS:
        out.append(t(plane, m, lines))
        lines = plane.lines()
    return out


def passed(checks: list[Check]) -> int:
    return sum(c.ok for c in checks)
