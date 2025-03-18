"""Tests for datetime utility functions."""

import unittest
from datetime import datetime, timezone, date
import pytz

from starloom.space_time.pythonic_datetimes import (
    ensure_utc,
    _normalize_longitude,
    _get_longitude_offset,
    get_local_datetime,
    get_closest_local_midnight_before,
    get_local_date,
    NaiveDateTimeError,
)


class TestPythonicDatetimes(unittest.TestCase):
    """Test cases for datetime utility functions."""

    def test_ensure_utc(self):
        """Test ensuring datetime is in UTC."""
        # Test UTC datetime remains unchanged
        dt_utc = datetime(2025, 1, 1, tzinfo=timezone.utc)
        self.assertEqual(ensure_utc(dt_utc), dt_utc)

        # Test conversion from another timezone to UTC
        est = pytz.timezone("America/New_York")
        dt_est = datetime(2025, 1, 1, tzinfo=est)
        dt_utc_expected = dt_est.astimezone(pytz.utc)
        self.assertEqual(ensure_utc(dt_est), dt_utc_expected)

        # Test naive datetime raises error
        dt_naive = datetime(2025, 1, 1)
        with self.assertRaises(NaiveDateTimeError):
            ensure_utc(dt_naive)

    def test_normalize_longitude(self):
        """Test longitude normalization."""
        # Test values within [-180, 180] remain unchanged
        self.assertEqual(_normalize_longitude(0), 0)
        self.assertEqual(_normalize_longitude(179), 179)
        self.assertEqual(_normalize_longitude(-180), -180)

        # Test values outside [-180, 180] are normalized
        self.assertEqual(_normalize_longitude(360), 0)
        self.assertEqual(_normalize_longitude(-360), 0)
        self.assertEqual(_normalize_longitude(540), -180)  # 540 = 180 (mod 360) -> -180
        self.assertEqual(
            _normalize_longitude(-540), -180
        )  # -540 = -180 (mod 360) -> -180

    def test_get_longitude_offset(self):
        """Test longitude to timezone offset conversion."""
        # Test prime meridian has no offset
        self.assertEqual(_get_longitude_offset(0).total_seconds(), 0)

        # Test positive longitude (east) has positive offset
        self.assertEqual(_get_longitude_offset(15).total_seconds(), 3600)  # 1 hour
        self.assertEqual(_get_longitude_offset(7.5).total_seconds(), 1800)  # 30 minutes

        # Test negative longitude (west) has negative offset
        self.assertEqual(_get_longitude_offset(-15).total_seconds(), -3600)  # -1 hour
        self.assertEqual(
            _get_longitude_offset(-7.5).total_seconds(), -1800
        )  # -30 minutes

    def test_get_local_datetime(self):
        """Test converting UTC datetime to local datetime based on longitude."""
        dt_utc = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        # Test prime meridian (no change)
        self.assertEqual(get_local_datetime(dt_utc, 0), dt_utc)

        # Test positive longitude (east)
        expected_east = datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc)  # +1 hour
        self.assertEqual(get_local_datetime(dt_utc, 15), expected_east)

        # Test negative longitude (west)
        expected_west = datetime(2025, 1, 1, 11, 0, tzinfo=timezone.utc)  # -1 hour
        self.assertEqual(get_local_datetime(dt_utc, -15), expected_west)

    def test_get_closest_local_midnight_before(self):
        """Test finding closest local midnight before given datetime."""
        dt_utc = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        # Test prime meridian
        expected_gmt = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(get_closest_local_midnight_before(dt_utc, 0), expected_gmt)

        # Test positive longitude (east)
        # At longitude 15°E, local midnight is at 23:00 UTC the previous day
        expected_east = datetime(2024, 12, 31, 23, 0, tzinfo=timezone.utc)
        self.assertEqual(get_closest_local_midnight_before(dt_utc, 15), expected_east)

        # Test negative longitude (west)
        # At longitude 15°W, local midnight is at 01:00 UTC
        expected_west = datetime(2025, 1, 1, 1, 0, tzinfo=timezone.utc)
        self.assertEqual(get_closest_local_midnight_before(dt_utc, -15), expected_west)

    def test_get_local_date(self):
        """Test converting UTC datetime to local date based on longitude."""
        dt_utc = datetime(2025, 1, 1, 23, 0, tzinfo=timezone.utc)

        # Test prime meridian
        self.assertEqual(get_local_date(dt_utc, 0), date(2025, 1, 1))

        # Test positive longitude (east)
        # At longitude 60°E (UTC+4), it's already the next day
        self.assertEqual(get_local_date(dt_utc, 60), date(2025, 1, 2))

        # Test negative longitude (west)
        # At longitude 60°W (UTC-4), it's still the same day
        self.assertEqual(get_local_date(dt_utc, -60), date(2025, 1, 1))


if __name__ == "__main__":
    unittest.main()
