"""The fixture repository and its CI, run inside the sandbox.

`fixture()` reads fare-rules as it stands on main after the date
library upgrade: one test fails. `ci()` copies the repository with a
proposal's changes applied into a fresh sandbox directory and runs the
tests there with `isolation.run_in_sandbox`; the test count and the
result come from the run, not from the proposal's description.
"""
from __future__ import annotations

import difflib
import hashlib
import re
import shutil
import tempfile
from pathlib import Path

from isolation.sandbox import run_in_sandbox

from .gate import CIResult, Proposal

FIXTURE = Path(__file__).parent / "fixtures" / "fare_rules"
TEST_ARGV = ["python3", "-m", "unittest", "discover", "-s", "tests",
             "-t", "."]


def fixture() -> dict[str, str]:
    out = {}
    for f in sorted(FIXTURE.rglob("*")):
        if f.is_file() and "__pycache__" not in f.parts:
            out[str(f.relative_to(FIXTURE))] = f.read_text()
    return out


def sha(files: dict[str, str]) -> str:
    h = hashlib.sha1()
    for k in sorted(files):
        h.update(k.encode() + b"\0" + files[k].encode() + b"\0")
    return h.hexdigest()[:7]


def apply(files: dict[str, str], after: dict[str, str | None]
          ) -> dict[str, str]:
    out = dict(files)
    for path, text in after.items():
        if text is None:
            out.pop(path, None)
        else:
            out[path] = text
    return out


def run_tests(files: dict[str, str]) -> tuple[bool, int, int, str]:
    wd = Path(tempfile.mkdtemp(prefix="ci-"))
    try:
        for rel, text in files.items():
            dest = wd / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text)
        r = run_in_sandbox(wd, TEST_ARGV, timeout=20)
    finally:
        shutil.rmtree(wd, ignore_errors=True)
    m = re.search(r"Ran (\d+) tests?", r.stderr)
    n = int(m.group(1)) if m else 0
    f = re.search(r"FAILED \((?:failures=(\d+))?(?:, )?(?:errors=(\d+))?",
                  r.stderr)
    fails = sum(int(x) for x in f.groups() if x) if f else 0
    return r.code == 0 and n > 0, n, fails, r.runner


def ci(base: dict[str, str], p: Proposal) -> CIResult:
    head = apply(base, p.after)
    ok, n, fails, _ = run_tests(head)
    return CIResult(head_sha=sha(head), base_sha=sha(base), passed=ok,
                    tests=n, failures=fails)


def diff_lines(p: Proposal) -> list[str]:
    out = []
    for path in p.changed():
        old = (p.before.get(path) or "").splitlines()
        new = (p.after[path] or "").splitlines()
        out += [ln for ln in difflib.unified_diff(
            old, new, f"a/{path}", f"b/{path}", n=0, lineterm="")]
    return out
