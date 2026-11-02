"""Figure 11.1  Isolation levels from process to VM.

Reading order: one row per level, weakest at the top. The bar shows what
a session still shares with its neighbors at that level; the shared
layer is named on the right. A thicker outline marks the two levels
Lakeshore runs: an OS sandbox for its own tools and a microVM for code.
"""
import figlib as fl
from matplotlib.patches import Rectangle

rows = [("Same process", 1, "memory"),
        ("Own process", 2, "filesystem"),
        ("OS sandbox", 3, "kernel"),
        ("Container", 3, "kernel"),
        ("User-space kernel", 4, "host kernel, narrowed"),
        ("MicroVM", 5, "hypervisor"),
        ("Own VM or host", 6, "hardware")]
used = {"OS sandbox", "MicroVM"}

fig, ax = fl.figure(4.5, 3.4)
ax.set_xlim(0, 7.4)
ax.set_ylim(-0.6, len(rows) + 0.6)
ax.axis("off")
ax.text(0.02, len(rows) + 0.2, "Level", fontsize=9.5, fontweight="bold")
ax.text(5.05, len(rows) + 0.2, "Still shared", fontsize=9.5,
        fontweight="bold")
for i, (name, depth, shared) in enumerate(rows):
    y = len(rows) - 1 - i
    tok = "policy" if name in used else "ops"
    ax.text(0.02, y + 0.45, name, ha="left", va="center", fontsize=9.5)
    ax.add_patch(Rectangle((2.3, y + 0.15), depth * 0.42, 0.6,
                           facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                           lw=1.6 if name in used else 0.6,
                           hatch="" if name in used else "///"))
    ax.text(5.05, y + 0.45, shared, ha="left", va="center", fontsize=9)
ax.annotate("", xy=(4.9, -0.35), xytext=(2.3, -0.35),
            arrowprops=dict(arrowstyle="->", color=fl.GREY_DARK, lw=0.8))
ax.text(3.6, -0.55, "stronger boundary, higher start cost", ha="center",
        va="top", fontsize=9, color=fl.INK)
fl.save(fig)
