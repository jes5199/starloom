"""Tests for the WeftEphemeris class."""

import os
import pytest
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from starloom.ephemeris.quantities import Quantity
from starloom.ephemeris.time_spec import TimeSpec
from starloom.weft_ephemeris.ephemeris import WeftEphemeris
from starloom.space_time.julian import datetime_to_julian


@pytest.fixture
def mercury_weftball_path():
    """Fixture to provide path to the mercury weftball."""
    # Check if the weftball exists at project root
    weftball_path = Path("mercury_weftball.tar.gz")
    if not weftball_path.exists():
        pytest.skip("Mercury weftball not found for testing")
    return str(weftball_path.absolute())


class TestWeftEphemeris:
    """Test the WeftEphemeris class."""

    def test_init(self, mercury_weftball_path):
        """Test initialization with a valid path."""
        ephemeris = WeftEphemeris(data=mercury_weftball_path)
        assert ephemeris.data_dir == mercury_weftball_path

        # Test backward compatibility
        ephemeris_old = WeftEphemeris(data_dir=mercury_weftball_path)
        assert ephemeris_old.data_dir == mercury_weftball_path

        # Test precedence
        ephemeris_both = WeftEphemeris(data_dir="ignored", data=mercury_weftball_path)
        assert ephemeris_both.data_dir == mercury_weftball_path

    def test_get_planet_position(self, mercury_weftball_path):
        """Test getting a single position."""
        ephemeris = WeftEphemeris(data=mercury_weftball_path)

        # Use a specific date within the weftball's range
        test_date = datetime(2025, 3, 22, tzinfo=timezone.utc)

        # Get the position
        position = ephemeris.get_planet_position("mercury", test_date)

        # Check that we got required quantities
        assert Quantity.ECLIPTIC_LONGITUDE in position
        assert Quantity.ECLIPTIC_LATITUDE in position
        assert Quantity.DELTA in position

        # Check that the values are reasonable
        assert 0 <= position[Quantity.ECLIPTIC_LONGITUDE] < 360
        assert -90 <= position[Quantity.ECLIPTIC_LATITUDE] <= 90
        assert position[Quantity.DELTA] > 0  # Distance should be positive

    def test_get_planet_positions_date_list(self, mercury_weftball_path):
        """Test getting multiple positions from a date list."""
        ephemeris = WeftEphemeris(data=mercury_weftball_path)

        # Create some test dates within the weftball's range
        test_dates = [
            datetime(2025, 3, 22, tzinfo=timezone.utc),
            datetime(2025, 3, 23, tzinfo=timezone.utc),
            datetime(2025, 3, 24, tzinfo=timezone.utc),
        ]

        # Create a TimeSpec from the dates
        time_spec = TimeSpec.from_dates(test_dates)

        # Get the positions
        positions = ephemeris.get_planet_positions("mercury", time_spec)

        # Check that we got the expected number of positions
        assert len(positions) == len(test_dates)

        # Check that the keys are Julian dates
        for date in test_dates:
            julian_date = datetime_to_julian(date)
            assert any(abs(jd - julian_date) < 0.001 for jd in positions.keys())

        # Check the first position
        first_jd = min(positions.keys())
        first_position = positions[first_jd]

        # Verify required quantities
        assert Quantity.ECLIPTIC_LONGITUDE in first_position
        assert Quantity.ECLIPTIC_LATITUDE in first_position
        assert Quantity.DELTA in first_position

    def test_get_planet_positions_date_range(self, mercury_weftball_path):
        """Test getting multiple positions from a date range."""
        ephemeris = WeftEphemeris(data=mercury_weftball_path)

        # Create a date range within the weftball's range
        start_date = datetime(2025, 3, 22, tzinfo=timezone.utc)
        end_date = datetime(2025, 3, 24, tzinfo=timezone.utc)

        # Create a TimeSpec with a 1-day step
        time_spec = TimeSpec.from_range(start_date, end_date, "1d")

        # Get the positions
        positions = ephemeris.get_planet_positions("mercury", time_spec)

        # We should have 3 positions (start, start+1d, start+2d)
        assert len(positions) == 3

        # Verify all positions have the required data
        for jd, pos in positions.items():
            assert Quantity.ECLIPTIC_LONGITUDE in pos
            assert Quantity.ECLIPTIC_LATITUDE in pos
            assert Quantity.DELTA in pos

    def test_file_not_found(self):
        """Test handling of a non-existent weftball."""
        # Use a non-existent path
        ephemeris = WeftEphemeris(data="/path/to/nonexistent/weftball.tar.gz")

        # Should raise FileNotFoundError when we try to get data
        with pytest.raises(FileNotFoundError):
            ephemeris.get_planet_position("mercury")

    def test_invalid_planet(self, mercury_weftball_path):
        """Test handling of an invalid planet name."""
        ephemeris = WeftEphemeris(data=mercury_weftball_path)

        # Create a temporary directory for the weftball
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a copy of the mercury weftball with a different planet name
            temp_weftball = os.path.join(temp_dir, "nonexistent_weftball.tar.gz")
            shutil.copy(mercury_weftball_path, temp_weftball)

            # Initialize with the temporary directory
            ephemeris = WeftEphemeris(data=temp_dir)

            # Should have no data for a non-existent planet
            position = ephemeris.get_planet_position("nonexistent")

            # Should return an empty dict or one with default values
            assert not position or all(val == 0.0 for val in position.values())
