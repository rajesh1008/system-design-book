"""Skills and instruction files as portable capability (Chapter 30).

A skill is a folder with a SKILL.md: a name and a description up
front, a body, and files the body links to. Progressive disclosure
loads them in that order. `ledger()` counts what each level costs in
tokens; `drift()` finds tools a skill or an instruction file names
that the Harness Manifest does not grant. Tokens are estimated as
characters over four, rounded up; the chapter prints estimates.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

from harness import manifest as M

SKILLS = Path(__file__).with_name("skills")
TOOL = re.compile(r"`([a-z][a-z0-9_]+)`")


def tokens(text: str) -> int:
    return math.ceil(len(text) / 4)


@dataclass
class Skill:
    name: str
    description: str
    body: str
    files: dict

    @property
    def meta_tokens(self) -> int:
        return tokens(f"{self.name}: {self.description}")

    @property
    def body_tokens(self) -> int:
        return tokens(self.body)

    @property
    def file_tokens(self) -> int:
        return sum(tokens(t) for t in self.files.values())

    def tools(self) -> list:
        return sorted(set(TOOL.findall(self.body)))


def parse(folder: Path) -> Skill:
    text = (folder / "SKILL.md").read_text()
    _, front, body = text.split("---\n", 2)
    meta = dict(line.split(": ", 1) for line in front.strip().splitlines())
    files = {str(p.relative_to(folder)): p.read_text()
             for p in sorted(folder.rglob("*.md")) if p.name != "SKILL.md"}
    return Skill(meta["name"], meta["description"], body, files)


def load_all(root: Path = SKILLS) -> list:
    return [parse(p) for p in sorted(root.iterdir()) if p.is_dir()]


def ledger(skills: list, used: set) -> dict:
    """Tokens in context when every skill's metadata is preloaded and
    only the skills in `used` load their bodies and linked files."""
    meta = sum(s.meta_tokens for s in skills)
    loaded = sum(s.body_tokens + s.file_tokens for s in skills
                 if s.name in used)
    everything = sum(s.meta_tokens + s.body_tokens + s.file_tokens
                     for s in skills)
    return {"metadata": meta, "loaded": loaded,
            "disclosed": meta + loaded, "all_upfront": everything}


def granted(name: str = "servicing-1.0.0") -> set:
    return {t["name"] for t in M.resolve(M.load(name))["tools"]}


def drift(skills: list, manifest: str = "servicing-1.0.0") -> list:
    tools = granted(manifest)
    return [f"{s.name}: names {t}, not in the manifest"
            for s in skills for t in s.tools() if t not in tools]
