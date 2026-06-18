"""Sanitize post HTML before rendering to prevent stored XSS."""

from __future__ import annotations

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
    "img": ["src", "alt", "title", "width", "height"],
    "iframe": ["src", "width", "height", "frameborder", "allowfullscreen", "title"],
    "video": ["src", "controls", "preload", "width", "height", "poster"],
    "audio": ["src", "controls", "preload"],
    "source": ["src", "type"],
}

ALLOWED_PROTOCOLS = frozenset({"http", "https", "mailto"})


def sanitize_post_html(html: str) -> str:
    """Strip scripts, event handlers, and dangerous URLs from archive HTML."""
    if not html:
        return ""
    return bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
