"""Figure 6.8  The reference diagram as data.

Reading order: one row per edge of the reference diagram, top to bottom.
Each edge names its contract, the planes it joins, and the unit test that
enforces it. Values from 04-code/designlab/planes/contracts.toml and
python3 -m planes.demo --part contracts (seed 6).
"""
import figlib as fl
from matplotlib.patches import Rectangle

rows = [("C1", "Knowledge", "Action", "test_c1"),
        ("C2", "Action", "Control", "test_c2"),
        ("C3", "Control", "Gateway", "test_c3"),
        ("C4", "Action", "Trail", "test_c4"),
        ("C5", "Control", "Trail", "test_c5"),
        ("C6", "Trail", "Everyone", "test_c6")]

fig, ax = fl.figure(4.5, 3.6)
ax.set_xlim(0, 4)
ax.set_ylim(-0.9, len(rows) + 1)
ax.axis("off")
for x, h in zip((0.3, 1.15, 2.2, 3.35), ("Edge", "From", "To", "Test")):
    ax.text(x, len(rows) + 0.45, h, ha="center", va="center", fontsize=10,
            fontweight="bold", color=fl.INK)
for i, (c, a, b, t) in enumerate(rows):
    y = len(rows) - 1 - i
    ax.add_patch(Rectangle((0.02, y + 0.1), 0.56, 0.8,
                           facecolor=fl.FILL["ops"], edgecolor=fl.C["ops"],
                           lw=0.75))
    ax.text(0.3, y + 0.5, c, ha="center", va="center", fontsize=10,
            color=fl.LABEL["ops"])
    ax.text(1.15, y + 0.5, a, ha="center", va="center", fontsize=9.5)
    ax.text(2.2, y + 0.5, b, ha="center", va="center", fontsize=9.5)
    ax.add_patch(Rectangle((2.8, y + 0.1), 1.1, 0.8,
                           facecolor=fl.FILL["evidence"],
                           edgecolor=fl.C["evidence"], lw=0.75))
    ax.text(3.35, y + 0.5, t, ha="center", va="center",
            color=fl.LABEL["evidence"], **fl.mono(t))
ax.text(2.0, -0.45, "Six contracts, none untested", ha="center",
        va="center", fontsize=10, fontstyle="italic", color=fl.INK)
fl.save(fig)
