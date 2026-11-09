"""The chain that stays: the final card, the four questions, the
renaming cycle, what runtimes absorb, and agents that hire agents."""
import tomllib
from dataclasses import dataclass
from pathlib import Path

from designs import registry

DATA = Path(__file__).resolve().parent / "data"
LINKS = ("effect", "permission", "verification", "trail")


def load(name: str) -> dict:
    return tomllib.loads((DATA / name).read_text())


# ------------------------------------------------------------ the card
def card() -> dict:
    c = load("card.toml")
    s = c["split"]
    c["split_total"] = sum(s.values())
    blended = float(next(r for r in c["row"]
                         if r["key"] == "cost_blended")["year_end"][1:])
    c["annual_check_m"] = round(c["meta"]["changes_per_year"]
                                * blended / 1e6, 1)
    return c


# ------------------------------------------ four questions per design
def four(design_id: str) -> dict:
    """Name the effect, the permission, the verification, the trail."""
    spec = registry.get(design_id)
    acts = [e["name"] for e in spec["effects"] if e["tier"] != "never"]
    return {
        "effect": ", ".join(acts),
        "permission": spec["gaps"]["G2"]["answer"],
        "verification": ", ".join(v["id"] for v in spec["verifiers"]),
        "trail": spec["record"]["id"] + " + "
        + ", ".join(spec["executor"]["writes"]),
    }


# ------------------------------------------------ the renaming cycle
@dataclass
class Reading:
    name: str
    date: str
    missing: list


def renames() -> list[Reading]:
    out = []
    for p in load("renames.toml")["pitch"]:
        miss = [k for k in LINKS if not p[k].strip()]
        # A self-report is not a verification; a judgment is not a rule.
        if "reports success" in p["verification"]:
            miss.append("verification")
        if "own judgment" in p["permission"]:
            miss.append("permission")
        out.append(Reading(p["name"], p["date"], sorted(set(miss),
                                                        key=LINKS.index)))
    return out


# ------------------------------------------- what runtimes absorb
def runtimes() -> list[dict]:
    rows = []
    for it in load("runtimes.toml")["item"]:
        state = ("absorbed " + it["since"]) if "since" in it else (
            "never" if it["by"] == "never" else "bet by " + it["by"])
        rows.append({"name": it["name"], "state": state,
                     "owned": it["still_owned"]})
    return rows


# -------------------------------------------- agents that hire agents
def hire(hops: list[dict] | None = None) -> list[str]:
    """Each hop's mandate must narrow its parent's: no more dollars, no
    new effects, no longer life. Returns findings; empty means sound."""
    hops = hops if hops is not None else load("hire.toml")["hop"]
    out = []
    for parent, child in zip(hops, hops[1:]):
        p, c = parent["mandate"], child["mandate"]
        who = f"{child['from']} -> {child['to']}"
        if c["max_usd"] > p["max_usd"]:
            out.append(f"{who}: ${c['max_usd']} above ${p['max_usd']}")
        extra = set(c["effects"]) - set(p["effects"])
        if extra:
            out.append(f"{who}: new effect {', '.join(sorted(extra))}")
        if c["expires_min"] > p["expires_min"]:
            out.append(f"{who}: lives longer than its parent")
    return out
