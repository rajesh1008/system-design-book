"""designlab.planes: the four planes and their contracts (Chapter 6).

The action plane runs the loop and the tools behind one gateway. The
control plane holds permission, policy, identity, and budgets outside the
loop. The knowledge plane returns facts with a source and an age. The
trail plane writes every decision and effect and verifies outcomes with
something that did not act. `autonomy.toml` sets how much each task type
hands over. Offline, seeded, standard library only.
"""
from .world import World, Bypass
from .knowledge import KnowledgePlane, Fact, ContextPacket, NotFound
from .control import ControlPlane, Decision
from .action import Gateway, AgentLoop, Outcome
from .trailplane import TrailPlane
from .autonomy import AutonomyTable, load_autonomy, check_autonomy
from .contracts import load_contracts, check_contracts
from .paths import wiring, unmediated_paths, probe_tools

__all__ = ["World", "Bypass", "KnowledgePlane", "Fact", "ContextPacket",
           "NotFound", "ControlPlane", "Decision", "Gateway", "AgentLoop",
           "Outcome", "TrailPlane", "AutonomyTable", "load_autonomy",
           "check_autonomy", "load_contracts", "check_contracts", "wiring",
           "unmediated_paths", "probe_tools"]
