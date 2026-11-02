"""designlab.knowops: operating the knowledge plane (Chapter 24).

Retrieval and memory are inputs that age. This package holds the
freshness contract for every source the agent reads, the weekly
fresh-sample evaluation that catches retrieval drift the golden set
cannot see, expiry and supersession for memories, and the destination
verifier that compares an outcome with the record of fact rather than
with the proposal. It reuses designlab.memory, designlab.context, and
designlab.retrieval; it forks none of them. Offline, seeded, standard
library only.
"""
from .freshness import CONTRACTS, Contract, check, contract_for
from .expiry import RETENTION_V2, ttl_for, review_legacy
from .verify import pnr_reconciler, destination_verifier

__all__ = ["CONTRACTS", "Contract", "check", "contract_for",
           "RETENTION_V2", "ttl_for", "review_legacy",
           "pnr_reconciler", "destination_verifier"]
