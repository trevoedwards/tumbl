"""Tests for Tumblr archive parsers."""

from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from app.archive_detect import ArchiveFormat, detect_archive_format
from app.parsers.modern_xml import build_index


SAMPLE_POSTS_XML = textwrap.dedent(
    """\
    <?xml version="1.0" encoding="UTF-8"?>
    <tumblr version="1.0">
      <posts>
        <post id="100" type="regular" date="January 1st, 2020 12:00pm">
          <tag>test</tag>
          <regular-body><![CDATA[<p>Hello world</p>]]></regular-body>
        </post>
        <post id="200" type="photo" date="February 2nd, 2020 3:00pm">
          <photo-url max-width="500">https://64.media.tumblr.com/photo.jpg</photo-url>
          <photo-caption><![CDATA[<p>A photo</p>]]></photo-caption>
        </post>
        <post id="300" type="answer" date="March 3rd, 2020 6:00pm">
          <question><![CDATA[<p>Who are you?</p>]]></question>
          <answer><![CDATA[<p>Just a test.</p>]]></answer>
        </post>
        <post id="400" type="quote" date="April 4th, 2020 9:00am">
          <tag>quotes</tag>
          <quote-text><![CDATA[<p>Stay curious.</p>]]></quote-text>
          <quote-source><![CDATA[Ada Lovelace]]></quote-source>
        </post>
      </posts>
    </tumblr>
    """
)


class ModernXmlParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.archive_root = Path(self.temp_dir.name)
        posts_dir = self.archive_root / "posts"
        posts_dir.mkdir()
        (posts_dir / "posts.xml").write_text(SAMPLE_POSTS_XML, encoding="utf-8")
        (self.archive_root / "media").mkdir()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_detect_modern_format(self) -> None:
        fmt = detect_archive_format(self.archive_root)
        self.assertEqual(fmt, ArchiveFormat.MODERN_XML)

    def test_parse_posts_xml(self) -> None:
        posts = build_index(self.archive_root)
        self.assertEqual(len(posts), 4)
        self.assertEqual(posts[0].id, "400")
        self.assertEqual(posts[1].id, "300")
        self.assertEqual(posts[2].id, "200")
        self.assertEqual(posts[3].id, "100")
        self.assertIn("Hello world", posts[3].body_html)
        self.assertEqual(posts[3].post_type, "text")
        self.assertEqual(posts[2].post_type, "photo")
        self.assertFalse(posts[1].is_submission)
        quote_post = posts[0]
        self.assertTrue(quote_post.is_quote)
        self.assertIn('class="quote-text"', quote_post.body_html)
        self.assertIn('<cite class="quote-source">— Ada Lovelace</cite>', quote_post.body_html)
        self.assertEqual(quote_post.tags, ["quotes"])

    def test_unextracted_posts_zip_is_auto_extracted(self) -> None:
        import io
        import zipfile

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("posts.xml", SAMPLE_POSTS_XML)
        (self.archive_root / "posts.zip").write_bytes(buffer.getvalue())

        from app.archive_prepare import prepare_archive

        prepare_archive(self.archive_root)
        fmt = detect_archive_format(self.archive_root)
        self.assertEqual(fmt, ArchiveFormat.MODERN_XML)

    def test_hybrid_archive_raises(self) -> None:
        html_dir = self.archive_root / "posts" / "html"
        html_dir.mkdir()
        (html_dir / "999.html").write_text("<html><body></body></html>", encoding="utf-8")
        with self.assertRaises(Exception) as ctx:
            detect_archive_format(self.archive_root)
        self.assertIn("hybrid", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
