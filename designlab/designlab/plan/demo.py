"""Chapter 48 lab. python3 -m plan.demo --part <part> [--fault <f>]

Parts: card, chain, renames, runtimes, hire, plan, window, check,
template. --file my-plan.toml checks a plan of your own. Faults (each expected to fail the plan check or the hire
check): roadmap, retired, undated, self-signed, crowded, widen."""
import argparse
import copy
import sys

from plan import core, template

W = 70


def line(s: str = "") -> None:
    assert len(s) <= W, s
    print(s)


def part_card() -> None:
    c = core.card()
    m = c["meta"]
    line(f"== final scoreboard, card {m['card_date']}, "
         f"board {m['board_date']} ==")
    line(f"{'number':<26}{'baseline':>9}  {'target':<18}{'year end':>9}")
    for r in c["row"]:
        line(f"{r['label']:<26}{r['baseline']:>9}  {r['target']:<18}"
             f"{r['year_end']:>9}")
    s = c["split"]
    line(f"split agent {s['agent']} / assisted {s['assisted']} / "
         f"self-service {s['self_service']} / person {s['person']}"
         f" = {c['split_total']}%")
    line(f"check: 2.1M changes x $9.76 = ${c['annual_check_m']}M a year")
    met = sum(r["met"] for r in c["row"])
    line(f"rows met: {met} of {len(c['row'])}")


def part_chain() -> None:
    line("== the chain that stays: four questions per design ==")
    for d in ("lakeshore-rebooking", "lakeshore-refunds"):
        f = core.four(d)
        line(d)
        for k in core.LINKS:
            txt = f[k]
            first = True
            while txt:
                cut = txt[:52] if len(txt) <= 52 else \
                    txt[:txt.rfind(" ", 0, 52)]
                line(f"  {k if first else '':<13}{cut}")
                txt, first = txt[len(cut):].strip(), False


def part_renames() -> None:
    line("== the renaming cycle: what each name left unanswered ==")
    for r in sorted(core.renames(), key=lambda r: r.date):
        gap = ", ".join(r.missing) if r.missing else "none"
        line(f"{r.date}  {r.name:<19} missing: {gap}")
    line("names read: " + str(len(core.renames())))


def part_runtimes() -> None:
    line("== what runtimes absorb, and what stays ==")
    for r in core.runtimes():
        line(f"{r['name']:<17}{r['state']:<20}{r['owned']}")


def part_hire(fault: str | None) -> int:
    hops = core.load("hire.toml")["hop"]
    if fault == "widen":
        hops = copy.deepcopy(hops)
        hops[1]["mandate"]["max_usd"] = 600
        hops[2]["mandate"]["effects"].append("refund")
    line("== agents that hire agents: mandates down the chain ==")
    for h in hops:
        m = h["mandate"]
        line(f"{h['from']:>20} -> {h['to']:<22} ${m['max_usd']:>3}"
             f" {m['expires_min']:>2} min")
    v = core.load("hire.toml")["verify"]
    line(f"verifier reads: {v['reads']}")
    found = core.hire(hops)
    for f in found:
        line("FAIL " + f)
    line("hire check: " + ("FAIL" if found else "pass"))
    return 1 if found else 0


def _plan(fault: str | None, path: str | None = None) -> dict:
    if path:
        import tomllib
        from pathlib import Path
        return tomllib.loads(Path(path).read_text())
    p = core.load("lakeshore-y2.toml")
    if fault == "roadmap":
        p["commitment"][2]["text"] = \
            "the next model will verify its own refunds"
    elif fault == "retired":
        p["bet"][0]["models"].append("claude-opus-4-1-20250805")
    elif fault == "undated":
        p["bet"][3]["revisit"] = ""
    elif fault == "self-signed":
        p["plan"]["signer"] = p["plan"]["owner"]
    elif fault == "crowded":
        p["bet"][1]["made"] = "2026-11-02"
        p["bet"][1]["revisit"] = "2026-12-14"
    return p


def part_plan() -> None:
    p = core.load("lakeshore-y2.toml")
    P, t = p["plan"], p["targets"]
    line(f"== {P['record']} {P['id']}, {P['date']} ==")
    line(f"owner {P['owner']}; signed {P['signer']}; "
         f"to {P['year_two_end']}")
    line(f"targets: split {t['agent']}/{t['assisted']}/"
         f"{t['self_service']}/{t['person']}, blended "
         f"${t['blended_usd']:.2f}")
    annual = P["changes_per_year"] * t["blended_usd"] / 1e6
    line(f"  = about ${annual:.1f}M a year at 2.1M changes")
    line("commitments (no model release needed):")
    for c in p["commitment"]:
        line(f"  {c['id']} {c['link']:<13}{c['owner']}")
        line(f"     {c['measure']}")
    line("bets (dated, tested, revisited):")
    for b in p["bet"]:
        line(f"  {b['id']} {b['area']:<10} due {b['due']} "
             f"revisit {b['revisit']}")
        line(f"     {b['claim']}")


def part_window() -> None:
    p = core.load("lakeshore-y2.toml")
    s = core.load("model_status.toml")
    line(f"== pinned models, status read {s['fetched']} ==")
    for mid, earliest, days in template.window(p, s):
        line(f"{mid:<20} not before {earliest}  {days:>4} days")
    line(f"notice promised: at least {s['notice_days']} days")


def part_check(fault: str | None, path: str | None = None) -> int:
    p = _plan(fault, path)
    found = template.check(p)
    line(f"== plan check{' (fault: ' + fault + ')' if fault else ''} ==")
    for f in found:
        line("FAIL " + f)
    line(f"rules PLN-1 to PLN-9, findings: {len(found)}")
    return 1 if found else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", required=True)
    ap.add_argument("--fault")
    ap.add_argument("--file", help="a plan TOML of your own")
    a = ap.parse_args(argv)
    if a.part == "template":
        line("== plan template ==")
        for ln in template.TEMPLATE.splitlines():
            line(ln)
        return 0
    if a.part == "hire":
        return part_hire(a.fault)
    if a.part == "check":
        return part_check(a.fault, a.file)
    {"card": part_card, "chain": part_chain, "renames": part_renames,
     "runtimes": part_runtimes, "plan": part_plan,
     "window": part_window}[a.part]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
