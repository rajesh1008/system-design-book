"""Fail if any file under designlab carries a credential.

    python3 -m common.secretscan [ROOT]

Every file is checked for provider key shapes and for the value of
ANTHROPIC_API_KEY when it is set. Files under a `fixtures` directory
also fail on the request-header name and the key prefix.
"""
from __future__ import annotations

import sys
from pathlib import Path

from .redact import scan_tree
from .text import emit

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else ROOT
    problems = scan_tree(root)
    files = sum(1 for p in root.rglob("*") if p.is_file()
                and "__pycache__" not in p.parts)
    for path, hits in problems.items():
        emit(f"FOUND {path[:40]}: {', '.join(hits)[:20]}")
    emit(f"secret scan: {files} files, {len(problems)} with findings")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
