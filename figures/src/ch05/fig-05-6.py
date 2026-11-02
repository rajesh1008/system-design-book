"""Figure 5.6  The decision table template.

Reading order: criteria top to bottom, options left to right; the two
criteria that protect money are marked. Scores read from v0_1.toml
(0 no, 1 with work, 2 as built).
"""
import sys
from pathlib import Path

import figlib as fl
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
from method.design import load  # noqa: E402

dec = load("v0_1").raw["decisions"][0]
crit = ["Keeps a pending\npermission", "One key on\nevery retry", "Ready for\nthe pilot",
        "Low lock-in", "Team can\noperate it"]
opts = dec["options"]
names = {"framework loop": "Framework\nloop (chosen)", "workflow engine": "Workflow\nengine",
         "queue and own ledger": "Queue and\nown ledger"}
WORD = {0: "no", 1: "with work", 2: "as built"}
TOK = {0: "fail", 1: "policy", 2: "verified"}
HATCH = {0: "///", 1: "...", 2: ""}
fig, ax = fl.figure(4.5, 4.0)
ax.set_xlim(0, 10)
ax.set_ylim(0, 7.4)
ax.axis("off")
for j, o in enumerate(opts):
    x = 3.4 + j * 2.2
    ax.text(x + 1.0, 6.85, names[o["name"]], ha="center", va="center", fontweight="bold",
            fontsize=9.5)
for i, c in enumerate(crit):
    y = 5.7 - i
    money = i < 2
    ax.text(0.05, y, c, va="center", fontsize=9.5, fontweight="bold" if money else "normal")
    for j, o in enumerate(opts):
        s = o["scores"][i]
        x = 3.4 + j * 2.2
        ax.add_patch(Rectangle((x, y - 0.42), 2.0, 0.84, facecolor=fl.FILL[TOK[s]],
                               edgecolor=fl.C[TOK[s]], lw=fl.STROKE["data"], hatch=HATCH[s]))
        ax.text(x + 1.0, y, WORD[s], ha="center", va="center", fontsize=9.5,
                bbox=dict(facecolor="white", edgecolor="none", pad=0.6))
ax.add_patch(Rectangle((0, 4.25), 10, 1.95, fill=False, edgecolor=fl.INK,
                       lw=fl.STROKE["emphasis"]))
ax.text(0.05, 0.75, "Sum", va="center", fontweight="bold")
for j, o in enumerate(opts):
    ax.text(3.4 + j * 2.2 + 1.0, 0.75, str(sum(o["scores"])), ha="center", va="center",
            **fl.mono("0"))
ax.text(5, 0.1, "Boxed rows protect money", ha="center", fontsize=9.5, fontstyle="italic")
fl.save(fig)
