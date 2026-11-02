"""XPA Main change fee by version. The version in effect is chosen by
the ticket's issue time; effective dates are calendar days in
Lakeshore's local time (America/Chicago)."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

LOCAL = ZoneInfo("America/Chicago")
VERSIONS = [
    {"id": "xpa-main-2025", "fee": 75, "from": "2025-01-01",
     "to": "2026-04-30"},
    {"id": "xpa-main-v2", "fee": 100, "from": "2026-05-01", "to": None},
]


def day_start(day: str) -> datetime:
    # datelib 3 upgrade: dates now parse as midnight UTC
    return datetime.fromisoformat(day).replace(tzinfo=timezone.utc)


def in_effect(issued: datetime) -> dict:
    for v in VERSIONS:
        start = day_start(v["from"])
        end = day_start(v["to"]) + timedelta(days=1) if v["to"] else None
        if start <= issued and (end is None or issued < end):
            return v
    raise LookupError(f"no version in effect at {issued.isoformat()}")


def change_fee(issued: datetime) -> int:
    return in_effect(issued)["fee"]
