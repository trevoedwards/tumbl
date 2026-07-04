"""Detect and normalize quote posts in legacy HTML and tumblr-utils exports."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup, NavigableString, Tag

if TYPE_CHECKING:
    from collections.abc import Iterable

IMG_TAG_RE = re.compile(r"<img\b", re.I)
VIDEO_TAG_RE = re.compile(r"<(?:video|iframe)\b", re.I)
AUDIO_TAG_RE = re.compile(r"<(?:audio|embed)[^>]*>", re.I)
VIDEO_EMBED_RE = re.compile(r"""<embed[^>]+type=["']video/""", re.I)
AUDIO_EMBED_RE = re.compile(r"""<embed[^>]+type=["']audio/""", re.I)
ATTRIBUTION_RE = re.compile(
    r"(?:—|&mdash;|--|\(via\b|via\s)",
    re.IGNORECASE,
)
LEADING_DASH_RE = re.compile(r"^(?:\s|—|–|-|&mdash;)+", re.IGNORECASE)
VIA_WRAPPER_RE = re.compile(r"^\s*\(?\s*via\s+", re.IGNORECASE)

QUOTE_ARTICLE_CLASSES = frozenset({"quote", "liked-quote"})
SKIP_TAGS = frozenset({"br", "hr"})


def _article_is_quote_type(article: Tag | None) -> bool:
    if article is None:
        return False
    if article.get("data-type") == "quote":
        return True
    classes = article.get("class", [])
    if isinstance(classes, str):
        classes = classes.split()
    return any(token in QUOTE_ARTICLE_CLASSES for token in classes)


def _has_media(soup: BeautifulSoup) -> bool:
    html = str(soup)
    if IMG_TAG_RE.search(html):
        return True
    if VIDEO_TAG_RE.search(html) or VIDEO_EMBED_RE.search(html):
        return True
    if AUDIO_TAG_RE.search(html) or AUDIO_EMBED_RE.search(html):
        return True
    return False


def _is_link_post(soup: BeautifulSoup) -> bool:
    for child in _substantive_children(soup):
        if isinstance(child, Tag) and child.name == "h2":
            link = child.find("a", href=True)
            return link is not None
        break
    return False


def _substantive_children(parent: Tag) -> Iterable[Tag | NavigableString]:
    for child in parent.children:
        if isinstance(child, NavigableString):
            if child.strip():
                yield child
        elif isinstance(child, Tag):
            if child.name in SKIP_TAGS:
                continue
            yield child


def _top_level_blockquotes(soup: BeautifulSoup) -> list[Tag]:
    blockquotes: list[Tag] = []
    for child in _substantive_children(soup):
        if isinstance(child, Tag) and child.name == "blockquote":
            if child.find_parent(class_="caption") is None:
                blockquotes.append(child)
    return blockquotes


def _caption_attribution(caption: Tag) -> bool:
    caption_html = caption.decode_contents()
    if ATTRIBUTION_RE.search(caption_html):
        return True
    if caption.find("a", class_="tumblr_blog"):
        return True
    return False


def _has_quotes_tag(tags: list[str] | None) -> bool:
    if not tags:
        return False
    return any(tag.strip().casefold() == "quotes" for tag in tags)


def _matches_blockquote_pattern(soup: BeautifulSoup) -> bool:
    blockquotes = _top_level_blockquotes(soup)
    if len(blockquotes) != 1:
        return False
    first = next(iter(_substantive_children(soup)), None)
    return first is blockquotes[0]


def _matches_plain_caption_pattern(soup: BeautifulSoup) -> bool:
    if soup.find("blockquote"):
        return False
    captions = [
        child
        for child in _substantive_children(soup)
        if isinstance(child, Tag) and "caption" in (child.get("class") or [])
    ]
    if len(captions) != 1:
        return False
    caption = captions[0]
    if caption.find("blockquote"):
        return False
    before_caption: list[str] = []
    for child in _substantive_children(soup):
        if child is caption:
            break
        if isinstance(child, NavigableString):
            before_caption.append(str(child).strip())
        elif isinstance(child, Tag):
            before_caption.append(child.decode_contents().strip())
    if not any(part for part in before_caption):
        return False
    return _caption_attribution(caption)


