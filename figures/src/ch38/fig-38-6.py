"""Figure 38.6  Chargeback by use case, July, by identity.

Reading order: one row per use case, top to bottom: the four kinds of
change the servicing agent makes, the two loops, the evaluation
harness, and spend with no identity; the owner who receives the line,
its ordinary model spend, and its incident spend. The storm is a line
on the waiver watch's owner, highlighted. From economics.chargeback
(Lakeshore figures are illustrative).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from economics import bill, chargeback  # noqa: E402

inv = {ln.identity: ln.usd for ln in bill.invoice("July")}
uc = chargeback.by_use_case("July")
rows = [(k.capitalize(), "Customer ops", f"{v:,.0f}", "0", "org")
        for k, v in uc.items()]
rows += [("Waiver watch", "Platform eng.",
          f"{inv['agent:waiver-watch']:,.0f}",
          f"{inv['agent:waiver-watch (Jul 25-26)']:,.0f}", "fail"),
         ("Fare watch", "Platform eng.",
          f"{inv['loop:fare-watch']:,.0f}", "0", "ops"),
         ("Evaluation", "Research", f"{inv['eval:harness']:,.0f}", "0",
          "knowledge"),
         ("No identity", "Unallocated",
          f"{inv['(no identity)']:,.0f}", "0", "ops")]
heads = ("Use case", "Owner", "Model $", "Incident $")
cols = (0.0, 1.5, 3.0, 3.95)
fig, ax = fl.figure(4.5, 3.4)
n = len(rows)
ax.set_xlim(0, 5.1)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=9.5,
            fontweight="bold", color=fl.INK)
for i, (*cells, tok) in enumerate(rows):
    y = n - 1 - i
    ax.add_patch(Rectangle((0.0, y + 0.06), 5.1, 0.88,
                           facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                           lw=1.5 if tok == "fail" else 0.75))
    for x, s in zip(cols, cells):
        ax.text(x + 0.05, y + 0.5, s, va="center", fontsize=9,
                color=fl.INK, fontweight="bold" if x == cols[0] else None)
fl.save(fig)
