"""Tests for security helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.security import (
    is_path_under,
    is_safe_http_url,
    is_valid_post_id,
    resolve_allowed_file,
)


class SecurityHelperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.allowed = self.root / "allowed"
        self.allowed.mkdir()
        self.allowed_file = self.allowed / "bg.jpg"
        self.allowed_file.write_bytes(b"image")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_valid_post_id(self) -> None:
        self.assertTrue(is_valid_post_id("123456"))
        self.assertFalse(is_valid_post_id("../etc/passwd"))
        self.assertFalse(is_valid_post_id("abc"))

    def test_resolve_allowed_file_rejects_outside_roots(self) -> None:
        outside = self.root / "outside.txt"
        outside.write_text("secret", encoding="utf-8")
        resolved = resolve_allowed_file(str(outside), [self.allowed])
        self.assertIsNone(resolved)

    def test_resolve_allowed_file_accepts_under_root(self) -> None:
        resolved = resolve_allowed_file(str(self.allowed_file), [self.allowed])
        self.assertEqual(resolved, self.allowed_file.resolve())

    def test_is_path_under(self) -> None:
        nested = self.allowed / "nested" / "file.txt"
        nested.parent.mkdir()
        nested.write_text("x", encoding="utf-8")
        self.assertTrue(is_path_under(nested, self.allowed))
        self.assertFalse(is_path_under(self.root / "outside.txt", self.allowed))

    def test_is_safe_http_url(self) -> None:
        self.assertTrue(is_safe_http_url("https://example.com/bg.jpg"))
        self.assertFalse(is_safe_http_url("javascript:alert(1)"))
        self.assertFalse(is_safe_http_url("file:///etc/passwd"))


if __name__ == "__main__":
    unittest.main()
