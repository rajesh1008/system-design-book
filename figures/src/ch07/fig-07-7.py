"""Figure 7.7  Hotel, airline and card network: three consistency models.

Reading order: one row per supplier type, top to bottom; columns say
what a yes means, when the truth is final, and how an effect is undone.
"""
import figlib as fl

rows = [
    ("Hotel", "confirmation number", "folio at checkout",
     "cancel, fee rules"),
    ("Airline", "ticket number", "ticketing record", "void same day"),
    ("Card network", "authorization", "settlement file", "new refund"),
]
heads = ("", "A yes means", "Final in", "Undo by")
xs = (0.1, 2.4, 5.0, 7.5)
fig, ax = fl.figure(4.5, 2.2)
ax.set_xlim(0, 10)
ax.set_ylim(0, len(rows) + 1)
ax.axis("off")
for x, h in zip(xs, heads):
    ax.text(x, len(rows) + 0.5, h, fontweight="bold", va="center")
for i, row in enumerate(rows):
    y = len(rows) - i - 0.5
    for j, (x, text) in enumerate(zip(xs, row)):
        tok = ("org", "ops", "evidence", "policy")[j]
        ax.text(x, y, text, va="center", color=fl.LABEL[tok],
                fontweight="bold" if j == 0 else "normal")
    ax.plot([0, 10], [y - 0.5, y - 0.5], color=fl.GREY_LIGHT, lw=0.5,
            linestyle="-", marker="")
fl.save(fig)
