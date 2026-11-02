"""Change and release for the servicing agent (Chapter 39).

A release is a bundle of the six things that change what the agent
does: prompts, models, tools, the harness manifest, the policy bundle,
and the memory schema. The bundle is hashed, recorded in the trail, and
exposed in stages: the gate, shadow, a fixed-horizon test where effects
are reversible, and a canary by task type. Rollback moves the whole
bundle back and handles the runs in flight. Offline only.
"""