def infer_is_quote(
    soup: BeautifulSoup,
    *,
    body_html: str,
    article: Tag | None = None,
    is_submission: bool = False,
    reblog_parent_url: str | None = None,
    tags: list[str] | None = None,
) -> bool:
    """Return True when legacy/tumblr-utils HTML looks like a native quote post."""
    if is_submission or reblog_parent_url:
        return False

    if _article_is_quote_type(article):
        return True

    body_soup = BeautifulSoup(body_html, "lxml")
    content_root = body_soup.find("body") or body_soup

    if _has_media(content_root):
        return False
    if _is_link_post(content_root):
        return False

    if _matches_blockquote_pattern(content_root):
        return True
    if _matches_plain_caption_pattern(content_root):
        return True

    if _has_quotes_tag(tags):
        if _top_level_blockquotes(content_root):
            return True
        captions = content_root.find_all("div", class_="caption")
        if len(captions) == 1 and _caption_attribution(captions[0]):
            return True

    return False


def _clean_source_html(source_html: str) -> str:
    cleaned = source_html.strip()
    cleaned = LEADING_DASH_RE.sub("", cleaned)
    cleaned = VIA_WRAPPER_RE.sub("", cleaned)
    if cleaned.endswith(")"):
        cleaned = cleaned.rstrip(")").strip()
    return cleaned.strip()


def _format_quote(quote_html: str, source_html: str | None = None) -> str:
    parts = [f'<blockquote class="quote-text">{quote_html.strip()}</blockquote>']
    if source_html and source_html.strip():
        source = _clean_source_html(source_html)
        if source:
            parts.append(f'<cite class="quote-source">— {source}</cite>')
    return "\n".join(parts)


def _normalize_from_article(article: Tag) -> str:
    soup = BeautifulSoup(str(article), "lxml")
    article_copy = soup.find("article") or soup
    for tag_name in ("header", "footer"):
        for node in article_copy.find_all(tag_name):
            node.decompose()

    blockquote = article_copy.find("blockquote")
    if blockquote is None:
        return article_copy.decode_contents().strip()

    quote_html = blockquote.decode_contents()
    blockquote.decompose()

    source_html = ""
    for child in _substantive_children(article_copy):
        if isinstance(child, Tag) and child.name in {"p", "cite"}:
            source_html = child.decode_contents()
            break

    return _format_quote(quote_html, source_html or None)


def _normalize_legacy_blockquote(soup: BeautifulSoup) -> str:
    content_root = soup.find("body") or soup
    blockquotes = _top_level_blockquotes(content_root)
    if not blockquotes:
        return content_root.decode_contents().strip()

    blockquote = blockquotes[0]
    quote_html = blockquote.decode_contents()
    blockquote.decompose()

    source_html = ""
    for child in _substantive_children(content_root):
        if isinstance(child, Tag):
            if child.name in {"p", "cite"}:
                source_html = child.decode_contents()
                child.decompose()
                break
            if "caption" in (child.get("class") or []):
                source_html = child.decode_contents()
                child.decompose()
                break

    return _format_quote(quote_html, source_html or None)


def _normalize_legacy_plain_caption(soup: BeautifulSoup) -> str:
    content_root = soup.find("body") or soup
    caption = next(
        child
        for child in _substantive_children(content_root)
        if isinstance(child, Tag) and "caption" in (child.get("class") or [])
    )

    quote_parts: list[str] = []
    for child in _substantive_children(content_root):
        if child is caption:
            break
        if isinstance(child, NavigableString):
            text = str(child).strip()
            if text:
                quote_parts.append(text)
        elif isinstance(child, Tag):
            quote_parts.append(child.decode_contents())

    source_html = caption.decode_contents()
    return _format_quote("".join(quote_parts), source_html)


def normalize_quote_html(
    body_html: str,
    *,
    article: Tag | None = None,
) -> str:
    """Rewrite legacy quote HTML to modern quote-text / quote-source markup."""
    if article is not None and _article_is_quote_type(article):
        return _normalize_from_article(article)

    soup = BeautifulSoup(body_html, "lxml")
    content_root = soup.find("body") or soup

    if _matches_plain_caption_pattern(content_root):
        return _normalize_legacy_plain_caption(soup)
    return _normalize_legacy_blockquote(soup)
