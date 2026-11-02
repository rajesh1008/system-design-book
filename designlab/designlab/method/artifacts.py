"""The eight artifacts of a checkable design, as data.

Every design in this book is written as these eight artifacts, in this
order. The linter (lint.py) checks the ones a machine can check; the
review checklist names what a person still has to read.
"""
from __future__ import annotations

# (key in the design file, artifact name, the question it answers)
ARTIFACTS = [
    ("scope", "Scope Card", "What may it do, and who owns it?"),
    ("requirements", "Question Bank", "What must be true, by plane?"),
    ("estimate", "Estimate Sheet", "How much at the worst hour, and why?"),
    ("diagram", "Diagram", "Where do control, data, evidence flow?"),
    ("decisions", "Decision Table", "Which option, on which criteria?"),
    ("deep_dives", "Deep Dive", "How does the riskiest step fail?"),
    ("records", "Decision Record", "What did we decide; what reverses it?"),
    ("gaps", "Checklist", "Does every gap have an answer and owner?"),
]

PLANES = ("action", "control", "knowledge", "trail")
GROUPS = ("action", "control", "knowledge", "trail", "outcome")

# The requirement question bank for systems that act: id -> question.
QUESTIONS = {
    "A1": "Which effects can the system cause, by name?",
    "A2": "Which effects can be undone, how, and within what time?",
    "A3": "What is the largest single effect one action can cause?",
    "A4": "Which systems does each effect land in, and who owns them?",
    "A5": "What does the far end do with a repeated request?",
    "A6": "Which tools are read-only?",
    "C1": "Who grants permission for each effect; where is it kept?",
    "C2": "Which effects run alone, with a person, or never?",
    "C3": "How long may an approval take; what if nobody answers?",
    "C4": "What stops a run: steps, spend, time or a person?",
    "C5": "Who switches the system off, and how fast?",
    "C6": "Which obligations attach to an effect?",
    "K1": "What must the model know at the decision, and from where?",
    "K2": "How old may a fact be before the system must not act on it?",
    "K3": "Which inputs come from outside and may carry instructions?",
    "K4": "What is remembered across sessions; who corrects it?",
    "T1": "What must be provable about an effect in a year, to whom?",
    "T2": "What is the source of truth that an effect happened?",
    "T3": "Who verifies the effect, and did that component act?",
    "T4": "How long is evidence kept, and who may read it?",
    "O1": "Which business number moves if this works; who owns it?",
    "O2": "What is the volume on an average day and the worst day?",
    "O3": "What does one change cost now, and what may it cost?",
    "O4": "What does failure cost: per wrong effect, per hour down?",
}
GROUP_OF = {"A": "action", "C": "control", "K": "knowledge",
            "T": "trail", "O": "outcome"}

# The first ten, asked in this order when time is short (Section 8).
FIRST_TEN = ["A1", "A2", "A3", "C1", "C2", "C3", "T2", "T3", "O1", "O2"]

# Diagram grammar: node kinds and edge kinds a design may use.
NODE_KINDS = {
    "model": "a model call (navy box)",
    "loop": "the harness that runs the model (navy, rounded)",
    "tool": "a tool or service (teal box)",
    "store": "a store of record (cylinder)",
    "gate": "a permission or policy gate (amber, double border)",
    "verifier": "checks the effect; did not act (green box)",
    "person": "a person or team (gray)",
    "external": "outside the boundary (dashed)",
}
EDGE_KINDS = {
    "control": "who tells whom to act (solid, heavy)",
    "data": "what is read or written (solid, light)",
    "effect": "a change in the world (solid, ends at external)",
    "trail": "evidence written (dotted)",
    "async": "queued, later (dashed)",
}

# The review checklist: item id, gap or method area, question, rules.
CHECKLIST = [
    ("G1", "output to proposal",
     "Is every action a typed proposal?", ("GAP-G1",)),
    ("G2", "proposal to permission",
     "Is permission granted outside the loop?", ("GAP-G2", "GRM-1")),
    ("G3", "permission to execution",
     "Does a retry stay the same request?", ("GAP-G3",)),
    ("G4", "execution to verified outcome",
     "Does something that did not act verify?", ("GAP-G4", "GRM-2")),
    ("G5", "verified outcome to business result",
     "Is the business result counted?", ("GAP-G5",)),
    ("M1", "estimates", "Has every input an assumption and source?",
     ("EST-1", "EST-2")),
    ("M2", "owners", "Has every artifact a named owner?", ("OWN-1",)),
    ("M3", "alternatives", "Has every decision a real alternative?",
     ("DEC-1", "DEC-2")),
    ("M4", "reversal", "Does every record say what reverses it?",
     ("REC-1",)),
    ("M5", "links", "Does every evidence link resolve?", ("LINK-1",)),
    ("M6", "coverage", "Are all eight artifacts and questions there?",
     ("ART-1", "REQ-1", "DIVE-1")),
    ("M7", "grammar", "Does the diagram use only the grammar?",
     ("GRM-3",)),
]

# The deep-dive template, step by step.
DEEP_DIVE_STEPS = [
    "pick the step whose failure costs most",
    "write its contract: inputs, outputs, invariant",
    "list at least three ways it fails",
    "for each: detect, contain, recover",
    "attach the numbers from the estimate sheet",
    "name the owner and the test that proves it",
]

# The decision record, field by field.
RECORD_FIELDS = ["context", "options", "decision", "consequences",
                 "reverse_if", "evidence", "owner", "status"]

# The forty-five-minute clock: (start, end, step).
CLOCK = [
    (0, 5, "Scope Card: effects, autonomy, owner"),
    (5, 12, "Question Bank: the first ten"),
    (12, 18, "Estimate Sheet: assumptions aloud"),
    (18, 26, "Diagram in the grammar"),
    (26, 31, "Decision Table: one real choice"),
    (31, 39, "Deep Dive: the riskiest step"),
    (39, 42, "Decision Record: what reverses it"),
    (42, 45, "Checklist by gap; open items"),
]
