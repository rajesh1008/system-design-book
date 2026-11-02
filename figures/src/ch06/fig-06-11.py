"""Figure 6.11  Autonomy level by task type, with hand-off mode and what
the customer sees.

Reading order: one row per task type in autonomy-2026-01. The ladder of
four squares fills one more square for each level handed over, and the
level is named beside it; every row runs at its ceiling. The right
columns give the hand-off mode and the first state the customer is shown.
Values from 04-code/designlab/planes/autonomy.toml.
"""
import figlib as fl
from matplotlib.patches import Rectangle

rows = [("Refund", 1, "Approval", "Sync", "waiting"),
        ("Rebook", 2, "Notify", "Async", "done"),
        ("Voucher", 3, "Unattended", "Async", "done"),
        ("Hotel", 0, "Suggest", "Async", "with a\nperson")]

fig, ax = fl.figure(4.5, 3.2)
ax.set_xlim(0, 7.3)
ax.set_ylim(0, len(rows) + 1)
ax.axis("off")
for x, h in ((2.75, "Level"), (5.0, "Hand-off"), (6.45, "Sees")):
    ax.text(x, len(rows) + 0.45, h, ha="center", va="center",
            fontsize=9.5, fontweight="bold")
for i, (name, lvl, lname, mode, sees) in enumerate(rows):
    y = len(rows) - 1 - i
    ax.text(0.02, y + 0.5, name, ha="left", va="center", fontsize=10)
    for j in range(4):
        x = 1.3 + j * 0.3
        on = j <= lvl
        ax.add_patch(Rectangle((x, y + 0.3), 0.24, 0.4,
                               facecolor=fl.C["policy"] if on else "white",
                               edgecolor=fl.C["policy"] if on else fl.GREY_DARK,
                               lw=0.75))
    ax.text(2.55, y + 0.5, lname, ha="left", va="center", fontsize=9.5,
            color=fl.LABEL["policy"])
    async_ = mode == "Async"
    ax.add_patch(Rectangle((4.5, y + 0.15), 1.0, 0.7,
                           facecolor="white", edgecolor=fl.C["org"],
                           ls="--" if async_ else "-", lw=0.9))
    ax.text(5.0, y + 0.5, mode, ha="center", va="center", fontsize=9.5)
    done = sees == "done"
    ax.text(6.45, y + 0.5, sees, ha="center", va="center", fontsize=9.5,
            color=fl.LABEL["verified"] if done else fl.INK,
            fontweight="bold" if done else "normal")
fl.save(fig)
