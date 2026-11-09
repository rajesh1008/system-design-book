"""designlab.org: the team, its decision rights and its rhythm (Ch 41).

Seats and partners (roles.py), the skills-to-planes gap analysis
(skills.py), the decision-rights matrix and the scenario checker
(rights.py), the operating rhythm (rhythm.py), and the team card
(card.py). Offline, deterministic, no model call and no key.
Lakeshore figures are illustrative.
"""
from .rights import (MATRICES, SCENARIOS, Decision, Finding, Scenario,
                     check, check_all)
from .roles import PARTNERS, SEATS, Person, Seat, seated
from .skills import PLANES, SKILLS, coverage, gaps

__all__ = ["MATRICES", "SCENARIOS", "Decision", "Finding", "Scenario",
           "check", "check_all", "PARTNERS", "SEATS", "Person", "Seat",
           "seated", "PLANES", "SKILLS", "coverage", "gaps"]
