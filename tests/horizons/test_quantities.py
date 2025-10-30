"""Tests for horizons quantity mappings."""

import unittest
from starloom.horizons.quantities import OrbitalElementsQuantityToQuantity
from starloom.horizons.parsers import OrbitalElementsQuantity
from starloom.ephemeris.quantities import Quantity


class TestOrbitalElementsQuantityMapping(unittest.TestCase):
    """Test OrbitalElementsQuantity to Quantity mapping."""

    def test_mapping_exists(self):
        """Test that the mapping dictionary exists."""
        self.assertIsInstance(OrbitalElementsQuantityToQuantity, dict)

    def test_ascending_node_longitude_mapping(self):
        """Test ASCENDING_NODE_LONGITUDE maps correctly."""
        result = OrbitalElementsQuantityToQuantity[
            OrbitalElementsQuantity.ASCENDING_NODE_LONGITUDE
        ]
        self.assertEqual(result, Quantity.ASCENDING_NODE_LONGITUDE)

    def test_eccentricity_mapping(self):
        """Test ECCENTRICITY maps correctly."""
        result = OrbitalElementsQuantityToQuantity[OrbitalElementsQuantity.ECCENTRICITY]
        self.assertEqual(result, Quantity.ECCENTRICITY)

    def test_inclination_mapping(self):
        """Test INCLINATION maps correctly."""
        result = OrbitalElementsQuantityToQuantity[OrbitalElementsQuantity.INCLINATION]
        self.assertEqual(result, Quantity.INCLINATION)

    def test_semi_major_axis_mapping(self):
        """Test SEMI_MAJOR_AXIS maps correctly."""
        result = OrbitalElementsQuantityToQuantity[
            OrbitalElementsQuantity.SEMI_MAJOR_AXIS
        ]
        self.assertEqual(result, Quantity.SEMI_MAJOR_AXIS)

    def test_periapsis_distance_mapping(self):
        """Test PERIAPSIS_DISTANCE maps correctly."""
        result = OrbitalElementsQuantityToQuantity[
            OrbitalElementsQuantity.PERIAPSIS_DISTANCE
        ]
        self.assertEqual(result, Quantity.PERIAPSIS_DISTANCE)


if __name__ == "__main__":
    unittest.main()
