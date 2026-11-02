"""Chapter 26: the tool gateway, its registry, code mode and tool search.

Every tool call passes one gateway or it does not happen. The gateway
authenticates the caller, finds the tool in the registry, checks the
description the server serves against the hash that was reviewed,
checks the caller's scope and the arguments, asks the policy hook
about effects, applies a rate limit, and writes one trail line for
every call, allowed or refused.

Reuses common.trail, common.clock, common.text, toolargs.schema,
toolargs.layer.digest, harness.tools (the fourteen tools) and
isolation.egress. No model call except in live.py.
"""
