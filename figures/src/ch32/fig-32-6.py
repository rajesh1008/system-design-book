"""Figure 32.6  Credential scope and lifetime.

Reading order: one row per credential, top to bottom; what it can
touch, how long it lives, and who can present it. The first row is
the June 16 account; the rest are what replaced it on June 22. From
identity.standing and identity.tokens. Lakeshore figures are
illustrative.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

rows = (("svc-agent-gw\n(June 16)", "Every customer,\n8 scopes", "Never expires", "fail"),
        ("Run token", "1 itinerary,\ngranted tools", "15 minutes", "verified"),
        ("Child token", "Subset of\nthe run's", "Within the run's", "verified"),
        ("Permission", "1 effect,\n1 argument digest", "15 min, used once", "verified"),
        ("Broker key", "1 system;\nbroker only", "Rotated in 30 days", "policy"))
cols = (0.0, 1.35, 2.95)
heads = ("Credential", "Reach", "Lifetime")
fig, ax = fl.figure(4.5, 3.0)
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
                           facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                           lw=1.5 if tok == "fail" else 0.75))
    for x, t in zip(cols, cells):
        ax.text(x + 0.05, y + 0.5, t, va="center", fontsize=9,
                color=fl.INK, fontweight="bold" if x == cols[0] else None)
fl.save(fig)
