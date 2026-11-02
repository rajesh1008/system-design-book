"""Figure 17.9  When not to adapt.

Reading order: top to bottom. Each row is a sign that a request to
adapt a model is the wrong fix, on the left, and what to do instead,
on the right. The last row is the one case where adaptation is the
right next step.
"""
import figlib as fl
from matplotlib.patches import Rectangle

rows = [("No failure measured", "Measure", "fail"),
        ("The fix is a rule", "Change the policy", "policy"),
        ("Facts change monthly", "Use context", "knowledge"),
        ("A tool can do it", "Fix the tool", "ops"),
        ("No golden set", "Refuse", "fail"),
        ("Too few labels", "Collect", "evidence"),
        ("Narrow, measured", "Adapt, gated",
         "verified")]

fig, ax = fl.figure(4.5, 3.2)
ax.set_xlim(0, 6.4)
ax.set_ylim(0, len(rows) + 1)
ax.axis("off")
for x, h in ((0.05, "Sign"), (3.65, "Do instead")):
    ax.text(x, len(rows) + 0.45, h, ha="left", va="center", fontsize=9.5,
            fontweight="bold")
for i, (sign, do, tok) in enumerate(rows):
    y = len(rows) - 1 - i
    last = tok == "verified"
    ax.add_patch(Rectangle((3.55, y + 0.12), 2.8, 0.76,
                           facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                           lw=1.6 if last else 0.6))
    ax.text(0.05, y + 0.5, sign, ha="left", va="center", fontsize=9,
            fontweight="bold" if last else "normal")
    ax.text(3.65, y + 0.5, do, ha="left", va="center", fontsize=9,
            color=fl.LABEL[tok], fontweight="bold")
fl.save(fig)
