"""Generate WordPress WXR (Extended RSS) import files from Tumblr archive posts."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

from app.parsers.base import PostMeta
from app.timestamp_parse import MONTHS, parse_timestamp

WXR_VERSION = "1.2"
WXR_NS = {
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "excerpt": f"http://wordpress.org/export/{WXR_VERSION}/excerpt/",
    "wp": f"http://wordpress.org/export/{WXR_VERSION}/",
    "wfw": "http://wellformedweb.org/CommentAPI/",
}

MEDIA_SRC_RE = re.compile(
    r"""(?:src|poster)=(["'])(/media/([^"']+))\1""",
    re.IGNORECASE,
)
FULL_TIMESTAMP_RE = re.compile(
    r"(?i)^\s*"
    r"(?P<month>[A-Za-z]+)\s+"
    r"(?P<day>\d{1,2})(?:st|nd|rd|th)?,\s+"
    r"(?P<year>\d{4})"
    r"(?:\s+(?P<hour>\d{1,2}):(?P<minute>\d{2})\s*(?P<ampm>am|pm))?"
    r"\s*$"
)
SLUG_SAFE_RE = re.compile(r"[^a-z0-9\-]+")
ATTACHMENT_ID_BASE = 900_000_000


def slugify(value: str) -> str:
    """Return a URL-safe slug for WordPress nicename fields."""
    slug = value.strip().lower().replace(" ", "-")
    slug = SLUG_SAFE_RE.sub("-", slug)
    return slug.strip("-") or "tag"


def post_slug(post_id: str) -> str:
    return f"tumblr-{post_id}"


def _register_namespaces() -> None:
    ET.register_namespace("content", WXR_NS["content"])
    ET.register_namespace("dc", WXR_NS["dc"])
    ET.register_namespace("excerpt", WXR_NS["excerpt"])
    ET.register_namespace("wp", WXR_NS["wp"])
    ET.register_namespace("wfw", WXR_NS["wfw"])


def _wp_el(parent: ET.Element, tag: str, text: str = "") -> ET.Element:
    element = ET.SubElement(parent, f"{{{WXR_NS['wp']}}}{tag}")
    if text:
        element.text = text
    return element


def _cdata_element(parent: ET.Element, tag: str, namespace: str, text: str) -> ET.Element:
    element = ET.SubElement(parent, f"{{{namespace}}}{tag}")
    element.text = text
    return element


def parse_post_datetime(timestamp: str) -> tuple[str, str]:
    """Return (post_date, post_date_gmt) in WordPress ``Y-m-d H:i:s`` format."""
    match = FULL_TIMESTAMP_RE.match(timestamp.strip())
    if match:
        month_key = match.group("month").lower()
        month = MONTHS.get(month_key)
        if month:
            year = int(match.group("year"))
            day = int(match.group("day"))
            hour = 12
            minute = 0
            if match.group("hour"):
                hour = int(match.group("hour"))
                minute = int(match.group("minute"))
                ampm = (match.group("ampm") or "").lower()
                if ampm == "pm" and hour < 12:
                    hour += 12
                elif ampm == "am" and hour == 12:
                    hour = 0
            try:
                dt = datetime(year, month, day, hour, minute, 0, tzinfo=timezone.utc)
            except ValueError:
                pass
            else:
                formatted = dt.strftime("%Y-%m-%d %H:%M:%S")
                return formatted, formatted

    parsed = parse_timestamp(timestamp)
    if parsed:
        year, month, day = parsed
        dt = datetime(year, month, day, 12, 0, 0, tzinfo=timezone.utc)
        formatted = dt.strftime("%Y-%m-%d %H:%M:%S")
        return formatted, formatted

    fallback = "1970-01-01 12:00:00"
    return fallback, fallback


def _attached_file_path(filename: str, post_date: str) -> str:
    try:
        dt = datetime.strptime(post_date, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return filename
    return f"{dt.year:04d}/{dt.month:02d}/{filename}"


def rewrite_media_urls(body_html: str, media_base_url: str) -> str:
    """Rewrite ``/media/...`` references to absolute URLs under ``media_base_url``."""
    base = media_base_url.rstrip("/")

    def _replace(match: re.Match[str]) -> str:
        attr_prefix = match.group(0).split("=")[0]
        quote = match.group(1)
        filename = match.group(3)
        return f"{attr_prefix}={quote}{base}/{filename}{quote}"

    return MEDIA_SRC_RE.sub(_replace, body_html)


def extract_media_filenames(body_html: str) -> list[str]:
    """Return unique ``/media/`` filenames referenced in post HTML."""
    seen: set[str] = set()
    ordered: list[str] = []
    for match in MEDIA_SRC_RE.finditer(body_html):
        filename = match.group(3)
        if filename not in seen:
            seen.add(filename)
            ordered.append(filename)
    return ordered


def _post_title(post: PostMeta) -> str:
    if post.timestamp:
        return post.timestamp
    return f"Tumblr post {post.id}"


def _post_link(site_url: str, slug: str) -> str:
    return f"{site_url.rstrip('/')}/{slug}/"


def _add_post_meta(parent: ET.Element, key: str, value: str) -> None:
    meta = _wp_el(parent, "postmeta")
    _wp_el(meta, "meta_key", key)
    _wp_el(meta, "meta_value", value)


def _add_tag_categories(item: ET.Element, tags: list[str]) -> None:
    for tag in tags:
        category = ET.SubElement(item, "category")
        category.set("domain", "post_tag")
        category.set("nicename", slugify(tag))
        category.text = tag


def _add_post_item(
    channel: ET.Element,
    post: PostMeta,
    *,
    site_url: str,
    author: str,
    body_html: str,
) -> None:
    slug = post_slug(post.id)
    post_date, post_date_gmt = parse_post_datetime(post.timestamp)
    title = _post_title(post)
    link = _post_link(site_url, slug)

    item = ET.SubElement(channel, "item")
    ET.SubElement(item, "title").text = title
    ET.SubElement(item, "link").text = link
    _cdata_element(item, "creator", WXR_NS["dc"], author)
    ET.SubElement(item, "pubDate").text = post_date
    ET.SubElement(item, "guid", {"isPermaLink": "false"}).text = link
    ET.SubElement(item, "description")
    _cdata_element(item, "encoded", WXR_NS["content"], body_html)
    _cdata_element(item, "encoded", WXR_NS["excerpt"], "")

    try:
        wp_post_id = str(int(post.id))
    except ValueError:
        wp_post_id = post.id

    _wp_el(item, "post_id", wp_post_id)
    _wp_el(item, "post_date", post_date)
    _wp_el(item, "post_date_gmt", post_date_gmt)
    _wp_el(item, "comment_status", "closed")
    _wp_el(item, "ping_status", "closed")
    _wp_el(item, "post_name", slug)
    _wp_el(item, "status", "publish")
    _wp_el(item, "post_parent", "0")
    _wp_el(item, "menu_order", "0")
    _wp_el(item, "post_type", "post")
    _wp_el(item, "post_password", "")
    _wp_el(item, "is_sticky", "0")

    _add_tag_categories(item, post.tags)

    if post.tumblr_url:
        _add_post_meta(item, "_tumblr_source_url", post.tumblr_url)
    if post.reblog_parent_url:
        _add_post_meta(item, "_tumblr_reblog_parent_url", post.reblog_parent_url)
    if post.reblog_parent_name:
        _add_post_meta(item, "_tumblr_reblog_parent_name", post.reblog_parent_name)
    _add_post_meta(item, "_tumblr_post_type", post.post_type)
    if post.is_submission:
        _add_post_meta(item, "_tumblr_is_submission", "1")


def _add_attachment_item(
    channel: ET.Element,
    *,
    attachment_id: int,
    parent_post_id: str,
    filename: str,
    attachment_url: str,
    author: str,
    post_date: str,
    post_date_gmt: str,
) -> None:
    slug = slugify(_path_stem(filename))
    item = ET.SubElement(channel, "item")
    ET.SubElement(item, "title").text = filename
    ET.SubElement(item, "link").text = attachment_url
    _cdata_element(item, "creator", WXR_NS["dc"], author)
    ET.SubElement(item, "pubDate").text = post_date
    ET.SubElement(item, "guid", {"isPermaLink": "false"}).text = attachment_url
    ET.SubElement(item, "description")

    _wp_el(item, "post_id", str(attachment_id))
    _wp_el(item, "post_date", post_date)
    _wp_el(item, "post_date_gmt", post_date_gmt)
    _wp_el(item, "comment_status", "closed")
    _wp_el(item, "ping_status", "closed")
    _wp_el(item, "post_name", slug)
    _wp_el(item, "status", "inherit")
    _wp_el(item, "post_parent", parent_post_id)
    _wp_el(item, "menu_order", "0")
    _wp_el(item, "post_type", "attachment")
    _wp_el(item, "post_password", "")
    _wp_el(item, "is_sticky", "0")
    _wp_el(item, "attachment_url", attachment_url)

    meta = _wp_el(item, "postmeta")
    _wp_el(meta, "meta_key", "_wp_attached_file")
    _wp_el(meta, "meta_value", _attached_file_path(filename, post_date))


def _path_stem(filename: str) -> str:
    """Return filename without extension for slug generation."""
    if "." in filename:
        return filename.rsplit(".", 1)[0]
    return filename


def generate_wxr(
    posts: list[PostMeta],
    *,
    site_url: str,
    author: str,
    blog_title: str,
    media_base_url: str | None = None,
) -> str:
    """Build a WXR document string from normalized Tumblr posts."""
    _register_namespaces()

    rss = ET.Element(
        "rss",
        {
            "version": "2.0",
            f"xmlns:content": WXR_NS["content"],
            f"xmlns:dc": WXR_NS["dc"],
            f"xmlns:excerpt": WXR_NS["excerpt"],
            f"xmlns:wp": WXR_NS["wp"],
            f"xmlns:wfw": WXR_NS["wfw"],
        },
    )
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = blog_title
    ET.SubElement(channel, "link").text = site_url.rstrip("/")
    ET.SubElement(channel, "description").text = f"Tumblr archive export for {blog_title}"
    ET.SubElement(channel, "language").text = "en-US"
    _wp_el(channel, "wxr_version", WXR_VERSION)
    _wp_el(channel, "base_site_url", site_url.rstrip("/"))
    _wp_el(channel, "base_blog_url", site_url.rstrip("/"))

    author_block = _wp_el(channel, "author")
    _wp_el(author_block, "author_id", "1")
    _wp_el(author_block, "author_login", author)
    _wp_el(author_block, "author_email", f"{author}@example.com")
    _wp_el(author_block, "author_display_name", author)
    _wp_el(author_block, "author_first_name", "")
    _wp_el(author_block, "author_last_name", "")

    ET.SubElement(channel, "generator").text = "https://github.com/trevoedwards/tumbl"

    media_base = media_base_url.rstrip("/") if media_base_url else None
    attachment_counter = ATTACHMENT_ID_BASE

    for post in posts:
        body_html = post.body_html
        if media_base:
            body_html = rewrite_media_urls(body_html, media_base)

        _add_post_item(
            channel,
            post,
            site_url=site_url,
            author=author,
            body_html=body_html,
        )

        if not media_base:
            continue

        post_date, post_date_gmt = parse_post_datetime(post.timestamp)
        try:
            parent_post_id = str(int(post.id))
        except ValueError:
            parent_post_id = post.id

        for filename in extract_media_filenames(post.body_html):
            attachment_counter += 1
            attachment_url = f"{media_base}/{filename}"
            _add_attachment_item(
                channel,
                attachment_id=attachment_counter,
                parent_post_id=parent_post_id,
                filename=filename,
                attachment_url=attachment_url,
                author=author,
                post_date=post_date,
                post_date_gmt=post_date_gmt,
            )

    return ET.tostring(rss, encoding="unicode", xml_declaration=True)
