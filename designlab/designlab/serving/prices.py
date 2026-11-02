"""API token prices for the serving lab.

Per-token prices come from common/models.toml (verified November 2,
2026). The cache-write multipliers are the provider's published ones
on the same date (prompt-caching documentation, accessed 2026-11-02):
a write with the default 5-minute lifetime costs 1.25 times base input,
a 1-hour write 2 times; a read costs what models.toml says.

Lakeshore's own bill uses its contract's illustrative prices, the ones
Chapter 10 quoted: $3.00 per million input tokens and $15.00 per
million output, with the provider's read multiplier of 0.1.
"""
from __future__ import annotations

from dataclasses import dataclass

from common import pin

WRITE_5M = 1.25
WRITE_1H = 2.0
READ = 0.1


@dataclass(frozen=True)
class Price:
    input_usd_per_mtok: float
    output_usd_per_mtok: float
    cache_read_usd_per_mtok: float


CONTRACT = Price(3.00, 15.00, 3.00 * READ)


def price(role: str) -> Price:
    if role == "contract":
        return CONTRACT
    p = pin(role)
    return Price(p.input_usd_per_mtok, p.output_usd_per_mtok,
                 p.cache_read_usd_per_mtok)


@dataclass(frozen=True)
class Bill:
    uncached: int = 0
    written: int = 0         # at the 5-minute write price
    read: int = 0
    output: int = 0
    written_1h: int = 0      # at the 1-hour write price

    def __add__(self, o: "Bill") -> "Bill":
        return Bill(self.uncached + o.uncached, self.written + o.written,
                    self.read + o.read, self.output + o.output,
                    self.written_1h + o.written_1h)

    @property
    def input_tokens(self) -> int:
        return self.uncached + self.written + self.written_1h + self.read

    def usd(self, role: str = "contract") -> float:
        p = price(role)
        return (self.uncached * p.input_usd_per_mtok
                + self.written * p.input_usd_per_mtok * WRITE_5M
                + self.written_1h * p.input_usd_per_mtok * WRITE_1H
                + self.read * p.cache_read_usd_per_mtok
                + self.output * p.output_usd_per_mtok) / 1e6

    def hit_rate(self) -> float:
        return self.read / self.input_tokens if self.input_tokens else 0.0
