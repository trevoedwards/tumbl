"""Facade for detecting archive format and building the post index."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path

from app.archive_detect import (
    ArchiveDetectionError,
    ArchiveFormat,
    archive_fingerprint,
    cache_filename_for_format,
    cache_meta_filename_for_format,
    detect_archive_format,
)
from app.archive_prepare import prepare_archive
from app.html_sanitize import sanitize_post_html
from app.parsers.base import PostMeta
from app.parsers.legacy_html import build_index as build_legacy_index
from app.parsers.modern_xml import build_index as build_modern_index
from app.parsers.tumblr_utils import build_index as build_tumblr_utils_index

logger = logging.getLogger(__name__)

CACHE_SCHEMA_VERSION = 5

_BUILDERS = {
    ArchiveFormat.LEGACY_HTML: build_legacy_index,
    ArchiveFormat.MODERN_XML: build_modern_index,
    ArchiveFormat.TUMBLR_UTILS: build_tumblr_utils_index,
}


def _get_builder(fmt: ArchiveFormat):
    builder = _BUILDERS.get(fmt)
    if builder is None:
        raise ArchiveDetectionError(
            f"Archive format '{fmt.value}' is recognized but not yet supported."
        )
    return builder


def _sanitize_posts(posts: list[PostMeta]) -> list[PostMeta]:
    for post in posts:
        post.body_html = sanitize_post_html(post.body_html)
    return posts


def cache_path(cache_root: Path, fmt: ArchiveFormat) -> Path:
    return cache_root / cache_filename_for_format(fmt)


def cache_meta_path(cache_root: Path, fmt: ArchiveFormat) -> Path:
    return cache_root / cache_meta_filename_for_format(fmt)


def load_cached_index(
    cache_root: Path,
    fmt: ArchiveFormat,
    archive_root: Path,
) -> list[PostMeta] | None:
    path = cache_path(cache_root, fmt)
    meta_path = cache_meta_path(cache_root, fmt)
    if not path.is_file() or not meta_path.is_file():
        return None

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        expected = archive_fingerprint(archive_root, fmt)
        if meta.get("fingerprint") != expected:
            logger.info(
                "Index cache fingerprint mismatch (cached=%s, current=%s); rebuilding",
                meta.get("fingerprint"),
                expected,
            )
            return None
        if meta.get("schema_version", 1) != CACHE_SCHEMA_VERSION:
            logger.info("Index cache schema mismatch; rebuilding")
            return None

        data = json.loads(path.read_text(encoding="utf-8"))
        posts = [PostMeta.from_dict(item) for item in data]
        return _sanitize_posts(posts)
    except (OSError, json.JSONDecodeError, TypeError, KeyError):
        return None


def save_index_cache(
    cache_root: Path,
    fmt: ArchiveFormat,
    posts: list[PostMeta],
    archive_root: Path,
) -> None:
    cache_root.mkdir(parents=True, exist_ok=True)
    path = cache_path(cache_root, fmt)
    meta_path = cache_meta_path(cache_root, fmt)
    temp_path = path.with_suffix(".json.tmp")
    temp_meta_path = meta_path.with_suffix(".meta.json.tmp")
    payload = [post.to_dict() for post in posts]
    temp_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    temp_meta_path.write_text(
        json.dumps(
            {
                "fingerprint": archive_fingerprint(archive_root, fmt),
                "schema_version": CACHE_SCHEMA_VERSION,
            }
        ),
        encoding="utf-8",
    )
    temp_path.replace(path)
    temp_meta_path.replace(meta_path)
    logger.info("Wrote index cache to %s", path)


def build_index(
    archive_root: Path,
    fmt: ArchiveFormat,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[PostMeta]:
    builder = _get_builder(fmt)
    return builder(archive_root, on_progress=on_progress)


def get_or_build_index(
    archive_root: Path,
    cache_root: Path | None = None,
    force_rebuild: bool = False,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[PostMeta]:
    prepare_archive(archive_root)
    writable_cache = cache_root or archive_root
    fmt = detect_archive_format(archive_root)
    logger.info("Detected archive format: %s", fmt.value)

    if not force_rebuild:
        cached = load_cached_index(writable_cache, fmt, archive_root)
        if cached is not None:
            logger.info("Loaded %s posts from cache", len(cached))
            if on_progress:
                on_progress(len(cached), len(cached))
            return cached

    posts = build_index(archive_root, fmt, on_progress=on_progress)
    _sanitize_posts(posts)
    save_index_cache(writable_cache, fmt, posts, archive_root)
    return posts
