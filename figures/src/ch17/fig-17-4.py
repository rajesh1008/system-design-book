"""Figure 17.4  Small against frontier, by change type.

Reading order: top to bottom, one row per change type, on the 1,200
golden cases from May 2026 (100 a type). Open circles are the student
alone, filled squares the student with escalation, and diamonds the
frontier teacher. The student alone falls behind on the types where
new words arrived; escalation closes the gap (designlab, seed 17).
"""
import figlib as fl

rows = [("Voluntary rebook", 89, 100, 98),
        ("Ancillary refund", 90, 100, 100),
        ("Cancel for credit", 91, 99, 100),
        ("Upgrade", 92, 100, 99),
        ("Involuntary refund", 93, 100, 100),
        ("Hotel cancel", 96, 100, 99),
        ("Cancel with refund", 98, 100, 99),
        ("Accept schedule", 100, 100, 100),
        ("Car", 100, 100, 98),
        ("Hotel date change", 100, 100, 99),
        ("Involuntary rebook", 100, 100, 100),
        ("Name correction", 100, 100, 99)]

fig, ax = fl.figure(4.5, 4.2)
ys = list(range(len(rows)))[::-1]
for y, (name, s, c, f) in zip(ys, rows):
    ax.plot([s, max(c, f)], [y, y], color=fl.C["knowledge"], lw=0.6)
    ax.plot(s, y, "o", mfc="white", mec=fl.C["fail"], ms=6)
    ax.plot(c, y, "s", color=fl.C["verified"], ms=5)
    ax.plot(f, y, "D", mfc="white", mec=fl.C["model"], ms=5)
ax.set_yticks(ys)
ax.set_yticklabels([r[0] for r in rows], fontsize=9)
ax.set_xlim(86, 101)
ax.set_xlabel("Accuracy on May golden cases (%)")
ax.plot([], [], "o", mfc="white", mec=fl.C["fail"], label="Student alone")
ax.plot([], [], "s", color=fl.C["verified"], label="Student + escalate")
ax.plot([], [], "D", mfc="white", mec=fl.C["model"], label="Frontier")
ax.legend(loc="lower left", fontsize=9, frameon=False)
ax.spines[["top", "right"]].set_visible(False)
fl.save(fig)
