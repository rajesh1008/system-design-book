"""Figure 4.9  Automation rate with and without hand-offs.

Reading order: one bar per definition, top to bottom, on the same 48,000
pilot sessions from July to September 2024. Only the bottom bar meets
the definition the scoreboard uses. From baseline.autonomy.
"""
import figlib as fl

rows = [("Abandons counted too", 75, "fail"),
        ("Vendor dashboard", 54, "fail"),
        ("Bot said done", 15, "fail"),
        ("Executed and verified", 9, "verified")]
fig, ax = fl.figure(4.0, 3.4)
y = list(range(len(rows)))[::-1]
for j, (yi, (name, v, tok)) in enumerate(zip(y, rows)):
    ok = tok == "verified"
    ax.barh(yi, v, height=0.6, color=fl.C[tok] if ok else fl.FILL[tok],
            edgecolor=fl.C[tok], hatch="" if ok else "///")
    fl.label_line(ax, v, yi, f"{v}%")
ax.set_yticks(y)
ax.set_yticklabels([r[0] for r in rows])
ax.set_xlim(0, 100)
ax.set_xlabel("Share of pilot sessions (%)")
ax.grid(axis="x")
fl.save(fig)
