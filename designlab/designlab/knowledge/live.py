"""Chapter 20 live lab: twelve questions, two ways, on the small model.

Each question is asked once against the semantic layer (a metric query
under the metric-query contract) and once against the raw schema (SQL,
the shadow trial's way). Both go through the same guard. Responses are
cached in knowledge/fixtures, so a second run spends nothing and the
offline demo replays them. Reads ANTHROPIC_API_KEY from the environment
through common.client and never prints it. The meter caps the run at
$0.50.

    python3 -m knowledge.live
"""
from __future__ import annotations

import sys

from common.spend import SpendMeter
from common.text import emit

from . import entitle as E
from . import sql as S
from . import translate as T
from .questions import CALLERS, QUESTIONS


def run(replay: bool | None = None) -> tuple[list[str], list[dict]]:
    meter = SpendMeter(cap_usd=0.50)
    c = T.client(meter, replay)
    guard = S.Guard()
    raw_guard = S.Guard(raw_allowed=True)
    lines, rows = [], []
    cached = 0
    for qid, who, text in QUESTIONS:
        ent = E.from_token(CALLERS[who])
        t = T.to_query(text, guard.layer, c)
        cached += t.cached
        if t.status == "ok":
            d = guard.ask(t.query, ent)
            layer_out = d.status if d.status == "answered" else d.reason
            metric = t.query.metric
        else:
            d, layer_out, metric = None, t.status, "-"
        sql, _, hit = T.to_sql(text, c)
        cached += hit
        rd = raw_guard.ask_sql(sql, ent)
        raw_usd = rd.estimate.usd if rd.estimate else None
        raw_out = rd.status if rd.status == "answered" else rd.reason
        rows.append({"id": qid, "who": who, "translation": t,
                     "metric": metric, "layer": layer_out,
                     "layer_decision": d, "raw_sql": sql,
                     "raw": raw_out, "raw_usd": raw_usd,
                     "raw_detail": rd.detail})
        usd = "   n/a" if raw_usd is None else f"{raw_usd:>9.4f}"
        lines.append(f"{qid:<4}{metric[:24]:<25}{layer_out:<13}"
                     f"{raw_out:<12}{usd}")
    lines.append(f"model calls {meter.calls}, cost as recorded "
                 f"${meter.spent_usd:.4f}")
    return lines, rows


def main() -> int:
    emit("id  layer metric             layer        raw SQL     raw $")
    lines, _ = run()
    for ln in lines:
        emit(ln)
    return 0


if __name__ == "__main__":
    sys.exit(main())
