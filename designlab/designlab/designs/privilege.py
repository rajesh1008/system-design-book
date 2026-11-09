"""Chapter 45's privilege rule for internal designs.

An internal agent is granted access by colleagues, often as a service
account that never expires. The design states its privilege in a
[privilege] block: what the run's credential is, how long it lives,
what it reads, which systems it writes, and which credentials stand
(exist between runs). The October request is kept beside it under
[privilege.requested] so the review can see what was asked for.

    PRV-1  an internal design has no privilege block, holds a standing
           credential, lets a run credential live past an hour, or
           writes a system no acting effect of the design names
           (gap G2)

Designs that do not say facing = "internal" get no finding.
"""
from __future__ import annotations

from method.lint import Finding

MAX_TTL_MINUTES = 60
ACTING = ("act", "notify", "approve")


def internal(spec: dict) -> bool:
    return spec.get("design", {}).get("facing") == "internal"


def acting_systems(spec: dict) -> set[str]:
    return {e["system"] for e in spec.get("effects", [])
            if e.get("tier") in ACTING and e.get("system")}


def prv_1(spec: dict) -> list[Finding]:
    if not internal(spec):
        return []
    p = spec.get("privilege")
    if not p:
        return [Finding("PRV-1", "privilege", "no privilege block")]
    out = [Finding("PRV-1", "privilege", f"standing credential: {c}")
           for c in p.get("standing", [])]
    ttl = p.get("ttl_minutes", 0)
    if not ttl:
        out.append(Finding("PRV-1", "privilege",
                           "credential never expires"))
    elif ttl > MAX_TTL_MINUTES:
        out.append(Finding("PRV-1", "privilege",
                           f"credential lives {ttl} minutes"))
    for s in p.get("writes", []):
        if s not in acting_systems(spec):
            out.append(Finding("PRV-1", "privilege",
                               f"writes {s}; no acting effect there"))
    return out


def requested_vs_designed(spec: dict) -> dict:
    """What the October request asked for against the design."""
    p = spec.get("privilege", {})
    r = p.get("requested", {})
    return {"standing_asked": len(r.get("standing", [])),
            "standing_now": len(p.get("standing", [])),
            "writes_asked": len(r.get("writes", [])),
            "writes_now": len(p.get("writes", [])),
            "ttl": p.get("ttl_minutes", 0)}
