"""The merge service's review gate for coding-agent proposals.

The coding agent's production role is proposal only: it pushes agent/*
branches and opens pull requests. The merge service merges, and only
when every rule below holds for the exact head commit:

1. tests pass on the head, on the current base (a new base is a new
   proposal, so the evidence is rerun);
2. the test count did not fall and no skip markers were added, unless
   the owner of tests/ approved that head;
3. protected paths (tests/, CI config, CODEOWNERS, instruction files)
   changed only with their named owner's approval of that head;
4. a person other than the requester approved that head.

The gate reads the change itself, not the pull request's description.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field

AGENT = "coding-agent"
MERGER = "merge-service"
SKIP = re.compile(r"(unittest\.skip|pytest\.mark\.(skip|xfail)|"
                  r"expectedFailure|skipTest\()")
INSTRUCTION_FILES = ("AGENTS.md", "CLAUDE.md", ".cursorrules",
                     ".github/copilot-instructions.md")


@dataclass(frozen=True)
class Approval:
    who: str
    sha: str


@dataclass(frozen=True)
class CIResult:
    head_sha: str
    base_sha: str
    passed: bool
    tests: int
    failures: int = 0


@dataclass
class Proposal:
    pr: int
    ticket: str
    branch: str
    author: str
    requester: str
    base_sha: str
    head_sha: str
    before: dict[str, str]           # path -> text on the base
    after: dict[str, str | None]     # changed paths; None = deleted
    description: str = ""
    approvals: list[Approval] = field(default_factory=list)

    def changed(self) -> list[str]:
        return sorted(self.after)


@dataclass
class GateVerdict:
    decision: str                 # merge | hold | refuse
    reasons: list[str]
    needs: list[str]              # who has to approve this head

    @property
    def merged(self) -> bool:
        return self.decision == "merge"


def owners(codeowners: str) -> list[tuple[str, str]]:
    out = []
    for line in codeowners.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        path, _, who = line.partition(" ")
        out.append((path, who.strip()))
    return out


def owner_of(path: str, table: list[tuple[str, str]]) -> str | None:
    best = None
    for prefix, who in table:
        if path == prefix or (prefix.endswith("/")
                              and path.startswith(prefix)):
            if best is None or len(prefix) > len(best[0]):
                best = (prefix, who)
    return best[1] if best else None


def names_of_tests(text: str | None) -> set[str]:
    if not text:
        return set()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    return {n.name for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name.startswith("test")}


def _skips(text: str | None) -> int:
    return len(SKIP.findall(text or ""))


def analyze(p: Proposal) -> dict:
    deleted, skips, protected = [], 0, []
    table = owners(p.before.get("CODEOWNERS", ""))
    for path in p.changed():
        old, new = p.before.get(path), p.after[path]
        if path.startswith("tests/"):
            deleted += sorted(names_of_tests(old) - names_of_tests(new))
            skips += max(0, _skips(new) - _skips(old))
        who = owner_of(path, table)
        if who or path in INSTRUCTION_FILES:
            protected.append((path, who or "Daniel Price"))
    return {"deleted_tests": deleted, "new_skips": skips,
            "protected": protected}


def review(p: Proposal, ci: CIResult, base_now: str,
           tests_on_base: int, merger: str = MERGER) -> GateVerdict:
    reasons, needs = [], []
    if merger != MERGER:
        return GateVerdict("refuse", [f"{merger} cannot merge; only "
                                      f"{MERGER} merges"], [])
    if p.author == AGENT and not p.branch.startswith("agent/"):
        return GateVerdict("refuse", ["agent pushes agent/* only"], [])
    a = analyze(p)
    if ci.head_sha != p.head_sha:
        reasons.append(f"evidence is for {ci.head_sha}, head is "
                       f"{p.head_sha}")
    if p.base_sha != base_now or ci.base_sha != base_now:
        reasons.append(f"base moved to {base_now}; new proposal, "
                       f"rerun tests")
    if not ci.passed:
        reasons.append(f"tests failing ({ci.failures} of {ci.tests})")
    head_ok = {x.who for x in p.approvals if x.sha == p.head_sha}
    stale = {x.who for x in p.approvals if x.sha != p.head_sha}
    for path, who in a["protected"]:
        if who not in head_ok:
            reasons.append(f"protected {path} needs {who}")
            needs.append(who)
    tests_owner = owner_of("tests/", owners(p.before.get("CODEOWNERS",
                                                         "")))
    if ci.tests < tests_on_base and tests_owner not in head_ok:
        reasons.append(f"test count fell {tests_on_base} to {ci.tests}")
    if a["deleted_tests"] and tests_owner not in head_ok:
        reasons.append("deleted " + ", ".join(a["deleted_tests"]))
    if a["new_skips"] and tests_owner not in head_ok:
        reasons.append(f"{a['new_skips']} skip marker(s) added")
    if (ci.tests < tests_on_base or a["deleted_tests"]
            or a["new_skips"]) and tests_owner not in needs \
            and tests_owner not in head_ok:
        needs.append(tests_owner)
    people = head_ok - {p.requester, p.author, AGENT}
    if not people:
        if stale - {p.requester, AGENT}:
            reasons.append("approval is for an older commit")
        elif p.requester in head_ok:
            reasons.append("requester cannot approve own request")
        else:
            reasons.append("no person approved this head")
    if reasons:
        return GateVerdict("hold", reasons, sorted(set(needs)))
    return GateVerdict("merge", ["all rules hold"], [])
