"""Figure 11.4  Egress allow-list by tool.

Reading order: one row per tool, one column per host. A filled square is
an allowed pair; every empty cell is a denial that the proxy writes to
the trail. Most tools reach one host. The agent loop reaches three, and
no tool reaches a host outside the eleven. Values from
04-code/designlab/isolation/egress.toml (version 2026-03-16).
"""
import tomllib
from pathlib import Path

import figlib as fl
from matplotlib.patches import Rectangle

toml = (Path(fl.HERE).parent / "04-code" / "designlab" / "isolation"
        / "egress.toml")
pol = tomllib.loads(toml.read_text())
hosts = [h["name"].split(".")[0] for h in pol["host"]]
tools = []
for h in pol["host"]:
    for t in h["tools"]:
        if t not in tools:
            tools.append(t)
allowed = {(t, h["name"].split(".")[0]) for h in pol["host"]
           for t in h["tools"]}

fig, ax = fl.figure(4.5, 3.6)
n, m = len(tools), len(hosts)
ax.set_xlim(-3.2, m)
ax.set_ylim(-0.2, n + 2.6)
ax.axis("off")
for j, h in enumerate(hosts):
    ax.text(j + 0.5, n + 0.2, h, rotation=60, ha="left", va="bottom",
            fontsize=9)
for i, t in enumerate(tools):
    y = n - 1 - i
    ax.text(-0.15, y + 0.5, t, ha="right", va="center", **fl.mono(t))
    for j, h in enumerate(hosts):
        on = (t, h) in allowed
        ax.add_patch(Rectangle((j + 0.1, y + 0.1), 0.8, 0.8,
                               facecolor=fl.C["policy"] if on else "white",
                               edgecolor=fl.C["policy"] if on
                               else fl.GREY_LIGHT, lw=0.6))
fl.save(fig)
