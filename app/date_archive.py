"""Build year/month archive navigation data."""

from __future__ import annotations

from collections import Counter, defaultdict

from app.parsers.base import PostMeta
from app.timestamp_parse import month_label, parse_timestamp


def build_archive_index(posts: list[PostMeta]) -> dict[int, Counter[int]]:
    archive: dict[int, Counter[int]] = defaultdict(Counter)
    for post in posts:
        parsed = parse_timestamp(post.timestamp)
        if not parsed:
            continue
        year, month, _ = parsed
        archive[year][month] += 1
    return dict(archive)


def sorted_years(archive: dict[int, Counter[int]]) -> list[int]:
    return sorted(archive.keys(), reverse=True)


def sorted_months(year_counts: Counter[int]) -> list[tuple[int, int]]:
    return sorted(
        ((month, count) for month, count in year_counts.items()),
        key=lambda item: item[0],
        reverse=True,
    )


def archive_heading(year: int, month: int | None = None) -> str:
    if month is None:
        return str(year)
    return month_label(year, month)
