"""Tests for tumblr-utils export parser."""

from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from app.archive_detect import ArchiveFormat, detect_archive_format
from app.parsers.tumblr_utils import build_index, parse_post_file


SAMPLE_UTILS_POST = textwrap.dedent(
    """\
    <!DOCTYPE html>
    <html>
    <body>
    <article data-type="photo">
        <img src="media/555.jpg" alt="">
        <p>Utils backup photo</p>
    </article>
    <footer>
        <time>April 10th, 2018 4:00pm</time>
        <a href="/tagged/landscape">#landscape</a>
    </footer>
    </body>
    </html>
    """
)

SAMPLE_UTILS_QUOTE_POST = textwrap.dedent(
    """\
    <!DOCTYPE html>
    <html>
    <body>
    <article class="quote">
        <header>
            <p><time datetime="2020-04-04">April 4th, 2020 9:00am</time></p>
        </header>
        <blockquote><p>Stay curious.</p></blockquote>
        <p>Ada Lovelace</p>
        <footer><a href="/tagged/quotes">#quotes</a></footer>
    </article>
    <footer>
        <time>April 4th, 2020 9:00am</time>
        <a href="/tagged/quotes">#quotes</a>
    </footer>
    </body>
    </html>
    """
)

SAMPLE_UTILS_DATA_TYPE_QUOTE = textwrap.dedent(
    """\
    <!DOCTYPE html>
    <html>
    <body>
    <article data-type="quote">
        <blockquote><p>Question everything.</p></blockquote>
        <p>Carl Sagan</p>
    </article>
    <footer>
        <time>June 6th, 2020 8:00am</time>
    </footer>
    </body>
    </html>
    """
)


class TumblrUtilsParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.archive_root = Path(self.temp_dir.name)
        posts_dir = self.archive_root / "posts"
        posts_dir.mkdir()
        (self.archive_root / "index.html").write_text("<html><body>Index</body></html>", encoding="utf-8")
        (self.archive_root / "media").mkdir()
        (posts_dir / "555.html").write_text(SAMPLE_UTILS_POST, encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_detect_tumblr_utils_format(self) -> None:
        fmt = detect_archive_format(self.archive_root)
        self.assertEqual(fmt, ArchiveFormat.TUMBLR_UTILS)

    def test_parse_utils_post(self) -> None:
        post = parse_post_file(self.archive_root / "posts" / "555.html", self.archive_root)
        assert post is not None
        self.assertEqual(post.id, "555")
        self.assertEqual(post.post_type, "photo")
        self.assertIn('/media/555.jpg', post.body_html)
        self.assertEqual(post.tags, ["landscape"])
        self.assertEqual(post.timestamp, "April 10th, 2018 4:00pm")

    def test_build_index(self) -> None:
        posts = build_index(self.archive_root)
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].id, "555")

    def test_body_fallback_excludes_footer(self) -> None:
        no_article = textwrap.dedent(
            """\
            <!DOCTYPE html>
            <html>
            <body>
                <img src="media/777.jpg" alt="">
                <p>No article wrapper</p>
            <footer>
                <time>May 5th, 2019 1:00pm</time>
                <a href="/tagged/test">#test</a>
            </footer>
            </body>
            </html>
            """
        )
        (self.archive_root / "posts" / "777.html").write_text(no_article, encoding="utf-8")
        post = parse_post_file(self.archive_root / "posts" / "777.html", self.archive_root)
        assert post is not None
        self.assertNotIn("<footer", post.body_html)
        self.assertNotIn("<time>", post.body_html)
        self.assertEqual(post.timestamp, "May 5th, 2019 1:00pm")
        self.assertEqual(post.tags, ["test"])

    def test_tags_deduplicate_case_insensitive(self) -> None:
        tagged = textwrap.dedent(
            """\
            <!DOCTYPE html>
            <html>
            <body>
            <article><p>Tagged post</p></article>
            <footer>
                <span class="tag">Nature</span>
                <a href="/tagged/nature">#nature</a>
            </footer>
            </body>
            </html>
            """
        )
        (self.archive_root / "posts" / "888.html").write_text(tagged, encoding="utf-8")
        post = parse_post_file(self.archive_root / "posts" / "888.html", self.archive_root)
        assert post is not None
        self.assertEqual(post.tags, ["Nature"])

    def test_article_class_quote_detected_and_normalized(self) -> None:
        (self.archive_root / "posts" / "401.html").write_text(
            SAMPLE_UTILS_QUOTE_POST, encoding="utf-8"
        )
        post = parse_post_file(self.archive_root / "posts" / "401.html", self.archive_root)
        assert post is not None
        self.assertTrue(post.is_quote)
        self.assertNotIn("<header", post.body_html)
        self.assertIn('<blockquote class="quote-text">', post.body_html)
        self.assertIn('<cite class="quote-source">— Ada Lovelace</cite>', post.body_html)
        self.assertEqual(post.tags, ["quotes"])

    def test_data_type_quote_detected_and_normalized(self) -> None:
        (self.archive_root / "posts" / "402.html").write_text(
            SAMPLE_UTILS_DATA_TYPE_QUOTE, encoding="utf-8"
        )
        post = parse_post_file(self.archive_root / "posts" / "402.html", self.archive_root)
        assert post is not None
        self.assertTrue(post.is_quote)
        self.assertIn('<cite class="quote-source">— Carl Sagan</cite>', post.body_html)


if __name__ == "__main__":
    unittest.main()
