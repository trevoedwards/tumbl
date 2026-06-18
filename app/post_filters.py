"""Filter and search helpers for post lists."""

from __future__ import annotations

import re

from app.parsers.base import PostMeta, PostType
from app.timestamp_parse import parse_timestamp

HTML_TAG_RE = re.compile(r"<[^>]+>")
VALID_POST_TYPES: frozenset[PostType] = frozenset({"photo", "audio", "video", "text"})


def strip_html(html: str) -> str:
    return re.sub(r"\s+", " ", HTML_TAG_RE.sub(" ", html)).strip()


def search_text(post: PostMeta) -> str:
    parts = [strip_html(post.body_html), post.timestamp, " ".join(post.tags)]
    return " ".join(part for part in parts if part).lower()


def filter_by_search(posts: list[PostMeta], query: str) -> list[PostMeta]:
    needle = query.strip().lower()
    if not needle:
        return posts
    return [post for post in posts if needle in search_text(post)]


def filter_by_tag(posts: list[PostMeta], tag: str) -> list[PostMeta]:
    if not tag:
        return posts
    return [
        post
        for post in posts
        if any(existing.lower() == tag.lower() for existing in post.tags)
    ]


def is_valid_post_type(post_type: str) -> bool:
    return post_type in VALID_POST_TYPES


def filter_by_type(posts: list[PostMeta], post_type: str) -> list[PostMeta]:
    if not is_valid_post_type(post_type):
        return []
    return [post for post in posts if post.post_type == post_type]


def filter_by_date(
    posts: list[PostMeta],
    year: int,
    month: int | None = None,
) -> list[PostMeta]:
    filtered: list[PostMeta] = []
    for post in posts:
        parsed = parse_timestamp(post.timestamp)
        if not parsed:
            continue
        post_year, post_month, _ = parsed
        if post_year != year:
            continue
        if month is not None and post_month != month:
            continue
        filtered.append(post)
    return filtered


def apply_filters(
    posts: list[PostMeta],
    *,
    tag: str | None = None,
    post_type: str | None = None,
    search: str | None = None,
    year: int | None = None,
    month: int | None = None,
) -> list[PostMeta]:
    result = posts
    if search:
        result = filter_by_search(result, search)
    if tag:
        result = filter_by_tag(result, tag)
    if post_type:
        if not is_valid_post_type(post_type):
            return []
        result = filter_by_type(result, post_type)
    if year is not None:
        result = filter_by_date(result, year, month)
    return result
