"""Tests for index cache invalidation."""

from __future__ import annotations

import json
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

from app.archive_detect import ArchiveFormat, archive_fingerprint
from app.parser import cache_meta_path, cache_path, get_or_build_index, load_cached_index


SAMPLE_POSTS_XML = textwrap.dedent(
    """\
    <?xml version="1.0" encoding="UTF-8"?>
    <tumblr version="1.0">
      <posts>
        <post id="100" type="regular" date="January 1st, 2020 12:00pm">
          <regular-body><![CDATA[<p>Hello world</p>]]></regular-body>
        </post>
      </posts>
    </tumblr>
    """
)


class CacheInvalidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.archive_root = Path(self.temp_dir.name) / "archive"
        self.cache_root = Path(self.temp_dir.name) / "cache"
        posts_dir = self.archive_root / "posts"
        posts_dir.mkdir(parents=True)
        (posts_dir / "posts.xml").write_text(SAMPLE_POSTS_XML, encoding="utf-8")
        (self.archive_root / "media").mkdir()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_stale_cache_rebuilds_when_archive_changes(self) -> None:
        posts = get_or_build_index(self.archive_root, cache_root=self.cache_root)
        self.assertEqual(len(posts), 1)

        fmt = ArchiveFormat.MODERN_XML
        cached = load_cached_index(self.cache_root, fmt, self.archive_root)
        self.assertEqual(len(cached or []), 1)

        posts_xml = self.archive_root / "posts" / "posts.xml"
        posts_xml.write_text(
            posts_xml.read_text(encoding="utf-8").replace(
                "Hello world",
                "Updated world",
            ),
            encoding="utf-8",
        )

        stale = load_cached_index(self.cache_root, fmt, self.archive_root)
        self.assertIsNone(stale)

        rebuilt = get_or_build_index(self.archive_root, cache_root=self.cache_root)
        self.assertEqual(len(rebuilt), 1)
        self.assertIn("Updated world", rebuilt[0].body_html)

    def test_cache_meta_records_fingerprint(self) -> None:
        get_or_build_index(self.archive_root, cache_root=self.cache_root)
        fmt = ArchiveFormat.MODERN_XML
        meta = json.loads(cache_meta_path(self.cache_root, fmt).read_text(encoding="utf-8"))
        self.assertEqual(meta["fingerprint"], archive_fingerprint(self.archive_root, fmt))
        self.assertEqual(meta["schema_version"], 5)
        self.assertTrue(cache_path(self.cache_root, fmt).is_file())

    def test_legacy_fingerprint_detects_edit_to_non_newest_file(self) -> None:
        legacy_root = Path(self.temp_dir.name) / "legacy"
        html_dir = legacy_root / "posts" / "html"
        html_dir.mkdir(parents=True)
        (legacy_root / "media").mkdir()
        newer = html_dir / "200.html"
        older = html_dir / "100.html"
        newer.write_text(
            "<html><body><p>newer</p><div id='footer'>"
            "<span id='timestamp'>Feb 1</span></div></body></html>",
            encoding="utf-8",
        )
        older.write_text(
            "<html><body><p>older</p><div id='footer'>"
            "<span id='timestamp'>Jan 1</span></div></body></html>",
            encoding="utf-8",
        )

        legacy_cache = Path(self.temp_dir.name) / "legacy-cache"
        get_or_build_index(legacy_root, cache_root=legacy_cache)
        fmt = ArchiveFormat.LEGACY_HTML
        cached = load_cached_index(legacy_cache, fmt, legacy_root)
        self.assertEqual(len(cached or []), 2)

        older.write_text(
            "<html><body><p>older edited</p><div id='footer'>"
            "<span id='timestamp'>Jan 1</span></div></body></html>",
            encoding="utf-8",
        )

        stale = load_cached_index(legacy_cache, fmt, legacy_root)
        self.assertIsNone(stale)

        rebuilt = get_or_build_index(legacy_root, cache_root=legacy_cache)
        self.assertTrue(any("older edited" in post.body_html for post in rebuilt))

    def test_empty_cache_is_loaded_not_rebuilt(self) -> None:
        empty_xml = textwrap.dedent(
            """\
            <?xml version="1.0" encoding="UTF-8"?>
            <tumblr version="1.0">
              <posts></posts>
            </tumblr>
            """
        )
        empty_root = Path(self.temp_dir.name) / "empty"
        posts_dir = empty_root / "posts"
        posts_dir.mkdir(parents=True)
        (posts_dir / "posts.xml").write_text(empty_xml, encoding="utf-8")
        (empty_root / "media").mkdir()
        empty_cache = Path(self.temp_dir.name) / "empty-cache"

        first = get_or_build_index(empty_root, cache_root=empty_cache)
        self.assertEqual(first, [])

        with patch("app.parser.build_index") as build_index_mock:
            second = get_or_build_index(empty_root, cache_root=empty_cache)
            build_index_mock.assert_not_called()

        self.assertEqual(second, [])


if __name__ == "__main__":
    unittest.main()
