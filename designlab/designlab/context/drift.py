"""Instruction-file drift: the file every call carries, release by
release, and a lint that finds the lines nobody can vouch for.

Each line is a record: its text, an owner, the date it was added, why,
the golden case that tests it, and a topic. The lint reports lines
that name something retired, pairs of lines on one topic that say
different things, lines with no owner, and lines with no test. The
versions are the lab's reconstruction of Lakeshore's file from
December 2025 to May 2026; token counts are the lab's.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from common.rand import seeded

RETIRED = ("refunds-v2", "search_flights_v1", "FR-071", "hold-desk",
           "goodwill-v0")


@dataclass(frozen=True)
class Line:
    lid: str
    text: str
    tokens: int
    owner: str | None
    added: str
    why: str | None
    test: str | None
    topic: str


# The lines quoted in the chapter. The rest are generated.
QUOTED = (
    Line("L-007", "Offer a voucher before a refund when the customer"
         " has not asked for money back.", 22, None, "2025-12-17",
         None, None, "voucher-first"),
    Line("L-052", "Never offer a voucher in place of a refund on a"
         " carrier cancellation; quote rule FR-112.", 24, "rmorgan",
         "2026-05-04", "FR-112 house format (Ch17)", "G-REF-031",
         "voucher-first"),
    Line("L-019", "Use search_flights_v1 for same-day changes.", 12,
         None, "2026-01-12", None, None, "search"),
    Line("L-033", "Send unclear refunds to the hold-desk queue.", 12,
         "mbell", "2026-02-10", "pilot desk layout", None, "routing"),
)

# version, date, lines, tokens, stale, contradiction pairs, no owner,
# no test, what changed
VERSIONS = (
    ("v1", "2025-12-01", 31, 640, 0, 0, 9, 31, "pilot"),
    ("v2", "2025-12-17", 34, 690, 0, 0, 11, 33, "credits-v1"),
    ("v3", "2026-01-12", 38, 760, 1, 0, 12, 34, "rebook-v2, refunds"),
    ("v4", "2026-02-10", 41, 820, 2, 1, 14, 34, "surname check"),
    ("v5", "2026-03-02", 46, 910, 3, 1, 15, 33, "phase two"),
    ("v6", "2026-04-06", 51, 1_010, 5, 1, 17, 30, "strict tools"),
    ("v7", "2026-04-20", 56, 1_100, 6, 2, 19, 27, "re-layout"),
    ("v8", "2026-05-04", 71, 1_460, 9, 3, 22, 38, "style guide, FR-112"),
    ("v9", "2026-05-27", 58, 1_180, 0, 0, 0, 9, "cleanup"),
)

OWNERS = ("dprice", "hclarke", "mbell", "rmorgan", "bcarter",
          "ofletcher")


def build(version: str) -> list[Line]:
    """The lines of one version, with exactly the counts in VERSIONS."""
    row = next(v for v in VERSIONS if v[0] == version)
    _, date, n, tokens, stale, pairs, no_owner, no_test, _ = row
    r = seeded(21, "drift", version)
    lines: list[Line] = []
    for k in range(stale):
        lines.append(Line(f"S-{k:02d}", f"Route by {RETIRED[k % 5]}.",
                          12, None if k < no_owner else "mbell",
                          "2026-01-12", None, None, f"stale-{k}"))
    for k in range(pairs):
        for side in ("always", "never"):
            lines.append(Line(f"C-{k}-{side}", f"{side} rule {k}", 22,
                              None if side == "always" else "rmorgan",
                              date, None, None, f"pair-{k}"))
    owned_left = no_owner - sum(1 for ln in lines if ln.owner is None)
    tested_left = no_test - len(lines)
    k = 0
    while len(lines) < n:
        lines.append(Line(f"L-{k:03d}", f"line {k}", 18,
                          None if k < owned_left else
                          OWNERS[k % len(OWNERS)], date,
                          None if k < owned_left else "golden reason",
                          None if k < tested_left else f"G-{k:03d}",
                          f"t-{k}"))
        k += 1
    # spread the token total over the lines, deterministically
    base = sum(ln.tokens for ln in lines)
    extra = tokens - base
    out = []
    for i, ln in enumerate(lines):
        share = extra // n + (1 if i < extra % n else 0)
        out.append(replace(ln, tokens=ln.tokens + share))
    r.shuffle(out)
    return out


def lint(lines: list[Line]) -> dict[str, list[str]]:
    found = {"stale": [], "contradiction": [], "no owner": [],
             "no test": []}
    for ln in lines:
        if any(x in ln.text for x in RETIRED):
            found["stale"].append(ln.lid)
        if ln.owner is None:
            found["no owner"].append(ln.lid)
        if ln.test is None:
            found["no test"].append(ln.lid)
    topics: dict[str, set] = {}
    for ln in lines:
        topics.setdefault(ln.topic, set()).add(ln.text)
    for t, texts in sorted(topics.items()):
        if len(texts) > 1:
            found["contradiction"].append(t)
    return found


def tokens(lines: list[Line]) -> int:
    return sum(ln.tokens for ln in lines)


def history() -> list[tuple[str, str, int, int, dict]]:
    out = []
    for v in VERSIONS:
        lines = build(v[0])
        out.append((v[0], v[1], len(lines), tokens(lines), lint(lines)))
    return out
