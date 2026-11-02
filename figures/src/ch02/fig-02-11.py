"""Figure 2.11  The auditor's view of one refund, before and after.

Reading order: one row per field of the chain record, top to bottom.
Left column is REF-000043 on Thursday, December 4, 2025; right column is
the same refund under the chain record. Missing evidence is hatched.
Values from the corpus (seed=2026) and python3 -m chain.demo.
"""
import figlib as fl
from matplotlib.patches import Rectangle

rows = ["Proposal", "Permission", "Idempotency key", "Execution",
        "Verification", "Trail entry"]
before = ["One refund", "None", "None", "Two credits", "Status 200",
          "None"]
after = ["One refund", "PRM-20931", "One key", "One credit",
         "Settlement file", "Hash linked"]
bad = {1, 2, 3, 4, 5}

fig, ax = fl.figure(4.5, 3.4)
ax.set_xlim(0, 3)
ax.set_ylim(0, len(rows) + 1)
ax.axis("off")
ax.text(1.5, 6.45, "Pilot", ha="center", va="center", fontsize=10)
ax.text(2.5, 6.45, "Chain", ha="center", va="center", fontsize=10)
for i, name in enumerate(rows):
    y = len(rows) - 1 - i
    ax.text(0.02, y + 0.5, name, ha="left", va="center", fontsize=10)
    miss = i in bad
    ax.add_patch(Rectangle((1.04, y + 0.08), 0.92, 0.84,
                           facecolor=fl.FILL["fail"] if miss else "white",
                           edgecolor=fl.C["fail"] if miss else fl.GREY_DARK,
                           hatch="///" if miss else "", lw=0.75))
    ax.text(1.5, y + 0.5, before[i], ha="center", va="center",
            fontsize=9.5, backgroundcolor="white",
            color=fl.LABEL["fail"] if miss else fl.INK)
    ax.add_patch(Rectangle((2.04, y + 0.08), 0.92, 0.84,
                           facecolor=fl.FILL["verified"],
                           edgecolor=fl.C["verified"], lw=0.75))
    ax.text(2.5, y + 0.5, after[i], ha="center", va="center",
            fontsize=9.5, color=fl.LABEL["verified"])
fl.save(fig)
