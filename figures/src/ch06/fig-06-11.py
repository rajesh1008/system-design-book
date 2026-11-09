"""Figure 6.9  Planes against the five gaps.

Reading order: one row per gap of the evidence chain, named by the state
it reaches; one column per plane. Each cell says whether the plane owns
the gap, feeds the plane that owns it, or writes it down. The last row has
no owning plane: people own the business result.
"""
import figlib as fl
from matplotlib.patches import Rectangle

cols = ["Knowledge", "Action", "Control", "Trail"]
gaps = ["G1 proposal", "G2 permission", "G3 execution", "G4 verified",
        "G5 result"]
cells = {(0, 0): "feeds", (0, 1): "owns", (0, 3): "writes",
         (1, 2): "owns", (1, 3): "writes",
         (2, 1): "owns", (2, 2): "feeds", (2, 3): "writes",
         (3, 3): "owns",
         (4, 3): "feeds"}
style = {"owns": ("verified", ""), "feeds": ("policy", "///"),
         "writes": ("evidence", "...")}

fig, ax = fl.figure(4.5, 3.4)
ax.set_xlim(0, 5.3)
ax.set_ylim(0, len(gaps) + 1)
ax.axis("off")
for j, c in enumerate(cols):
    ax.text(1.78 + j * 0.9, len(gaps) + 0.45, c, ha="center", va="center",
            fontsize=9.5, fontweight="bold")
for i, g in enumerate(gaps):
    y = len(gaps) - 1 - i
    ax.text(0.02, y + 0.5, g, ha="left", va="center", fontsize=9.5)
    for j in range(len(cols)):
        x = 1.35 + j * 0.9
        kind = cells.get((i, j))
        if kind is None:
            ax.add_patch(Rectangle((x, y + 0.1), 0.86, 0.8,
                                   facecolor="white",
                                   edgecolor=fl.GREY_DARK, lw=0.5))
            continue
        tok, hatch = style[kind]
        ax.add_patch(Rectangle((x, y + 0.1), 0.86, 0.8,
                               facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                               hatch=hatch, lw=0.75))
        ax.text(x + 0.43, y + 0.5, kind, ha="center", va="center",
                fontsize=9.5, color=fl.LABEL[tok],
                fontweight="bold" if kind == "owns" else "normal",
                backgroundcolor="white" if hatch else fl.FILL[tok])
fl.save(fig)
