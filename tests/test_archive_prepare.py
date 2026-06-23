"""Tests for archive preparation helpers."""

from __future__ import annotations

import io
import tempfile
import textwrap
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from app import archive_prepare
from app.archive_detect import ArchiveFormat, detect_archive_format
from app.archive_prepare import prepare_archive


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


class ArchivePrepareTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.archive_root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_extract_root_posts_zip(self) -> None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("posts.xml", SAMPLE_POSTS_XML)
        (self.archive_root / "posts.zip").write_bytes(buffer.getvalue())

        prepare_archive(self.archive_root)

        self.assertTrue((self.archive_root / "posts" / "posts.xml").is_file())
        fmt = detect_archive_format(self.archive_root)
        self.assertEqual(fmt, ArchiveFormat.MODERN_XML)

    def test_rejects_zip_slip_paths(self) -> None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("../evil.txt", "bad")
        (self.archive_root / "posts.zip").write_bytes(buffer.getvalue())

        with self.assertRaises(ValueError):
            prepare_archive(self.archive_root)

        self.assertFalse((self.archive_root / "evil.txt").exists())

    def test_rejects_zip_slip_backslash_paths(self) -> None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("..\\..\\evil.txt", "bad")
        (self.archive_root / "posts.zip").write_bytes(buffer.getvalue())

        with self.assertRaises(ValueError):
            prepare_archive(self.archive_root)

    @patch.object(archive_prepare, "MAX_ZIP_UNCOMPRESSED_BYTES", 100)
    def test_rejects_oversized_zip(self) -> None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("posts.xml", "x" * 101)
        (self.archive_root / "posts.zip").write_bytes(buffer.getvalue())

        with self.assertRaises(ValueError):
            prepare_archive(self.archive_root)


if __name__ == "__main__":
    unittest.main()
