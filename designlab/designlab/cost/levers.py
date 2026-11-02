"""The five levers and how far each one moves the bill.

Each lever is moved from Lakeshore's May 2026 design to a worse and a
better setting, one at a time, and the month is recosted. The worse
settings are where the pilot started or what a careless change would
do; the better settings are the next step anyone has proposed.
"""
from __future__ import annotations

from dataclasses import replace

from .unit import MAY, Month, month_cost, with_levers

# lever: (worse settings, label, better settings, label)
MOVES = {
    "model mix": ({"small": 0.0, "mid": 0.0}, "all frontier",
                  {"small": 0.80, "mid": 0.05}, "80% small"),
    "cache": ({"cache": False}, "no cache",
              {"hit": 0.88}, "88% hit"),
    "steps": ({"repeat_cap": None, "step_cap": None}, "no caps",
              {"repeat_cap": 0}, "no re-search"),
    "retries": ({"retry_scale": 3.0}, "3x retries",
                {"retry_scale": 0.0}, "no retries"),
    "tokens": ({"token_scale": 1.3}, "+30% prompt",
               {"token_scale": 0.7}, "-30% prompt"),
}


def sensitivity(m: Month = MAY, seed: int = 18) -> list[dict]:
    base = month_cost(m, seed)
    rows = []
    for lever, (worse, wl, better, bl) in MOVES.items():
        w = month_cost(with_levers(m, **worse), seed)
        b = month_cost(with_levers(m, **better), seed)
        rows.append({
            "lever": lever, "worse": wl, "better": bl,
            "model_base": base["model_per_attempt"],
            "model_worse": w["model_per_attempt"],
            "model_better": b["model_per_attempt"],
            "outcome_base": base["per_outcome"],
            "outcome_worse": w["per_outcome"],
            "outcome_better": b["per_outcome"],
        })
    rows.sort(key=lambda r: r["model_worse"] - r["model_better"],
              reverse=True)
    return rows


def price_cut(m: Month = MAY, cut: float = 0.5, seed: int = 18) -> dict:
    """What a provider price cut does to the month."""
    base = month_cost(m, seed)
    lines = dict(base["lines"])
    lines["model tokens"] *= (1.0 - cut)
    total = sum(lines.values())
    return {"before": base["per_outcome"],
            "after": total / base["verified"],
            "model_before": base["lines"]["model tokens"],
            "model_after": lines["model tokens"]}


def handoff_lever(m: Month = MAY, seed: int = 18,
                  rates=(0.06, 0.12, 0.18)) -> list[tuple[float, float]]:
    """The lever that is not on the token bill: attempts handed off."""
    return [(r, month_cost(replace(m, handoff=r), seed)["per_outcome"])
            for r in rates]
