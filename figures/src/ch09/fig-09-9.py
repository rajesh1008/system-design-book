"""Figure 9.9  Replay time distribution.

Reading order: left to right from the median to the slowest replay in
Ben Carter's March benchmark; the line is the three-second target.
From durable.card.BEN_REPLAY_S.
"""
import sys
from pathlib import Path

import figlib as fl

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
from durable.card import BEN_REPLAY_S as B  # noqa: E402

fig, ax = fl.figure(4.5, 3.2)
keys = ["p50", "p90", "p99", "max"]
vals = [B[k] for k in keys]
toks = ["ops", "ops", "verified", "ops"]
for i, (k, v, t) in enumerate(zip(keys, vals, toks)):
    ax.bar(i, v, width=0.6, color=fl.FILL[t], edgecolor=fl.C[t], lw=fl.STROKE["data"],
           hatch=fl.HATCH[i])
    ax.text(i, v + 0.08, f"{v:.1f} s" if k != "p50" else f"{v:.2f} s", ha="center", fontsize=9.5)
ax.axhline(B["target"], color=fl.C["policy"], ls="--", lw=1.2)
ax.text(3.45, B["target"] + 0.07, "target 3 s", color=fl.LABEL["policy"], fontsize=9.5, ha="right")
ax.set_xticks(range(4))
ax.set_xticklabels(keys)
ax.set_ylabel("Replay time (s)")
ax.set_ylim(0, 3.5)
ax.set_xlabel(f"{B['runs']:,} trajectories, phase-2 journal")
for sp in ("top", "right"):
    ax.spines[sp].set_visible(False)
fl.save(fig)
