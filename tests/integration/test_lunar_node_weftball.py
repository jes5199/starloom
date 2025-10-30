"""Integration test for lunar node weftball generation."""

import unittest
import tempfile
import os
from datetime import datetime, timezone

from starloom.weft.ephemeris_weft_generator import generate_weft_file
from starloom.planet import Planet
from starloom.ephemeris.quantities import Quantity
from starloom.weft.weft_reader import WeftReader


class TestLunarNodeWeftballIntegration(unittest.TestCase):
    """Test end-to-end lunar node weftball generation."""

    def test_generate_lunar_node_weft_file(self):
        """Test generating a weft file for lunar north node."""
        # Create temporary output file
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".weft", delete=False
        ) as tmp:
            output_path = tmp.name

        try:
            # Generate weft file for 30 days with hourly steps
            # (Need sufficient data density for blocks to be enabled)
            start = datetime(2024, 3, 1, 0, 0, 0, tzinfo=timezone.utc)
            end = datetime(2024, 3, 31, 0, 0, 0, tzinfo=timezone.utc)

            result_path = generate_weft_file(
                planet=Planet.LUNAR_NORTH_NODE,
                quantity=Quantity.ASCENDING_NODE_LONGITUDE,
                start_date=start,
                end_date=end,
                output_path=output_path,
                step_hours="1h",
                custom_timespan="2024-03",
            )

            # Verify file was created
            self.assertEqual(result_path, output_path)
            self.assertTrue(os.path.exists(output_path))
            self.assertGreater(os.path.getsize(output_path), 0)

            # Read the weft file and verify contents
            reader = WeftReader()
            reader.load_file(output_path)

            # Verify preamble contains expected information
            preamble = reader.file.preamble
            # Should contain Moon's ID (301) since we query Moon's orbital elements
            self.assertIn("301", preamble)
            self.assertIn("ascending_node_longitude", preamble.lower())

            # Get a value from the middle of the range
            test_date = datetime(2024, 3, 15, 12, 0, 0, tzinfo=timezone.utc)
            value = reader.get_value(test_date)

            # Verify value is a valid longitude (0-360 degrees)
            self.assertIsInstance(value, float)
            self.assertGreaterEqual(value, 0.0)
            self.assertLess(value, 360.0)

        finally:
            # Clean up
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_lunar_node_with_string_planet_name(self):
        """Test that string planet name 'lunar_north_node' works."""
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".weft", delete=False
        ) as tmp:
            output_path = tmp.name

        try:
            start = datetime(2024, 3, 1, 0, 0, 0, tzinfo=timezone.utc)
            end = datetime(2024, 3, 3, 0, 0, 0, tzinfo=timezone.utc)

            # Use string planet name
            generate_weft_file(
                planet="lunar_north_node",
                quantity=Quantity.ASCENDING_NODE_LONGITUDE,
                start_date=start,
                end_date=end,
                output_path=output_path,
                step_hours="24h",
            )

            # Verify file was created
            self.assertTrue(os.path.exists(output_path))
            self.assertGreater(os.path.getsize(output_path), 0)

        finally:
            # Clean up
            if os.path.exists(output_path):
                os.unlink(output_path)


if __name__ == "__main__":
    unittest.main()
