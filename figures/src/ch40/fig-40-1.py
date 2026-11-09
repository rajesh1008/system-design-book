"""Figure 40.1  Platform or project, and maturity by evidence-chain coverage.

Reading order: one row per question, top to bottom; how the project's
control plane answered it on Monday, August 10, 2026, and how the
platform answered it on Monday, August 31. The last row is the
maturity reading: a level counts what is built, coverage counts what
can be proved. From agentplatform.plane and agentplatform.chain
(Lakeshore figures are illustrative).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "04-code" / "designlab"))
sys.path.insert(0, str(HERE))
import figlib as fl  # noqa: E402
from _table import table  # noqa: E402

rows = (("Callers", "Written in code", "From manifests"),
        ("Policy", "Servicing's rules", "Rules per use case"),
        ("Run token", "One trip", "Use case's resource"),
        ("Golden sets", "One", "One each"),
        ("Maturity", "A level", "Coverage, 2 of 3"))
fig = table(rows, ("Question", "Project, Aug 10", "Platform, Aug 31"),
            (0.0, 1.25, 3.0), toks=["ops"] * 4 + ["org"])
fl.save(fig)
