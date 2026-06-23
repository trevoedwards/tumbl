"""Tests for Tumblr timestamp parsing."""

from __future__ import annotations

import unittest

from app.timestamp_parse import month_label, parse_timestamp


class TimestampParseTests(unittest.TestCase):
    def test_parse_common_timestamp(self) -> None:
        parsed = parse_timestamp("April 29th, 2017 9:28pm")
        self.assertEqual(parsed, (2017, 4, 29))

    def test_parse_without_time(self) -> None:
        parsed = parse_timestamp("January 1st, 2020 12:00pm")
        self.assertEqual(parsed, (2020, 1, 1))

    def test_invalid_timestamp(self) -> None:
        self.assertIsNone(parse_timestamp("not a date"))
        self.assertIsNone(parse_timestamp("February 30th, 2020"))
        self.assertIsNone(parse_timestamp("April 31st, 2020"))
        self.assertIsNone(parse_timestamp("January 0th, 2020"))

    def test_month_label(self) -> None:
        self.assertEqual(month_label(2017, 4), "April 2017")


if __name__ == "__main__":
    unittest.main()
