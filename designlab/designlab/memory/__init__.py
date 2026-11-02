"""designlab.memory: memory as governed state (Chapter 22).

A memory is a record the agent wrote about a customer, kept so a later
task can read it. The store refuses a write that cannot say where the
memory came from, what it applies to, and how sure anyone is of it. It
takes the tenant from the session token, never from the draft. A new
value supersedes the old one by compare-and-set on the head, and the
old version stays readable as history. Deletion follows derived_from
links. A memory is evidence for a person or a proposal; it is never
grounds for a permission. Offline, seeded, standard library only.
"""
from .record import Draft, MemoryRecord, Source, SCOPES, KINDS
from .store import (MemoryStore, SessionToken, WriteRefused, StaleHead,
                    OlderThanHead)
from .policy import READ_POLICY, can_read, authorize, grounds_problems
from .forget import forget, naive_forget, restore
from .audit import audit_legacy
from .render import to_items

__all__ = ["Draft", "MemoryRecord", "Source", "SCOPES", "KINDS",
           "MemoryStore", "SessionToken", "WriteRefused", "StaleHead",
           "OlderThanHead", "READ_POLICY", "can_read", "authorize",
           "grounds_problems", "forget",
           "naive_forget", "restore", "audit_legacy", "to_items"]
