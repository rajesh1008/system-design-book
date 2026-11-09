"""Figure 47.2  The seven formats.

Reading order: one row per round in Lakeshore's loop, in loop order,
from the phone screen to the hiring manager, with its minutes and its
evidence. Teal rows are publicly evidenced formats; white rows are
this book's recommendation (Book). The phone screen and the hiring
manager are the two tags outside the seven formats. From bank/data/loop.toml.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from _table import table  # noqa: E402

from bank.loop import config  # noqa: E402

NAME = {"phone-screen": "Phone screen", "system-design": "Whiteboard",
        "distributed-systems": "Distributed", "agent-runtime": "Harness",
        "control-plane-security": "Control", "evaluation-operations":
        "Eval and ops", "take-home": "Take-home",
        "bar-raiser": "Bar-raiser", "hiring-manager": "Hiring manager"}
rows, toks = [], []
for tag, r in config()["rounds"].items():
    ev = "Public" if r.evidence == "public" else "Book"
    rows.append((NAME[tag], str(r.minutes), ev))
    toks.append("ops" if r.evidence == "public" else "org")
fig, ax = table(rows, ("Round", "Minutes", "Evidence"),
                (0.0, 2.55, 3.55), width=5.0, toks=toks, h=3.6)
fl.save(fig)
