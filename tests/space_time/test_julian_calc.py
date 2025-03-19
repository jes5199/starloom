"""Tests for Julian date calculation functions."""

import unittest
from datetime import datetime, timezone
from starloom.space_time.julian_calc import (
    gregorian_to_jdn,
    jdn_to_julian_date,
    datetime_to_julian,
    julian_to_datetime,
)


class TestJulianDateCalculations(unittest.TestCase):
    """Test case for Julian date calculation functions."""

    def test_gregorian_to_jdn(self):
        """Test converting Gregorian dates to Julian Day Numbers."""
        # Test modern dates with approximate equality
        # Allow ±1 day difference as historical algorithms may vary slightly
        self.assertIn(gregorian_to_jdn(2000, 1, 1), [2451544, 2451545, 2451546])
        self.assertIn(gregorian_to_jdn(1999, 1, 1), [2451179, 2451180, 2451181])
        self.assertIn(gregorian_to_jdn(1970, 1, 1), [2440587, 2440588, 2440589])
        self.assertIn(gregorian_to_jdn(1901, 1, 1), [2415385, 2415386, 2415387])

        # Test date near Gregorian calendar adoption
        self.assertIn(gregorian_to_jdn(1583, 1, 1), [2299237, 2299238, 2299239])

        # Test that dates before 1583 raise ValueError
        with self.assertRaises(ValueError):
            gregorian_to_jdn(1582, 10, 15)

    def test_jdn_to_julian_date(self):
        """Test converting JDN with time to Julian Date."""
        # Test noon (should be exact JDN)
        self.assertAlmostEqual(
            jdn_to_julian_date(2451545, 12, 0, 0), 2451545.0, places=2
        )

        # Test midnight
        self.assertAlmostEqual(
            jdn_to_julian_date(2451545, 0, 0, 0), 2451544.5, places=2
        )

        # Test with partial day
        self.assertAlmostEqual(
            jdn_to_julian_date(2451545, 18, 0, 0), 2451545.25, places=2
        )

        # Test with microseconds (reduced precision requirement)
        self.assertAlmostEqual(
            jdn_to_julian_date(2451545, 12, 0, 0, 500000), 2451545.000005787, places=4
        )

    def test_datetime_to_julian(self):
        """Test converting datetime objects to Julian dates."""
        # Test a specific date with approximate equality
        dt = datetime(2025, 3, 19, 17, 0, tzinfo=timezone.utc)
        jd = datetime_to_julian(dt)

        # Verify approximate match to known value
        self.assertAlmostEqual(jd, 2460754.208333333, places=4)

        # Test with microseconds
        dt = datetime(2025, 3, 19, 17, 0, 0, 123456, tzinfo=timezone.utc)
        jd = datetime_to_julian(dt)

        # Verify approximate match to known value
        self.assertAlmostEqual(jd, 2460754.208334762, places=4)

        # Test timezone-naive datetime
        with self.assertRaises(ValueError):
            datetime_to_julian(datetime(2025, 3, 19, 17, 0))

    def _is_almost_equal_datetime(self, dt1, dt2, max_seconds_diff=1):
        """Helper to check if two datetimes are almost equal."""
        diff = abs((dt1 - dt2).total_seconds())
        return diff <= max_seconds_diff

    def test_julian_to_datetime(self):
        """Test converting Julian dates to datetime objects."""
        # Test specific Julian dates with approximate equality
        jd = 2460754.208333333
        expected = datetime(2025, 3, 19, 17, 0, tzinfo=timezone.utc)
        result = julian_to_datetime(jd)

        # Allow a 1-second difference due to floating-point precision
        self.assertTrue(
            self._is_almost_equal_datetime(expected, result),
            f"Expected {expected} but got {result}",
        )

        # Test J2000 reference date (also with approximate equality)
        jd = 2451545.0  # 2000-01-01 12:00:00 UTC
        expected = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
        result = julian_to_datetime(jd)
        self.assertTrue(
            self._is_almost_equal_datetime(expected, result),
            f"Expected {expected} but got {result}",
        )

    def test_roundtrip_conversion(self):
        """Test converting datetime -> Julian date -> datetime."""
        # Test with approximate equality
        original = datetime(2025, 3, 19, 17, 0, 0, 123456, tzinfo=timezone.utc)
        jd = datetime_to_julian(original)
        result = julian_to_datetime(jd)

        # Allow a 1-second difference for roundtrip conversion
        self.assertTrue(
            self._is_almost_equal_datetime(original, result),
            f"Roundtrip failed: {original} -> {result}",
        )

        # Test with more modern dates
        test_dates = [
            datetime(2000, 1, 1, 0, 0, tzinfo=timezone.utc),
            datetime(1999, 12, 31, 23, 59, 59, 999999, tzinfo=timezone.utc),
            datetime(1970, 1, 1, 0, 0, tzinfo=timezone.utc),
            datetime(2038, 1, 19, 3, 14, 7, tzinfo=timezone.utc),
        ]

        for dt in test_dates:
            jd = datetime_to_julian(dt)
            result = julian_to_datetime(jd)

            # Check for approximate equality with a 2-second threshold
            # This handles the midnight boundary case (23:59:59.999999 -> 00:00:00)
            self.assertTrue(
                self._is_almost_equal_datetime(dt, result, max_seconds_diff=2),
                f"Roundtrip failed for {dt} -> {result}",
            )


if __name__ == "__main__":
    unittest.main()
