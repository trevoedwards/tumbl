"""Parser for legacy Tumblr HTML backup exports (.tumblrbackup layout)."""

from __future__ import annotations

import html
import logging
import os
import re
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from bs4 import BeautifulSoup

from app.parsers.base import PostMeta, PostType, sort_posts
from app.post_metadata import merge_metadata

logger = logging.getLogger(__name__)

AUDIO_EMBED_RE = re.compile(
    r'<embed\s+type=["\']audio/mpeg["\']\s+src=["\']([^"\']+)["\']\s*/?>',
    re.IGNORECASE,
)
VIDEO_EMBED_RE = re.compile(
    r'<embed\s+type=["\']video/[^"\']+["\']\s+src=["\']([^"\']+)["\']\s*/?>',
    re.IGNORECASE,
)
STRAY_EMBED_SUFFIX_RE = re.compile(r"</embed>['\"];?", re.IGNORECASE)
MEDIA_PATH_RE = re.compile(r"\.\./\.\./media/")
YOUTUBE_IFRAME_RE = re.compile(r"""id=["']youtube_iframe["']""", re.I)
VIDEO_EMBED_TYPE_RE = re.compile(r"""<embed[^>]+type=["']video/""", re.I)
AUDIO_EMBED_TYPE_RE = re.compile(r"""<embed[^>]+type=["']audio/""", re.I)
IMG_TAG_RE = re.compile(r"<img\b", re.I)


def _infer_post_type(content: str) -> PostType:
    if YOUTUBE_IFRAME_RE.search(content):
        return "video"
    if VIDEO_EMBED_TYPE_RE.search(content):
        return "video"
    if AUDIO_EMBED_TYPE_RE.search(content) or "<audio" in content:
        return "audio"
    if IMG_TAG_RE.search(content):
        return "photo"
    return "text"


def _needs_unescape(content: str) -> bool:
    return "&lt;" in content or "&quot;" in content or "&#" in content


def _process_body_html(raw_html: str) -> str:
    content = raw_html.strip()
    if not content:
        return ""

    if _needs_unescape(content):
        content = html.unescape(content)

    content = STRAY_EMBED_SUFFIX_RE.sub("</embed>", content)
    content = MEDIA_PATH_RE.sub("/media/", content)

    def _audio_replacer(match: re.Match[str]) -> str:
        src = html.escape(match.group(1), quote=True)
        return f'<audio controls preload="metadata" src="{src}"></audio>'

    content = AUDIO_EMBED_RE.sub(_audio_replacer, content)

    def _video_replacer(match: re.Match[str]) -> str:
        src = html.escape(match.group(1), quote=True)
        return (
            f'<div class="video-embed">'
            f'<video controls preload="metadata" src="{src}"></video>'
            f"</div>"
        )

    content = VIDEO_EMBED_RE.sub(_video_replacer, content)
    return content


def parse_post_file(path: Path, archive_root: Path) -> PostMeta | None:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None

    soup = BeautifulSoup(raw, "lxml")
    body = soup.find("body")
    if not body:
        return None

    footer = body.find("div", id="footer")
    timestamp = ""
    tags: list[str] = []

    if footer:
        ts_el = footer.find("span", id="timestamp")
        if ts_el:
            timestamp = ts_el.get_text(strip=True)
        tags = [tag.get_text(strip=True) for tag in footer.find_all("span", class_="tag")]
        footer.decompose()

    raw_body = body.decode_contents()
    body_html = _process_body_html(raw_body)
    post_type = _infer_post_type(body_html)

    post_id = path.stem
    submissions_dir = archive_root / "posts" / "html" / "submissions"
    is_submission = submissions_dir in path.parents or path.parent == submissions_dir

    tumblr_url, reblog_parent_url, reblog_parent_name = merge_metadata(body_html=body_html)

    return PostMeta(
        id=post_id,
        body_html=body_html,
        timestamp=timestamp,
        tags=tags,
        post_type=post_type,
        is_submission=is_submission,
        tumblr_url=tumblr_url,
        reblog_parent_url=reblog_parent_url,
        reblog_parent_name=reblog_parent_name,
    )


def discover_post_files(archive_root: Path) -> list[Path]:
    posts_html = archive_root / "posts" / "html"
    files: list[Path] = []

    if not posts_html.is_dir():
        return files

    for path in sorted(posts_html.glob("*.html")):
        files.append(path)

    submissions_dir = posts_html / "submissions"
    if submissions_dir.is_dir():
        for path in sorted(submissions_dir.glob("*.html")):
            files.append(path)

    return files


def build_index(
    archive_root: Path,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[PostMeta]:
    paths = discover_post_files(archive_root)
    total = len(paths)
    worker_count = max(1, min(4, int(os.environ.get("INDEX_WORKERS", "4"))))
    logger.info("Building legacy HTML index for %s posts using %s workers", total, worker_count)

    if on_progress:
        on_progress(0, total)

    posts: list[PostMeta] = []
    completed = 0

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = {
            executor.submit(parse_post_file, path, archive_root): path for path in paths
        }
        for future in as_completed(futures):
            post = future.result()
            if post:
                posts.append(post)
            completed += 1
            if on_progress and (completed % 100 == 0 or completed == total):
                on_progress(completed, total)
            if completed % 500 == 0 or completed == total:
                logger.info("Indexed %s/%s posts", completed, total)

    sort_posts(posts)
    logger.info("Legacy HTML index complete: %s posts", len(posts))
    return posts
