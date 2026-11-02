"""The weekly fresh-sample evaluation.

Every Monday, sample 200 tasks from the week just ended, label them
(Marcus Bell's desk labels at Lakeshore; the lab knows the answers),
and score retrieval on them beside the golden set. The golden set is
the same questions every week, so it measures the system against the
world as it was when the set was built. The fresh sample measures it
against the world this week. Alert on the gap.

Two hundred questions is a small sample: a two-point move is four
questions. So the alert needs two things at once: the gap has widened
by at least two points over its trailing baseline, and at least half
of the misses fall in one slice (a source kind, a carrier, a topic).
Two points spread evenly is noise; two points on one slice is a
finding someone can act on.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

from common.rand import DEFAULT_SEED, seeded
from corpus.docs import CARRIERS, PRODUCTS, TOPICS, documents, in_effect
from retrieval.golden import Question, questions as golden_questions

from .drift import GOLDEN_BUILT, published, recall

WEEKS = tuple(date(2026, 4, 20) + timedelta(weeks=w) for w in range(8))
SAMPLE = 200
GAP_POINTS = 2.0
CLUSTER_SHARE = 0.5


def golden() -> list[Question]:
    """The golden set as built May 6 to 8: questions whose answers were
    published by then."""
    docs = {d.doc_id: d for d in documents()}
    return [q for q in golden_questions()
            if all(published(docs[r]) <= GOLDEN_BUILT
                   for r in q.relevant)]


def _rule_q(rng, n: int, as_of: date):
    code, name = rng.choice(CARRIERS)
    topic = rng.choice(sorted(TOPICS))
    title, _, says = TOPICS[topic]
    doc = in_effect(code, topic, as_of)
    if doc is None:
        return None
    prod, say = rng.choice(PRODUCTS), rng.choice(says)
    style = rng.choice(("code", "customer", "desk", "ref"))
    text = {"code": f"{code} {title} {prod}",
            "ref": f"{doc.facts['ref']} {prod}",
            "customer": f"{say[0].upper()}{say[1:]} on {name}; "
                        f"I have a {prod} fare.",
            "desk": f"{name.split()[0]} {prod} {say}"}[style]
    return Question(f"F{n:03d}", text, as_of, (doc.doc_id,), "rule")


def fresh_sample(week: date, n: int = SAMPLE,
                 seed: int = DEFAULT_SEED) -> list[Question]:
    """`n` tasks asked in the week starting `week`, as labeled. When a
    waiver is posted that week, a tenth of the week's questions are
    about it, and a quarter of those come the day it is posted."""
    rng = seeded(seed, "knowops", "fresh", week.isoformat())
    end = week + timedelta(days=6)
    new = [d for d in documents() if d.kind == "notice"
           and week <= published(d) <= end]
    old = [d for d in documents() if d.kind == "notice"
           and published(d) < week]
    names = dict(CARRIERS)
    out: list[Question] = []
    n_waiver = n // 10 if new else n // 20
    while len(out) < n_waiver:
        d = rng.choice(new or old)
        p = published(d)
        if new:
            lag = 0 if rng.random() < 0.25 else rng.randint(1, 3)
            as_of = min(p + timedelta(days=lag), end)
        else:
            as_of = week + timedelta(days=rng.randint(0, 6))
        if not d.in_effect(as_of):
            continue
        apt = d.topic.split("-")[1]
        out.append(Question(f"F{len(out) + 1:03d}",
                            f"Is there a {names[d.carrier]} waiver for "
                            f"{apt}?", as_of, (d.doc_id,), "notice"))
    while len(out) < n:
        q = _rule_q(rng, len(out) + 1,
                    week + timedelta(days=rng.randint(0, 6)))
        if q is not None:
            out.append(q)
    return out


def slice_of(q: Question) -> str:
    return q.style if q.style in ("notice", "rule") else "rule"


def run(policy: str, weeks=WEEKS, seed: int = DEFAULT_SEED) -> list[dict]:
    """One row per week: golden and fresh recall, gap, and the alert."""
    g, _ = recall(golden(), policy)
    rows, gaps = [], []
    for w in weeks:
        f, missed = recall(fresh_sample(w, seed=seed), policy)
        gap = g - f
        base = sorted(gaps[-4:])[len(gaps[-4:]) // 2] if gaps else gap
        by = Counter(slice_of(q) for q in missed)
        top, top_n = by.most_common(1)[0] if by else ("", 0)
        share = top_n / len(missed) if missed else 0.0
        alert = (gap - base >= GAP_POINTS and share >= CLUSTER_SHARE)
        rows.append({"week": w, "golden": g, "fresh": f, "gap": gap,
                     "baseline": base, "missed": len(missed),
                     "slice": top, "share": share, "alert": alert})
        if not alert:
            gaps.append(gap)
    return rows
