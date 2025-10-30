"""Tests for Planet enum."""

import unittest
from starloom.planet import Planet


class TestPlanetEnum(unittest.TestCase):
    """Test Planet enum values."""

    def test_lunar_north_node_exists(self):
        """Test that LUNAR_NORTH_NODE is defined."""
        self.assertTrue(hasattr(Planet, "LUNAR_NORTH_NODE"))

    def test_lunar_north_node_value(self):
        """Test that LUNAR_NORTH_NODE has unique identifier value."""
        # Uses a unique marker value to avoid enum aliasing with MOON
        # Actual Horizons ID (301) is used in OrbitalElementsEphemeris
        self.assertEqual(Planet.LUNAR_NORTH_NODE.value, "lunar_north_node")

    def test_lunar_north_node_name(self):
        """Test that LUNAR_NORTH_NODE has correct name."""
        self.assertEqual(Planet.LUNAR_NORTH_NODE.name, "LUNAR_NORTH_NODE")


if __name__ == "__main__":
    unittest.main()
