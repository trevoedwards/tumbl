"""Parser for modern official Tumblr exports (posts.xml layout)."""

from __future__ import annotations

import html
import logging
import re
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path

from app.media_resolve import build_media_index, find_local_media, media_url
from app.parsers.base import PostMeta, PostType, sort_posts
from app.post_metadata import extract_from_xml_post, merge_metadata

logger = logging.getLogger(__name__)


def _text_content(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return (element.text or "").strip()


def _inner_html(element: ET.Element | None) -> str:
    if element is None:
        return ""
    parts = [element.text or ""]
    for child in element:
        parts.append(ET.tostring(child, encoding="unicode", method="html"))
        parts.append(child.tail or "")
    return "".join(parts).strip()


def _render_photo_post(
    post_el: ET.Element,
    post_id: str,
    media_dir: Path,
    *,
    media_index: dict | None = None,
) -> str:
    parts: list[str] = []
    local_files = find_local_media(media_dir, post_id, media_index=media_index)

    if local_files:
        for media_path in local_files:
            parts.append(f'<img src="{media_url(media_path)}" alt="">')
    else:
        for photo_url in post_el.findall("photo-url"):
            url = (photo_url.text or "").strip()
            if url:
                parts.append(f'<img src="{html.escape(url)}" alt="">')

    caption = _inner_html(post_el.find("photo-caption"))
    if caption:
        parts.append(f'<div class="caption">{caption}</div>')

    return "\n".join(parts)


def _render_regular_post(post_el: ET.Element) -> str:
    title = _text_content(post_el.find("regular-title"))
    body = _inner_html(post_el.find("regular-body"))
    if title:
        return f"<h2>{html.escape(title)}</h2>\n{body}"
    return body


def _render_quote_post(post_el: ET.Element) -> str:
    quote = _inner_html(post_el.find("quote-text"))
    source = _inner_html(post_el.find("quote-source"))
    parts = [f"<blockquote>{quote}</blockquote>"]
    if source:
        parts.append(f'<div class="caption">— {source}</div>')
    return "\n".join(parts)


def _render_link_post(post_el: ET.Element) -> str:
    text = _text_content(post_el.find("link-text"))
    url = _text_content(post_el.find("link-url"))
    if text and url:
        return f'<p><a href="{html.escape(url)}">{html.escape(text)}</a></p>'
    if url:
        return f'<p><a href="{html.escape(url)}">{html.escape(url)}</a></p>'
    return html.escape(text)


def _render_conversation_post(post_el: ET.Element) -> str:
    title = _text_content(post_el.find("conversation-title"))
    text = _inner_html(post_el.find("conversation-text"))
    lines = post_el.find("conversation")
    parts: list[str] = []
    if title:
        parts.append(f"<h3>{html.escape(title)}</h3>")
    if text:
        parts.append(text)
    if lines is not None:
        for line in lines.findall("line"):
            label = line.get("label", "")
            name = line.get("name", "")
            speaker = label or name
            content = _text_content(line)
            if speaker:
                parts.append(f"<p><strong>{html.escape(speaker)}:</strong> {html.escape(content)}</p>")
            else:
                parts.append(f"<p>{html.escape(content)}</p>")
    return "\n".join(parts)


def _render_audio_post(
    post_el: ET.Element,
    post_id: str,
    media_dir: Path,
    *,
    media_index: dict | None = None,
) -> str:
    parts: list[str] = []
    local_files = find_local_media(media_dir, post_id, media_index=media_index)
    audio_file = next((p for p in local_files if p.suffix.lower() in {".mp3", ".m4a"}), None)
    if audio_file:
        parts.append(
            f'<audio controls preload="metadata" src="{media_url(audio_file)}"></audio>'
        )
    else:
        player = _inner_html(post_el.find("audio-player"))
        if player:
            parts.append(player)

    caption = _inner_html(post_el.find("audio-caption"))
    if caption:
        parts.append(f'<div class="caption">{caption}</div>')
    return "\n".join(parts)


def _render_video_post(
    post_el: ET.Element,
    post_id: str,
    media_dir: Path,
    *,
    media_index: dict | None = None,
) -> str:
    parts: list[str] = []
    local_files = find_local_media(media_dir, post_id, media_index=media_index)
    video_file = next((p for p in local_files if p.suffix.lower() in {".mp4", ".mov"}), None)
    if video_file:
        parts.append(
            f'<div class="video-embed"><video controls preload="metadata" '
            f'src="{media_url(video_file)}"></video></div>'
        )
    else:
        player = _inner_html(post_el.find("video-player"))
        if player:
            parts.append(f'<div class="video-embed">{player}</div>')

    caption = _inner_html(post_el.find("video-caption"))
    if caption:
        parts.append(f'<div class="caption">{caption}</div>')
    return "\n".join(parts)


def _render_answer_post(post_el: ET.Element) -> str:
    question = _inner_html(post_el.find("question"))
    answer = _inner_html(post_el.find("answer"))
    return (
        f'<div class="ask"><p><strong>Question:</strong></p>{question}</div>'
        f'<div class="answer"><p><strong>Answer:</strong></p>{answer}</div>'
    )


def _xml_type_to_post_type(xml_type: str, body_html: str) -> PostType:
    mapping: dict[str, PostType] = {
        "photo": "photo",
        "audio": "audio",
        "video": "video",
    }
    if xml_type in mapping:
        return mapping[xml_type]
    if re.search(r"<img\b", body_html, re.I):
        return "photo"
    if re.search(r"<video\b|<iframe\b", body_html, re.I):
        return "video"
    if re.search(r"<audio\b", body_html, re.I):
        return "audio"
    return "text"


def _render_post_body(
    post_el: ET.Element,
    post_id: str,
    media_dir: Path,
    *,
    media_index: dict | None = None,
) -> str:
    xml_type = post_el.get("type", "regular")

    renderers = {
        "photo": lambda: _render_photo_post(
            post_el, post_id, media_dir, media_index=media_index
        ),
        "regular": lambda: _render_regular_post(post_el),
        "quote": lambda: _render_quote_post(post_el),
        "link": lambda: _render_link_post(post_el),
        "conversation": lambda: _render_conversation_post(post_el),
        "audio": lambda: _render_audio_post(
            post_el, post_id, media_dir, media_index=media_index
        ),
        "video": lambda: _render_video_post(
            post_el, post_id, media_dir, media_index=media_index
        ),
        "answer": lambda: _render_answer_post(post_el),
    }

    renderer = renderers.get(xml_type, renderers["regular"])
    return renderer()


def parse_posts_xml(archive_root: Path, *, max_bytes: int = 512 * 1024 * 1024) -> list[PostMeta]:
    posts_xml = archive_root / "posts" / "posts.xml"
    xml_size = posts_xml.stat().st_size
    if xml_size > max_bytes:
        raise ValueError(
            f"posts.xml is too large ({xml_size} bytes; limit is {max_bytes})"
        )

    media_dir = archive_root / "media"
    media_index = build_media_index(media_dir)

    tree = ET.parse(posts_xml)
    root = tree.getroot()
    posts_node = root.find("posts")
    if posts_node is None:
        return []

    posts: list[PostMeta] = []
    for post_el in posts_node.findall("post"):
        post_id = post_el.get("id", "")
        if not post_id:
            continue

        timestamp = post_el.get("date", "").strip()
        tags = [tag.text.strip() for tag in post_el.findall("tag") if tag.text]
        body_html = _render_post_body(
            post_el, post_id, media_dir, media_index=media_index
        )
        xml_type = post_el.get("type", "regular")
        xml_url, xml_parent_url, xml_parent_name = extract_from_xml_post(post_el)
        tumblr_url, reblog_parent_url, reblog_parent_name = merge_metadata(
            tumblr_url=xml_url,
            reblog_parent_url=xml_parent_url,
            reblog_parent_name=xml_parent_name,
            body_html=body_html,
        )

        posts.append(
            PostMeta(
                id=post_id,
                body_html=body_html,
                timestamp=timestamp,
                tags=tags,
                post_type=_xml_type_to_post_type(xml_type, body_html),
                is_submission=False,
                tumblr_url=tumblr_url,
                reblog_parent_url=reblog_parent_url,
                reblog_parent_name=reblog_parent_name,
            )
        )

    return posts


def build_index(
    archive_root: Path,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[PostMeta]:
    logger.info("Building modern XML index from %s", archive_root / "posts" / "posts.xml")
    if on_progress:
        on_progress(0, 1)
    posts = parse_posts_xml(archive_root)
    sort_posts(posts)
    if on_progress:
        on_progress(1, 1)
    logger.info("Modern XML index complete: %s posts", len(posts))
    return posts
