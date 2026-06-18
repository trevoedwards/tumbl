"""Extract Tumblr URLs and reblog context from archive post data."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from app.security import is_safe_http_url

TUMBLR_POST_HREF_RE = re.compile(
    r"""href=["'](https?://[^"']*tumblr\.com/post/[^"']+)["']""",
    re.IGNORECASE,
)
TUMBLR_POST_URL_RE = re.compile(
    r"https?://[^/\s\"']+\.tumblr\.com/post/[\w\-]+/\d+",
    re.IGNORECASE,
)
TUMBLR_POST_ID_RE = re.compile(r"/post/(?:[\w-]+/)?(\d+)")
REBLOG_HEADER_RE = re.compile(
    r"(?:reblogged from|posted by|via)\s+(?:<a[^>]*>)?([^<]+)",
    re.IGNORECASE,
)
BLOG_NAME_FROM_URL_RE = re.compile(r"https?://([^.]+)\.tumblr\.com/", re.IGNORECASE)


def local_post_id_from_url(url: str) -> str | None:
    match = TUMBLR_POST_ID_RE.search(url)
    return match.group(1) if match else None


def blog_name_from_url(url: str) -> str | None:
    match = BLOG_NAME_FROM_URL_RE.search(url)
    return match.group(1) if match else None


def _first_safe_tumblr_post_url(*candidates: str | None) -> str | None:
    for candidate in candidates:
        if not candidate:
            continue
        candidate = candidate.strip()
        if is_safe_http_url(candidate) and "tumblr.com/post/" in candidate:
            return candidate
    return None


def extract_from_body_html(body_html: str) -> tuple[str | None, str | None, str | None]:
    """Return (tumblr_url, reblog_parent_url, reblog_parent_name) from post HTML."""
    tumblr_url: str | None = None
    reblog_parent_url: str | None = None
    reblog_parent_name: str | None = None

    hrefs = TUMBLR_POST_HREF_RE.findall(body_html)
    safe_hrefs = [href for href in hrefs if is_safe_http_url(href)]
    header = REBLOG_HEADER_RE.search(body_html)

    if header and safe_hrefs:
        reblog_parent_url = safe_hrefs[0]
        reblog_parent_name = header.group(1).strip()
        if len(safe_hrefs) > 1:
            tumblr_url = safe_hrefs[1]
    elif safe_hrefs:
        tumblr_url = safe_hrefs[0]

    if reblog_parent_url and not reblog_parent_name:
        reblog_parent_name = blog_name_from_url(reblog_parent_url)

    return tumblr_url, reblog_parent_url, reblog_parent_name


def extract_from_xml_post(post_el: ET.Element) -> tuple[str | None, str | None, str | None]:
    tumblr_url = _first_safe_tumblr_post_url(post_el.get("url"))
    reblog_parent_url: str | None = None
    reblog_parent_name: str | None = None

    for tag in ("reblog-parent", "parent-post-url", "reblogged-from-url"):
        child = post_el.find(tag)
        if child is not None and child.text:
            reblog_parent_url = _first_safe_tumblr_post_url(child.text.strip())
            if reblog_parent_url:
                break

    for tag in ("reblogged-from-name", "reblog-parent-title", "parent-blog-name"):
        child = post_el.find(tag)
        if child is not None and child.text:
            reblog_parent_name = child.text.strip()
            break

    if reblog_parent_url and not reblog_parent_name:
        reblog_parent_name = blog_name_from_url(reblog_parent_url)

    return tumblr_url, reblog_parent_url, reblog_parent_name


def merge_metadata(
    *,
    tumblr_url: str | None = None,
    reblog_parent_url: str | None = None,
    reblog_parent_name: str | None = None,
    body_html: str = "",
) -> tuple[str | None, str | None, str | None]:
    body_url, body_parent_url, body_parent_name = extract_from_body_html(body_html)
    merged_url = tumblr_url or body_url
    merged_parent_url = reblog_parent_url or body_parent_url
    merged_parent_name = reblog_parent_name or body_parent_name
    if merged_parent_url and not merged_parent_name:
        merged_parent_name = blog_name_from_url(merged_parent_url)
    return merged_url, merged_parent_url, merged_parent_name
