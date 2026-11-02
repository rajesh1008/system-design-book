"""Figure 0.4  Duplicate effects per 10,000 actions as retries grow, with and without idempotency keys."""
import figlib as fl

retries = [0, 1, 2, 3, 4, 5]
naive = [0, 38, 71, 102, 130, 155]
keyed = [0, 0.4, 0.7, 0.9, 1.1, 1.2]

fig, ax = fl.figure(4.5, 3.4)
ax.plot(retries, naive, color=fl.C["fail"], linestyle="--", marker="s", lw=fl.STROKE["control"])
ax.plot(retries, keyed, color=fl.C["verified"], linestyle="-", marker="o", lw=fl.STROKE["control"])
fl.label_line(ax, retries[-1], naive[-1], "No key", color=fl.LABEL["fail"])
fl.label_line(ax, retries[-1], keyed[-1] + 6, "Idempotency key", color=fl.LABEL["verified"])
ax.set_xlabel("Retries per action")
ax.set_ylabel("Duplicate effects per 10,000")
ax.set_xlim(0, 6.6)
ax.set_ylim(0, 175)
ax.grid(axis="y")
fl.save(fig)
