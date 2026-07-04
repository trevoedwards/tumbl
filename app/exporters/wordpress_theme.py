"""Fetch typography and color tokens from a target WordPress site."""

from __future__ import annotations

import logging
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.security import is_safe_http_url

logger = logging.getLogger(__name__)

MAX_RESPONSE_BYTES = 2 * 1024 * 1024
FETCH_TIMEOUT = 10

CSS_VAR_FONT_RE = re.compile(
    r"--wp--preset--font-family--[^:]+:\s*([^;}{]+)",
    re.IGNORECASE,
)
CSS_VAR_CONTRAST_RE = re.compile(
    r"--wp--preset--color--contrast:\s*([^;}{]+)",
    re.IGNORECASE,
)
CSS_VAR_LINK_RE = re.compile(
    r"--wp--preset--color--(?:link|primary):\s*([^;}{]+)",
    re.IGNORECASE,
)
BODY_FONT_RE = re.compile(
    r"body\s*\{[^}]*font-family:\s*([^;}{]+)",
    re.IGNORECASE | re.DOTALL,
)
BODY_COLOR_RE = re.compile(
    r"body\s*\{[^}]*\bcolor:\s*([^;}{]+)",
    re.IGNORECASE | re.DOTALL,
)
ANCHOR_COLOR_RE = re.compile(
    r"a\s*:link\s*\{[^}]*\bcolor:\s*([^;}{]+)",
    re.IGNORECASE | re.DOTALL,
)
BLOCKQUOTE_BORDER_RE = re.compile(
    r"blockquote\s*\{[^}]*border-left(?:-color)?:\s*([^;}{]+)",
    re.IGNORECASE | re.DOTALL,
)


@dataclass
class ThemeStyles:
    font_family: str | None = None
    text_color: str | None = None
    link_color: str | None = None
    blockquote_color: str | None = None
    caption_color: str | None = None
    font_import_url: str | None = None


def _same_host(url: str, site_url: str) -> bool:
    return urlparse(url).netloc.lower() == urlparse(site_url).netloc.lower()


def _fetch_url(url: str, *, site_url: str) -> str | None:
    if not is_safe_http_url(url) or not _same_host(url, site_url):
        return None
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "tumbl-wordpress-export/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT) as response:
            data = response.read(MAX_RESPONSE_BYTES + 1)
            if len(data) > MAX_RESPONSE_BYTES:
                logger.warning("Theme fetch truncated (>%s bytes): %s", MAX_RESPONSE_BYTES, url)
                data = data[:MAX_RESPONSE_BYTES]
            charset = response.headers.get_content_charset() or "utf-8"
            return data.decode(charset, errors="replace")
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        logger.warning("Theme fetch failed for %s: %s", url, exc)
        return None


def _clean_css_value(value: str) -> str:
    cleaned = value.strip().strip('"').strip("'")
    if cleaned.startswith("var("):
        inner = cleaned[4:-1].strip()
        if inner.startswith("--"):
            return inner
    return cleaned


def _first_match(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    if not match:
        return None
    value = _clean_css_value(match.group(1))
    return value or None


def _resolve_css_variables(css: str) -> ThemeStyles:
    font = _first_match(CSS_VAR_FONT_RE, css)
    text_color = _first_match(CSS_VAR_CONTRAST_RE, css)
    link_color = _first_match(CSS_VAR_LINK_RE, css)

    if not font:
        font = _first_match(BODY_FONT_RE, css)
    if not text_color:
        text_color = _first_match(BODY_COLOR_RE, css)
    if not link_color:
        link_color = _first_match(ANCHOR_COLOR_RE, css)

    blockquote_color = _first_match(BLOCKQUOTE_BORDER_RE, css)
    caption_color = text_color

    return ThemeStyles(
        font_family=font,
        text_color=text_color,
        link_color=link_color,
        blockquote_color=blockquote_color,
        caption_color=caption_color,
    )


def _extract_font_import(soup: BeautifulSoup) -> str | None:
    for link in soup.find_all("link", rel=lambda value: value and "stylesheet" in value):
        href = (link.get("href") or "").strip()
        if "fonts.googleapis.com" in href and is_safe_http_url(href):
            return href
    return None


def _collect_stylesheet_urls(soup: BeautifulSoup, page_url: str, site_url: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for link in soup.find_all("link", rel=lambda value: value and "stylesheet" in value):
        href = (link.get("href") or "").strip()
        if not href:
            continue
        absolute = urljoin(page_url, href)
        if not is_safe_http_url(absolute) or not _same_host(absolute, site_url):
            continue
        if absolute not in seen:
            seen.add(absolute)
            urls.append(absolute)
    return urls[:5]


def fetch_theme_styles(site_url: str) -> ThemeStyles | None:
    """Return color and font tokens from the target WordPress site homepage."""
    site_url = site_url.strip().rstrip("/")
    if not is_safe_http_url(site_url):
        return None

    homepage = _fetch_url(site_url, site_url=site_url)
    if not homepage:
        return None

    soup = BeautifulSoup(homepage, "lxml")
    combined_css = ""

    inline_global = soup.find("style", id="global-styles-inline-css")
    if inline_global and inline_global.string:
        combined_css += inline_global.string

    for sheet_url in _collect_stylesheet_urls(soup, site_url, site_url):
        sheet_css = _fetch_url(sheet_url, site_url=site_url)
        if sheet_css:
            combined_css += "\n" + sheet_css

    if not combined_css.strip():
        return None

    styles = _resolve_css_variables(combined_css)
    styles.font_import_url = _extract_font_import(soup)

    if not any((styles.font_family, styles.text_color, styles.link_color)):
        return None
    return styles


def build_theme_css(styles: ThemeStyles) -> str:
    """Build a compact stylesheet scoped to imported archive posts."""
    lines: list[str] = []
    if styles.font_import_url:
        lines.append(f"@import url({styles.font_import_url});")
        lines.append("")

    lines.append(".tumblr-archive-post {")
    if styles.font_family:
        lines.append(f"  font-family: {styles.font_family};")
    if styles.text_color:
        lines.append(f"  color: {styles.text_color};")
    lines.append("  max-width: 100%;")
    lines.append("}")
    lines.append("")

    if styles.link_color:
        lines.extend(
            [
                ".tumblr-archive-post a {",
                f"  color: {styles.link_color};",
                "}",
                "",
            ]
        )

    if styles.blockquote_color:
        lines.extend(
            [
                ".tumblr-archive-post blockquote {",
                f"  border-left-color: {styles.blockquote_color};",
                "}",
                "",
            ]
        )

    if styles.caption_color:
        lines.extend(
            [
                ".tumblr-archive-post .caption {",
                f"  color: {styles.caption_color};",
                "  opacity: 0.85;",
                "}",
                "",
            ]
        )

    lines.extend(
        [
            ".tumblr-archive-post img,",
            ".tumblr-archive-post video {",
            "  max-width: 100%;",
            "  height: auto;",
            "}",
        ]
    )
    return "\n".join(lines)
