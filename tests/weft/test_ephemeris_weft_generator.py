"""Tests for ephemeris weft generator detection logic."""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from starloom.weft.ephemeris_weft_generator import generate_weft_file
from starloom.planet import Planet
from starloom.ephemeris.quantities import Quantity


class TestEphemerisWeftGeneratorDetection(unittest.TestCase):
    """Test detection and routing logic in generate_weft_file."""

    @patch("starloom.weft.ephemeris_weft_generator.OrbitalElementsEphemeris")
    @patch("starloom.weft.ephemeris_weft_generator.WeftWriter")
    @patch("starloom.weft.ephemeris_weft_generator.EphemerisDataSource")
    @patch("starloom.weft.ephemeris_weft_generator.get_recommended_blocks")
    def test_lunar_node_uses_orbital_elements_ephemeris(
        self,
        mock_get_blocks,
        mock_data_source,
        mock_writer,
        mock_orbital_ephemeris,
    ):
        """Test that lunar node planet uses OrbitalElementsEphemeris."""
        # Setup mocks
        mock_get_blocks.return_value = {"monthly": True}
        mock_ephemeris_instance = MagicMock()
        mock_orbital_ephemeris.return_value = mock_ephemeris_instance

        mock_writer_instance = MagicMock()
        mock_writer.return_value = mock_writer_instance
        mock_weft_file = MagicMock()
        mock_writer_instance.create_multi_precision_file.return_value = mock_weft_file

        # Call with LUNAR_NORTH_NODE
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)

        generate_weft_file(
            planet=Planet.LUNAR_NORTH_NODE,
            quantity=Quantity.ASCENDING_NODE_LONGITUDE,
            start_date=start,
            end_date=end,
            output_path="/tmp/test.weft",
        )

        # Verify OrbitalElementsEphemeris was instantiated
        mock_orbital_ephemeris.assert_called_once()

    @patch("starloom.weft.ephemeris_weft_generator.HorizonsEphemeris")
    @patch("starloom.weft.ephemeris_weft_generator.WeftWriter")
    @patch("starloom.weft.ephemeris_weft_generator.EphemerisDataSource")
    @patch("starloom.weft.ephemeris_weft_generator.get_recommended_blocks")
    def test_regular_planet_uses_horizons_ephemeris(
        self,
        mock_get_blocks,
        mock_data_source,
        mock_writer,
        mock_horizons_ephemeris,
    ):
        """Test that regular planet uses HorizonsEphemeris."""
        # Setup mocks
        mock_get_blocks.return_value = {"monthly": True}
        mock_ephemeris_instance = MagicMock()
        mock_horizons_ephemeris.return_value = mock_ephemeris_instance

        mock_writer_instance = MagicMock()
        mock_writer.return_value = mock_writer_instance
        mock_weft_file = MagicMock()
        mock_writer_instance.create_multi_precision_file.return_value = mock_weft_file

        # Call with regular planet (Mars)
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)

        generate_weft_file(
            planet=Planet.MARS,
            quantity=Quantity.ECLIPTIC_LONGITUDE,
            start_date=start,
            end_date=end,
            output_path="/tmp/test.weft",
        )

        # Verify HorizonsEphemeris was instantiated
        mock_horizons_ephemeris.assert_called_once()


if __name__ == "__main__":
    unittest.main()
