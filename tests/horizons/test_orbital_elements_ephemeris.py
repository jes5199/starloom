"""Tests for OrbitalElementsEphemeris."""

import unittest
from datetime import datetime, timezone
from starloom.horizons.orbital_elements_ephemeris import OrbitalElementsEphemeris
from starloom.ephemeris.quantities import Quantity
from starloom.horizons.time_spec import TimeSpec


class TestOrbitalElementsEphemeris(unittest.TestCase):
    """Test OrbitalElementsEphemeris class."""

    def test_init_default_center(self):
        """Test initialization with default center."""
        ephemeris = OrbitalElementsEphemeris()
        self.assertEqual(ephemeris.center, "10")

    def test_init_custom_center(self):
        """Test initialization with custom center."""
        ephemeris = OrbitalElementsEphemeris(center="500@0")
        self.assertEqual(ephemeris.center, "500@0")


class TestOrbitalElementsEphemerisGetPosition(unittest.TestCase):
    """Test get_planet_position method."""

    def test_get_moon_ascending_node_with_datetime(self):
        """Test getting Moon's ascending node with datetime."""
        ephemeris = OrbitalElementsEphemeris()

        # Use a fixed date for reproducible test
        test_date = datetime(2024, 3, 15, 12, 0, 0, tzinfo=timezone.utc)

        result = ephemeris.get_planet_position("301", test_date)

        # Should return at least ASCENDING_NODE_LONGITUDE
        self.assertIn(Quantity.ASCENDING_NODE_LONGITUDE, result)

        # Value should be a valid degree (0-360)
        longitude = float(result[Quantity.ASCENDING_NODE_LONGITUDE])
        self.assertGreaterEqual(longitude, 0.0)
        self.assertLess(longitude, 360.0)

    def test_get_moon_ascending_node_with_julian_date(self):
        """Test getting Moon's ascending node with Julian date."""
        ephemeris = OrbitalElementsEphemeris()

        # Julian date for 2024-03-15 12:00:00 UTC
        jd = 2460384.0

        result = ephemeris.get_planet_position("301", jd)

        self.assertIn(Quantity.ASCENDING_NODE_LONGITUDE, result)
        longitude = float(result[Quantity.ASCENDING_NODE_LONGITUDE])
        self.assertGreaterEqual(longitude, 0.0)
        self.assertLess(longitude, 360.0)

    def test_get_position_returns_multiple_quantities(self):
        """Test that get_position returns multiple orbital elements."""
        ephemeris = OrbitalElementsEphemeris()
        test_date = datetime(2024, 3, 15, 12, 0, 0, tzinfo=timezone.utc)

        result = ephemeris.get_planet_position("301", test_date)

        # Should return multiple orbital elements
        self.assertGreater(len(result), 1)

        # Should include common orbital elements
        expected_quantities = [
            Quantity.ASCENDING_NODE_LONGITUDE,
            Quantity.ECCENTRICITY,
            Quantity.INCLINATION,
        ]
        for quantity in expected_quantities:
            self.assertIn(quantity, result)


class TestOrbitalElementsEphemerisGetPositions(unittest.TestCase):
    """Test get_planet_positions method."""

    def test_get_moon_ascending_node_time_range(self):
        """Test getting Moon's ascending node over time range."""
        ephemeris = OrbitalElementsEphemeris()

        # Query 6 days with 1-day step (March 15-20, inclusive)
        start = datetime(2024, 3, 15, 0, 0, 0, tzinfo=timezone.utc)
        time_spec = TimeSpec.from_range(
            start=start,
            stop=datetime(2024, 3, 20, 0, 0, 0, tzinfo=timezone.utc),
            step="1d",
        )

        result = ephemeris.get_planet_positions("301", time_spec)

        # Should return 6 data points (inclusive endpoints)
        self.assertEqual(len(result), 6)

        # Each data point should have ASCENDING_NODE_LONGITUDE
        for jd, values in result.items():
            self.assertIsInstance(jd, float)
            self.assertIn(Quantity.ASCENDING_NODE_LONGITUDE, values)
            longitude = float(values[Quantity.ASCENDING_NODE_LONGITUDE])
            self.assertGreaterEqual(longitude, 0.0)
            self.assertLess(longitude, 360.0)

    def test_get_positions_multiple_quantities(self):
        """Test that get_positions returns multiple orbital elements."""
        ephemeris = OrbitalElementsEphemeris()

        start = datetime(2024, 3, 15, 0, 0, 0, tzinfo=timezone.utc)
        time_spec = TimeSpec.from_range(
            start=start,
            stop=datetime(2024, 3, 17, 0, 0, 0, tzinfo=timezone.utc),
            step="1d",
        )

        result = ephemeris.get_planet_positions("301", time_spec)

        # Each data point should have multiple quantities
        for jd, values in result.items():
            self.assertGreater(len(values), 1)
            self.assertIn(Quantity.ASCENDING_NODE_LONGITUDE, values)
            self.assertIn(Quantity.ECCENTRICITY, values)
            self.assertIn(Quantity.INCLINATION, values)


if __name__ == "__main__":
    unittest.main()
