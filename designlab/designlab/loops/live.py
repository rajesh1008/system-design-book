"""Chapter 28 live lab: who writes the hour's report.

The small model plays the fare watch's reporting step. It gets the
tool results of one hour for twelve watches and writes the one-line
report the dashboard shows. In the refused arm it sees the raw
results: every read came back invalid_arguments, as on June 14. In
the counters arm it sees what 1.0.0's actor handed its reporting
step on June 14: its own tallies, in which a refused read counted as
a check with no offers. In the read arm every read worked and no fare
dropped. The verifier does not read the report: it counts
allowed reads on the gateway trail. Whatever the model writes, the
refused hour is red.

Reads ANTHROPIC_API_KEY from the environment through common.client and
never prints it. Eighteen short calls; the meter caps spend at $0.05.
All identifiers are synthetic.

    python3 -m loops.live
"""
from __future__ import annotations

import textwrap

from common.client import ModelClient
from common.spend import SpendMeter
from common.text import emit

from .fare_watch import V100, V110, Actor, Verifier
from .world import fare_world

SYSTEM = ("You are the reporting step of an hourly fare-watch job at a "
          "travel company. Write the one-line status for the operations "
          "dashboard. One line, no preamble.")
WORDS = ("error", "fail", "invalid", "refus", "could not", "unable",
         "0 of 12", "0/12", "none of", "no fares were")


def packet(results: list[str]) -> str:
    return ("Hour 12:00 to 13:00. Watches due: 12. Tool results:\n"
            + "\n".join(results) + "\nWrite the status line.")


def hour(design) -> tuple[list[str], dict]:
    fw = fare_world(12)
    a, v = Actor(fw, design), Verifier(fw, sample=0.25)
    rows = []
    for w in fw.list:
        seg = str(w.segment) if design.segment_bug else w.segment
        r = fw.w.gateway.call("wl-fare-watch", "offers", "offers_search",
                              {"booking_ref": w.booking, "segment": seg,
                               "kind": "flight"})
        if r.ok:
            o = r.output["offers"][0]
            rows.append(f"{w.wid} offers_search: fare {o['fare_usd']}, "
                        f"floor {w.booked:.2f}, no drop")
        else:
            rows.append(f"{w.wid} offers_search: {r.reason} "
                        f"field {r.field}")
    fw.w.trail.lines.clear()
    h = a.run_hour(60)
    return rows, v.check_hour(60, h, a.store)


def run(trials: int = 6, client: ModelClient | None = None) -> dict:
    client = client or ModelClient("small",
                                   meter=SpendMeter(cap_usd=0.05))
    out = {}
    for arm, design in (("refused", V100), ("counters", V100),
                        ("read", V110)):
        rows, verdict = hour(design)
        if arm == "counters":
            rows = [f"tally: watches checked {len(rows)}, offers found "
                    "0, drops 0, vouchers 0"]
        reps = []
        for k in range(trials):
            c = client.complete(packet(rows) + f"\n(run {k + 1})",
                                system=SYSTEM, max_tokens=400)
            line = c.text.strip().splitlines()[0] if c.text.strip() \
                else ""
            reps.append({"text": line, "names_failure": any(
                x in line.lower() for x in WORDS)})
        out[arm] = {"reports": reps, "verifier": verdict}
    out["spent"] = client.meter.spent_usd
    out["calls"] = client.meter.calls
    out["model"] = client.pin.id
    return out


def summarize(res: dict) -> list[str]:
    lines = [f"model {res['model']}  calls {res['calls']}  "
             f"spent ${res['spent']:.4f}"]
    for arm in ("refused", "counters", "read"):
        a = res[arm]
        n = len(a["reports"])
        k = sum(r["names_failure"] for r in a["reports"])
        v = a["verifier"]
        lines.append(f"{arm:8} reports naming a failure {k} of {n}; "
                     f"verifier {'green' if v['green'] else 'RED'}")
        first = textwrap.wrap(a["reports"][0]["text"].replace(
            "\u2013", "-").replace("\u2014", "-"), 64)
        lines += [f"  {t}" for t in first[:3]]
    return lines


if __name__ == "__main__":
    for line in summarize(run()):
        emit(line)
