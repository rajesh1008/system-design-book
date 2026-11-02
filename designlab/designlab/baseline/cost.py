"""Cost per change, split by path, then blended.

Finance's cost pools (labor, tooling, rework) are divided by the
changes each path handled. The blend is recomposed from the two paths,
never averaged directly, so a shift in mix shows up as a shift in mix.
"""
from __future__ import annotations

from statistics import mean

from corpus.ops import LOADED_HOURLY_USD, WEIGHTS


def decompose(t: dict, person_scale: float = 1.0,
              drop_rework: bool = False) -> dict:
    w = WEIGHTS["ops_changes"]
    changes = t["ops_changes"]
    n = {"person": 0, "self-service": 0}
    for c in changes:
        n[c["handled_by"]] += w
    pools: dict[str, dict[str, float]] = {"person": {}, "self-service": {}}
    for p in t["ops_cost_pools"]:
        if drop_rework and p["category"] == "rework":
            continue
        usd = p["annual_usd"] * (person_scale if p["path"] == "person"
                                 else 1.0)
        pools[p["path"]][p["pool"]] = usd / n[p["path"]]
    per = {path: sum(v.values()) for path, v in pools.items()}
    total_usd = sum(per[p] * n[p] for p in n)
    total_n = sum(n.values())
    minutes = mean(c["handle_minutes"] for c in changes
                   if c["handle_minutes"] is not None)
    return {
        "changes": n, "pools": pools, "per_change": per,
        "blended": total_usd / total_n, "annual_usd": total_usd,
        "share": {p: n[p] / total_n for p in n},
        "log_minutes": minutes,
        "log_labor_per_change": minutes / 60 * LOADED_HOURLY_USD,
    }
