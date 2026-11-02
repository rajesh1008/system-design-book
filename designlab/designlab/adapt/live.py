"""Chapter 17 live lab: frontier and small-model labels, live.

One hundred messages from the training months, then one hundred golden
cases from May 2026. Ten messages a call, ten calls a role. The frontier role is the
teacher; the small role, with the same prompt, is the "try the context
first" baseline. Responses are cached in adapt/fixtures, so a second
run spends nothing and the offline demo replays them. Reads
ANTHROPIC_API_KEY from the environment through common.client and never
prints it. The meter caps the run at $0.50.

    python3 -m adapt.live
"""
from __future__ import annotations

import sys
from collections import Counter

from common.spend import SpendMeter
from common.text import emit

from . import teacher as T
from .data import generate


def run(seed: int = 17, n: int = 100) -> list[str]:
    msgs = generate(seed)
    meter = SpendMeter(cap_usd=0.50)
    lines = []
    for month in (None, "2026-05"):
        sample = T.live_sample(msgs, n, seed, month)
        where = "training messages" if month is None else \
            f"golden cases from {month}"
        lines.append(f"live: {n} {where}, 10 to a call")
        lines += _roles(sample, meter, n)
    lines.append(f"spent ${meter.spent_usd:.4f} on {meter.calls} calls")
    return lines


def _roles(sample, meter, n) -> list[str]:
    lines = []
    for role in ("frontier", "small"):
        got, st = T.label(sample, role, meter, offline=False)
        right = sum(got[m.msg_id] == m.label for m in sample)
        miss = Counter((m.label, got[m.msg_id]) for m in sample
                       if got[m.msg_id] != m.label)
        lines.append(f"  {role:<8} {st['model']:<16} agrees {right}/{n};"
                     f" calls {st['calls']}, cached {st['cached']}")
        for (want, said), k in miss.most_common(3):
            lines.append(f"    {k} x {want} -> {said}")
    return lines


def main() -> int:
    for ln in run():
        emit(ln)
    return 0


if __name__ == "__main__":
    sys.exit(main())
