"""Figure 8.10  The messaging scorecard: brokers, streams, workflow
engines, and actor runtimes.

Reading order: one row per product family, top to bottom; columns are
order per key, redelivery, a backpressure signal, and an exactly-once
effect. A filled square means the product gives it, a hatched square
means with configuration, an open square means it does not. The last
column is open in every row. Verified against official documentation
on November 2, 2026; see the chapter's table for the source of each.
"""
import figlib as fl
from matplotlib.patches import Rectangle

cols = ["Order\nby key", "Re-\ndelivers", "Back-\npressure", "Effect\nonce"]
F, H, O = "full", "half", "open"
rows = [("Kafka", (F, F, F, O)),
        ("RabbitMQ", (H, F, F, O)),
        ("NATS JetStream", (H, F, F, O)),
        ("Amazon SQS FIFO", (F, F, H, O)),
        ("Google Pub/Sub", (F, F, H, O)),
        ("Akka, Pekko", (H, O, H, O)),
        ("Orleans", (F, O, H, O)),
        ("Ray actors", (F, O, H, O)),
        ("Dapr actors", (F, H, H, O))]

fig, ax = fl.figure(4.5, 4.4)
n = len(rows)
ax.set_xlim(0, 5.4)
ax.set_ylim(-0.2, n + 1.1)
ax.axis("off")
for j, c in enumerate(cols):
    ax.text(2.35 + j * 0.8, n + 0.5, c, ha="center", va="center",
            fontsize=9, fontweight="bold")
for i, (name, marks) in enumerate(rows):
    y = n - 1 - i
    ax.text(0.02, y + 0.5, name, ha="left", va="center", fontsize=9.5)
    for j, m in enumerate(marks):
        x = 2.35 + j * 0.8 - 0.22
        tok = "verified" if m != O else "ops"
        ax.add_patch(Rectangle(
            (x, y + 0.28), 0.44, 0.44,
            facecolor=fl.C[tok] if m == F else "white",
            edgecolor=fl.C[tok], lw=1.0,
            hatch="////" if m == H else ""))
fl.save(fig)
