"""Tests for post filtering and search."""

from __future__ import annotations

import unittest

from app.parsers.base import PostMeta
from app.post_filters import apply_filters, filter_by_search, filter_by_type


def _post(
    post_id: str,
    *,
    body: str = "",
    tags: list[str] | None = None,
    post_type: str = "text",
    timestamp: str = "",
) -> PostMeta:
    return PostMeta(
        id=post_id,
        body_html=body,
        timestamp=timestamp,
        tags=tags or [],
        post_type=post_type,  # type: ignore[arg-type]
        is_submission=False,
    )


class PostFilterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.posts = [
            _post(
                "1",
                body="<p>Hello world</p>",
                tags=["nature"],
                post_type="text",
                timestamp="April 1st, 2020 12:00pm",
            ),
            _post(
                "2",
                body="<p>Photo of mountains</p><img src='/media/2.jpg'>",
                tags=["photography", "nature"],
                post_type="photo",
                timestamp="May 2nd, 2020 3:00pm",
            ),
            _post(
                "3",
                body="<p>Another note</p>",
                tags=["music"],
                post_type="text",
                timestamp="April 3rd, 2020 6:00pm",
            ),
        ]

    def test_search_matches_body_and_tags(self) -> None:
        results = filter_by_search(self.posts, "mountains")
        self.assertEqual([post.id for post in results], ["2"])

        tag_results = filter_by_search(self.posts, "music")
        self.assertEqual([post.id for post in tag_results], ["3"])

    def test_filter_by_type(self) -> None:
        photos = filter_by_type(self.posts, "photo")
        self.assertEqual([post.id for post in photos], ["2"])

    def test_filter_by_type_invalid_returns_empty(self) -> None:
        self.assertEqual(filter_by_type(self.posts, "invalid"), [])
        self.assertEqual(
            [post.id for post in apply_filters(self.posts, post_type="invalid")],
            ["1", "2", "3"],
        )

    def test_apply_filters_combine_search_type_and_date(self) -> None:
        results = apply_filters(
            self.posts,
            search="nature",
            post_type="text",
            year=2020,
            month=4,
        )
        self.assertEqual([post.id for post in results], ["1"])


if __name__ == "__main__":
    unittest.main()
