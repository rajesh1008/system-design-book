"""Figure 16.4  Checks on one rebooking call.

Reading order: top to bottom, in the order the gateway runs them. The
call is the one from May 7, 2026, replayed through the May 18 intake.
The first three rows pass; the ticket check fails, so the later checks
never run and the policy rule is never asked (Lakeshore figures are
illustrative).
"""
import figlib as fl
from matplotlib.patches import Rectangle

rows = [("Shape matches schema", "pass", "verified"),
        ("Itinerary is this session's", "pass", "verified"),
        ("Ticket exists", "pass", "verified"),
        ("Ticket is on the itinerary", "fail", "fail"),
        ("Passenger on the ticket", "not run", "knowledge"),
        ("Fare equals the quote", "not run", "knowledge"),
        ("Policy rule", "not asked", "policy")]

fig, ax = fl.figure(4.5, 3.2)
ax.set_xlim(0, 6.4)
ax.set_ylim(0, len(rows) + 1)
ax.axis("off")
for x, h in ((0.05, "Check"), (4.25, "Result")):
    ax.text(x, len(rows) + 0.45, h, ha="left", va="center", fontsize=9.5,
            fontweight="bold")
for i, (name, val, tok) in enumerate(rows):
    y = len(rows) - 1 - i
    strong = tok == "fail"
    ax.add_patch(Rectangle((4.15, y + 0.12), 2.1, 0.76,
                           facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                           lw=1.6 if strong else 0.6,
                           ls="--" if tok == "knowledge" else "-"))
    ax.text(0.05, y + 0.5, name, ha="left", va="center", fontsize=9.5,
            fontweight="bold" if strong else "normal")
    ax.text(4.25, y + 0.5, val, ha="left", va="center", fontsize=9.5,
            color=fl.LABEL[tok], fontweight="bold")
fl.save(fig)
