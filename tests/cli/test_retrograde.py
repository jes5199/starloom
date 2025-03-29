"""Tests for the retrograde CLI command."""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from click.testing import CliRunner

from starloom.cli.retrograde import retrograde
from starloom.planet import Planet
from starloom.retrograde.finder import RetrogradePeriod


class TestRetrogradeCommand(unittest.TestCase):
    """Tests for the retrograde CLI command."""

    @patch("starloom.cli.retrograde.RetrogradeFinder")
    @patch("starloom.cli.retrograde.get_ephemeris_factory")
    def test_retrograde_handles_mid_retrograde(self, mock_factory, mock_finder_class):
        """Test that the retrograde command can handle starting in the middle of a retrograde period."""
        # Setup mock factory and ephemeris
        mock_ephemeris = MagicMock()
        mock_factory.return_value.return_value = mock_ephemeris

        # Setup mock retrograde finder
        mock_finder = MagicMock()
        mock_finder_class.return_value = mock_finder

        # Create a retrograde period that starts before our search period
        retrograde_start = datetime(2024, 11, 15, tzinfo=timezone.utc)
        from starloom.space_time.julian import julian_from_datetime

        retrograde_start_jd = julian_from_datetime(retrograde_start)

        # Create a RetrogradePeriod object with a station_retrograde date before our search start
        # and a station_direct date within our search range
        period = RetrogradePeriod(
            planet=Planet.MARS,
            station_retrograde=(retrograde_start_jd, 120.0),  # Before search start
            station_direct=(retrograde_start_jd + 60, 110.0),  # Within search range
            pre_shadow_start=(retrograde_start_jd - 30, 110.0),
            post_shadow_end=(retrograde_start_jd + 90, 120.0),
        )

        # Setup mock finder to return our retrograde period
        mock_finder.find_retrograde_periods.return_value = [period]

        # Create a CliRunner to test our command
        runner = CliRunner()

        # Run the retrograde command with a start date after the retrograde began
        search_start = "2025-01-01"  # After retrograde began
        search_end = "2025-12-31"
        result = runner.invoke(
            retrograde,
            ["mars", "--start", search_start, "--stop", search_end, "--format", "text"],
        )

        # Check that the command executed successfully
        self.assertEqual(result.exit_code, 0)

        # Check that the output contains the retrograde period
        self.assertIn("Found 1 retrograde period(s) for MARS", result.output)

        # Verify that the finder was created with our mocked ephemeris
        mock_finder_class.assert_called_once()
        args, kwargs = mock_finder_class.call_args
        self.assertEqual(kwargs["planet_ephemeris"], mock_ephemeris)

        # Verify that find_retrograde_periods was called with the correct parameters
        mock_finder.find_retrograde_periods.assert_called_once()
        args, kwargs = mock_finder.find_retrograde_periods.call_args
        self.assertEqual(kwargs["planet"], Planet.MARS)

        # The key test: verify that the start date passed to find_retrograde_periods
        # matches what we provided in the CLI command
        self.assertEqual(kwargs["start_date"].strftime("%Y-%m-%d"), search_start)
        self.assertEqual(kwargs["end_date"].strftime("%Y-%m-%d"), search_end)


if __name__ == "__main__":
    unittest.main()
