"""Tests for index progress reporting."""

from __future__ import annotations

import unittest

from app import index_progress


class IndexProgressTests(unittest.TestCase):
    def setUp(self) -> None:
        index_progress.reset()

    def test_mark_error_sets_error_phase(self) -> None:
        index_progress.set_total(10)
        index_progress.mark_error()
        state = index_progress.snapshot()
        self.assertEqual(state["phase"], "error")
        self.assertFalse(state["ready"])

    def test_mark_complete_sets_ready(self) -> None:
        index_progress.set_total(10)
        index_progress.mark_complete()
        state = index_progress.snapshot()
        self.assertEqual(state["phase"], "complete")
        self.assertTrue(state["ready"])


if __name__ == "__main__":
    unittest.main()
