"""Figure 7.10  Replay of 10,000 runs at a 5 percent timeout rate.

Reading order: one bar per way an unknown outcome left the unknown
state, largest first. Totals 539 unknowns from 10,000 keyed runs (seed
2026, effects.demo replay). The last two bars are the ones a key
cannot help with.
"""
import figlib as fl

bars = [("Retry with same key", 248, "verified"),
        ("Lookup found it", 103, "knowledge"),
        ("Lookup: never landed", 69, "knowledge"),
        ("Escalated to a person", 67, "fail"),
        ("Message not resent", 52, "org")]
fig, ax = fl.figure(4.5, 2.8)
ys = list(range(len(bars)))[::-1]
for y, (label, n, tok) in zip(ys, bars):
    ax.barh(y, n, color=fl.FILL[tok], edgecolor=fl.C[tok],
            lw=fl.STROKE["data"], hatch="///" if tok == "fail" else "")
    ax.text(n + 6, y, str(n), va="center", color=fl.LABEL[tok],
            fontweight="bold")
ax.set_yticks(ys)
ax.set_yticklabels([b[0] for b in bars])
ax.set_xlim(0, 300)
ax.set_xlabel("Unknown outcomes")
fl.save(fig)
