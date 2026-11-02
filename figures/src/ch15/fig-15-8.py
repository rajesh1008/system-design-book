"""Figure 15.8  The Decision Table's columns and their owners.

Reading order: one row per column group, top to bottom; the middle
column says where the value comes from and the right column who keeps
it true. The router owns nothing but the route it computes. Lakeshore,
May 2026 (illustrative).
"""
import sys
from pathlib import Path

from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402

rows = (("Step, kind, share", "Plan and trail", "Daniel Price", "ops"),
        ("Risk class, floor", "Risk policy", "Rachel Morgan", "policy"),
        ("Data rule", "Data policy", "Owen Fletcher", "policy"),
        ("Gate result, date", "Golden runs", "Dr. Hannah Clarke", "evidence"),
        ("Route, reason", "Router's rule", "The router", "knowledge"),
        ("Flag, last exercised", "Control plane", "Ben Carter", "ops"))
cols = (0.0, 1.6, 2.95)
heads = ("Columns", "Comes from", "Kept true by")
fig, ax = fl.figure(4.5, 3.4)
n = len(rows)
ax.set_xlim(0, 4.5)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=10, fontweight="bold", color=fl.INK)
for i, (c, src, who, tok) in enumerate(rows):
    y = n - 1 - i
    ax.add_patch(Rectangle((0.0, y + 0.06), 4.5, 0.88, facecolor=fl.FILL[tok],
                           edgecolor=fl.C[tok], lw=0.75))
    for x, t in zip(cols, (c, src, who)):
        ax.text(x + 0.05, y + 0.5, t, va="center", fontsize=9.5, color=fl.INK,
                style="italic" if t == "The router" else None)
fl.save(fig)
