"""Tests for OrbitalElementsEphemeris."""

import unittest
from datetime import datetime, timezone
from starloom.horizons.orbital_elements_ephemeris import OrbitalElementsEphemeris
from starloom.ephemeris.quantities import Quantity


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


if __name__ == "__main__":
    unittest.main()
