"""Figure 9.5  Engines and frameworks compared.

Reading order: one row per option, top to bottom from the engine to the
pilot loop; columns name what survives a restart. From durable.card.
"""
import sys
from pathlib import Path

import figlib as fl
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
from durable.card import ENGINE_COLS, ENGINES  # noqa: E402

fig, ax = fl.figure(4.8, 3.4)
ax.axis("off")
ncol = len(ENGINE_COLS)
x0, cw, rh = 2.9, 1.45, 1.0
ax.set_xlim(0, x0 + cw * ncol)
ax.set_ylim(-0.2, len(ENGINES) + 1.2)
for j, c in enumerate(ENGINE_COLS):
    ax.text(x0 + cw * (j + 0.5), len(ENGINES) + 0.55, c, ha="center", va="center",
            fontsize=9.5, fontweight="bold")
TOK = {"yes": "verified", "keys": "verified", "no": "fail", "in state": "org"}
for i, (name, cells) in enumerate(ENGINES):
    y = len(ENGINES) - 1 - i
    tok_row = "ops" if i != 2 else "evidence"
    ax.text(0.05, y + 0.5, name, va="center", fontsize=9.5,
            color=fl.LABEL[tok_row], fontweight="bold" if i == 2 else "normal")
    for j, v in enumerate(cells):
        tok = TOK[v]
        ax.add_patch(Rectangle((x0 + cw * j + 0.04, y + 0.08), cw - 0.08, rh - 0.16,
                               facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                               lw=fl.STROKE["data"], hatch=fl.HATCH[1] if v == "no" else ""))
        ax.text(x0 + cw * (j + 0.5), y + 0.5, v, ha="center", va="center", fontsize=9.5)
fl.save(fig)
