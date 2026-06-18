"""Tests for Open Graph preview helpers."""

from __future__ import annotations

import unittest

from app.open_graph import preview_description, preview_image_src, preview_image_url
from app.parsers.base import PostMeta


def _post(body: str, *, tags: list[str] | None = None) -> PostMeta:
    return PostMeta(
        id="100",
        body_html=body,
        timestamp="April 1st, 2020 12:00pm",
        tags=tags or [],
        post_type="photo",
        is_submission=False,
    )


class OpenGraphTests(unittest.TestCase):
    def test_preview_image_src_from_local_media(self) -> None:
        post = _post('<p>Hi</p><img src="/media/100.jpg" alt="">')
        self.assertEqual(preview_image_src(post), "/media/100.jpg")

    def test_preview_image_url_resolves_local_media(self) -> None:
        post = _post('<img src="/media/100.jpg" alt="">')
        url = preview_image_url(
            post,
            absolute_media_url=lambda name: f"https://example.com/media/{name}",
        )
        self.assertEqual(url, "https://example.com/media/100.jpg")

    def test_preview_image_url_allows_https_cdn(self) -> None:
        post = _post('<img src="https://64.media.tumblr.com/photo.jpg" alt="">')
        url = preview_image_url(
            post,
            absolute_media_url=lambda name: f"https://example.com/media/{name}",
        )
        self.assertEqual(url, "https://64.media.tumblr.com/photo.jpg")

    def test_preview_image_url_rejects_javascript(self) -> None:
        post = _post('<img src="javascript:alert(1)" alt="">')
        self.assertIsNone(
            preview_image_url(
                post,
                absolute_media_url=lambda name: f"https://example.com/media/{name}",
            )
        )

    def test_preview_description_strips_html_and_truncates(self) -> None:
        post = _post("<p>Hello <strong>world</strong></p>", tags=["nature"])
        desc = preview_description(post, max_length=50)
        self.assertIn("Hello world", desc)
        self.assertIn("#nature", desc)

    def test_preview_description_falls_back_to_timestamp(self) -> None:
        post = _post("", tags=[])
        self.assertEqual(preview_description(post), "April 1st, 2020 12:00pm")


if __name__ == "__main__":
    unittest.main()
