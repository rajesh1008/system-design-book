"""Figure 35.7  Alerts that mean something.

Reading order: one row per rule, top to bottom; who it pages and what
they do. The last three rows are the pilot's alerts, kept as
dashboards because each fired on an ordinary day. From tracing.alerts.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

rows = (("Trace incomplete", "Ben Carter", "Freeze the release", "policy"),
        ("Effect not verified", "Marcus Bell", "Desk rechecks each refund", "policy"),
        ("Reads refused > 5%", "Daniel Price", "Tier one: tool off", "policy"),
        ("Cost/decision p95\n> $0.12", "Daniel Price", "Diff cache and prompt\nby version", "policy"),
        ("Hand-offs > 8%", "Marcus Bell", "Staff the desk;\nread the stops", "policy"),
        ("Call latency p95", "Dashboard", "Fires every day", "fail"),
        ("Any tool error", "Dashboard", "Fires every day", "fail"),
        ("Tokens per call", "Dashboard", "Fires every day", "fail"))
cols = (0.0, 1.55, 2.7)
heads = ("Rule", "Pages", "Action")
fig, ax = fl.figure(4.5, 3.8)
n = len(rows)
ax.set_xlim(0, 4.6)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=10,
            fontweight="bold", color=fl.INK)
for i, (*cells, tok) in enumerate(rows):
    y = n - 1 - i
    ax.add_patch(Rectangle((0.0, y + 0.06), 4.6, 0.88,
                           facecolor=fl.FILL[tok] if tok == "fail" else "white",
                           edgecolor=fl.C[tok] if tok == "fail" else fl.GREY_LIGHT,
                           lw=0.75))
    for x, t in zip(cols, cells):
        ax.text(x + 0.05, y + 0.5, t, va="center", fontsize=9,
                color=fl.INK, fontweight="bold" if x == cols[0] else None)
fl.save(fig)
