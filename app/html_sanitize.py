"""Sanitize post HTML before rendering to prevent stored XSS."""

from __future__ import annotations

import re

import bleach

ALLOWED_TAGS = frozenset(
    {
        "a",
        "abbr",
        "audio",
        "b",
        "blockquote",
        "br",
        "code",
        "div",
        "em",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "hr",
        "i",
        "iframe",
        "img",
        "li",
        "ol",
        "p",
        "pre",
        "source",
        "span",
        "strong",
        "u",
        "ul",
        "video",
    }
)

ALLOWED_ATTRIBUTES: dict[str, list[str]] = {
    "*": ["class", "id"],
    "a": ["href", "title", "rel", "target"],
    "img": ["src", "alt", "title", "width", "height", "loading", "decoding"],
    "iframe": ["src", "width", "height", "frameborder", "allowfullscreen", "title"],
    "video": ["src", "controls", "preload", "width", "height", "poster"],
    "audio": ["src", "controls", "preload"],
    "source": ["src", "type"],
}

ALLOWED_PROTOCOLS = frozenset({"http", "https", "mailto"})

IMG_TAG_OPEN_RE = re.compile(r"<img\b", re.IGNORECASE)


def add_lazy_media_attrs(html: str) -> str:
    """Add lazy-loading hints to images in post bodies."""

    def _replacer(match: re.Match[str]) -> str:
        tag = match.group(0)
        if re.search(r"\bloading\s*=", tag, re.I):
            return tag
        return re.sub(r"<img\b", '<img loading="lazy" decoding="async"', tag, count=1, flags=re.I)

    return IMG_TAG_OPEN_RE.sub(_replacer, html)


def sanitize_post_html(html: str) -> str:
    """Strip scripts, event handlers, and dangerous URLs from archive HTML."""
    if not html:
        return ""
    cleaned = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    return add_lazy_media_attrs(cleaned)
