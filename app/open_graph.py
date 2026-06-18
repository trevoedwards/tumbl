"""Open Graph / social preview helpers for permalink pages."""

from __future__ import annotations

import re
from collections.abc import Callable

from app.parsers.base import PostMeta
from app.post_filters import strip_html
from app.security import is_safe_http_url

IMG_SRC_RE = re.compile(r"""<img[^>]+src=["']([^"']+)["']""", re.IGNORECASE)
MAX_DESCRIPTION_LENGTH = 200


def preview_image_src(post: PostMeta) -> str | None:
    """Return the first image src from post HTML, if any."""
    match = IMG_SRC_RE.search(post.body_html)
    if not match:
        return None
    src = match.group(1).strip()
    return src or None


def preview_image_url(
    post: PostMeta,
    *,
    absolute_media_url: Callable[[str], str],
) -> str | None:
    """Resolve a shareable absolute URL for the post preview image."""
    src = preview_image_src(post)
    if not src:
        return None
    if src.startswith("/media/"):
        filename = src.removeprefix("/media/").lstrip("/")
        if filename and "/" not in filename and ".." not in filename:
            return absolute_media_url(filename)
        return None
    if is_safe_http_url(src):
        return src
    return None


def preview_description(post: PostMeta, *, max_length: int = MAX_DESCRIPTION_LENGTH) -> str:
    """Plain-text excerpt for og:description and twitter:description."""
    parts = [strip_html(post.body_html)]
    if post.tags:
        parts.append(" ".join(f"#{tag}" for tag in post.tags))
    text = " ".join(part for part in parts if part).strip()
    if not text and post.timestamp:
        text = post.timestamp
    if len(text) <= max_length:
        return text
    truncated = text[: max_length - 3].rstrip()
    return f"{truncated}..."
