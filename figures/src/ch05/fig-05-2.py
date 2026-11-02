"""Figure 5.2  The requirement question bank by plane.

Reading order: five columns left to right (action, control, knowledge,
trail, outcome), question ids top to bottom; the first ten asked when
time is short are filled. Generated from method.artifacts.
"""
import sys
from pathlib import Path

import figlib as fl
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
from method.artifacts import FIRST_TEN, GROUP_OF, QUESTIONS  # noqa: E402

TOK = {"action": "ops", "control": "policy", "knowledge": "knowledge",
       "trail": "evidence", "outcome": "org"}
SHORT = {"A1": "effects", "A2": "undo", "A3": "largest", "A4": "systems",
         "A5": "repeats", "A6": "read-only", "C1": "grantor", "C2": "autonomy",
         "C3": "wait", "C4": "stop", "C5": "off switch", "C6": "obligations",
         "K1": "knows", "K2": "freshness", "K3": "outside",
         "K4": "memory", "T1": "proof", "T2": "truth", "T3": "verifier",
         "T4": "retention", "O1": "number", "O2": "volume", "O3": "cost",
         "O4": "failure cost"}
groups = ["action", "control", "knowledge", "trail", "outcome"]
fig, ax = fl.figure(4.5, 3.6)
ax.set_xlim(0, 5)
ax.set_ylim(0, 7.4)
ax.axis("off")
for c, g in enumerate(groups):
    tok = TOK[g]
    ax.text(c + 0.5, 7.0, g.capitalize(), ha="center", va="center",
            fontweight="bold", color=fl.LABEL[tok])
    ids = [q for q in QUESTIONS if GROUP_OF[q[0]] == g]
    for r, q in enumerate(ids):
        y = 6.1 - r
        first = q in FIRST_TEN
        ax.add_patch(Rectangle((c + 0.05, y - 0.42), 0.9, 0.84,
                               facecolor=fl.FILL[tok] if first else "white",
                               edgecolor=fl.C[tok], lw=fl.STROKE["control" if first else "data"]))
        ax.text(c + 0.5, y + 0.15, q, ha="center", va="center", **fl.mono(q))
        ax.text(c + 0.5, y - 0.2, SHORT[q], ha="center", va="center", fontsize=9.5)
ax.text(2.5, 0.25, "Filled, heavy border: the first ten", ha="center",
        va="center", fontsize=9.5, fontstyle="italic")
fl.save(fig)
