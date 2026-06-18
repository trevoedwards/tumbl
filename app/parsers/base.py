"""Shared types and utilities for Tumblr archive parsers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, Protocol

PostType = Literal["photo", "audio", "video", "text"]


@dataclass
class PostMeta:
    id: str
    body_html: str
    timestamp: str
    tags: list[str]
    post_type: PostType
    is_submission: bool
    tumblr_url: str | None = None
    reblog_parent_url: str | None = None
    reblog_parent_name: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> PostMeta:
        return cls(
            id=data["id"],
            body_html=data["body_html"],
            timestamp=data["timestamp"],
            tags=data["tags"],
            post_type=data["post_type"],
            is_submission=data["is_submission"],
            tumblr_url=data.get("tumblr_url"),
            reblog_parent_url=data.get("reblog_parent_url"),
            reblog_parent_name=data.get("reblog_parent_name"),
        )


def post_sort_key(post: PostMeta) -> int:
    try:
        return int(post.id)
    except ValueError:
        return 0


def sort_posts(posts: list[PostMeta]) -> list[PostMeta]:
    posts.sort(key=post_sort_key, reverse=True)
    return posts


class ArchiveParser(Protocol):
    def build_index(self, archive_root: Path) -> list[PostMeta]: ...
