"""Tests for tag override persistence."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.parsers.base import PostMeta
from app.tag_overrides import (
    apply_tag_overrides,
    load_tag_overrides,
    normalize_tags,
    overrides_path,
    save_tag_overrides,
    validate_and_normalize_tags,
)


def _sample_post(post_id: str = "100", tags: list[str] | None = None) -> PostMeta:
    return PostMeta(
        id=post_id,
        body_html="<p>Hello</p>",
        timestamp="Jan 1",
        tags=tags or ["original"],
        post_type="text",
        is_submission=False,
    )


class TagOverridesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_normalize_tags_trims_dedupes_and_strips_hash(self) -> None:
        tags = normalize_tags(["  photo ", "#Photo", "", "travel", "TRAVEL"])
        self.assertEqual(tags, ["photo", "travel"])

    def test_validate_and_normalize_tags_rejects_invalid(self) -> None:
        long_tag = "x" * 201
        tags, error = validate_and_normalize_tags(["ok", long_tag])
        self.assertIsNone(tags)
        self.assertIn("Invalid tag", error or "")

    def test_apply_tag_overrides_updates_matching_posts(self) -> None:
        posts = [_sample_post("100"), _sample_post("200", ["other"])]
        apply_tag_overrides(posts, {"100": ["edited"], "200": []})
        self.assertEqual(posts[0].tags, ["edited"])
        self.assertEqual(posts[1].tags, [])

    def test_save_and_load_round_trip(self) -> None:
        overrides = {"100": ["alpha", "beta"], "200": []}
        save_tag_overrides(self.cache_root, overrides)
        loaded = load_tag_overrides(self.cache_root)
        self.assertEqual(loaded, overrides)
        payload = json.loads(overrides_path(self.cache_root).read_text(encoding="utf-8"))
        self.assertEqual(payload["200"], [])


if __name__ == "__main__":
    unittest.main()
