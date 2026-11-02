"""The scoreboard row at baseline: every value with who measured it."""
from __future__ import annotations

from corpus.ops import AS_OF, PILOT_INCIDENTS
from .autonomy import autonomy_share
from .cost import decompose
from .errors import refund_error
from .volume import count_changes


def baseline_row(t: dict) -> list[tuple[str, str, str]]:
    v = count_changes(t)
    c = decompose(t)
    e = refund_error(t)
    a = autonomy_share(t["ops_changes"])
    perm = sum(1 for x in t["ops_refunds"] if x.get("permission_id"))
    return [
        ("As of", AS_OF.strftime("%b %d, %Y"), "Daniel Price"),
        ("Changes a year", f"{v['changes'] / 1e6:.1f}M", "Marcus Bell"),
        ("Changes a month", f"{v['changes'] / 12e3:.0f}k", "Marcus Bell"),
        ("Agent", f"{a['agent']:.0%}", "Ben Carter"),
        ("Assisted", f"{a['assisted']:.0%}", "Ben Carter"),
        ("Self-service", f"{a['self-service']:.0%}", "Marcus Bell"),
        ("Person", f"{a['person']:.0%}", "Marcus Bell"),
        ("Cost per change", f"${c['blended']:.2f}", "Sarah Whitfield"),
        ("Annual handling", f"${c['annual_usd'] / 1e6:.1f}M",
         "Sarah Whitfield"),
        ("Refund error", f"{e['matured_rate']:.1%}", "Rachel Morgan"),
        ("Permission records", f"{perm}", "Owen Fletcher"),
        ("Pilot incidents (2024)", f"{len(PILOT_INCIDENTS)}", "Ben Carter"),
        ("Unauthorized actions", "0", "Owen Fletcher"),
        ("Incidents (program year)", "0", "Ben Carter"),
        ("Cost per verified outcome", "n/a", "Sarah Whitfield"),
        ("Verified-outcome rate", "n/a", "Marcus Bell"),
        ("Duplicates", "n/a", "Rachel Morgan"),
        ("p95 task latency", "n/a", "Ben Carter"),
        ("Use cases", "1", "Daniel Price"),
    ]
