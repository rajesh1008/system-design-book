"""The topology card: one row per thing the chapter measured, a
target, the measured value, and a check. The highlighted cell is the
count of task types one agent wins, the cell that decided DR-27.1.

The model line converts tokens to dollars at April's blended rate,
$3.12 per million tokens (Chapter 18), so it can sit beside the cost
per verified outcome without a second price table.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import compare, handoff, hierarchy, lock, vote
from .tasks import label

HIGHLIGHT = "types one agent wins"
RATE_PER_MTOK = 3.12


@dataclass
class Row:
    name: str
    target: str
    value: str
    ok: bool


def model_line(tokens_per_task: float, success: float) -> float:
    """Dollars of model tokens per verified outcome."""
    return tokens_per_task * RATE_PER_MTOK / 1e6 / success


def decisions(res: dict) -> list[tuple[str, str, float, float]]:
    """(type, winner, paired difference, token ratio), golden order."""
    out = []
    for kind, r in res.items():
        out.append((label(kind), r.winner, r.diff,
                    r.ow_tokens / r.single_tokens))
    return out


def rows(seed: int = 27, lock_mode: str = "stick") -> list[Row]:
    res = compare.compare(seed)
    t = compare.totals(res)
    r = compare.routed()
    many = r["many"]
    lk = lock.trial(lock_mode, seed=seed)
    hb = handoff.trial("baton", seed=seed)
    d1 = hierarchy.trial(1, "pinned", seed=seed)
    d2 = hierarchy.trial(2, "pinned", seed=seed)
    vt = {x.design: x for x in vote.table(seed)}
    base = vt["single"].tokens
    single_line = model_line(t["single_tokens_per_task"], t["single_ok"])
    routed_tok = t["single_tokens_per_task"] * r["routed_token_ratio"]
    routed_line = model_line(routed_tok, r["routed_ok"])
    ow_names = [label(k) for k, x in res.items()
                if x.winner in ("orchestrator", "tie-orchestrator")]
    return [
        Row(HIGHLIGHT, ">= 9 of 12",
            f"{t['single_wins']} of 12 ({t['single_clear']} clear, "
            f"{t['ties']} ties)", t["single_wins"] >= 9),
        Row("types orchestrator wins", "multi-leg only",
            f"{t['ow_wins']}: rebookings, sched. change",
            all("rebook" in n or "schedule" in n for n in ow_names)),
        Row("3+ legs, verified", "orchestrator ahead",
            f"{100 * many.ow_ok / many.n:.1f}% vs "
            f"{100 * many.single_ok / many.n:.1f}%",
            many.ow_ok > many.single_ok),
        Row("routed by legs", ">= all-single",
            f"{100 * r['routed_ok']:.1f}% at "
            f"{r['routed_token_ratio']:.2f}x tokens",
            r["routed_ok"] >= r["all_single_ok"]),
        Row("model line / outcome", "<= one agent",
            f"${routed_line:.3f} vs ${single_line:.3f}",
            routed_line <= single_line + 0.005),
        Row("conflicting effects", "0",
            f"{lk.conflicts:,} in {lk.overlaps:,} overlaps",
            lk.conflicts == 0),
        Row("handoffs orphaned/2x", "0 and 0",
            f"{hb.orphaned} and {hb.two_owners}",
            hb.orphaned == 0 and hb.two_owners == 0),
        Row("levels below the lead", "<= 2, facts pinned",
            f"1 ({d1.intact:,}/{d2.intact:,} intact)",
            d1.intact >= d1.cases - 2),
        Row("checker on eligibility", "verifier, not vote",
            f"{100 * vt['verifier'].success:.1f}% at "
            f"{vt['verifier'].tokens / base:.2f}x",
            vt["verifier"].success > vt["vote"].success),
    ]
