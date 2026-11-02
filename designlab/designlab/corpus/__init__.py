"""designlab.corpus: the synthetic Lakeshore Travel Group data (v0).

Seeded and versioned. Extended in Chapters 4, 7, 10, 19, 34 and 44.
Every company, person and record in it is invented; airport codes are
real places only.
"""
from .generate import (ANCHOR, CHANGE_TYPES, SCALES, TABLES, VERSION,
                       generate, manifest, write)

__all__ = ["ANCHOR", "CHANGE_TYPES", "SCALES", "TABLES", "VERSION",
           "generate", "manifest", "write"]
