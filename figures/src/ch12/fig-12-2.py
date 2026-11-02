"""Figure 12.2  Retry policies by plane.

Reading order: one row per operation, grouped by plane; columns give
the timeout, the number of tries, and what makes a retry safe. A
heavy red cell is an operation that is never retried. From
failure.retry.POLICIES.
"""
import sys
from pathlib import Path

import figlib as fl
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
from failure.retry import POLICIES  # noqa: E402

TOK = {"action": "ops", "control": "policy", "knowledge": "knowledge",
       "trail": "evidence"}
n = len(POLICIES)
fig, ax = fl.figure(4.5, 3.6)
ax.axis("off")
ax.set_xlim(0, 10)
ax.set_ylim(-0.1, n + 1.1)
for x, h in ((0.1, "Plane"), (2.2, "Operation"), (5.15, "Timeout"),
             (6.55, "Tries"), (7.85, "Safe because")):
    ax.text(x, n + 0.5, h, ha="left", va="center", fontsize=9.5,
            fontweight="bold")
for i, p in enumerate(POLICIES):
    y = n - 1 - i
    tok = TOK[p.plane]
    never = p.key == "never"
    ax.text(0.1, y + 0.5, p.plane, va="center", fontsize=9,
            color=fl.LABEL[tok], fontweight="bold")
    ax.text(2.2, y + 0.5, p.operation, va="center", fontsize=9)
    ax.text(5.15, y + 0.5, f"{p.timeout_s:g} s", va="center", fontsize=9)
    ax.add_patch(Rectangle((7.75, y + 0.1), 2.2, 0.8,
                           facecolor=fl.FILL["fail" if never else tok],
                           edgecolor=fl.C["fail" if never else tok],
                           lw=fl.STROKE["emphasis" if never else "data"],
                           ))
    ax.text(6.9, y + 0.5, str(p.attempts), va="center", ha="center",
            fontsize=9)
    ax.text(7.85, y + 0.5, "not retried" if never else
            {"read": "a read"}.get(p.key, p.key),
            va="center", fontsize=9)
fl.save(fig)
