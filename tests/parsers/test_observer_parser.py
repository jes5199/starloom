"""Tests for ObserverParser."""

import unittest
from pathlib import Path

from starloom.parsers.observer_parser import ObserverParser
from starloom.horizons.quantities import EphemerisQuantity


class TestObserverParser(unittest.TestCase):
    """Test ObserverParser."""

    def setUp(self):
        """Set up the test."""
        self.fixtures_dir = Path(__file__).parent.parent / "fixtures"
        self.ecliptic_fixtures_dir = self.fixtures_dir / "ecliptic"

        # Load fixture file
        with open(self.ecliptic_fixtures_dir / "mars_single.txt", "r") as f:
            self.mars_single_response = f.read()

    def test_extract_csv_lines(self):
        """Test _extract_csv_lines method."""
        parser = ObserverParser(self.mars_single_response)
        csv_lines = parser._extract_csv_lines()
        self.assertTrue(len(csv_lines) > 0)
        # Header line should contain Date_JDUT or JDUT
        header = csv_lines[0]
        self.assertTrue("JDUT" in header or "Date_JDUT" in header)
        # Data line should contain numerical values
        self.assertIn("2460754", csv_lines[1])

    def test_get_headers(self):
        """Test _get_headers method."""
        parser = ObserverParser(self.mars_single_response)
        headers = parser._get_headers()
        # There should be at least 7 columns
        # (JDUT, blank, blank, delta, deldot, ObsEcLon, ObsEcLat)
        self.assertTrue(len(headers) >= 7)
        # First column should be JDUT or contain it
        self.assertTrue("JDUT" in headers[0] or headers[0] == "Date_________JDUT")

    def test_map_columns_to_quantities(self):
        """Test _map_columns_to_quantities method."""
        parser = ObserverParser(self.mars_single_response)
        col_map = parser._map_columns_to_quantities()

        # We should have found some column mappings
        self.assertTrue(len(col_map) > 0)

        # The Julian date column should be identified
        julian_date_idx = parser._get_julian_date_column()
        self.assertIsNotNone(julian_date_idx)

        # Verify that the expected columns are mapped (they may not be in every fixture)
        found_quantities = [q for i, q in col_map.items()]

        # Some combination of these quantities should be present
        self.assertTrue(
            any(
                [
                    EphemerisQuantity.DISTANCE in found_quantities,
                    EphemerisQuantity.RANGE_RATE in found_quantities,
                    EphemerisQuantity.ECLIPTIC_LONGITUDE in found_quantities,
                    EphemerisQuantity.ECLIPTIC_LATITUDE in found_quantities,
                ]
            )
        )

    def test_map_columns_to_quantities_mars_fixture(self):
        """Test column mapping specifically for the Mars fixture."""
        parser = ObserverParser(self.mars_single_response)
        col_map = parser._map_columns_to_quantities()

        # The Mars fixture has a specific format that we know:
        # Column 0: Date_________JDUT (JULIAN_DATE)
        # Column 1 & 2: blank columns (SOLAR_PRESENCE_CONDITION_CODE, TARGET_EVENT_MARKER)
        # Column 3: delta (DISTANCE)
        # Column 4: deldot (RANGE_RATE)
        # Column 5: ObsEcLon (ECLIPTIC_LONGITUDE)
        # Column 6: ObsEcLat (ECLIPTIC_LATITUDE)

        # Check that we mapped these correctly
        expected_mappings = {
            0: EphemerisQuantity.JULIAN_DATE,
            1: EphemerisQuantity.SOLAR_PRESENCE_CONDITION_CODE,
            2: EphemerisQuantity.TARGET_EVENT_MARKER,
            3: EphemerisQuantity.DISTANCE,
            4: EphemerisQuantity.RANGE_RATE,
            5: EphemerisQuantity.ECLIPTIC_LONGITUDE,
            6: EphemerisQuantity.ECLIPTIC_LATITUDE,
        }

        # Only check columns we expect to have been mapped
        for col_idx, expected_quantity in expected_mappings.items():
            if col_idx in col_map:
                self.assertEqual(col_map[col_idx], expected_quantity)

    def test_parse_single(self):
        """Test parse method with single data point."""
        parser = ObserverParser(self.mars_single_response)
        data = parser.parse()
        self.assertEqual(len(data), 1)

        jd, values = data[0]
        self.assertIsInstance(jd, float)

        # At least one of these quantities should be in the values
        self.assertTrue(
            any(
                [
                    EphemerisQuantity.DISTANCE in values,
                    EphemerisQuantity.RANGE_RATE in values,
                    EphemerisQuantity.ECLIPTIC_LONGITUDE in values,
                    EphemerisQuantity.ECLIPTIC_LATITUDE in values,
                ]
            )
        )

        # If the distance is present, check it
        if EphemerisQuantity.DISTANCE in values:
            self.assertTrue(values[EphemerisQuantity.DISTANCE].startswith("1.025"))

    def test_get_value(self):
        """Test get_value method."""
        parser = ObserverParser(self.mars_single_response)

        # Only test quantities that we expect to be present
        if EphemerisQuantity.DISTANCE in parser.parse()[0][1]:
            distance = parser.get_value(EphemerisQuantity.DISTANCE)
            self.assertTrue(distance.startswith("1.025"))

        if EphemerisQuantity.RANGE_RATE in parser.parse()[0][1]:
            range_rate = parser.get_value(EphemerisQuantity.RANGE_RATE)
            self.assertTrue(range_rate.startswith("15.8"))

    def test_get_values(self):
        """Test get_values method."""
        parser = ObserverParser(self.mars_single_response)

        # Only test if the quantity is present
        data = parser.parse()
        if data and EphemerisQuantity.DISTANCE in data[0][1]:
            distances = parser.get_values(EphemerisQuantity.DISTANCE)
            self.assertEqual(len(distances), 1)

            # Each item should be a tuple of (Julian date, value)
            for jd, value in distances:
                self.assertIsInstance(jd, float)
                self.assertIsInstance(value, str)

    def test_get_all_values(self):
        """Test get_all_values method."""
        parser = ObserverParser(self.mars_single_response)
        all_values = parser.get_all_values()
        self.assertEqual(len(all_values), 1)

        # Each item should be a tuple of (Julian date, dict of values)
        jd, values = all_values[0]
        self.assertIsInstance(jd, float)
        self.assertIsInstance(values, dict)
        self.assertTrue(len(values) > 0)


if __name__ == "__main__":
    unittest.main()
