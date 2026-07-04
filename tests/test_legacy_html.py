"""Tests for legacy Tumblr HTML backup parser."""

from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from app.archive_detect import ArchiveFormat, detect_archive_format
from app.parsers.legacy_html import build_index, parse_post_file


SAMPLE_POST_HTML = textwrap.dedent(
    """\
    <!DOCTYPE HTML>
    <html>
        <body>
            <img src="../../media/12345.jpg"/>
            <div class="caption"><p>A photo post</p></div>
            <div id="footer">
                <span id="timestamp">January 1st, 2020 12:00pm</span>
                <span class="tag">photography</span>
                <span class="tag">nature</span>
            </div>
        </body>
    </html>
    """
)

SAMPLE_SUBMISSION_HTML = textwrap.dedent(
    """\
    <!DOCTYPE HTML>
    <html>
        <body>
            <p>Ask answer content</p>
            <div id="footer">
                <span id="timestamp">February 2nd, 2020 3:00pm</span>
            </div>
        </body>
    </html>
    """
)

SAMPLE_BLOCKQUOTE_QUOTE_HTML = textwrap.dedent(
    """\
    <!DOCTYPE HTML>
    <html>
        <body>
            <blockquote><p>Stay curious.</p></blockquote>
            <p>Ada Lovelace</p>
            <div id="footer">
                <span id="timestamp">April 4th, 2020 9:00am</span>
                <span class="tag">quotes</span>
            </div>
        </body>
    </html>
    """
)

SAMPLE_PLAIN_QUOTE_HTML = textwrap.dedent(
    """\
    <!DOCTYPE HTML>
    <html>
        <body>
            Directly, or indirectly, everything we write is for someone.
            <div class="caption">&mdash; (via <a class="tumblr_blog" href="http://example.tumblr.com/">example</a>)</div>
            <div id="footer">
                <span id="timestamp">March 17th, 2014 10:10am</span>
                <span class="tag">quotes</span>
            </div>
        </body>
    </html>
    """
)

SAMPLE_REBLOG_QUOTE_HTML = textwrap.dedent(
    """\
    <!DOCTYPE HTML>
    <html>
        <body>
            <p>Reblogged from <a href="https://other.tumblr.com/post/123/456">other</a></p>
            <div class="caption">
                <blockquote><p>Nested quote</p></blockquote>
            </div>
            <div id="footer">
                <span id="timestamp">May 5th, 2020 1:00pm</span>
            </div>
        </body>
    </html>
    """
)


class LegacyHtmlParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.archive_root = Path(self.temp_dir.name)
        self.html_dir = self.archive_root / "posts" / "html"
        self.submissions_dir = self.html_dir / "submissions"
        self.html_dir.mkdir(parents=True)
        self.submissions_dir.mkdir()
        (self.archive_root / "media").mkdir()
        (self.html_dir / "12345.html").write_text(SAMPLE_POST_HTML, encoding="utf-8")
        (self.html_dir / "54321.html").write_text(SAMPLE_BLOCKQUOTE_QUOTE_HTML, encoding="utf-8")
        (self.html_dir / "79880.html").write_text(SAMPLE_PLAIN_QUOTE_HTML, encoding="utf-8")
        (self.html_dir / "21036.html").write_text(SAMPLE_REBLOG_QUOTE_HTML, encoding="utf-8")
        (self.submissions_dir / "99999.html").write_text(
            SAMPLE_SUBMISSION_HTML, encoding="utf-8"
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_detect_legacy_format(self) -> None:
        fmt = detect_archive_format(self.archive_root)
        self.assertEqual(fmt, ArchiveFormat.LEGACY_HTML)

    def test_parse_tags_and_timestamp(self) -> None:
        post = parse_post_file(self.html_dir / "12345.html", self.archive_root)
        assert post is not None
        self.assertEqual(post.id, "12345")
        self.assertEqual(post.timestamp, "January 1st, 2020 12:00pm")
        self.assertEqual(post.tags, ["photography", "nature"])

    def test_rewrite_media_paths(self) -> None:
        post = parse_post_file(self.html_dir / "12345.html", self.archive_root)
        assert post is not None
        self.assertIn('src="/media/12345.jpg"', post.body_html)
        self.assertNotIn("../../media/", post.body_html)
        self.assertEqual(post.post_type, "photo")

    def test_submission_flag(self) -> None:
        post = parse_post_file(self.submissions_dir / "99999.html", self.archive_root)
        assert post is not None
        self.assertTrue(post.is_submission)

    def test_build_index_includes_submissions(self) -> None:
        posts = build_index(self.archive_root)
        self.assertEqual(len(posts), 5)
        ids = {post.id for post in posts}
        self.assertEqual(ids, {"12345", "54321", "79880", "21036", "99999"})

    def test_blockquote_quote_detected_and_normalized(self) -> None:
        post = parse_post_file(self.html_dir / "54321.html", self.archive_root)
        assert post is not None
        self.assertTrue(post.is_quote)
        self.assertIn('<blockquote class="quote-text">', post.body_html)
        self.assertIn('<cite class="quote-source">— Ada Lovelace</cite>', post.body_html)

    def test_plain_text_quote_detected_and_normalized(self) -> None:
        post = parse_post_file(self.html_dir / "79880.html", self.archive_root)
        assert post is not None
        self.assertTrue(post.is_quote)
        self.assertIn('<blockquote class="quote-text">', post.body_html)
        self.assertIn('<cite class="quote-source">', post.body_html)
        self.assertIn("everything we write is for someone", post.body_html)

    def test_photo_post_is_not_quote(self) -> None:
        post = parse_post_file(self.html_dir / "12345.html", self.archive_root)
        assert post is not None
        self.assertFalse(post.is_quote)

    def test_reblog_with_nested_blockquote_is_not_quote(self) -> None:
        post = parse_post_file(self.html_dir / "21036.html", self.archive_root)
        assert post is not None
        self.assertFalse(post.is_quote)


if __name__ == "__main__":
    unittest.main()
