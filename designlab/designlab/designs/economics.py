"""Cost per verified outcome for a worked design, in Chapter 38's lines.

Each design states its month in the same seven lines finance closes
Lakeshore's month in (cost.unit.LINES): model tokens, tools and fees,
platform, verification, review labor, rework, and repeat contacts.
Model tokens are priced at Lakeshore's contract (serving.prices,
$3.00 and $15.00 per million, cached reads at a tenth), and people's
minutes at Chapter 4's loaded rate. Every input is a stated
assumption in the design file; the outputs are design-time estimates,
not measurements. All amounts are US dollars.
"""
from __future__ import annotations

from dataclasses import dataclass

from cost.unit import LINES, LOADED_PER_MIN
from serving.prices import CONTRACT

INPUTS = ("cases_per_year", "agent_share", "calls_per_case",
          "in_tokens", "out_tokens", "cached_share", "fees_per_case",
          "platform_month", "verify_per_case", "approval_share",
          "approval_min", "handoff_share", "pickup_min", "error_rate",
          "rework_min", "repeat_share", "repeat_min", "verified_rate",
          "person_cost", "build_usd")


@dataclass(frozen=True)
class Month:
    design: str
    verified: float
    lines: dict
    total: float
    per_outcome: float
    person_cost: float
    payback_months: float


def month(spec: dict, **override) -> Month:
    e = dict(spec["economics"])
    e.update(override)
    executed = e["cases_per_year"] / 12 * e["agent_share"]
    attempts = executed / (1.0 - e["handoff_share"])
    verified = executed * e["verified_rate"]
    tok_in = e["in_tokens"] * e["calls_per_case"]
    tok_out = e["out_tokens"] * e["calls_per_case"]
    per_attempt = (tok_in * (1 - e["cached_share"])
                   * CONTRACT.input_usd_per_mtok
                   + tok_in * e["cached_share"]
                   * CONTRACT.cache_read_usd_per_mtok
                   + tok_out * CONTRACT.output_usd_per_mtok) / 1e6
    rate = LOADED_PER_MIN
    review = (executed * e["approval_share"] * e["approval_min"]
              + (attempts - executed) * e["pickup_min"]) * rate
    lines = dict(zip(LINES, (
        attempts * per_attempt,
        attempts * e["fees_per_case"],
        e["platform_month"],
        executed * e["verify_per_case"],
        review,
        executed * e["error_rate"] * e["rework_min"] * rate,
        verified * e["repeat_share"] * e["repeat_min"] * rate,
    )))
    total = sum(lines.values())
    per = total / verified
    saved = (e["person_cost"] - per) * verified
    payback = e["build_usd"] / saved if saved > 0 else float("inf")
    return Month(spec["design"]["id"], verified, lines, total, per,
                 e["person_cost"], payback)
