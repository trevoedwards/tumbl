"""Parse Tumblr-style timestamp strings into structured dates."""

from __future__ import annotations

import re
from calendar import month_name, month_abbr
from datetime import datetime

MONTHS = {
    name.lower(): index
    for index, name in enumerate(month_name)
    if index
}
MONTHS.update({abbr.lower(): index for index, abbr in enumerate(month_abbr) if index})

TIMESTAMP_RE = re.compile(
    r"(?i)^\s*"
    r"(?P<month>[A-Za-z]+)\s+"
    r"(?P<day>\d{1,2})(?:st|nd|rd|th)?,\s+"
    r"(?P<year>\d{4})\b"
)


def parse_timestamp(timestamp: str) -> tuple[int, int, int] | None:
    """Return (year, month, day) or None if parsing fails."""
    match = TIMESTAMP_RE.match(timestamp.strip())
    if not match:
        return None

    month_key = match.group("month").lower()
    month = MONTHS.get(month_key)
    if not month:
        return None

    year = int(match.group("year"))
    day = int(match.group("day"))
    try:
        datetime(year, month, day)
    except ValueError:
        return None
    return year, month, day


def month_label(year: int, month: int) -> str:
    return f"{month_name[month]} {year}"
