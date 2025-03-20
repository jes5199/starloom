"""Tests for the TimeSpec class."""

import unittest
from datetime import datetime, timezone
from starloom.ephemeris.time_spec import TimeSpec


class TestTimeSpec(unittest.TestCase):
    """Test cases for the TimeSpec class."""

    def test_get_time_points_from_dates(self):
        """Test getting time points from a list of dates."""
        # Test with datetime objects
        dates = [
            datetime(2025, 3, 19, 20, 0, tzinfo=timezone.utc),
            datetime(2025, 3, 19, 21, 0, tzinfo=timezone.utc),
            datetime(2025, 3, 19, 22, 0, tzinfo=timezone.utc),
        ]
        time_spec = TimeSpec.from_dates(dates)
        result = time_spec.get_time_points()

        self.assertEqual(len(result), 3)
        self.assertEqual(result, dates)  # Should return the exact same list

        # Test with Julian dates
        julian_dates = [2460754.333333333, 2460754.375, 2460754.416666667]
        time_spec = TimeSpec.from_dates(julian_dates)
        result = time_spec.get_time_points()

        self.assertEqual(len(result), 3)
        self.assertEqual(result, julian_dates)  # Should return the exact same list

        # Test with mixed datetime and Julian dates
        mixed_dates = [
            datetime(2025, 3, 19, 20, 0, tzinfo=timezone.utc),
            2460754.375,
            datetime(2025, 3, 19, 22, 0, tzinfo=timezone.utc),
        ]
        time_spec = TimeSpec.from_dates(mixed_dates)
        result = time_spec.get_time_points()

        self.assertEqual(len(result), 3)
        self.assertEqual(result, mixed_dates)  # Should return the exact same list

    def test_get_time_points_from_range(self):
        """Test getting time points from a time range."""
        # Test with datetime objects and hourly step
        start = datetime(2025, 3, 19, 20, 0, tzinfo=timezone.utc)
        stop = datetime(2025, 3, 19, 22, 0, tzinfo=timezone.utc)
        time_spec = TimeSpec.from_range(start, stop, "1h")
        result = time_spec.get_time_points()

        self.assertEqual(len(result), 3)  # Should include start, start+1h, start+2h
        self.assertEqual(result[0], start)
        self.assertEqual(result[1], datetime(2025, 3, 19, 21, 0, tzinfo=timezone.utc))
        self.assertEqual(result[2], stop)

        # Test with Julian dates and daily step
        start_jd = 2460754.0  # 2025-03-19 12:00:00 UTC
        stop_jd = 2460756.0  # 2025-03-21 12:00:00 UTC
        time_spec = TimeSpec.from_range(start_jd, stop_jd, "1d")
        result = time_spec.get_time_points()

        self.assertEqual(len(result), 3)  # Should include start, start+1d, start+2d
        self.assertEqual(result[0], start_jd)
        self.assertEqual(result[1], 2460755.0)
        self.assertEqual(result[2], stop_jd)

        # Test with datetime objects and minute step
        start = datetime(2025, 3, 19, 20, 0, tzinfo=timezone.utc)
        stop = datetime(2025, 3, 19, 20, 30, tzinfo=timezone.utc)
        time_spec = TimeSpec.from_range(start, stop, "15m")
        result = time_spec.get_time_points()

        self.assertEqual(len(result), 3)  # Should include start, start+15m, start+30m
        self.assertEqual(result[0], start)
        self.assertEqual(result[1], datetime(2025, 3, 19, 20, 15, tzinfo=timezone.utc))
        self.assertEqual(result[2], stop)

    def test_get_time_points_errors(self):
        """Test error cases for get_time_points."""
        # Test with neither dates nor range
        time_spec = TimeSpec()
        with self.assertRaises(ValueError):
            time_spec.get_time_points()

        # Test with incomplete range (missing step)
        time_spec = TimeSpec(
            start_time=datetime(2025, 3, 19, 20, 0, tzinfo=timezone.utc),
            stop_time=datetime(2025, 3, 19, 22, 0, tzinfo=timezone.utc),
        )
        with self.assertRaises(ValueError):
            time_spec.get_time_points()

        # Test with invalid step size format
        time_spec = TimeSpec(
            start_time=datetime(2025, 3, 19, 20, 0, tzinfo=timezone.utc),
            stop_time=datetime(2025, 3, 19, 22, 0, tzinfo=timezone.utc),
            step_size="invalid",
        )
        with self.assertRaises(ValueError):
            time_spec.get_time_points()

        # Test with empty step size
        time_spec = TimeSpec(
            start_time=datetime(2025, 3, 19, 20, 0, tzinfo=timezone.utc),
            stop_time=datetime(2025, 3, 19, 22, 0, tzinfo=timezone.utc),
            step_size="",
        )
        with self.assertRaises(ValueError):
            time_spec.get_time_points()

        # Test with invalid step unit
        time_spec = TimeSpec(
            start_time=datetime(2025, 3, 19, 20, 0, tzinfo=timezone.utc),
            stop_time=datetime(2025, 3, 19, 22, 0, tzinfo=timezone.utc),
            step_size="1x",  # Invalid unit
        )
        with self.assertRaises(ValueError):
            time_spec.get_time_points()

        # Test with negative step value
        time_spec = TimeSpec(
            start_time=datetime(2025, 3, 19, 20, 0, tzinfo=timezone.utc),
            stop_time=datetime(2025, 3, 19, 22, 0, tzinfo=timezone.utc),
            step_size="-1h",
        )
        with self.assertRaises(ValueError):
            time_spec.get_time_points()
