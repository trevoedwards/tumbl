"""Tests for the /random route."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.parsers.base import PostMeta


def _sample_posts() -> list[PostMeta]:
    return [
        PostMeta(
            id="1",
            body_html="<p>One</p>",
            timestamp="Jan 1",
            tags=[],
            post_type="text",
            is_submission=False,
        ),
        PostMeta(
            id="2",
            body_html="<p>Two</p>",
            timestamp="Jan 2",
            tags=[],
            post_type="text",
            is_submission=False,
        ),
    ]


class RandomRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        warmup_patcher = patch("app.main.start_index_warmup")
        warmup_patcher.start()
        self.addCleanup(warmup_patcher.stop)
        from app.main import create_app

        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    @patch("app.main._posts_index", _sample_posts())
    @patch("app.main._index_error", None)
    @patch("app.main.random.choice", return_value=_sample_posts()[1])
    def test_random_redirects_to_post(self, _mock_choice: object) -> None:
        response = self.client.get("/random")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/post/2", response.headers["Location"])

    @patch("app.main._posts_index", None)
    @patch("app.main._index_error", None)
    def test_random_waits_while_index_loading(self) -> None:
        response = self.client.get("/random")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Loading archive", response.data)


if __name__ == "__main__":
    unittest.main()
