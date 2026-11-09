"""Figure 16.7  Rejection reasons by type.

Reading order: top to bottom, most common first. Each bar counts first
proposals the world check rejected from May 18 to 31, 2026, by reason
code. Wrong-identifier reasons are solid; the rest are hatched
(Lakeshore figures are illustrative).
"""
import figlib as fl

data = [("Ticket not on itinerary", 226, True),
        ("Fare differs from quote", 178, False),
        ("Amount above fare left", 137, False),
        ("Passenger not on ticket", 113, True),
        ("Flight not on route", 73, False),
        ("Ticket unknown", 41, True),
        ("Flight canceled", 39, False)]

fig, ax = fl.figure(4.2, 3.4)
names = [d[0] for d in data][::-1]
vals = [d[1] for d in data][::-1]
ident = [d[2] for d in data][::-1]
bars = ax.barh(names, vals, height=0.6,
               color=[fl.FILL["fail"] if i else fl.FILL["ops"]
                      for i in ident],
               edgecolor=[fl.C["fail"] if i else fl.C["ops"]
                          for i in ident], linewidth=1.0)
for b, i in zip(bars, ident):
    if not i:
        b.set_hatch("///")
for b, v in zip(bars, vals):
    ax.text(v + 4, b.get_y() + b.get_height() / 2, str(v), va="center",
            fontsize=9.5, color=fl.INK)
ax.set_xlabel("Rejected first proposals")
ax.set_xlim(0, 260)
ax.spines[["top", "right"]].set_visible(False)
fl.save(fig)
