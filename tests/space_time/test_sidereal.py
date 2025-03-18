"""Tests for sidereal time calculations."""

import unittest
from datetime import datetime, timezone
from starloom.space_time.sidereal import (
    sidereal_time_from_julian,
    sidereal_time_from_datetime,
)


class TestSiderealTime(unittest.TestCase):
    """Test cases for sidereal time calculations."""

    def test_sidereal_time_from_julian(self):
        """Test calculating sidereal time from Julian date."""
        # Test case from Astronomical Algorithms by Jean Meeus (Chapter 12)
        # For 1987 April 10, 0h TD at Greenwich
        jd = 2446895.5
        longitude = 0  # Greenwich
        lst = sidereal_time_from_julian(jd, longitude)
        self.assertAlmostEqual(
            lst, 13.1795, places=4
        )  # Expected: 13h 10m 46.3s = 13.1795 hours

        # Test different longitudes
        # At 15 degrees east, LMST should be 1 hour ahead
        lst_east = sidereal_time_from_julian(jd, 15)
        self.assertAlmostEqual(lst_east, (13.1795 + 1) % 24, places=4)

        # At 15 degrees west, LMST should be 1 hour behind
        lst_west = sidereal_time_from_julian(jd, -15)
        self.assertAlmostEqual(lst_west, (13.1795 - 1) % 24, places=4)

    def test_sidereal_time_from_datetime(self):
        """Test calculating sidereal time from datetime."""
        # Test case for J2000.0 epoch
        dt = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)  # J2000.0
        longitude = 0  # Greenwich
        lst = sidereal_time_from_datetime(dt, longitude)
        self.assertAlmostEqual(lst, 18.697374558, places=4)  # Expected value at J2000.0

        # Test different longitudes
        # At 30 degrees east, LMST should be 2 hours ahead
        lst_east = sidereal_time_from_datetime(dt, 30)
        self.assertAlmostEqual(lst_east, (18.697374558 + 2) % 24, places=4)

        # At 30 degrees west, LMST should be 2 hours behind
        lst_west = sidereal_time_from_datetime(dt, -30)
        self.assertAlmostEqual(lst_west, (18.697374558 - 2) % 24, places=4)

        # Test normalization to [0, 24) hours
        # Using a longitude that would push the time beyond 24 hours
        lst_wrap = sidereal_time_from_datetime(dt, 90)  # +6 hours
        self.assertLess(lst_wrap, 24.0)
        self.assertGreaterEqual(lst_wrap, 0.0)


if __name__ == "__main__":
    unittest.main()
