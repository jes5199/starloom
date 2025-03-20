"""Tests for ElementsParser."""

import csv
import unittest
from pathlib import Path

from starloom.horizons.observer_elements_parser import (
    ElementsParser,
    ObserverElementsQuantity,
)


class TestObserverElementsParser(unittest.TestCase):
    """Test ElementsParser."""

    def setUp(self):
        """Set up the test."""
        self.fixtures_dir = Path(__file__).parent.parent / "fixtures"
        self.elements_fixtures_dir = self.fixtures_dir / "elements"

        # Load fixture file
        with open(self.elements_fixtures_dir / "jupiter_single.txt", "r") as f:
            self.jupiter_single_response = f.read()

    def test_extract_csv_lines(self):
        """Test _extract_csv_lines method."""
        parser = ElementsParser(self.jupiter_single_response)
        csv_lines = parser._extract_csv_lines()
        self.assertTrue(len(csv_lines) > 0)
        # Header line should contain JDTDB
        header = csv_lines[0]
        self.assertIn("JDTDB", header)
        # Data line should contain numerical values
        self.assertIn("2460754", csv_lines[1])

    def test_map_columns_to_quantities(self):
        """Test _map_columns_to_quantities method."""
        parser = ElementsParser(self.jupiter_single_response)
        csv_lines = parser._extract_csv_lines()
        reader = csv.reader(csv_lines)
        headers = [h.strip() for h in next(reader)]

        col_map = parser._map_columns_to_quantities(headers)

        # We should have found some column mappings
        self.assertTrue(len(col_map) > 0)

        # Verify that the expected quantities are mapped
        expected_quantities = [
            ObserverElementsQuantity.JULIAN_DATE,
            ObserverElementsQuantity.CALENDAR_DATE,
            ObserverElementsQuantity.ECCENTRICITY,
            ObserverElementsQuantity.PERIAPSIS_DISTANCE,
            ObserverElementsQuantity.INCLINATION,
            ObserverElementsQuantity.ASCENDING_NODE_LONGITUDE,
            ObserverElementsQuantity.ARGUMENT_OF_PERIAPSIS,
            ObserverElementsQuantity.TIME_OF_PERIAPSIS,
            ObserverElementsQuantity.MEAN_MOTION,
            ObserverElementsQuantity.MEAN_ANOMALY,
            ObserverElementsQuantity.TRUE_ANOMALY,
            ObserverElementsQuantity.SEMI_MAJOR_AXIS,
            ObserverElementsQuantity.APOAPSIS_DISTANCE,
            ObserverElementsQuantity.ORBITAL_PERIOD,
        ]

        for col_idx, quantity in col_map.items():
            self.assertIn(quantity, expected_quantities)

    def test_jupiter_columns_mapping(self):
        """Test column mapping specifically for the Jupiter fixture."""
        parser = ElementsParser(self.jupiter_single_response)
        data = parser.parse()
        self.assertEqual(len(data), 1)

        jd, values = data[0]
        self.assertIsInstance(jd, float)

        # Check that all the quantities are present
        expected_quantities = [
            ObserverElementsQuantity.JULIAN_DATE,
            ObserverElementsQuantity.CALENDAR_DATE,
            ObserverElementsQuantity.ECCENTRICITY,
            ObserverElementsQuantity.PERIAPSIS_DISTANCE,
            ObserverElementsQuantity.INCLINATION,
            ObserverElementsQuantity.ASCENDING_NODE_LONGITUDE,
            ObserverElementsQuantity.ARGUMENT_OF_PERIAPSIS,
            ObserverElementsQuantity.TIME_OF_PERIAPSIS,
            ObserverElementsQuantity.MEAN_MOTION,
            ObserverElementsQuantity.MEAN_ANOMALY,
            ObserverElementsQuantity.TRUE_ANOMALY,
            ObserverElementsQuantity.SEMI_MAJOR_AXIS,
            ObserverElementsQuantity.APOAPSIS_DISTANCE,
            ObserverElementsQuantity.ORBITAL_PERIOD,
        ]

        for quantity in expected_quantities:
            if (
                quantity != ObserverElementsQuantity.JULIAN_DATE
            ):  # already in jd variable
                self.assertIn(quantity, values)

    def test_parse_jupiter_single(self):
        """Test parse method with Jupiter single data point."""
        parser = ElementsParser(self.jupiter_single_response)
        data = parser.parse()
        self.assertEqual(len(data), 1)

        jd, values = data[0]
        self.assertIsInstance(jd, float)

        # Check specific values
        self.assertEqual(jd, 2460754.333333333)

        if ObserverElementsQuantity.ECCENTRICITY in values:
            self.assertEqual(
                values[ObserverElementsQuantity.ECCENTRICITY], "4.829493868247705E-02"
            )

        if ObserverElementsQuantity.PERIAPSIS_DISTANCE in values:
            self.assertEqual(
                values[ObserverElementsQuantity.PERIAPSIS_DISTANCE],
                "7.408137812767066E+08",
            )

        if ObserverElementsQuantity.INCLINATION in values:
            self.assertEqual(
                values[ObserverElementsQuantity.INCLINATION], "1.303298428030365E+00"
            )

    def test_get_value(self):
        """Test get_value method."""
        parser = ElementsParser(self.jupiter_single_response)

        eccentricity = parser.get_value(ObserverElementsQuantity.ECCENTRICITY)
        self.assertEqual(eccentricity, "4.829493868247705E-02")

        periapsis_distance = parser.get_value(
            ObserverElementsQuantity.PERIAPSIS_DISTANCE
        )
        self.assertEqual(periapsis_distance, "7.408137812767066E+08")

        inclination = parser.get_value(ObserverElementsQuantity.INCLINATION)
        self.assertEqual(inclination, "1.303298428030365E+00")

    def test_get_values(self):
        """Test get_values method."""
        parser = ElementsParser(self.jupiter_single_response)

        # Get values for a specific quantity
        eccentricities = parser.get_values(ObserverElementsQuantity.ECCENTRICITY)
        self.assertEqual(len(eccentricities), 1)

        # Check format of the result
        jd, value = eccentricities[0]
        self.assertIsInstance(jd, float)
        self.assertEqual(value, "4.829493868247705E-02")

    def test_get_all_values(self):
        """Test get_all_values method."""
        parser = ElementsParser(self.jupiter_single_response)
        all_values = parser.get_all_values()
        self.assertEqual(len(all_values), 1)

        # Each item should be a tuple of (Julian date, dict of values)
        jd, values = all_values[0]
        self.assertIsInstance(jd, float)
        self.assertIsInstance(values, dict)

        # Check that we have all the expected quantities
        expected_quantities = [
            ObserverElementsQuantity.CALENDAR_DATE,
            ObserverElementsQuantity.ECCENTRICITY,
            ObserverElementsQuantity.PERIAPSIS_DISTANCE,
            ObserverElementsQuantity.INCLINATION,
            ObserverElementsQuantity.ASCENDING_NODE_LONGITUDE,
            ObserverElementsQuantity.ARGUMENT_OF_PERIAPSIS,
            ObserverElementsQuantity.TIME_OF_PERIAPSIS,
            ObserverElementsQuantity.MEAN_MOTION,
            ObserverElementsQuantity.MEAN_ANOMALY,
            ObserverElementsQuantity.TRUE_ANOMALY,
            ObserverElementsQuantity.SEMI_MAJOR_AXIS,
            ObserverElementsQuantity.APOAPSIS_DISTANCE,
            ObserverElementsQuantity.ORBITAL_PERIOD,
        ]

        for quantity in expected_quantities:
            self.assertIn(quantity, values)


if __name__ == "__main__":
    unittest.main()
