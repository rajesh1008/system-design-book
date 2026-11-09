"""Figure 9.8  Resume rate by kill point.

Reading order: left to right along the twelve steps; each line is one
strategy's share of kill points (two per step) that resumed correctly.
From durable.killsuite, run when the figure is built.
"""
import sys
from pathlib import Path

import figlib as fl

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
from durable.killsuite import suite  # noqa: E402
from durable.workflow import STEPS  # noqa: E402

fig, ax = fl.figure(4.8, 3.4)
x = list(range(1, len(STEPS) + 1))
series = [("durable", "verified", "run store"), ("framework", "org", "February checkpointer"),
          ("memory", "fail", "pilot loop")]
for k, (s, tok, label) in enumerate(series):
    rows = suite(s)
    y = [100 * sum(r["correct"] for r in rows[2 * i:2 * i + 2]) / 2 for i in range(len(STEPS))]
    off = (1 - k) * 2.0
    ax.plot(x, [v + off for v in y], color=fl.C[tok], marker=fl.MARKERS[k], ls=fl.LINESTYLES[k], lw=1.6)
    ax.text(12.3, y[-1] + off + (-5 if k == 1 else 6 if k == 0 else 0), label,
            color=fl.LABEL[tok], fontsize=9.5, va="center")
ax.set_xticks(x)
ax.set_xlabel("Kill point (step number)")
ax.set_ylabel("Kill points resumed correctly (%)")
ax.set_ylim(-8, 112)
ax.set_xlim(0.5, 16.2)
for sp in ("top", "right"):
    ax.spines[sp].set_visible(False)
fl.save(fig)
