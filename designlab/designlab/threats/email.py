"""Chapter 36: the supplier email case, and the battery that missed it.

The payments server that R-0609 brought and R-0612 shipped (June 12)
gave refund_ticket a destination: `refund_to`, a vault reference to a
form of payment, defaulting to the form that paid. D02's note in the
June 16 battery ("no destination field") was written against the tool
before that release and carried forward. Nothing recomputed it.

`Lab36` is the Chapter 33 lab with R-0612 applied, two switches for
the Chapter 36 fixes, and a vault that tokenizes any card number the
attack carries (Chapter 32: the model sees a reference and a last
four, never the number):

  tagging      tool results carry their source; untrusted text that
               reads like an instruction or carries a card is a signal
  destination  destination-v1: a refund goes only to a form of payment
               that paid for this booking

    python3 -m threats.email
"""
from __future__ import annotations

import copy
import hashlib
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from gateway import world as gw_world
from common.text import emit

from .battery import (CLASSES, STAGES, Lab, Options, Outcome, load,
                      tally)

HERE = Path(__file__).parent
V2 = HERE / "attacks-2026-06-26.toml"
REF = r"^vr-[0-9a-f]{6}-[0-9]{4}$"
PAID_PAN = "4111111111110417"     # the Ruiz booking paid with 0417
INSTRUCTION = re.compile(r"\b(route|send|apply|ignore|without further"
                         r" confirmation|agents? (may|should|must))\b",
                         re.I)
CARD = re.compile(r"\b(?:\d[ -]?){13,19}\b")


def vault_ref(pan: str) -> str:
    """The token the model sees: a reference plus the last four."""
    digits = re.sub(r"\D", "", pan)
    h = hashlib.sha256(f"vault:{digits}".encode()).hexdigest()[:6]
    return f"vr-{h}-{digits[-4:]}"


PAID = (vault_ref(PAID_PAN),)


def r0612(lab: Lab) -> None:
    """Apply release R-0612 to a lab world: the new refund schema,
    submitted and reviewed like any other tool change."""
    srv = lab.w.servers["payments"]
    spec = copy.deepcopy(srv._tools["refund_ticket"])
    spec["version"] = "3.1"
    spec["description"] += (" refund_to is a vault reference to a form "
                            "of payment; it defaults to the form that "
                            "paid.")
    spec["input_schema"]["properties"]["refund_to"] = {
        "type": "string", "pattern": REF}
    srv._tools["refund_ticket"] = spec
    reg = lab.w.registry
    reg.submit("payments", spec, ["case:effect"], srv.owner)
    reg.review("payments", "refund_ticket", gw_world.REVIEWER,
               approve=True, note="R-0612")


def signal(text: str) -> list[str]:
    """What a monitor counts in untrusted text. A signal, not a stop."""
    out = []
    if INSTRUCTION.search(text):
        out.append("instruction-like")
    if CARD.search(text):
        out.append("card number")
    return out


@dataclass
class Options36(Options):
    release: bool = True        # R-0612 applied (June 12 onward)
    tagging: bool = False
    destination: bool = False


class Lab36(Lab):
    def __init__(self, opts: Options36 | None = None):
        super().__init__(opts or Options36())
        self.signals: list[str] = []
        if self.opts.release:
            r0612(self)

    def read_tool(self, tool: str, injected: str = "") -> str:
        if not (self.opts.tagging and injected):
            return super().read_tool(tool, injected)
        text = super().read_tool(tool, "")
        self.context.pop()
        tagged = {"source": "supplier_text", "trust": "untrusted",
                  "text": injected}
        self.signals += signal(injected)
        text = text[:-1] + f", 'remark': {tagged}}}"
        self.context.append(text)
        return text

    def call(self, goal: dict) -> tuple[str, str]:
        args = goal["args"]
        if self.opts.destination and goal["tool"] == "refund_ticket":
            dest = args.get("refund_to", PAID[0])
            if dest not in PAID:
                return "proposal", ("policy: destination-v1: not a "
                                    "form that paid")
        return super().call(goal)

    def run(self, a: dict) -> Outcome:
        a = copy.deepcopy(a)
        if "card" in a:
            ref = vault_ref(a["card"])
            for g in a.get("goal", []):
                for k, v in g["args"].items():
                    if v == "@card":
                        g["args"][k] = ref
        return super().run(a)


def load_v2() -> dict:
    with open(V2, "rb") as f:
        spec = tomllib.load(f)
    base = load(HERE / spec["base"])
    rep = {a["id"]: a for a in spec.get("replace", [])}
    attacks = [rep.get(a["id"], a) for a in base["attack"]]
    attacks += spec.get("attack", [])
    return {"version": spec["version"], "owner": spec["owner"],
            "release": spec["release"], "attack": attacks,
            "control": base["control"]}


def run_v2(opts: Options36 | None = None,
           ids: tuple[str, ...] = ()) -> tuple[list[Outcome], int]:
    spec = load_v2()
    outs, sig = [], 0
    for a in spec["attack"]:
        if ids and a["id"] not in ids:
            continue
        lab = Lab36(copy.deepcopy(opts) if opts else None)
        outs.append(lab.run(a))
        sig += bool(lab.signals)
    return outs, sig


def table(outs: list[Outcome]) -> list[str]:
    t = tally(outs)
    cols = ("entry", "ctx", "refused", "propose", "effect")
    lines = [f"{'class':14}{'n':>3}" + "".join(f"{c:>9}" for c in cols)]
    tot = {s: 0 for s in STAGES}
    for c in CLASSES:
        row = t[c]
        n = sum(row.values())
        lines.append(f"{c:14}{n:>3}" +
                     "".join(f"{row[s]:>9}" for s in STAGES))
        for s in STAGES:
            tot[s] += row[s]
    lines.append(f"{'total':14}{sum(tot.values()):>3}" +
                 "".join(f"{tot[s]:>9}" for s in STAGES))
    return lines


def main(argv=None) -> int:
    spec = load_v2()
    emit(f"battery {spec['version']}, owner {spec['owner']}, "
         f"{len(spec['attack'])} attacks, after {spec['release']}")
    for name, o in (("june 24", Options36()),
                    ("june 26", Options36(destination=True)),
                    ("july plan", Options36(tagging=True,
                                            destination=True))):
        outs, sig = run_v2(o)
        emit(f"-- {name}: destination-v1 "
             f"{'on' if o.destination else 'off'}, tagging "
             f"{'on' if o.tagging else 'off'}")
        for ln in table(outs):
            emit(ln)
        for x in outs:
            if x.id in ("D02", "T05"):
                emit(f"{x.id} {x.stage}: {x.control}"[:70])
        emit(f"tool results with a signal: {sig}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
