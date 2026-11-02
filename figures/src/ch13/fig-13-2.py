"""Figure 13.2  What a model promises and what it cannot.

Reading order: left column first (what the provider states in writing
and the response carries), then the right column (what no provider
states, so the contract must check it). Seed 2026, no data.
"""
import figlib as fl

left = ["Model ID echoed", "Snapshot IDs fixed",
        "60 days' notice", "Token usage", "Stop reason"]
right = ["Same output twice", "Same format later",
         "Correct amounts", "No refusals", "A latency bound"]
fig, ax = fl.figure(4.5, 3.4)
ax.set_xlim(0, 10)
ax.set_ylim(0, 6.6)
ax.axis("off")
ax.text(0.2, 6.2, "Stated by provider", fontweight="bold",
        color=fl.LABEL["verified"])
ax.text(5.2, 6.2, "Left to contract", fontweight="bold",
        color=fl.LABEL["fail"])
for i, (a, b) in enumerate(zip(left, right)):
    y = 5.2 - i * 1.05
    ax.plot(0.35, y, marker="o", color=fl.C["verified"], ms=6)
    ax.text(0.7, y, a, va="center", color=fl.LABEL["model"])
    ax.plot(5.35, y, marker="X", color=fl.C["fail"], ms=7)
    ax.text(5.7, y, b, va="center", color=fl.LABEL["model"])
ax.plot([5.0, 5.0], [0.4, 6.4], color=fl.C["model"], lw=fl.STROKE["data"])
fl.save(fig)
