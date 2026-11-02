"""Figure 7.7  Hotel, airline and card network: three consistency models.

Reading order: one block per supplier type, top to bottom. Each block
says what a yes means, where the truth becomes final, and how an
effect is undone.
"""
import figlib as fl

blocks = [
    ("Hotel", "confirmation number", "folio at checkout",
     "cancel, under fee rules"),
    ("Airline", "ticket number", "ticketing record",
     "void same day, then refund"),
    ("Card network", "authorization", "settlement file",
     "a new refund transaction"),
]
labels = ("A yes means", "Final in", "Undo by")
toks = ("ops", "evidence", "policy")
fig, ax = fl.figure(4.5, 4.4)
ax.set_xlim(0, 10)
ax.set_ylim(0, 13)
ax.axis("off")
y = 12.4
for name, *vals in blocks:
    ax.text(0.1, y, name, fontweight="bold", va="center")
    for lab, val, tok in zip(labels, vals, toks):
        y -= 0.9
        ax.text(0.6, y, lab, va="center", color=fl.LABEL["org"])
        ax.text(4.2, y, val, va="center", color=fl.LABEL[tok])
    y -= 0.55
    ax.plot([0, 10], [y, y], color=fl.GREY_LIGHT, lw=0.5,
            linestyle="-", marker="")
    y -= 0.55
fl.save(fig)
