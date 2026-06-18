"""Detect Tumblr backup archive format from directory layout."""

from __future__ import annotations

from enum import Enum
from pathlib import Path


class ArchiveFormat(str, Enum):
    LEGACY_HTML = "legacy_html"
    MODERN_XML = "modern_xml"
    TUMBLR_UTILS = "tumblr_utils"


class ArchiveDetectionError(Exception):
    pass


def _has_legacy_html(legacy_html_dir: Path) -> bool:
    if not legacy_html_dir.is_dir():
        return False
    if any(legacy_html_dir.glob("*.html")):
        return True
    submissions = legacy_html_dir / "submissions"
    return submissions.is_dir() and any(submissions.glob("*.html"))


def detect_archive_format(archive_root: Path) -> ArchiveFormat:
    if not archive_root.is_dir():
        raise ArchiveDetectionError(f"Archive directory not found: {archive_root}")

    posts_xml = archive_root / "posts" / "posts.xml"
    legacy_html_dir = archive_root / "posts" / "html"
    has_modern = posts_xml.is_file()
    has_legacy = _has_legacy_html(legacy_html_dir)

    if has_modern and has_legacy:
        raise ArchiveDetectionError(
            "Detected a hybrid archive with both posts/posts.xml and posts/html/*.html. "
            "tumbl expects one export format per archive. Remove posts/posts.xml to use "
            "the legacy HTML layout, or remove posts/html/ to use the modern XML export."
        )

    if has_modern:
        return ArchiveFormat.MODERN_XML

    if has_legacy:
        return ArchiveFormat.LEGACY_HTML

    posts_dir = archive_root / "posts"
    index_html = archive_root / "index.html"
    if posts_dir.is_dir() and index_html.is_file():
        if any(posts_dir.glob("*.html")):
            return ArchiveFormat.TUMBLR_UTILS

    raise ArchiveDetectionError(
        "Unrecognized archive layout. Expected one of:\n"
        "  - Legacy HTML: posts/html/*.html\n"
        "  - Modern export: posts/posts.xml (extract posts.zip first)\n"
        "  - tumblr-utils: index.html + posts/*.html"
    )


def cache_filename_for_format(fmt: ArchiveFormat) -> str:
    return f"index-{fmt.value}.json"


def cache_meta_filename_for_format(fmt: ArchiveFormat) -> str:
    return f"index-{fmt.value}.meta.json"


def archive_fingerprint(archive_root: Path, fmt: ArchiveFormat) -> str:
    """Return a stable fingerprint used to invalidate stale index caches."""
    if fmt == ArchiveFormat.MODERN_XML:
        posts_xml = archive_root / "posts" / "posts.xml"
        stat = posts_xml.stat()
        media_dir = archive_root / "media"
        media_count = 0
        media_mtime_sum = 0
        if media_dir.is_dir():
            for path in media_dir.iterdir():
                if path.is_file():
                    media_count += 1
                    media_mtime_sum += path.stat().st_mtime_ns
        return f"modern:{stat.st_size}:{stat.st_mtime_ns}:{media_count}:{media_mtime_sum}"

    if fmt == ArchiveFormat.LEGACY_HTML:
        from app.parsers.legacy_html import discover_post_files

        files = discover_post_files(archive_root)
        if not files:
            return "legacy:0:0"
        mtime_sum = sum(path.stat().st_mtime_ns for path in files)
        return f"legacy:{len(files)}:{mtime_sum}"

    if fmt == ArchiveFormat.TUMBLR_UTILS:
        from app.parsers.tumblr_utils import discover_post_files

        files = discover_post_files(archive_root)
        index_html = archive_root / "index.html"
        index_mtime = index_html.stat().st_mtime_ns if index_html.is_file() else 0
        if not files:
            return f"tumblr_utils:0:{index_mtime}"
        mtime_sum = sum(path.stat().st_mtime_ns for path in files)
        return f"tumblr_utils:{len(files)}:{mtime_sum}:{index_mtime}"

    return fmt.value
