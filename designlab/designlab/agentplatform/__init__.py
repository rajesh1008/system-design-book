"""Chapter 40: the agent platform.

The control plane Lakeshore built for one servicing agent, extracted
so that more than one agent use case can run on it: identity, the
gateway, the registry, the policy engine, the evaluation gate, the
trace, and the trail stay shared; prompts, retrieval, tools, and the
business result stay with the team that owns the use case. A use case
arrives as a manifest, is checked against a template, goes through
one review, and must pass six conformance tests before it is live.

Reuses gateway, policy, identity, evals, and trace without forking
them. The package is named agentplatform because a package named
platform would shadow the standard library's. Offline, no model call
and no key. Lakeshore figures are illustrative.
"""
