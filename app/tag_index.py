"""Build tag frequency data for the tag cloud page."""

from __future__ import annotations

from collections import Counter

from app.parsers.base import PostMeta


def build_tag_counts(posts: list[PostMeta]) -> list[tuple[str, int]]:
    counts: Counter[str] = Counter()
    for post in posts:
        for tag in post.tags:
            normalized = tag.strip()
            if normalized:
                counts[normalized] += 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0].lower()))
