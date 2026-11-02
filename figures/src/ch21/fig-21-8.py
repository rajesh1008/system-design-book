"""Figure 21.8  Instruction-file drift over releases.

Reading order: left to right by release, v1 (December 1, 2025) to v9
(May 27, 2026). Bars are the file's size in tokens; the line is lint
findings (stale, contradictory, or without an owner). Both climb for six
months, jump at v8, and fall at v9 after the cleanup. The dotted line is
the 1,200-token cap set on May 4.
"""
import figlib as fl

v = ["v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9"]
tok = [640, 690, 760, 820, 910, 1010, 1100, 1460, 1180]
find = [9, 11, 13, 17, 19, 23, 27, 34, 0]

fig, ax = fl.figure(4.0, 3.4)
ax.bar(v, tok, width=0.6, color=fl.FILL["model"], edgecolor=fl.C["model"])
ax.axhline(1200, color=fl.C["ops"], ls=":", lw=1.3)
ax.text(-0.4, 1230, "cap 1,200", fontsize=9, color=fl.LABEL["ops"])
ax.set_ylabel("Tokens (bars)")
ax.set_ylim(0, 1700)
ax2 = ax.twinx()
ax2.plot(v, find, color=fl.C["ops"], marker="D", lw=1.4)
ax2.set_ylabel("Lint findings (line)")
ax2.set_ylim(0, 40)
ax.spines[["top"]].set_visible(False)
ax2.spines[["top"]].set_visible(False)
fl.save(fig)
