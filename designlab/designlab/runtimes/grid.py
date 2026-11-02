"""The comparison grid: every cell a dated claim, scored by plane.

The grid's rows are the shortlist that `map` produces (Chapter 3), so
an option the map did not shortlist cannot enter the bake-off and an
option it did cannot be left out quietly. The validator refuses a
cell with no date, a cell dated after the grid, a criterion nobody
defined, a score outside 0 to 2, and a doc cell without a source.
Staleness is a warning, as it is on the map.
"""
from __future__ import annotations

import copy
import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path

from map.model import load as load_map
from map.model import parse_date
from map.shortlist import shortlist
from map.yamlish import loads

GRID_FILE = Path(__file__).with_name("grid.yaml")
PLANES = ("action", "control", "knowledge", "trail", "portability")
BASES = ("doc", "test", "own")


class GridError(ValueError):
    pass


@dataclass
class Cell:
    criterion: str
    score: int
    basis: str
    as_of: dt.date
    src: str


@dataclass
class Option:
    id: str
    kind: str
    how: str
    cells: dict = field(default_factory=dict)


@dataclass
class Grid:
    as_of: dt.date
    criteria: list
    options: list
    sources: dict
    stale_after: int
    warnings: list = field(default_factory=list)

    def plane_of(self, cid: str) -> str:
        return next(c["plane"] for c in self.criteria if c["id"] == cid)

    def musts(self) -> list:
        return [c["id"] for c in self.criteria if c["must"]]


def read(path: Path = GRID_FILE) -> dict:
    return loads(Path(path).read_text())


def shortlist_ids(today: dt.date | None = None) -> list:
    picks = shortlist(load_map(today=today))
    return [s.option.id for group in picks.values() for s in group]


def build(raw: dict, today: dt.date | None = None,
          check_shortlist: bool = True) -> Grid:
    errors: list = []
    as_of = parse_date(raw.get("as_of"), "grid", errors)
    crits = raw.get("criteria") or []
    ids = [c["id"] for c in crits]
    for c in crits:
        c["must"] = str(c.get("must")).lower() == "true"
        if c.get("plane") not in PLANES:
            errors.append(f"{c['id']}: unknown plane {c.get('plane')}")
    sources = raw.get("sources") or {}
    options = []
    for row in raw.get("options") or []:
        opt = Option(row["id"], row.get("kind", ""), row.get("how", ""))
        cells = row.get("cells") or {}
        for cid in cells:
            if cid not in ids:
                errors.append(f"{opt.id}.{cid}: no such criterion")
        for cid in ids:
            where = f"{opt.id}.{cid}"
            c = cells.get(cid)
            if c is None:
                errors.append(f"{where}: no cell (a gap must be scored)")
                continue
            d = parse_date(c.get("as_of"), where, errors)
            s = c.get("s")
            if s not in (0, 1, 2):
                errors.append(f"{where}: score {s} is not 0, 1 or 2")
            basis = c.get("basis")
            if basis not in BASES:
                errors.append(f"{where}: basis {basis} unknown")
            src = str(c.get("src") or "")
            if basis == "doc" and not str(
                    sources.get(src, "")).startswith("https://"):
                errors.append(f"{where}: doc cell without a source")
            if d and as_of and d > as_of:
                errors.append(f"{where}: dated after the grid")
            if d:
                opt.cells[cid] = Cell(cid, s, basis, d, src)
        options.append(opt)
    if check_shortlist and not errors:
        want = shortlist_ids()
        got = [o.id for o in options]
        if sorted(want) != sorted(got):
            errors.append(f"options {got} are not the shortlist {want}")
    if errors:
        raise GridError("; ".join(errors))
    g = Grid(as_of, crits, options, sources,
             int(raw.get("stale_after_days", 92)))
    if today:
        for o in options:
            old = [c for c in o.cells.values()
                   if (today - c.as_of).days > g.stale_after]
            if old:
                age = max((today - c.as_of).days for c in old)
                g.warnings.append(f"{o.id}: {len(old)} cells stale, "
                                  f"oldest {age} days")
    return g


def load(path: Path = GRID_FILE, today: dt.date | None = None) -> Grid:
    return build(read(path), today)


def by_plane(g: Grid, opt: Option) -> dict:
    out = {p: 0 for p in PLANES}
    for cid, cell in opt.cells.items():
        out[g.plane_of(cid)] += cell.score
    return out


def total(g: Grid, opt: Option, weights: dict | None = None) -> float:
    w = weights or {}
    return sum(v * w.get(p, 1) for p, v in by_plane(g, opt).items())


def failed_musts(g: Grid, opt: Option) -> list:
    return [cid for cid in g.musts() if opt.cells[cid].score == 0]


def rank(g: Grid, weights: dict | None = None) -> list:
    rows = [(o, total(g, o, weights), failed_musts(g, o))
            for o in g.options]
    return sorted(rows, key=lambda r: (bool(r[2]), -r[1], r[0].id))


def drop(raw: dict, option: str, criterion: str, score: int = 0) -> dict:
    """A variant grid with one cell re-scored, for the exercises."""
    out = copy.deepcopy(raw)
    for row in out["options"]:
        if row["id"] == option:
            row["cells"][criterion]["s"] = score
    return out


def feature_table(raw: dict) -> dict:
    """The grid as vendors' comparison pages present it: check marks,
    no dates, no sources. The validator should refuse every cell."""
    out = copy.deepcopy(raw)
    for row in out["options"]:
        for cell in row["cells"].values():
            cell.pop("as_of", None)
            cell["basis"] = "doc"
            cell["src"] = ""
            cell["s"] = 2
    return out
