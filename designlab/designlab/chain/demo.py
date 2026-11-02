"""Replay Thursday's refund four ways, then 1,000 refunds two ways (Chapter 2 lab).

Run from 04-code/designlab:  python3 -m chain.demo
"""
from __future__ import annotations

import random

from .loop import ACTOR, PaymentProcessor, ChainLoop, Trail, mint_key, naive_refund
from .record import ChainRecord, Permission, Proposal, Refused

ITINERARY, AMOUNT = "LTG-4471902", 412.60


def proposal(itinerary: str = ITINERARY, amount: float = AMOUNT) -> Proposal:
    return Proposal("refund", itinerary, amount, "flight canceled by carrier")


def permission(pid: str = "PRM-20931") -> Permission:
    return Permission(pid, granted_by="policy-engine", policy_version="refunds-v3",
                      max_amount_usd=1500.00)


def full_record(itinerary: str = ITINERARY, amount: float = AMOUNT,
                pid: str = "PRM-20931") -> ChainRecord:
    rec = ChainRecord(proposal=proposal(itinerary, amount), permission=permission(pid))
    rec.idempotency_key = mint_key(rec)
    return rec


def thursday() -> None:
    print(f"Thursday replay: {ITINERARY}, refund ${AMOUNT:.2f}")

    net = PaymentProcessor(slow_calls={1})
    naive_refund(net, ITINERARY, AMOUNT)
    print(f"  pilot loop     credits={len(net.settled(ITINERARY))}  permission=none")

    net = PaymentProcessor(slow_calls={1})
    try:
        ChainLoop(net, Trail()).execute(ChainRecord(proposal=proposal()))
    except Refused as exc:
        print(f"  proposal only  credits={len(net.settled(ITINERARY))}  {exc}")

    net = PaymentProcessor(slow_calls={1})
    rec = ChainLoop(net, Trail()).execute(full_record())
    print(f"  full record    credits={len(net.settled(ITINERARY))}"
          f"  attempts={len(rec.notes) + 1}  by={rec.verification['verified_by']}")

    net = PaymentProcessor(slow_calls={1})
    self_check = lambda n, r: {"verified_by": ACTOR, "credits_found": 1, "ok": True}
    try:
        ChainLoop(net, Trail(), verifier=self_check).execute(full_record())
    except Refused as exc:
        print(f"  actor checks   credits={len(net.settled(ITINERARY))}  {exc}")


def batch(n: int = 1000, slow_rate: float = 0.02, seed: int = 7) -> None:
    rng = random.Random(seed)
    slow = {i for i in range(1, 4 * n) if rng.random() < slow_rate}
    naive_net, chain_net = PaymentProcessor(slow_calls=set(slow)), PaymentProcessor(slow_calls=set(slow))
    trail = Trail()
    loop = ChainLoop(chain_net, trail)
    for i in range(n):
        itin, amount = f"LTG-{5000000 + i}", round(rng.uniform(60, 1400), 2)
        naive_refund(naive_net, itin, amount)
        loop.execute(full_record(itin, amount, pid=f"PRM-{30000 + i}"))
    def dupes(net):
        return sum(1 for i in range(n) if len(net.settled(f"LTG-{5000000 + i}")) > 1)
    print(f"\n{n:,} refunds, {slow_rate:.0%} answered after the 8.0 s timeout")
    print(f"  pilot loop  duplicates={dupes(naive_net)}  permissions=0")
    print(f"  chain loop  duplicates={dupes(chain_net)}  permissions={n:,}"
          f"  trail lines={len(trail.lines):,}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--slow-rate", type=float, default=0.02)
    a = ap.parse_args()
    thursday()
    batch(a.n, a.slow_rate, a.seed)
