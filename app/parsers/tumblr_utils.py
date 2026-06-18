"""Parser for tumblr-utils / tumblr-backup exports."""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from bs4 import BeautifulSoup

from app.parsers.base import PostMeta, PostType, sort_posts
from app.post_metadata import merge_metadata
from app.parsers.legacy_html import (
    IMG_TAG_RE,
    _infer_post_type,
    _process_body_html,
)

logger = logging.getLogger(__name__)

MEDIA_PATH_RE = re.compile(r"(?:\.\./)?media/")
TAGGED_LINK_RE = re.compile(r"/tagged/[^\"']+", re.I)


def _rewrite_media_paths(content: str) -> str:
    return MEDIA_PATH_RE.sub("/media/", content)


def parse_post_file(path: Path, archive_root: Path) -> PostMeta | None:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None

    soup = BeautifulSoup(raw, "lxml")
    article = soup.find("article")
    footer = soup.find("footer")

    if article:
        raw_body = article.decode_contents()
    else:
        body = soup.find("body")
        if not body:
            return None
        raw_body = body.decode_contents()

    timestamp = ""
    tags: list[str] = []

    if footer:
        time_el = footer.find("time")
        if time_el:
            timestamp = time_el.get_text(strip=True)
        if not timestamp:
            ts_el = footer.find("span", id="timestamp")
            if ts_el:
                timestamp = ts_el.get_text(strip=True)
        for tag_el in footer.find_all("span", class_="tag"):
            tags.append(tag_el.get_text(strip=True))
        for link in footer.find_all("a", href=TAGGED_LINK_RE):
            label = link.get_text(strip=True).lstrip("#")
            if label and label not in tags:
                tags.append(label)
        footer.decompose()

    body_html = _process_body_html(_rewrite_media_paths(raw_body))
    if not body_html.strip():
        return None

    post_type: PostType = _infer_post_type(body_html)
    if not IMG_TAG_RE.search(body_html) and article and article.get("data-type") == "photo":
        post_type = "photo"

    tumblr_url, reblog_parent_url, reblog_parent_name = merge_metadata(body_html=body_html)

    return PostMeta(
        id=path.stem,
        body_html=body_html,
        timestamp=timestamp,
        tags=tags,
        post_type=post_type,
        is_submission=False,
        tumblr_url=tumblr_url,
        reblog_parent_url=reblog_parent_url,
        reblog_parent_name=reblog_parent_name,
    )


def discover_post_files(archive_root: Path) -> list[Path]:
    posts_dir = archive_root / "posts"
    if not posts_dir.is_dir():
        return []
    return sorted(path for path in posts_dir.glob("*.html") if path.is_file())


def build_index(
    archive_root: Path,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[PostMeta]:
    paths = discover_post_files(archive_root)
    total = len(paths)
    worker_count = max(1, min(4, int(os.environ.get("INDEX_WORKERS", "4"))))
    logger.info(
        "Building tumblr-utils index for %s posts using %s workers",
        total,
        worker_count,
    )

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
    logger.info("tumblr-utils index complete: %s posts", len(posts))
    return posts
