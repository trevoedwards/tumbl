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
        self.assertEqual(len(posts), 2)
        ids = {post.id for post in posts}
        self.assertEqual(ids, {"12345", "99999"})


if __name__ == "__main__":
    unittest.main()
