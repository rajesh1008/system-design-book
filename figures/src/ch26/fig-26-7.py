"""Figure 26.7  Code mode against direct calls, one refund check.

Reading order: two pairs of bars, direct calls above code mode in
each. Left pair: tokens in the final context; right pair: tokens
processed across all turns. Values from gateway.demo --part codemode;
both paths make eleven calls through the gateway.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402

groups = ("Final context", "Processed, all turns")
direct = (2491, 27467)
code = (984, 1794)
fig, ax = fl.figure(4.5, 3.0)
y = [3, 2, 1, 0]
vals = [direct[0], code[0], direct[1], code[1]]
cols = [fl.C["ops"], fl.FILL["model"], fl.C["ops"], fl.FILL["model"]]
edges = [fl.C["ops"], fl.C["model"], fl.C["ops"], fl.C["model"]]
ax.barh(y, vals, color=cols, edgecolor=edges, height=0.6,
        hatch=["", "///", "", "///"])
ax.set_yticks(y)
ax.set_yticklabels(["Direct", "Code mode", "Direct", "Code mode"])
for yi, v in zip(y, vals):
    fl.label_line(ax, v, yi, f"{v:,}")
ax.axhline(1.5, color=fl.GREY_LIGHT, lw=0.75)
ax.text(31000, 2.5, groups[0], ha="right", va="center", fontsize=9,
        color=fl.INK)
ax.text(31000, 0.5, groups[1], ha="right", va="center", fontsize=9,
        color=fl.INK)
ax.set_xlim(0, 32000)
ax.set_xlabel("Tokens (eleven calls either way)")
ax.grid(axis="x")
fl.save(fig)
