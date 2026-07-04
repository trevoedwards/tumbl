"""Tests for the post tag editing API."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.parsers.base import PostMeta


def _sample_posts() -> list[PostMeta]:
    return [
        PostMeta(
            id="100",
            body_html="<p>One</p>",
            timestamp="Jan 1",
            tags=["alpha"],
            post_type="text",
            is_submission=False,
        ),
    ]


SAMPLE_POSTS = _sample_posts()


class ApiTagsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_root = Path(self.temp_dir.name)
        SAMPLE_POSTS[0].tags = ["alpha"]
        warmup_patcher = patch("app.main.start_index_warmup")
        warmup_patcher.start()
        self.addCleanup(warmup_patcher.stop)
        from app.main import create_app

        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["CACHE_DIR"] = self.cache_root
        self.app.config["TAG_EDITING_ENABLED"] = True
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    @patch("app.main._posts_index", SAMPLE_POSTS)
    @patch("app.main._index_error", None)
    @patch("app.main.detect_archive_format")
    @patch("app.main.save_index_cache")
    def test_patch_tags_updates_post_and_overrides(
        self,
        mock_save_cache: object,
        mock_detect_format: object,
    ) -> None:
        response = self.client.patch(
            "/api/posts/100/tags",
            json={"tags": ["beta", "gamma"]},
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["id"], "100")
        self.assertEqual(data["tags"], ["beta", "gamma"])
        self.assertEqual(SAMPLE_POSTS[0].tags, ["beta", "gamma"])

        from app.tag_overrides import load_tag_overrides

        overrides = load_tag_overrides(self.cache_root)
        self.assertEqual(overrides["100"], ["beta", "gamma"])
        mock_save_cache.assert_called_once()

    @patch("app.main._posts_index", SAMPLE_POSTS)
    @patch("app.main._index_error", None)
    def test_patch_tags_rejects_invalid_post_id(self) -> None:
        response = self.client.patch(
            "/api/posts/not-a-number/tags",
            json={"tags": ["beta"]},
        )
        self.assertEqual(response.status_code, 400)

    @patch("app.main._posts_index", SAMPLE_POSTS)
    @patch("app.main._index_error", None)
    def test_patch_tags_returns_404_for_unknown_post(self) -> None:
        response = self.client.patch(
            "/api/posts/999/tags",
            json={"tags": ["beta"]},
        )
        self.assertEqual(response.status_code, 404)

    @patch("app.main._posts_index", SAMPLE_POSTS)
    @patch("app.main._index_error", None)
    def test_patch_tags_rejects_invalid_tag(self) -> None:
        response = self.client.patch(
            "/api/posts/100/tags",
            json={"tags": ["x" * 201]},
        )
        self.assertEqual(response.status_code, 400)

    @patch("app.main._posts_index", SAMPLE_POSTS)
    @patch("app.main._index_error", None)
    def test_patch_tags_disabled_returns_403(self) -> None:
        self.app.config["TAG_EDITING_ENABLED"] = False
        response = self.client.patch(
            "/api/posts/100/tags",
            json={"tags": ["beta"]},
        )
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
