"""Tests for Julian date conversion functions."""

import unittest
from datetime import datetime, timezone
from starloom.space_time.julian import (
    julian_from_datetime,
    julian_from_datetime_with_microseconds,
    julian_to_datetime,
    julian_to_int_frac,
    julian_parts_from_datetime,
    julian_parts_from_datetimes,
)
from starloom.space_time.rounding import create_and_round_to_millisecond


class TestJulianDateConversion(unittest.TestCase):
    """Test case for Julian date conversion functions."""

    def test_julian_from_datetime(self):
        """Test converting datetime to Julian date."""
        # Test a specific date from the Horizons API response
        dt = datetime(2025, 3, 19, 17, 0, tzinfo=timezone.utc)
        jd = julian_from_datetime(dt)
        self.assertAlmostEqual(jd, 2460754.208333333, places=9)

    def test_julian_from_datetime_with_microseconds(self):
        """Test converting datetime with microseconds to Julian date."""
        dt = datetime(2025, 3, 19, 17, 0, 0, 123456, tzinfo=timezone.utc)
        jd = julian_from_datetime_with_microseconds(dt)
        self.assertAlmostEqual(jd, 2460754.208334762, places=9)

    def test_julian_to_datetime(self):
        """Test converting Julian date to datetime."""
        # Test a specific Julian date from the Horizons API response
        jd = 2460754.208333333
        dt = julian_to_datetime(jd)
        expected = datetime(2025, 3, 19, 17, 0, tzinfo=timezone.utc)
        self.assertEqual(dt, expected)

    def test_julian_to_int_frac(self):
        """Test splitting Julian date into integer and fractional parts."""
        jd = 2460754.208333333
        jd_int, jd_frac = julian_to_int_frac(jd)
        self.assertEqual(jd_int, 2460754)
        self.assertAlmostEqual(jd_frac, 0.208333333, places=9)

    def test_julian_parts_from_datetime(self):
        """Test getting Julian date parts from datetime."""
        dt = datetime(2025, 3, 19, 17, 0, tzinfo=timezone.utc)
        jd_int, jd_frac = julian_parts_from_datetime(dt)
        self.assertEqual(jd_int, 2460754)
        self.assertAlmostEqual(jd_frac, 0.208333333, places=9)

    def test_julian_parts_from_datetimes(self):
        """Test getting Julian date parts from multiple datetimes."""
        dts = [
            datetime(2025, 3, 19, 17, 0, tzinfo=timezone.utc),
            datetime(2025, 3, 20, 17, 0, tzinfo=timezone.utc),
        ]
        parts = julian_parts_from_datetimes(dts)
        self.assertEqual(len(parts), 2)
        self.assertEqual(parts[0][0], 2460754)
        self.assertAlmostEqual(parts[0][1], 0.208333333, places=9)
        self.assertEqual(parts[1][0], 2460755)
        self.assertAlmostEqual(parts[1][1], 0.208333333, places=9)

    def test_round_to_millisecond(self):
        """Test rounding microseconds to nearest millisecond."""
        # Test normal case
        dt = create_and_round_to_millisecond(123456, 0, 0, 0, 1, 1, 2025)
        self.assertEqual(dt, datetime(2025, 1, 1, 0, 0, 0, 123000, tzinfo=timezone.utc))

        # Test overflow case
        dt = create_and_round_to_millisecond(999999, 0, 0, 0, 1, 1, 2025)
        self.assertEqual(dt, datetime(2025, 1, 1, 0, 0, 1, 0, tzinfo=timezone.utc))


if __name__ == "__main__":
    unittest.main()
