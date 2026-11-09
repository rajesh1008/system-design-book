"""Chapter 45: six internal designs and five rules, added to Chapter
43's package without editing it.

    with installed():          # the twelve designs, the thirteen rules
        ...

installed() registers the six specs in designs/internal_specs/ with
registry.register, adds LOOP-1, LOOP-2, LOOP-3, PRV-1, and RVW-1 with
lint.register_rule, maps them to gaps, and puts everything back on
exit, so Chapter 43's tests and outputs never see them. Nothing
registers at import. Lakeshore figures are illustrative.
"""
from __future__ import annotations

from contextlib import contextmanager
from importlib import import_module
from pathlib import Path

from . import registry
from .privilege import internal, prv_1
from .records import rvw_1
from .unattended import loop_1, loop_2, loop_3, unattended

# The package exports lint() under the name lint; this is the module.
worked = import_module("designs.lint")

DATA = Path(__file__).resolve().parent / "internal_specs"
ORDER = ("lakeshore-research", "lakeshore-coding", "lakeshore-analytics",
         "lakeshore-itops", "lakeshore-compliance", "lakeshore-recon")
SHORT = {"lakeshore-research": "res", "lakeshore-coding": "cod",
         "lakeshore-analytics": "ana", "lakeshore-itops": "ops",
         "lakeshore-compliance": "cmp", "lakeshore-recon": "rec"}
RULES = (("LOOP-1", loop_1), ("LOOP-2", loop_2), ("LOOP-3", loop_3),
         ("PRV-1", prv_1), ("RVW-1", rvw_1))
GAPS = {"LOOP-1": "G3", "LOOP-2": "G2", "LOOP-3": "G4", "PRV-1": "G2"}


def load() -> dict[str, dict]:
    return {did: registry.load_spec(DATA / f"{did}.toml")
            for did in ORDER}


def install() -> None:
    for spec in load().values():
        registry.register(spec)
    have = {n for n, _ in worked.RULES}
    for name, fn in RULES:
        if name not in have:
            worked.register_rule(name, fn)
    worked.GAP_OF.update(GAPS)


@contextmanager
def installed():
    designs = dict(registry.DESIGNS)
    rules = list(worked.RULES)
    gaps = dict(worked.GAP_OF)
    try:
        install()
        yield registry.DESIGNS
    finally:
        registry.DESIGNS.clear()
        registry.DESIGNS.update(designs)
        worked.RULES[:] = rules
        worked.GAP_OF.clear()
        worked.GAP_OF.update(gaps)


# Patterns Chapter 43's table could not ask, because its six designs
# face customers and run when a customer asks.
def _no_standing(s):
    return internal(s) and not prv_1(s)


def _loop_declared(s):
    return unattended(s) and not (loop_1(s) or loop_2(s) or loop_3(s))


def _signed(s):
    return internal(s) and not rvw_1(s)


PATTERNS = (
    ("no standing credential", _no_standing),
    ("unattended loop in seven properties", _loop_declared),
    ("record signed by someone else", _signed),
)
