"""Tests for WordPress WXR export generation."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.exporters.wordpress_wxr import (
    extract_media_filenames,
    generate_wxr,
    parse_post_datetime,
    post_slug,
    rewrite_media_urls,
    slugify,
)
from app.parsers.base import PostMeta


def _sample_post(**overrides: object) -> PostMeta:
    defaults = {
        "id": "12345",
        "body_html": '<img src="/media/12345.jpg" alt="">',
        "timestamp": "January 1st, 2020 12:00pm",
        "tags": ["photography", "nature"],
        "post_type": "photo",
        "is_submission": False,
        "tumblr_url": "https://example.tumblr.com/post/12345",
    }
    defaults.update(overrides)
    return PostMeta(**defaults)  # type: ignore[arg-type]


class WordPressWxrTests(unittest.TestCase):
    def test_slugify_tag(self) -> None:
        self.assertEqual(slugify("Hello World"), "hello-world")
        self.assertEqual(slugify("  Mixed Case!  "), "mixed-case")

    def test_post_slug(self) -> None:
        self.assertEqual(post_slug("999"), "tumblr-999")

    def test_parse_post_datetime_with_time(self) -> None:
        local, gmt = parse_post_datetime("February 2nd, 2020 3:00pm")
        self.assertEqual(local, "2020-02-02 15:00:00")
        self.assertEqual(gmt, "2020-02-02 15:00:00")

    def test_parse_post_datetime_date_only(self) -> None:
        local, gmt = parse_post_datetime("March 3rd, 2020")
        self.assertEqual(local, "2020-03-03 12:00:00")
        self.assertEqual(gmt, "2020-03-03 12:00:00")

    def test_parse_post_datetime_invalid_date_falls_back(self) -> None:
        local, gmt = parse_post_datetime("February 31st, 2020 12:00pm")
        self.assertEqual(local, "1970-01-01 12:00:00")
        self.assertEqual(gmt, "1970-01-01 12:00:00")

    def test_rewrite_media_urls(self) -> None:
        html = '<img src="/media/photo.jpg"><video src="/media/clip.mp4"></video>'
        rewritten = rewrite_media_urls(html, "https://cdn.example.com/media")
        self.assertIn('src="https://cdn.example.com/media/photo.jpg"', rewritten)
        self.assertIn('src="https://cdn.example.com/media/clip.mp4"', rewritten)

    def test_extract_media_filenames_deduplicates(self) -> None:
        html = (
            '<img src="/media/a.jpg"><img src="/media/b.png">'
            '<img src="/media/a.jpg">'
        )
        self.assertEqual(extract_media_filenames(html), ["a.jpg", "b.png"])

    def test_generate_wxr_contains_post_fields(self) -> None:
        xml = generate_wxr(
            [_sample_post()],
            site_url="https://myblog.wordpress.com",
            author="admin",
            blog_title="My Blog",
        )
        self.assertIn('xmlns:wp="http://wordpress.org/export/1.2/"', xml)
        self.assertIn("<wp:post_type>post</wp:post_type>", xml)
        self.assertIn("<wp:status>publish</wp:status>", xml)
        self.assertIn("<wp:post_name>tumblr-12345</wp:post_name>", xml)
        self.assertIn('domain="post_tag"', xml)
        self.assertIn("photography", xml)
        self.assertIn("_tumblr_source_url", xml)
        self.assertIn("https://example.tumblr.com/post/12345", xml)

    def test_generate_wxr_without_media_base_keeps_relative_urls(self) -> None:
        xml = generate_wxr(
            [_sample_post()],
            site_url="https://myblog.wordpress.com",
            author="admin",
            blog_title="My Blog",
        )
        self.assertIn('src="/media/12345.jpg"', xml)
        self.assertNotIn("<wp:post_type>attachment</wp:post_type>", xml)

    def test_generate_wxr_with_media_base_rewrites_and_adds_attachments(self) -> None:
        xml = generate_wxr(
            [_sample_post()],
            site_url="https://myblog.wordpress.com",
            author="admin",
            blog_title="My Blog",
            media_base_url="https://cdn.example.com/archive-media",
        )
        self.assertIn(
            'src="https://cdn.example.com/archive-media/12345.jpg"',
            xml,
        )
        self.assertIn("<wp:post_type>attachment</wp:post_type>", xml)
        self.assertIn(
            "<wp:attachment_url>https://cdn.example.com/archive-media/12345.jpg</wp:attachment_url>",
            xml,
        )
        self.assertIn("<wp:post_parent>12345</wp:post_parent>", xml)


class WordPressExportRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        warmup_patcher = patch("app.main.start_index_warmup")
        warmup_patcher.start()
        self.addCleanup(warmup_patcher.stop)

    @patch.dict(os.environ, {"WORDPRESS_EXPORT_ENABLED": "false"}, clear=False)
    @patch("app.main._posts_index", [_sample_post()])
    @patch("app.main._index_error", None)
    def test_export_route_absent_when_disabled(self) -> None:
        from app.main import create_app

        app = create_app()
        app.config["TESTING"] = True
        client = app.test_client()
        response = client.get("/export/wordpress.xml")
        self.assertEqual(response.status_code, 404)

    @patch.dict(
        os.environ,
        {
            "WORDPRESS_EXPORT_ENABLED": "true",
            "WORDPRESS_EXPORT_SITE_URL": "https://myblog.wordpress.com",
            "WORDPRESS_EXPORT_AUTHOR": "admin",
        },
        clear=False,
    )
    @patch("app.main._posts_index", [_sample_post()])
    @patch("app.main._index_error", None)
    def test_export_route_downloads_xml_when_enabled(self) -> None:
        from app.main import create_app

        app = create_app()
        app.config["TESTING"] = True
        client = app.test_client()
        response = client.get("/export/wordpress.xml")
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/rss+xml", response.content_type)
        self.assertIn(b"tumblr-wordpress-export.xml", response.headers.get("Content-Disposition", "").encode())
        self.assertIn(b"<wp:post_type>post</wp:post_type>", response.data)


if __name__ == "__main__":
    unittest.main()
