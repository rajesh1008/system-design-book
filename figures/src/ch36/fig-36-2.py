"""Figure 36.2  The regulatory frame by obligation.

Reading order: one row per obligation that reaches a refund the agent
proposes, top to bottom; where it comes from and which pack questions
answer it. Read November 2, 2026; counsel, not this table, decides
what applies. Rows marked "not yet" do not reach Lakeshore's refunds.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

rows = (("Refund promptly, to the\noriginal form of payment", "US DOT, 14 CFR 260", "P1, P5, P6", "policy"),
        ("Card numbers unreadable\nwherever stored", "PCI DSS", "Tokens only", "policy"),
        ("Tell people they are\ntalking to an AI system", "EU AI Act Art. 50,\nfrom Aug 2, 2026", "P10", "policy"),
        ("A person can contest an\nautomated decision", "GDPR Art. 22", "P4, P7", "policy"),
        ("Controls over reported\nrevenue and refunds", "External auditor", "P1, P6, P8", "policy"),
        ("Logs and oversight for\nhigh-risk systems", "EU AI Act Arts. 12, 14;\nAnnex III, Dec 2, 2027", "Not yet", "org"))
cols = (0.0, 2.2, 3.85)
heads = ("Obligation", "Source", "Pack answers")
fig, ax = fl.figure(5.0, 3.6)
n = len(rows)
ax.set_xlim(0, 5.0)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=10,
            fontweight="bold", color=fl.INK)
for i, (*cells, tok) in enumerate(rows):
    y = n - 1 - i
    ax.add_patch(Rectangle((0.0, y + 0.06), 5.0, 0.88, facecolor="white",
                           edgecolor=fl.GREY_LIGHT, lw=0.75))
    ax.add_patch(Rectangle((0.0, y + 0.06), cols[1] - 0.05, 0.88,
                           facecolor=fl.FILL[tok] if tok == "policy" else "white",
                           edgecolor=fl.C[tok], lw=0.75,
                           ls="-" if tok == "policy" else "--"))
    for x, t in zip(cols, cells):
        ax.text(x + 0.05, y + 0.5, t, va="center", fontsize=9, color=fl.INK,
                fontweight="bold" if x == cols[0] else None)
fl.save(fig)
