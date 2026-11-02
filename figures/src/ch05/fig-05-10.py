"""Figure 5.10  The forty-five-minute clock.

Reading order: top to bottom, one bar per artifact in the order each
feeds the next, along a minute axis left to right. From
method.artifacts.CLOCK and ARTIFACTS.
"""
import sys
from pathlib import Path

import figlib as fl

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
from method.artifacts import ARTIFACTS, CLOCK  # noqa: E402

TOK = ["org", "ops", "ops", "ops", "policy", "fail", "evidence", "verified"]
fig, ax = fl.figure(4.5, 3.4)
for i, ((s, e, _), (_, name, _), tok, h) in enumerate(zip(CLOCK, ARTIFACTS, TOK, fl.HATCH)):
    ax.barh(i, e - s, left=s, height=0.62, color=fl.FILL[tok], edgecolor=fl.C[tok],
            linewidth=fl.STROKE["data"], hatch=h)
    ax.text(e + 0.6, i, f"{e - s} min", va="center", fontsize=9.5)
ax.set_yticks(range(len(CLOCK)))
ax.set_yticklabels([a[1] for a in ARTIFACTS])
ax.invert_yaxis()
ax.set_xlim(0, 52)
ax.set_xticks([0, 5, 12, 18, 26, 31, 39, 45])
ax.set_xlabel("Minutes into the interview")
ax.grid(axis="y", visible=False)
for sp in ("top", "right"):
    ax.spines[sp].set_visible(False)
fl.save(fig)
