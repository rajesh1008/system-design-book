"""Figure 44.2  The ramp by task type.

Reading order: one stacked bar per month, December 2025 to September
2026 (January and February held at December's shares and are left
out). Each segment is a task type's contribution to the agent's share
of all changes: its weight times the share of that type the agent
handles alone. The total is printed above each bar. Refunds stay
assisted, so they never appear. From golive.ramp (Lakeshore figures
are illustrative).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402

from golive.ramp import MONTHS, SHARES, TYPES, agent_share  # noqa: E402

kinds = ("R1", "V1", "C1", "R2", "U1")
toks = ("ops", "verified", "knowledge", "policy", "org")
names = {"R1": "R1", "V1": "V1", "C1": "C1", "R2": "R2", "U1": "U1"}
fig, ax = fl.figure(4.5, 3.4)
xs = range(len(MONTHS))
base = [0.0] * len(MONTHS)
for k, tok, h in zip(kinds, toks, fl.HATCH[:5]):
    vals = [TYPES[k][1] * SHARES[m].get(k, 0) * 100 for m in MONTHS]
    ax.bar(xs, vals, bottom=base, color=fl.FILL[tok],
           edgecolor=fl.C[tok], hatch=h, lw=0.75, label=names[k],
           width=0.7)
    base = [b + v for b, v in zip(base, vals)]
for x, m in zip(xs, MONTHS):
    ax.text(x, agent_share(m) * 100 + 0.8, f"{agent_share(m):.0%}"
            if agent_share(m) >= 0.1 else f"{agent_share(m):.1%}",
            ha="center", fontsize=9, color=fl.INK)
ax.set_xticks(list(xs))
ax.set_xticklabels([m.split()[0][0] for m in MONTHS], fontsize=9)
ax.set_xlabel("Dec 2025 to Sep 2026", fontsize=9)
ax.set_ylabel("Agent share of all changes (%)")
ax.set_ylim(0, 52)
ax.legend(fontsize=9, loc="upper left", frameon=False)
fl.save(fig)
