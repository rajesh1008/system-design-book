"""designlab.designs: worked architectures as checkable designs (Ch 43).

A worked design is written once, as a compact spec in data/*.toml,
and expanded by templates.py into the eight artifacts that Chapter 5's
method linter reads. lint.py runs that linter and then the rules a
worked design adds on top: an independent verifier for every effect,
a permission tier no wider than the limit allows, a person wherever a
rule reserves the decision for one, the six states a customer sees,
obligations enforced outside the prompt, and an economics block.

The package is built to grow. registry.register() adds a design and
lint.register_rule() adds a rule; Chapter 45 uses both for six
internal designs and the loop properties. Offline, deterministic, no
model call and no key. Every organization here is an illustrative
composite; Lakeshore figures are illustrative.
"""
from .lint import RULES, Finding, lint, register_rule
from .registry import DESIGNS, get, load_spec, register
from .templates import STATES, TIERS, derived_tier, expand

__all__ = ["RULES", "Finding", "lint", "register_rule", "DESIGNS",
           "get", "load_spec", "register", "STATES", "TIERS",
           "derived_tier", "expand"]
