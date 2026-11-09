"""Figure 20.9  Refusals by reason.

Reading order: top to bottom. The 1,436 metric queries in the replay of
May 21 to 31, 2026 (designlab, seed 20): 1,296 answered and 140
refused, each with one reason. Cost refusals are 42, or 3 percent, all
on the two event metrics; no query ran without an estimate.
"""
import figlib as fl

rows = [("Entitlement", 55, "policy"),
        ("Cost (over $1)", 42, "fail"),
        ("Window too long", 32, "policy"),
        ("Not in the layer", 11, "knowledge"),
        ("No estimate", 0, "fail")]

fig, ax = fl.figure(4.5, 3.3)
y = list(range(len(rows)))[::-1]
for yi, (name, n, tok) in zip(y, rows):
    ax.barh(yi, n, height=0.6, color=fl.FILL[tok], edgecolor=fl.C[tok],
            lw=1.6 if tok == "fail" and n else 1.0,
            hatch="///" if tok == "fail" else "")
    ax.text(n + 1, yi, f"{n}", va="center", fontsize=9.5, color=fl.INK)
ax.set_yticks(y, [r[0] for r in rows])
ax.set_xlabel("Refused queries, of 1,436")
ax.set_xlim(0, 65)
ax.spines[["top", "right"]].set_visible(False)
fl.save(fig)
