"""Figure 29.3  Escape paths and the control for each.

Reading order: one row per probe class, top to bottom; the path a run
tries and the sandbox layer that stops it. From sandbox.battery.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

rows = (("Filesystem", "Host files,\nsymlinks", "Own directory only"),
        ("Network", "Replica,\nmetadata, DNS", "Proxy, listed hosts"),
        ("Secrets", "Env, keys,\ntranscripts", "Nothing injected"),
        ("Limits", "Spin, memory,\nfork", "cpu, memory, wall"),
        ("Persistence", "Files left for\nthe next run", "Fresh per run"))
cols = (0.0, 1.35, 3.05)
heads = ("Class", "Escape path", "Control")
fig, ax = fl.figure(4.5, 3.0)
n = len(rows)
ax.set_xlim(0, 4.6)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=10,
            fontweight="bold", color=fl.INK)
for i, row in enumerate(rows):
    y = n - 1 - i
    tok = "policy" if i % 2 == 0 else "ops"
    ax.add_patch(Rectangle((0.0, y + 0.06), 4.6, 0.88,
                           facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                           lw=0.75))
    for x, t in zip(cols, row):
        ax.text(x + 0.05, y + 0.5, t, va="center", fontsize=9,
                color=fl.INK, fontweight="bold" if x == cols[0] else None)
fl.save(fig)
