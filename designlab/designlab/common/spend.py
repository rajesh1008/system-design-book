"""The spend meter: every live call is priced, and a run stops at its cap.

The cap is checked before a call, with the worst case for that call
(prompt estimate plus max_tokens), so the meter never learns about an
overrun after paying for it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CAP_USD = 2.00


class SpendCapExceeded(RuntimeError):
    pass


@dataclass
class SpendMeter:
    cap_usd: float = DEFAULT_CAP_USD
    ledger_path: Path | None = None
    spent_usd: float = 0.0
    calls: int = 0
    entries: list[dict] = field(default_factory=list)

    @staticmethod
    def price(pin, input_tokens: int, output_tokens: int,
              cache_read: int = 0, cache_write: int = 0) -> float:
        per = 1_000_000
        return (input_tokens * pin.input_usd_per_mtok
                + cache_write * pin.input_usd_per_mtok * 1.25
                + cache_read * pin.cache_read_usd_per_mtok
                + output_tokens * pin.output_usd_per_mtok) / per

    def check(self, pin, prompt_chars: int, max_tokens: int) -> float:
        """Raise before the call if its worst case would pass the cap."""
        worst = self.price(pin, prompt_chars // 2 + 16, max_tokens)
        if self.spent_usd + worst > self.cap_usd:
            raise SpendCapExceeded(
                f"cap ${self.cap_usd:.4f}, spent ${self.spent_usd:.4f}, "
                f"call up to ${worst:.4f}")
        return worst

    def record(self, pin, usage: dict) -> float:
        cost = self.price(pin, usage.get("input_tokens", 0),
                          usage.get("output_tokens", 0),
                          usage.get("cache_read_input_tokens", 0) or 0,
                          usage.get("cache_creation_input_tokens", 0) or 0)
        self.spent_usd += cost
        self.calls += 1
        entry = {"model": pin.id, "input_tokens": usage.get("input_tokens"),
                 "output_tokens": usage.get("output_tokens"),
                 "cost_usd": round(cost, 8)}
        self.entries.append(entry)
        if self.ledger_path is not None:
            self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
            with self.ledger_path.open("a") as f:
                f.write(json.dumps(entry, sort_keys=True) + "\n")
        return cost
