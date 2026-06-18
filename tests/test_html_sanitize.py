"""Tests for post HTML sanitization."""

from __future__ import annotations

import unittest

from app.html_sanitize import sanitize_post_html


class HtmlSanitizeTests(unittest.TestCase):
    def test_strips_script_tags(self) -> None:
        dirty = '<p>Hello</p><script>alert("xss")</script>'
        clean = sanitize_post_html(dirty)
        self.assertNotIn("script", clean.lower())
        self.assertIn("Hello", clean)

    def test_adds_lazy_loading_to_images(self) -> None:
        clean = sanitize_post_html('<img src="/media/1.jpg" alt="">')
        self.assertIn('loading="lazy"', clean)
        self.assertIn('decoding="async"', clean)

    def test_strips_event_handlers(self) -> None:
        dirty = '<img src="/media/1.jpg" onerror="alert(1)" alt="">'
        clean = sanitize_post_html(dirty)
        self.assertNotIn("onerror", clean.lower())
        self.assertIn('src="/media/1.jpg"', clean)

    def test_blocks_javascript_urls(self) -> None:
        dirty = '<a href="javascript:alert(1)">click</a>'
        clean = sanitize_post_html(dirty)
        self.assertNotIn("javascript:", clean.lower())

    def test_preserves_safe_embeds(self) -> None:
        dirty = (
            '<iframe src="https://www.youtube.com/embed/abc" '
            'width="560" height="315"></iframe>'
        )
        clean = sanitize_post_html(dirty)
        self.assertIn("youtube.com/embed/abc", clean)


if __name__ == "__main__":
    unittest.main()
