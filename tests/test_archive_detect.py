"""Tests for archive format detection and fingerprints."""

from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from app.archive_detect import ArchiveFormat, archive_fingerprint, detect_archive_format
from app.parser import get_or_build_index, load_cached_index


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


class ArchiveDetectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_legacy_submissions_only_archive_detected(self) -> None:
        html_dir = self.root / "posts" / "html" / "submissions"
        html_dir.mkdir(parents=True)
        (html_dir / "100.html").write_text(
            "<html><body><p>submission</p></body></html>",
            encoding="utf-8",
        )
        (self.root / "media").mkdir()

        fmt = detect_archive_format(self.root)
        self.assertEqual(fmt, ArchiveFormat.LEGACY_HTML)

    def test_modern_fingerprint_includes_media_changes(self) -> None:
        archive_root = self.root / "archive"
        cache_root = self.root / "cache"
        posts_dir = archive_root / "posts"
        media_dir = archive_root / "media"
        posts_dir.mkdir(parents=True)
        media_dir.mkdir()
        (posts_dir / "posts.xml").write_text(SAMPLE_POSTS_XML, encoding="utf-8")

        fmt = ArchiveFormat.MODERN_XML
        get_or_build_index(archive_root, cache_root=cache_root)
        cached = load_cached_index(cache_root, fmt, archive_root)
        self.assertEqual(len(cached or []), 1)

        (media_dir / "photo.jpg").write_bytes(b"image")
        stale = load_cached_index(cache_root, fmt, archive_root)
        self.assertIsNone(stale)
        self.assertNotEqual(
            archive_fingerprint(archive_root, fmt),
            f"modern:{(posts_dir / 'posts.xml').stat().st_size}:"
            f"{(posts_dir / 'posts.xml').stat().st_mtime_ns}:0:0",
        )


if __name__ == "__main__":
    unittest.main()
