"""Tests for OrbitalElementsEphemeris."""

import unittest
from starloom.horizons.orbital_elements_ephemeris import OrbitalElementsEphemeris


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


if __name__ == "__main__":
    unittest.main()
