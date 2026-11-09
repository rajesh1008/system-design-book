"""Figure 41.4  Skills by role.

Reading order: one row per seat, top to bottom, one column per skill,
left to right; each cell is the level from 0 to 3, and a shaded cell
is level 2 or higher. The two seats marked with a start date were
signed hires on August 31, 2026. Below the grid, the count of
holders at level 2 or higher, lead excluded: control and evaluation
have one each until September. From org.roles and org.skills.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from org.roles import SEATS  # noqa: E402
from org.skills import SKILLS, coverage  # noqa: E402

heads = ("Dist.", "Models", "Retr.", "Control", "Eval.", "Ops")
short = {"Daniel Price": "Lead", "agent systems architect": "Architect*",
         "evaluation engineer 2": "Eval. eng. 2*"}


def label(s):
    if s.holder in short:
        return short[s.holder]
    return (s.holder.replace("agent engineer", "Agent eng.")
            .replace("platform engineer", "Platform eng.")
            .replace("evaluation engineer", "Eval. eng."))


fig, ax = fl.figure(4.5, 3.8)
n = len(SEATS)
x0, cw = 1.6, 0.62
ax.set_xlim(0, x0 + cw * 6 + 0.05)
ax.set_ylim(-1.3, n + 0.9)
ax.axis("off")
for j, h in enumerate(heads):
    ax.text(x0 + cw * j + cw / 2, n + 0.4, h, ha="center", va="center",
            fontsize=9, fontweight="bold", color=fl.INK)
for i, s in enumerate(SEATS):
    y = n - 1 - i
    ax.text(0.02, y + 0.5, label(s), va="center", fontsize=9,
            color=fl.INK)
    for j, lvl in enumerate(s.levels):
        ax.add_patch(Rectangle((x0 + cw * j, y + 0.06), cw - 0.06, 0.88,
                               facecolor=fl.C["org"] if lvl >= 2 else "white",
                               edgecolor=fl.C["org"], lw=0.6))
        ax.text(x0 + cw * j + cw / 2 - 0.03, y + 0.5, str(lvl),
                ha="center", va="center", fontsize=9,
                color="white" if lvl >= 2 else fl.INK)
cov = coverage()
ax.text(0.02, -0.55, "Aug 31, 2+", va="center", fontsize=9,
        fontweight="bold", color=fl.INK)
for j, k in enumerate(SKILLS):
    ax.text(x0 + cw * j + cw / 2 - 0.03, -0.55, str(len(cov[k])),
            ha="center", va="center", fontsize=9, fontweight="bold",
            color=fl.INK)
fl.save(fig)
