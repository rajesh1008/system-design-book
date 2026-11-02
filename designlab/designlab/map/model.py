"""Load the map and refuse any row that cannot be checked.

A claim is checkable when it names the gap it claims to touch, the
https page it came from, and the date that page makes it true. The
validator returns errors (the map is refused) and warnings (the map
loads, but someone must re-read a page). A claim older than the map's
stale_after_days, counted from today, is a warning, not an error: a
quarter-old claim may still be true, but nobody may assume so.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path

from .yamlish import loads

MAP_FILE = Path(__file__).with_name("map.yaml")
GAP_IDS = ("G1", "G2", "G3", "G4", "G5")
GAP_NAMES = {
    "G1": "output -> proposal",
    "G2": "proposal -> permission",
    "G3": "permission -> execution",
    "G4": "execution -> verified outcome",
    "G5": "verified outcome -> business result",
}
# closes: enforced or recorded outside the loop, a record you can read
# partial: a hook inside the loop, or a record you must finish yourself
# claims: a page says so; no mechanism found.  none: not in scope.
GAP_POINTS = {"closes": 2, "partial": 1, "claims": 0, "none": 0}
STATUSES = ("ga", "beta", "preview", "pre-1.0", "development", "sunset")
REQUIRED = ("id", "name", "category", "vendor", "status", "version",
            "lock_in", "cost", "gaps", "where", "hides", "claims")


@dataclass
class Claim:
    text: str
    gap: str
    source: str
    as_of: dt.date


@dataclass
class Option:
    id: str
    name: str
    category: str
    vendor: str
    status: str
    version: str
    lock_in: int
    cost: str
    gaps: dict
    where: str
    hides: str
    claims: list = field(default_factory=list)

    @property
    def points(self) -> int:
        return sum(GAP_POINTS[self.gaps[g]] for g in GAP_IDS)

    @property
    def newest(self) -> dt.date:
        return max(c.as_of for c in self.claims)

    @property
    def oldest(self) -> dt.date:
        return min(c.as_of for c in self.claims)


@dataclass
class Map:
    as_of: dt.date
    owner: str
    stale_after_days: int
    categories: dict
    options: list
    struck: list
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def by_category(self) -> dict:
        out = {c: [] for c in self.categories}
        for o in self.options:
            out.setdefault(o.category, []).append(o)
        return out

    def claim_count(self) -> int:
        return sum(len(o.claims) for o in self.options)


def parse_date(value, where: str, errors: list):
    if value in (None, ""):
        errors.append(f"{where}: no as_of date")
        return None
    try:
        return dt.date.fromisoformat(str(value))
    except ValueError:
        errors.append(f"{where}: as_of '{value}' is not YYYY-MM-DD")
        return None


def load(path: Path = MAP_FILE, today: dt.date | None = None) -> Map:
    return build(loads(Path(path).read_text()), today)


def build(raw: dict, today: dt.date | None = None) -> Map:
    errors, warnings = [], []
    as_of = parse_date(raw.get("as_of"), "map", errors)
    today = today or as_of or dt.date.today()
    stale = int(raw.get("stale_after_days", 92))
    cats = {c["id"]: c["name"] for c in raw.get("categories") or []}
    seen, options = set(), []
    for i, row in enumerate(raw.get("options") or []):
        opt = _option(row, i, cats, as_of, errors)
        if opt is None:
            continue
        if opt.id in seen:
            errors.append(f"{opt.id}: duplicate id")
        seen.add(opt.id)
        options.append(opt)
        _warn(opt, today, stale, warnings)
    for c in cats:
        if not any(o.category == c for o in options):
            errors.append(f"category {c}: no options")
    struck = []
    for row in raw.get("struck") or []:
        d = parse_date(row.get("as_of"), f"struck {row.get('id')}",
                       errors)
        if not str(row.get("source", "")).startswith("https://"):
            errors.append(f"struck {row.get('id')}: no https source")
        struck.append(dict(row, as_of=d))
    return Map(as_of, raw.get("owner", ""), stale, cats, options, struck,
               errors, warnings)


def _option(row, i, cats, as_of, errors):
    oid = row.get("id") or f"row {i + 1}"
    missing = [k for k in REQUIRED if row.get(k) in (None, "")]
    if missing:
        errors.append(f"{oid}: missing {', '.join(missing)}")
        return None
    if row["category"] not in cats:
        errors.append(f"{oid}: unknown category {row['category']}")
    if row["status"] not in STATUSES:
        errors.append(f"{oid}: unknown status {row['status']}")
    lock = row["lock_in"]
    if not isinstance(lock, int) or not 1 <= lock <= 5:
        errors.append(f"{oid}: lock_in must be 1 to 5")
    gaps = row["gaps"] if isinstance(row["gaps"], dict) else {}
    for g in GAP_IDS:
        if gaps.get(g) not in GAP_POINTS:
            errors.append(f"{oid}: gap {g} code '{gaps.get(g)}' unknown")
    extra = set(gaps) - set(GAP_IDS)
    if extra:
        errors.append(f"{oid}: unknown gap {sorted(extra)[0]}")
    claims = []
    for j, c in enumerate(row["claims"] or []):
        where = f"{oid} claim {j + 1}"
        d = parse_date(c.get("as_of"), where, errors)
        if not str(c.get("source", "")).startswith("https://"):
            errors.append(f"{where}: no https source")
        if c.get("gap") not in GAP_IDS + ("none",):
            errors.append(f"{where}: gap '{c.get('gap')}' unknown")
        if d and as_of and d > as_of:
            errors.append(f"{where}: dated {d}, after the map")
        if d:
            claims.append(Claim(str(c.get("text", "")), c.get("gap"),
                                c.get("source", ""), d))
    if not claims:
        errors.append(f"{oid}: no dated claim")
        return None
    if any(e.startswith(f"{oid}:") or e.startswith(f"{oid} ")
           for e in errors):
        return None
    return Option(row["id"], row["name"], row["category"],
                  row["vendor"], row["status"], str(row["version"]),
                  lock, row["cost"], {g: gaps[g] for g in GAP_IDS},
                  row["where"], row["hides"], claims)


def _warn(opt, today, stale, warnings):
    age = (today - opt.newest).days
    if age > stale:
        warnings.append(f"{opt.id}: newest claim {age} days old")
    if opt.status in ("beta", "preview", "development", "sunset"):
        warnings.append(f"{opt.id}: status {opt.status}")
