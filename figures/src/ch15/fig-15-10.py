"""Figure 15.10  The portfolio scorecard, May 12 to 25, 2026.

Reading order: one row per route, top to bottom; columns are share of
steps, golden pass, residual failure rate, escalation, and cost per
verified outcome in cents. Every flag was last exercised May 12, 2026.
Lakeshore (illustrative).
"""
import sys
from pathlib import Path

from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402

rows = (("Booking read\nOW small", "33%", "60/60", "0.1%", "-", "0.1"),
        ("Fare read\nfrontier", "11%", "60/60", "0.2%", "-", "0.5"),
        ("Change intent\ncascade", "18%", "98.9%", "0.8%", "11%", "0.3"),
        ("Refund reason\nsmall", "9%", "60/60", "0.1%", "-", "0.1"),
        ("Offer choice\nsmall", "5%", "60/60", "0.1%", "-", "0.1"),
        ("Eligibility\nmid at high", "5%", "60/60", "0.0%", "-", "0.3"),
        ("Exception\nfrontier", "7%", "60/60", "0.3%", "-", "0.6"),
        ("Desk note\nmid", "4%", "60/60", "0.4%", "-", "0.4"),
        ("Reply\nfrontier", "8%", "60/60", "0.5%", "-", "0.5"))
cols = (0.0, 1.35, 1.95, 2.65, 3.35, 3.95)
heads = ("Route", "Share", "Golden", "Residual", "Escal.", "Cents")
fig, ax = fl.figure(4.5, 4.4)
n = len(rows)
ax.set_xlim(0, 4.5)
ax.set_ylim(-0.7, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.04, n + 0.45, h, va="center", fontsize=9.5, fontweight="bold",
            color=fl.INK)
for i, r in enumerate(rows):
    y = n - 1 - i
    tok = "policy" if "cascade" in r[0] else "verified"
    ax.add_patch(Rectangle((0.0, y + 0.05), 4.5, 0.9, facecolor=fl.FILL[tok],
                           edgecolor=fl.C[tok], lw=0.6))
    for x, t in zip(cols, r):
        ax.text(x + 0.04, y + 0.5, t, va="center", fontsize=9, color=fl.INK)
ax.text(0.04, -0.35, "Total 2.9 cents a verified outcome; all flags exercised May 12",
        fontsize=9, style="italic", color=fl.INK)
fl.save(fig)
