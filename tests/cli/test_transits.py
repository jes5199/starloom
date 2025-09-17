"""Tests for the transits CLI command."""

from datetime import datetime, timezone
import unittest
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from starloom.cli.transits import transits
from starloom.planet import Planet
from starloom.transits import ASPECT_ANGLES, TransitEvent
from starloom.space_time.julian import julian_from_datetime


class TestTransitsCLI(unittest.TestCase):
    """Validate CLI wiring for transit generation."""

    @patch("starloom.cli.transits.TransitFinder")
    @patch("starloom.cli.transits.get_ephemeris_factory")
    def test_transits_csv_output(self, mock_factory, mock_finder_class) -> None:
        mock_ephemeris = MagicMock()
        factory_mock = MagicMock(return_value=mock_ephemeris)
        mock_factory.return_value = factory_mock

        event_time = datetime(2024, 1, 5, tzinfo=timezone.utc)
        event = TransitEvent(
            primary=Planet.MARS,
            secondary=Planet.JUPITER,
            aspect="CONJUNCTION",
            target_angle=ASPECT_ANGLES["CONJUNCTION"],
            julian_date=julian_from_datetime(event_time),
            primary_longitude=10.0,
            secondary_longitude=10.0,
        )

        mock_finder = MagicMock()
        mock_finder.find_transits.return_value = [event]
        mock_finder_class.return_value = mock_finder

        runner = CliRunner()
        result = runner.invoke(
            transits,
            [
                "mars",
                "jupiter",
                "--start",
                "2024-01-01",
                "--stop",
                "2024-12-31",
                "--step",
                "5d",
                "--data",
                "./weftballs",
                "--format",
                "csv",
            ],
        )

        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertIn("primary,secondary,aspect", result.output)
        self.assertIn("MARS,JUPITER,CONJUNCTION", result.output)

        mock_factory.assert_called_once_with("weft")
        self.assertEqual(factory_mock.call_count, 1)
        mock_finder_class.assert_called_once_with(mock_ephemeris, mock_ephemeris)

        args, kwargs = mock_finder.find_transits.call_args
        self.assertEqual(args[0], Planet.MARS)
        self.assertEqual(args[1], Planet.JUPITER)
        self.assertEqual(args[2].strftime("%Y-%m-%d"), "2024-01-01")
        self.assertEqual(args[3].strftime("%Y-%m-%d"), "2024-12-31")
        self.assertEqual(kwargs["step"], "5d")
        self.assertEqual(kwargs["aspects"], ASPECT_ANGLES)


if __name__ == "__main__":
    unittest.main()
