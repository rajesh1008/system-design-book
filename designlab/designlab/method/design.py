"""Load a design file and compute its estimate sheet.

A design is a TOML file with one table per artifact. An estimate line is
either an input (a value with an assumption and a source) or derived (a
formula over earlier lines). Formulas allow + - * / and parentheses
only; nothing else is evaluated.
"""
from __future__ import annotations

import ast
import operator
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DESIGNS = Path(__file__).resolve().parent / "designs"

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub,
        ast.Mult: operator.mul, ast.Div: operator.truediv}


class FormulaError(ValueError):
    pass


def names_in(formula: str) -> list[str]:
    tree = ast.parse(formula, mode="eval")
    return [n.id for n in ast.walk(tree) if isinstance(n, ast.Name)]


def evaluate(formula: str, env: dict[str, float]) -> float:
    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(
                node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.Name):
            if node.id not in env:
                raise FormulaError(f"unknown name {node.id}")
            return env[node.id]
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.left), ev(node.right))
        raise FormulaError("only + - * / and names are allowed")
    try:
        return ev(ast.parse(formula, mode="eval"))
    except SyntaxError as e:
        raise FormulaError(f"cannot parse {formula!r}") from e


@dataclass
class Design:
    raw: dict
    path: Path | None = None
    values: dict[str, float] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)

    @property
    def meta(self) -> dict:
        return self.raw.get("design", {})

    @property
    def people(self) -> list[str]:
        return list(self.meta.get("people", []))

    def section(self, key: str):
        return self.raw.get(key)

    @property
    def lines(self) -> list[dict]:
        return list(self.raw.get("estimate", []))

    def compute(self, overrides: dict[str, float] | None = None
                ) -> dict[str, float]:
        """Evaluate every line in order; inputs may be overridden."""
        overrides = overrides or {}
        env: dict[str, float] = {}
        self.errors = {}
        for ln in self.lines:
            name = ln.get("name", "?")
            try:
                if "formula" in ln:
                    env[name] = evaluate(ln["formula"], env)
                else:
                    env[name] = float(overrides.get(name, ln["value"]))
            except (FormulaError, KeyError, ZeroDivisionError) as e:
                self.errors[name] = str(e)
        if not overrides:
            self.values = env
        return env

    def sensitivity(self, target: str, factors=(0.5, 2.0)
                    ) -> list[tuple[str, float, float]]:
        """Move each input to its low and high; report the target's range.

        An input without a stated low and high is halved and doubled.
        The result is sorted with the widest swing first.
        """
        base = self.compute()
        out = []
        for ln in self.lines:
            if "formula" in ln or ln.get("name") not in base:
                continue
            n = ln["name"]
            ends = ([ln["low"], ln["high"]] if "low" in ln and "high" in ln
                    else [base[n] * f for f in factors])
            got = [self.compute({n: v}).get(target) for v in ends]
            if None not in got:
                out.append((n, min(got), max(got)))
        self.compute()
        return sorted(out, key=lambda t: t[2] - t[1], reverse=True)


def load(name_or_path: str | Path) -> Design:
    p = Path(name_or_path)
    if not p.suffix:
        p = DESIGNS / f"{p}.toml"
    d = Design(tomllib.loads(p.read_text()), p)
    d.compute()
    return d


def from_dict(raw: dict) -> Design:
    d = Design(raw)
    d.compute()
    return d
