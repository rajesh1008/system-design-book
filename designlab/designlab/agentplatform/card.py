"""The platform card for Monday, August 31, 2026, computed from a
plane with all three use cases on it. Lakeshore figures are
illustrative."""
from __future__ import annotations

from . import chain, conformance, onboard, onboarding, plane, template

OWNER = "Daniel Price"
DATE = "Monday, August 31, 2026"
OUTSIDE = (
    ("IT ticket bot", "gateway for tools; own model key; no golden set"),
    ("marketing copy", "team key; drafts only, no effects"),
)
AUGUST_RUNS = 20


def august(bypass: int = 0):
    """Build August: extract servicing and the desk, onboard loyalty,
    then run each use case's script AUGUST_RUNS times."""
    p = plane.build()
    obs = onboard.extract(p)
    obs.append(onboard.onboard(p, template.load("loyalty"),
                               rev="pb-2026.08.24", bypass=bypass))
    for _ in range(AUGUST_RUNS):
        for name in template.USE_CASES:
            p.run(name)
    return p, obs


def compute(p, obs) -> dict:
    live = [o for o in obs if o.live]
    final = {n: conformance.run(p, p.manifests[n])
             for n in template.USE_CASES}
    covered = [n for n in template.USE_CASES
               if chain.use_case_covered(p, p.manifests[n])]
    gaps = {n: chain.coverage(p, p.manifests[n])
            for n in template.USE_CASES if n not in covered}
    return {"use_cases": len(live),
            "conformance": {n: conformance.passed(c)
                            for n, c in final.items()},
            "covered": covered, "gaps": gaps,
            "builds": len(template.USE_CASES) + len(OUTSIDE),
            "onboard_days": onboarding.total(onboarding.LOYALTY),
            "before_days": onboarding.total(onboarding.DESK)}


def lines(c: dict) -> list[str]:
    n = c["use_cases"]
    conf = ", ".join(f"{k} {v}/6" for k, v in c["conformance"].items())
    out = [f"Platform card, {DATE}. Owner: {OWNER}.",
           f"  use cases on the shared control plane  {n}",
           f"  agent builds on the paved road         {n} of "
           f"{c['builds']}",
           f"  onboarding, latest use case            "
           f"{c['onboard_days']} days (was {c['before_days']})",
           f"  conformance  {conf}",
           f"  evidence-chain coverage                "
           f"{len(c['covered'])} of {n} use cases"]
    for k, (full, total, miss) in c["gaps"].items():
        out.append(f"  still: {k}, {full} of {total} effects; "
                   f"missing {', '.join(miss)}")
    out.append("  outside: " + "; ".join(x for x, _ in OUTSIDE))
    return out
