"""Write the corpus as JSON Lines plus a manifest.

    python3 -m corpus.build [--seed 2026] [--scale v0|full] [--out DIR]

The default output is out/corpus/<version>-<scale>-seed<seed>/, which
is ignored by git. The manifest digest identifies the exact bytes.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from common.rand import DEFAULT_SEED
from common.text import emit
from .generate import SCALES, VERSION, write

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--scale", choices=sorted(SCALES), default="v0")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)
    out = a.out or ROOT / "out" / "corpus" / \
        f"{VERSION}-{a.scale}-seed{a.seed}"
    m = write(out, a.seed, a.scale)
    try:
        shown = out.relative_to(ROOT)
    except ValueError:
        shown = out
    emit(f"wrote {shown}")
    for name, t in m["tables"].items():
        emit(f"  {name:17} {t['rows']:>8,} rows  {t['sha256'][:12]}")
    emit(f"digest {m['digest'][:32]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
