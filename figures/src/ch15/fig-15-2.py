"""Figure 15.2  Steps by risk and cost.

Reading order: top to bottom, steps grouped by kind (read, classify,
judge, write); bar length is the share of April's model steps and the
colour and mark give the risk class. Lakeshore, April 2026
(illustrative); 176,700 steps.
"""
import sys
from pathlib import Path

from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402

steps = (("Booking read", "read", 33, "low"), ("Fare-record read", "read", 11, "low"),
         ("Change intent", "classify", 18, "medium"), ("Refund reason", "classify", 9, "low"),
         ("Offer choice", "judge", 5, "low"), ("Refund eligibility", "judge", 5, "high"),
         ("Exception judgment", "judge", 7, "high"),
         ("Desk note", "write", 4, "low"), ("Customer reply", "write", 8, "medium"))
tok = {"low": "verified", "medium": "policy", "high": "fail"}
hatch = {"low": "", "medium": "///", "high": "xx"}
fig, ax = fl.figure(4.5, 3.6)
n = len(steps)
for i, (name, kind, share, risk) in enumerate(steps):
    y = n - 1 - i
    ax.barh(y, share, color=fl.FILL[tok[risk]], edgecolor=fl.C[tok[risk]],
            hatch=hatch[risk], lw=0.75, height=0.7)
    ax.text(share + 0.6, y, f"{share}%  {risk}", va="center", fontsize=10,
            color=fl.LABEL[tok[risk]])
ax.set_yticks(range(n))
ax.set_yticklabels([s[0] for s in reversed(steps)], fontsize=10)
for i, s in enumerate(steps):
    if i == 0 or steps[i - 1][1] != s[1]:
        ax.text(51, n - 1 - i, s[1], ha="right", va="center", fontsize=10,
                style="italic", color=fl.INK)
        if i:
            ax.axhline(n - 0.5 - i, color=fl.C["org"], lw=0.5, ls=":")
ax.set_xlim(0, 52)
ax.set_xlabel("Share of April's model steps (%)")
ax.tick_params(labelsize=10)
ax.xaxis.label.set_size(10)
fl.save(fig)
