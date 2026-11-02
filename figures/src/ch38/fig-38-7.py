"""Figure 38.7  The bill that tripled.

Reading order: one stacked bar per month, left to right: the servicing
agent, the evaluation harness, the two loops in ordinary running, the
weekend of July 25 and 26 hatched, and spend with no identity. From
economics.bill (Lakeshore figures are illustrative).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from economics import bill  # noqa: E402

months = ("June", "July", "August")
groups = (("Servicing agent", "model", ("agent:servicing",)),
          ("Evaluation", "knowledge", ("eval:harness",)),
          ("Loops, ordinary", "ops", ("loop:fare-watch",
                                      "agent:waiver-watch")),
          ("Storm, Jul 25-26", "fail", ("agent:waiver-watch (Jul 25-26)",)),
          ("No identity", "org", ("(no identity)",)))
fig, ax = fl.figure(4.5, 3.0)
for i, m in enumerate(months):
    lines = {l.identity: l.usd for l in bill.invoice(m)}
    base = 0.0
    for name, tok, ids in groups:
        v = sum(lines.get(k, 0.0) for k in ids) / 1000
        ax.bar(i, v, bottom=base, width=0.55, color=fl.FILL[tok],
               edgecolor=fl.C[tok], lw=0.9,
               hatch="///" if tok == "fail" else "",
               label=name if i == 1 else None)
        base += v
    ax.text(i, base + 0.3, f"${base:.1f}k", ha="center", fontsize=9,
            color=fl.INK)
ax.set_xticks(range(3))
ax.set_xticklabels(months)
ax.set_ylim(0, 21)
ax.set_ylabel("Invoice, thousands of dollars")
ax.legend(fontsize=9, frameon=False, loc="upper left")
fl.save(fig)
