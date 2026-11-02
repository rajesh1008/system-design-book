"""designlab.effects: idempotency keys, the effect ledger and sagas (Ch 7).

The control plane mints one key per permitted effect before the first
attempt (`keys`). The executor writes every attempt to the effect ledger
(`ledger`) and resolves an unknown outcome by the tool's contract
(`execute`): replay the key, look the request up, or hand it to a
person. Multi-step changes run as sagas ordered by reversibility
(`saga`). `replay` and `check` measure the result against the
suppliers' own records. No live API is used.
"""
from .keys import EffectKey, KeyIssuer, KeyRefused
from .ledger import Ledger, LedgerConflict, StaleLease
from .execute import Executor

__all__ = ["EffectKey", "KeyIssuer", "KeyRefused", "Ledger",
           "LedgerConflict", "StaleLease", "Executor"]
