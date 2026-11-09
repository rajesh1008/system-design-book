"""Figure 41.5  Who holds the eighteen decisions.

Reading order: one row per owner, top to bottom, in the order the
matrix lists them: the owner, the decisions held, and how many. Every
decision has exactly one owner and a named deputy except going live,
which the product owner holds. The two rule signers are amber. Signed
with DR-41.1 on August 24, 2026. From org.rights.owners.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from org import rights  # noqa: E402

short = {"rules.ops": "ops rules", "rules.refund": "refund rules",
         "rules.security": "security rules", "bundle.activate": "activate",
         "gate": "gate", "release": "release", "tool.register": "register",
         "tool.scopes": "scopes", "autonomy": "autonomy", "stop": "stop",
         "message": "message", "restore": "restore",
         "budget.loop": "loop day", "budget.envelope": "envelope",
         "usecase.accept": "accept", "usecase.tier": "tier",
         "usecase.threat": "threat", "usecase.live": "go live"}
names = {"on-call primary": "On-call primary",
         "loyalty product owner": "Product owner"}
rows = []
for who, keys in rights.owners().items():
    signs = any(d.signs and d.owners[0] == who for d in rights.SIGNED)
    rows.append((names.get(who, who), ", ".join(short[k] for k in keys),
                 str(len(keys)), "policy" if signs else "org"))
heads = ("Owner", "Holds", "")
cols = (0.0, 1.75, 4.55)
fig, ax = fl.figure(4.5, 3.4)
n = len(rows)
W = 4.85
ax.set_xlim(0, W)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=9.5,
            fontweight="bold", color=fl.INK)
for i, (*cells, tok) in enumerate(rows):
    y = n - 1 - i
    ax.add_patch(Rectangle((0.0, y + 0.06), W, 0.88,
                           facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                           lw=1.5 if tok == "policy" else 0.75))
    for x, s in zip(cols, cells):
        ax.text(x + 0.05, y + 0.5, s, va="center", fontsize=9,
                color=fl.INK, fontweight="bold" if x == cols[0] else None)
fl.save(fig)
