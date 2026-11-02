"""The method linter: what a machine can check in a design.

It checks that the design says something checkable and names who owns
it. It cannot check that what the design says is right; that is what
the review is for (Section 7).

Rules, one finding per offending item:
    ART-1  an artifact is missing or empty
    REQ-1  a bank question is neither answered nor open with an owner
    EST-1  an estimate input has no assumption or no source
    EST-2  a derived estimate line does not compute
    OWN-1  an artifact item has no owner, or the owner is not listed
    DEC-1  a decision has fewer than two options
    DEC-2  the choice is not an option, or a rejected option has no why
    REC-1  a decision record does not say what would reverse it
    LINK-1 an evidence link does not resolve
    DIVE-1 a deep dive lists fewer than three complete failure modes
    GRM-1  an effect is not preceded by a gate
    GRM-2  a verifier acted, or reads what the actor writes
    GRM-3  a node or edge is outside the diagram grammar
    GAP-Gn a gap has no answer
"""
from __future__ import annotations

from dataclasses import dataclass

from .artifacts import (ARTIFACTS, CHECKLIST, EDGE_KINDS, NODE_KINDS,
                        PLANES, QUESTIONS)
from .design import Design, names_in

GAPS = ("G1", "G2", "G3", "G4", "G5")


@dataclass(frozen=True)
class Finding:
    rule: str
    where: str
    message: str

    def line(self) -> str:
        return f"{self.rule:<6} {self.where}: {self.message}"


def _owner(d: Design, item: dict | None, where: str, out: list) -> None:
    who = (item or {}).get("owner", "")
    if not who:
        out.append(Finding("OWN-1", where, "no owner"))
    elif who not in d.people:
        out.append(Finding("OWN-1", where, f"owner {who} not listed"))


def _targets(d: Design) -> set[str]:
    t = {f"est:{ln.get('name')}" for ln in d.lines}
    t |= {f"req:{q}" for q in (d.section("requirements") or {})}
    dia = d.section("diagram") or {}
    t |= {f"node:{n.get('id')}" for n in dia.get("nodes", [])}
    t |= {f"dec:{x.get('id')}" for x in d.section("decisions") or []}
    t |= {f"dive:{x.get('id')}" for x in d.section("deep_dives") or []}
    t |= {f"rec:{x.get('id')}" for x in d.section("records") or []}
    return t


def _links(d: Design, links, where: str, targets: set, out: list) -> None:
    for link in links or []:
        if link.startswith(("doc:", "https://")):
            continue
        if link not in targets:
            out.append(Finding("LINK-1", where, f"{link} does not resolve"))


def lint(d: Design, questions: dict[str, str] | None = None
         ) -> list[Finding]:
    questions = QUESTIONS if questions is None else questions
    out: list[Finding] = []
    for key, name, _ in ARTIFACTS:
        if not d.section(key):
            out.append(Finding("ART-1", key, f"no {name}"))
    targets = _targets(d)

    if d.section("scope"):
        _owner(d, d.section("scope"), "scope", out)

    reqs = d.section("requirements") or {}
    if reqs:
        for qid in questions:
            r = reqs.get(qid, {})
            if r.get("answer"):
                continue
            if r.get("status") == "open" and r.get("owner"):
                _owner(d, r, f"req {qid}", out)
                continue
            out.append(Finding("REQ-1", f"req {qid}", "no answer"))

    for ln in d.lines:
        name = ln.get("name", "?")
        if "formula" in ln:
            if name in d.errors:
                out.append(Finding("EST-2", f"estimate {name}",
                                   d.errors[name]))
            continue
        missing = [f for f in ("assumption", "source") if not ln.get(f)]
        if missing:
            out.append(Finding("EST-1", f"estimate {name}",
                               "no " + ", no ".join(missing)))

    for dec in d.section("decisions") or []:
        w = f"decision {dec.get('id')}"
        _owner(d, dec, w, out)
        opts = dec.get("options", [])
        if len(opts) < 2:
            out.append(Finding("DEC-1", w, f"{len(opts)} option, no "
                               "alternative"))
            continue
        names = [o.get("name") for o in opts]
        if dec.get("chosen") not in names:
            out.append(Finding("DEC-2", w, "choice is not an option"))
        for o in opts:
            if o.get("name") != dec.get("chosen") and not o.get("why_not"):
                out.append(Finding("DEC-2", w,
                                   f"{o.get('name')}: no why_not"))

    for dive in d.section("deep_dives") or []:
        w = f"deep_dive {dive.get('id')}"
        _owner(d, dive, w, out)
        modes = [m for m in dive.get("failure_modes", [])
                 if all(m.get(k) for k in ("detect", "contain", "recover"))]
        if len(modes) < 3:
            out.append(Finding("DIVE-1", w,
                               f"{len(modes)} complete failure modes"))
        _links(d, dive.get("numbers"), w, targets, out)

    for rec in d.section("records") or []:
        w = f"record {rec.get('id')}"
        _owner(d, rec, w, out)
        if not rec.get("reverse_if"):
            out.append(Finding("REC-1", w, "no reversal condition"))
        _links(d, rec.get("evidence"), w, targets, out)

    gaps = d.section("gaps") or {}
    for g in GAPS:
        ans = gaps.get(g, {})
        if not ans.get("answer"):
            out.append(Finding(f"GAP-{g}", f"gap {g}", "no answer"))
            continue
        _owner(d, ans, f"gap {g}", out)
        _links(d, ans.get("evidence"), f"gap {g}", targets, out)

    out += lint_diagram(d.section("diagram") or {})
    return out


