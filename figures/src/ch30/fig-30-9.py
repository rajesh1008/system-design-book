"""Figure 30.9  The decision for Lakeshore.

Reading order: one row per part, top to bottom; whether Lakeshore
rents it or owns it, and the evidence behind the line. From DR-30.1,
Tuesday, June 30, 2026.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

rows = (("Runtime", "Rent:\nAgentCore", "39 of 44", "org"),
        ("Loop", "LangGraph,\nopen source", "No manifest\nchange", "org"),
        ("Checkpoints", "Own:\nrun store", "0 lost in\nmigration", "verified"),
        ("Policy, tools", "Own: engine,\ngateway", "One engine", "verified"),
        ("Memory, trail", "Own; memory\noff", "K1, T3", "verified"),
        ("Exit", "LangSmith\nadapter", "0 manifest\nchanges", "org"))
cols = (0.0, 1.45, 3.05)
heads = ("Part", "Rent or own", "Evidence")
fig, ax = fl.figure(4.5, 3.0)
n = len(rows)
ax.set_xlim(0, 4.6)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=10,
            fontweight="bold", color=fl.INK)
for i, (a, b, c, tok) in enumerate(rows):
    y = n - 1 - i
    ax.add_patch(Rectangle((0.0, y + 0.06), 4.6, 0.88,
                           facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                           lw=0.75))
    for x, t in zip(cols, (a, b, c)):
        ax.text(x + 0.05, y + 0.5, t, va="center", fontsize=9,
                color=fl.INK, linespacing=0.95,
                fontweight="bold" if x == cols[0] else None)
fl.save(fig)
