"""Tests for datetime utility functions."""

import unittest
from datetime import datetime, timezone, timedelta

from starloom.space_time.pythonic_datetimes import (
    ensure_utc,
    get_local_datetime,
    get_local_date,
    get_closest_local_midnight_before,
    normalize_longitude,
    NaiveDateTimeError,
)


class TestPythonicDatetimes(unittest.TestCase):
    """Test cases for datetime utility functions."""

    def test_ensure_utc(self):
        """Test ensuring datetime is in UTC."""
        # Test UTC datetime remains unchanged
        dt_utc = datetime(2025, 1, 1, tzinfo=timezone.utc)
        self.assertEqual(ensure_utc(dt_utc), dt_utc)

        # Test naive datetime raises error
        dt_naive = datetime(2025, 1, 1)
        with self.assertRaises(NaiveDateTimeError):
            ensure_utc(dt_naive)

        # Test non-UTC datetime is converted to UTC
        dt_est = datetime(2025, 1, 1, tzinfo=timezone(timedelta(hours=-5)))
        dt_utc = datetime(2025, 1, 1, 5, tzinfo=timezone.utc)
        self.assertEqual(ensure_utc(dt_est), dt_utc)

    def test_normalize_longitude(self):
        """Test longitude normalization."""
        # Test values within [-180, 180] remain unchanged
        self.assertEqual(normalize_longitude(0), 0)
        self.assertEqual(normalize_longitude(179), 179)
        self.assertEqual(normalize_longitude(-180), -180)

        # Test values outside [-180, 180] are normalized
        self.assertEqual(normalize_longitude(360), 0)
        self.assertEqual(normalize_longitude(-360), 0)
        self.assertEqual(normalize_longitude(540), -180)  # 540 = 180 (mod 360) -> -180
        self.assertEqual(
            normalize_longitude(-540), -180
        )  # -540 = -180 (mod 360) -> -180

    def test_get_local_datetime(self):
        """Test converting UTC datetime to local datetime based on longitude."""
        dt_utc = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        # Test prime meridian (no change)
        self.assertEqual(get_local_datetime(dt_utc, 0), dt_utc)

        # Test positive longitude (east)
        dt_east = datetime(2025, 1, 1, 16, 0, tzinfo=timezone.utc)  # +4 hours
        self.assertEqual(get_local_datetime(dt_utc, 60), dt_east)

        # Test negative longitude (west)
        dt_west = datetime(2025, 1, 1, 8, 0, tzinfo=timezone.utc)  # -4 hours
        self.assertEqual(get_local_datetime(dt_utc, -60), dt_west)

    def test_get_closest_local_midnight_before(self):
        """Test finding closest local midnight before given datetime."""
        dt_utc = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        # Test prime meridian
        expected_gmt = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(get_closest_local_midnight_before(dt_utc, 0), expected_gmt)

        # Test positive longitude (east)
        expected_east = datetime(2024, 12, 31, 20, 0, tzinfo=timezone.utc)  # -4 hours
        self.assertEqual(get_closest_local_midnight_before(dt_utc, 60), expected_east)

        # Test negative longitude (west)
        expected_west = datetime(2025, 1, 1, 4, 0, tzinfo=timezone.utc)  # +4 hours
        self.assertEqual(get_closest_local_midnight_before(dt_utc, -60), expected_west)

    def test_get_local_date(self):
        """Test converting UTC datetime to local date based on longitude."""
        dt_utc = datetime(2025, 1, 1, 23, 0, tzinfo=timezone.utc)

        # Test prime meridian
        self.assertEqual(get_local_date(dt_utc, 0), dt_utc.date())

        # Test positive longitude (east)
        self.assertEqual(get_local_date(dt_utc, 60), dt_utc.date())  # Still Jan 1

        # Test negative longitude (west)
        self.assertEqual(get_local_date(dt_utc, -60), dt_utc.date())  # Still Jan 1


if __name__ == "__main__":
    unittest.main()
