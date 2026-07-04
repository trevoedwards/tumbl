"""Persist user-edited post tags outside the original archive."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.parsers.base import PostMeta
from app.security import is_valid_tag

logger = logging.getLogger(__name__)

OVERRIDES_FILENAME = "tag-overrides.json"


def overrides_path(cache_root: Path) -> Path:
    return cache_root / OVERRIDES_FILENAME


def normalize_tags(raw: list[str]) -> list[str]:
    """Trim, strip leading #, dedupe case-insensitively, drop invalid tags."""
    seen: set[str] = set()
    normalized: list[str] = []
    for item in raw:
        tag = item.strip().lstrip("#")
        if not tag:
            continue
        key = tag.casefold()
        if key in seen:
            continue
        if not is_valid_tag(tag):
            continue
        seen.add(key)
        normalized.append(tag)
    return normalized


def validate_and_normalize_tags(raw: object) -> tuple[list[str] | None, str | None]:
    """Validate API tag input. Returns (tags, error_message)."""
    if not isinstance(raw, list):
        return None, "tags must be a list"
    seen: set[str] = set()
    normalized: list[str] = []
    for item in raw:
        tag = str(item).strip().lstrip("#")
        if not tag:
            continue
        if not is_valid_tag(tag):
            return None, f"Invalid tag: {tag}"
        key = tag.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(tag)
    return normalized, None


def load_tag_overrides(cache_root: Path) -> dict[str, list[str]]:
    path = overrides_path(cache_root)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        logger.warning("Could not read tag overrides from %s", path)
        return {}
    if not isinstance(data, dict):
        return {}
    overrides: dict[str, list[str]] = {}
    for post_id, tags in data.items():
        if not isinstance(post_id, str) or not isinstance(tags, list):
            continue
        overrides[post_id] = normalize_tags([str(tag) for tag in tags])
    return overrides


def save_tag_overrides(cache_root: Path, overrides: dict[str, list[str]]) -> None:
    cache_root.mkdir(parents=True, exist_ok=True)
    path = overrides_path(cache_root)
    temp_path = path.with_suffix(".json.tmp")
    payload = {post_id: tags for post_id, tags in sorted(overrides.items())}
    temp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp_path.replace(path)
    logger.info("Wrote tag overrides to %s", path)


def apply_tag_overrides(
    posts: list[PostMeta],
    overrides: dict[str, list[str]],
) -> list[PostMeta]:
    if not overrides:
        return posts
    for post in posts:
        if post.id in overrides:
            post.tags = list(overrides[post.id])
    return posts
