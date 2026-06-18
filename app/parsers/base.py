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

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> PostMeta:
        return cls(**data)


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
