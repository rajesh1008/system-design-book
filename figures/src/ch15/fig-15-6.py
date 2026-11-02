"""Figure 15.6  Small-model pass rate by step.

Reading order: top to bottom, one bar per Decision Table row; the gate
line is at full marks. Change intent shows the small model alone and,
as a mark, the cascade. Two high-risk steps are barred by their floor
whatever they score. Lakeshore bake-off, May 5 to 8, 2026 (illustrative).
"""
import sys
from pathlib import Path

from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402

rows = (("Booking read", 100, "pass"), ("Fare-record read", 90, "fail"),
        ("Change intent", 95.2, "cascade"), ("Refund reason", 100, "pass"),
        ("Offer choice", 100, "pass"), ("Refund eligibility", 98, "barred"),
        ("Exception judgment", 82, "barred"), ("Desk note", 93, "fail"),
        ("Customer reply", 85, "fail"))
tok = {"pass": "verified", "fail": "fail", "cascade": "policy", "barred": "org"}
hatch = {"pass": "", "fail": "///", "cascade": "", "barred": "xx"}
fig, ax = fl.figure(4.5, 3.6)
n = len(rows)
for i, (name, v, st) in enumerate(rows):
    y = n - 1 - i
    ax.barh(y, v, color=fl.FILL[tok[st]], edgecolor=fl.C[tok[st]],
            hatch=hatch[st], lw=0.75, height=0.7)
    lab = {"pass": "pass", "fail": "fail", "cascade": "alone; cascade 98.9%",
           "barred": "barred"}[st]
    ax.text(101.5, y, f"{v:g}%  {lab}", va="center", fontsize=10, color=fl.INK)
ax.plot([98.9], [n - 3], marker=fl.MARKERS[3], ms=8, color=fl.C["verified"], ls="none")
ax.axvline(100, color=fl.INK, lw=1.2, ls="--")
ax.set_yticks(range(n))
ax.set_yticklabels([r[0] for r in reversed(rows)], fontsize=10)
ax.set_xlim(60, 128)
ax.set_xlabel("Golden cases passed by the best small candidate (%)")
ax.tick_params(labelsize=10)
ax.xaxis.label.set_size(10)
fl.save(fig)
