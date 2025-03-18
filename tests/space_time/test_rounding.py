"""Tests for Julian date conversion functions."""

import unittest
from datetime import datetime, timezone
from starloom.space_time.rounding import (
    create_and_round_to_millisecond,
    round_to_nearest_minute,
    round_to_nearest_second,
)


class TestRounding(unittest.TestCase):
    """Test cases for rounding functions."""

    def test_create_and_round_to_millisecond(self):
        """Test rounding microseconds to nearest millisecond."""
        # Test normal case
        dt = create_and_round_to_millisecond(123456, 0, 0, 0, 1, 1, 2025)
        self.assertEqual(dt, datetime(2025, 1, 1, 0, 0, 0, 123000, tzinfo=timezone.utc))

        # Test overflow case
        dt = create_and_round_to_millisecond(999999, 0, 0, 0, 1, 1, 2025)
        self.assertEqual(dt, datetime(2025, 1, 1, 0, 0, 1, 0, tzinfo=timezone.utc))

    def test_round_to_nearest_minute(self):
        """Test rounding datetime to nearest minute."""
        # Test rounding down (seconds < 30)
        dt = datetime(2025, 1, 1, 12, 30, 29, 999999, tzinfo=timezone.utc)
        expected = datetime(2025, 1, 1, 12, 30, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(round_to_nearest_minute(dt), expected)

        # Test rounding up (seconds >= 30)
        dt = datetime(2025, 1, 1, 12, 30, 30, 0, tzinfo=timezone.utc)
        expected = datetime(2025, 1, 1, 12, 31, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(round_to_nearest_minute(dt), expected)

        # Test rounding up at end of hour
        dt = datetime(2025, 1, 1, 12, 59, 30, 0, tzinfo=timezone.utc)
        expected = datetime(2025, 1, 1, 13, 0, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(round_to_nearest_minute(dt), expected)

    def test_round_to_nearest_second(self):
        """Test rounding datetime to nearest second."""
        # Test rounding down (microseconds < 500000)
        dt = datetime(2025, 1, 1, 12, 30, 45, 499999, tzinfo=timezone.utc)
        expected = datetime(2025, 1, 1, 12, 30, 45, 0, tzinfo=timezone.utc)
        self.assertEqual(round_to_nearest_second(dt), expected)

        # Test rounding up (microseconds >= 500000)
        dt = datetime(2025, 1, 1, 12, 30, 45, 500000, tzinfo=timezone.utc)
        expected = datetime(2025, 1, 1, 12, 30, 46, 0, tzinfo=timezone.utc)
        self.assertEqual(round_to_nearest_second(dt), expected)

        # Test rounding up at end of minute
        dt = datetime(2025, 1, 1, 12, 30, 59, 500000, tzinfo=timezone.utc)
        expected = datetime(2025, 1, 1, 12, 31, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(round_to_nearest_second(dt), expected)


if __name__ == "__main__":
    unittest.main()
