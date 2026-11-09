"""Figure 36.5  Why the golden set missed it.

Reading order: one row per place a refund destination can come from,
top to bottom; whether the agent should trust it; how many tasks in
the June and July golden sets put such a card in front of the agent.
refund_other_card was forbidden on every task, and no June task
offered a card from untrusted text. From assurance.gaps.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from assurance import gaps  # noqa: E402
from evals import golden as G  # noqa: E402

june = gaps.table(G.build())
july = gaps.table(gaps.july())
short = ("Card that paid", "Another profile card",
         "Newer card, expired\noriginal", "Card named in chat",
         "In a tool result\nor document")
rows = [(s, t, f"{a}", f"{b}") for s, (_, t, a), (_, _, b)
        in zip(short, june, july)]
cols = (0.0, 1.75, 2.85, 3.85)
heads = ("Came from", "Trust", "June", "July")
fig, ax = fl.figure(4.6, 3.3)
n = len(rows)
ax.set_xlim(0, 4.6)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=10,
            fontweight="bold", color=fl.INK)
for i, (*cells,) in enumerate(rows):
    y = n - 1 - i
    gap = cells[1] == "untrusted"
    ax.add_patch(Rectangle((0.0, y + 0.06), 4.6, 0.88,
                           facecolor=fl.FILL["fail"] if gap else "white",
                           edgecolor=fl.C["fail"] if gap else fl.GREY_LIGHT,
                           lw=0.75))
    ax.add_patch(Rectangle((cols[3], y + 0.06), 0.75, 0.88,
                           facecolor=fl.FILL["verified"],
                           edgecolor=fl.C["verified"], lw=0.75))
    for x, t in zip(cols, cells):
        ax.text(x + 0.05, y + 0.5, t, va="center", fontsize=9,
                color=fl.INK, fontweight="bold" if x == cols[0] else None)
fl.save(fig)
