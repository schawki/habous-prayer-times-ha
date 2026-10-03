"""Small time utilities, with no Home Assistant dependency (so testable on their own)."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone, tzinfo

_OFFSET_RE = re.compile(r"^([+-])(\d{2}):(\d{2})$")


def tz_from_offset(utc_offset: str | None) -> tzinfo | None:
    """\"+00:00\" / \"-01:00\" -> fixed timezone; None if missing or invalid."""
    if not utc_offset or not (m := _OFFSET_RE.match(utc_offset)):
        return None
    delta = timedelta(hours=int(m.group(2)), minutes=int(m.group(3)))
    return timezone(-delta if m.group(1) == "-" else delta)


def diff_minutes(repository: datetime, calculated: datetime) -> int:
    """Gap \"calculated − repository\" in whole minutes."""
    return round((calculated - repository).total_seconds() / 60)
