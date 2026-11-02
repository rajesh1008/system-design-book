"""Figure 4.7  Existing controls and their owners.

Reading order: one row per control that existed on October 14, 2025,
with its owner and whether it leaves a record. Solid boxes leave one;
dashed boxes do not. From the controls inventory in section 5.
"""
import figlib as fl
from matplotlib.patches import Rectangle

rows = [("Refund limit by role", "Rachel", True),
        ("Fare-rule waivers", "Marcus", False),
        ("Named accounts", "Owen", False),
        ("Settlement match", "Rachel", True),
        ("Dispute response", "Rachel", True),
        ("Refund clock", "Rachel", True),
        ("Queue alarm", "Marcus", True),
        ("Change freeze", "Ben", False)]
fig, ax = fl.figure(4.5, 3.8)
n = len(rows)
ax.set_xlim(0, 10)
ax.set_ylim(0, n + 1)
ax.axis("off")
ax.text(0.1, n + 0.5, "Control", va="center", fontweight="bold")
ax.text(5.6, n + 0.5, "Owner", va="center", fontweight="bold")
ax.text(8.5, n + 0.5, "Record", va="center", ha="center",
        fontweight="bold")
for i, (c, o, rec) in enumerate(rows):
    y = n - i - 0.5
    ax.text(0.1, y, c, va="center")
    ax.text(5.6, y, o, va="center", color=fl.LABEL["org"])
    tok = "evidence" if rec else "policy"
    ax.add_patch(Rectangle((7.4, y - 0.34), 2.2, 0.68,
                           facecolor=fl.FILL[tok] if rec else "white",
                           edgecolor=fl.C[tok], lw=fl.STROKE["data"],
                           linestyle="-" if rec else "--"))
    ax.text(8.5, y, "Yes" if rec else "No", va="center", ha="center",
            color=fl.TEXT_ON[tok] if rec else fl.LABEL[tok])
fl.save(fig)
