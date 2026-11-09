"""Figure 13.9  Drift detected by the contract tests.

Reading order: left to right by run. Golden cases passing out of 16 for
refund-reason in the April 2026 nightly runs (Lakeshore figures are
illustrative): 16 every night until April 8, when the alias had moved
and 0 passed; the pin went back that morning and April 9 is 16 again.
Seed 2026, no randomness.
"""
import figlib as fl

days = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
passed = [16, 16, 16, 16, 16, 16, 16, 0, 16, 16]
fig, ax = fl.figure(4.5, 3.4)
ax.plot(days, passed, color=fl.C["model"], marker=fl.MARKERS[0],
        lw=fl.STROKE["data"], ls=fl.LINESTYLES[0])
ax.plot([8], [0], marker=fl.MARKERS[6], ms=10, color=fl.C["fail"],
        ls="none")
ax.plot([9], [16], marker=fl.MARKERS[1], ms=8, color=fl.C["verified"],
        ls="none")
fl.note(ax, (8, 0.6), (3.2, 5.0), "April 8, 02:00: alias moved,\n"
        "codes title-cased, new key")
fl.label_line(ax, 9, 16, "pinned to the dated ID", dy=-12,
              color=fl.LABEL["verified"])
ax.set_xticks(days)
ax.set_xticklabels([str(d) for d in days])
ax.set_xlabel("April 2026, nightly run")
ax.set_ylabel("Golden cases passing")
ax.set_ylim(-1, 18)
ax.set_yticks([0, 4, 8, 12, 16])
ax.set_xlim(0.5, 10.8)
fl.save(fig)
