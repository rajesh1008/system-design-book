"""The design method (Chapter 5): eight artifacts and one linter.

    artifacts.py  the eight artifacts, the question bank, the checklist,
                  the deep-dive steps and the forty-five-minute clock
    design.py     load a design (TOML) and compute its estimate sheet
    lint.py       the linter: assumptions, owners, alternatives,
                  reversal conditions, evidence links, diagram grammar
    designs/      the October 6 demo, the v0 design and v0.1
    demo.py       python3 -m method.demo

Standard library only. No model calls: a design is checked as data.
"""
from .artifacts import ARTIFACTS, CHECKLIST, CLOCK, QUESTIONS
from .design import Design, load
from .lint import Finding, checklist, lint

__all__ = ["ARTIFACTS", "CHECKLIST", "CLOCK", "QUESTIONS", "Design",
           "load", "Finding", "checklist", "lint"]