def lint_diagram(dia: dict) -> list[Finding]:
    out: list[Finding] = []
    nodes = {n.get("id"): n for n in dia.get("nodes", [])}
    edges = dia.get("edges", [])
    for nid, n in nodes.items():
        if n.get("kind") not in NODE_KINDS:
            out.append(Finding("GRM-3", f"node {nid}",
                               f"kind {n.get('kind')} not in grammar"))
        if n.get("plane") not in PLANES:
            out.append(Finding("GRM-3", f"node {nid}",
                               f"plane {n.get('plane')} not in grammar"))
    for e in edges:
        w = f"edge {e.get('from')}>{e.get('to')}"
        if e.get("kind") not in EDGE_KINDS:
            out.append(Finding("GRM-3", w, f"kind {e.get('kind')}"))
        if e.get("from") not in nodes or e.get("to") not in nodes:
            out.append(Finding("GRM-3", w, "unknown endpoint"))
        if not e.get("label"):
            out.append(Finding("GRM-3", w, "no label"))
    actors = {e["from"] for e in edges if e.get("kind") == "effect"}
    for a in sorted(actors):
        gated = any(e.get("to") == a and e.get("kind") == "control"
                    and nodes.get(e.get("from"), {}).get("kind") == "gate"
                    for e in edges)
        if not gated:
            out.append(Finding("GRM-1", f"node {a}",
                               "acts with no gate before it"))
    written = {e.get("to") for e in edges if e.get("from") in actors
               and e.get("kind") in ("data", "effect", "trail")}
    for nid, n in nodes.items():
        if n.get("kind") != "verifier":
            continue
        if nid in actors:
            out.append(Finding("GRM-2", f"node {nid}", "verifier acted"))
        reads = {e.get("from") for e in edges if e.get("to") == nid
                 and e.get("kind") == "data"}
        for src in sorted(reads & written):
            out.append(Finding("GRM-2", f"node {nid}",
                               f"reads {src}, which the actor writes"))
    return out


# A checklist item cannot pass when the artifact it reads is missing.
NEEDS = {"G1": "gaps", "G2": "gaps", "G3": "gaps", "G4": "gaps",
         "G5": "gaps", "M1": "estimate", "M3": "decisions",
         "M4": "records", "M5": "records", "M7": "diagram"}


def checklist(findings: list[Finding]) -> list[tuple]:
    """The review checklist: (item, area, question, passed, count)."""
    missing = {f.where for f in findings if f.rule == "ART-1"}
    rows = []
    for item, area, question, rules in CHECKLIST:
        n = sum(1 for f in findings if f.rule in rules)
        n += NEEDS.get(item) in missing
        rows.append((item, area, question, n == 0, n))
    return rows


def formula_names(d: Design) -> dict[str, list[str]]:
    return {ln["name"]: names_in(ln["formula"]) for ln in d.lines
            if "formula" in ln}
