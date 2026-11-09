"""The golden path, run: a manifest in, a live use case out, or a
named reason it is not live.

    1 template     the manifest against the template
    2 identity     one caller, exactly the declared tools
    3 registry     new tools submitted and screened
    4 review       one meeting: tools approved, the team's rules
                   signed into the shared bundle, the golden set gated
    5 staging      the use case's own scripts, through the plane
    6 conformance  K1 to K6; live only if all six pass
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import conformance, template


@dataclass
class Onboarding:
    use_case: str
    steps: list = field(default_factory=list)   # (step, ok, detail)
    checks: list = field(default_factory=list)

    @property
    def live(self) -> bool:
        return bool(self.checks) and all(c.ok for c in self.checks)

    def add(self, step: str, ok: bool, detail: str) -> bool:
        self.steps.append((step, ok, detail))
        return ok


def with_kinds(plane, m: dict) -> dict:
    """Tools already in the registry keep their registered kind."""
    out = dict(m)
    out["tools"] = [dict(t, kind=t.get("kind") or
                         plane.kind_of(t["server"], t["name"]))
                    for t in m["tools"]]
    return out


def onboard(plane, m: dict, rev: str, runs: int = 5,
            bypass: int = 0) -> Onboarding:
    name = m["use_case"]["name"]
    ob = Onboarding(name)
    rules = list(plane.world.bundles.active().rules)
    problems = template.check(with_kinds(plane, m), rules)
    if not ob.add("template", not problems,
                  problems[0] if problems else "no problems"):
        return ob
    caller = plane.admit(m)
    ob.add("identity", True,
           f"{caller.sub}, {len(caller.tools)} tools")
    found = plane.submit_tools(m)
    open_ = [(t, f) for t, f in found if f]
    if not ob.add("registry", not open_,
                  f"{open_[0][0]}: {open_[0][1][0]}" if open_ else
                  f"{len(found)} new tools, no findings"):
        return ob
    plane.approve_tools(m, f"{name} onboarding")
    new_rules = m.get("policy", {}).get("rules", [])
    if new_rules:
        plane.add_rules(rev, m, f"{m['use_case']['team']}")
    gate = template.pass_k(m["evaluation"])
    ob.add("review", True,
           f"{len(found)} tools, {len(new_rules)} rules, "
           f"pass^{m['evaluation']['k']} {gate:.3f}")
    for _ in range(runs):
        plane.run(name)
    for _ in range(bypass):   # the old ledger key, still valid
        srv = plane.world.servers[m["tools"][-1]["server"]]
        srv.handle(m["tools"][-1]["name"], {})
    ob.add("staging", True, f"{runs} runs")
    ob.checks = conformance.run(plane, m)
    ob.add("conformance", ob.live,
           f"{conformance.passed(ob.checks)} of 6")
    return ob


def extract(plane) -> list[Onboarding]:
    """Servicing and the desk, moved from code to manifests on
    August 14. Their tools and rules existed; nothing new is
    submitted."""
    return [onboard(plane, template.load(n), rev="", runs=5)
            for n in ("servicing", "desk")]
