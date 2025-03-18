"""Tests for Julian date conversion functions."""

import unittest
from datetime import datetime, timezone
from lib.time.rounding import create_and_round_to_millisecond


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


if __name__ == "__main__":
    unittest.main()
