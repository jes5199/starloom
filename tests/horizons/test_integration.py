"""Integration tests for Horizons API functionality."""

from click.testing import CliRunner

from starloom.cli.horizons import horizons


def test_single_time_query():
    """Test querying Horizons for a single time."""
    runner = CliRunner()
    # Use a fixed date to make the test deterministic
    result = runner.invoke(
        horizons, ["ecliptic", "venus", "--date", "2025-03-19T20:00:00"]
    )

    assert result.exit_code == 0
    # Check for expected parts of the response
    assert "Target body name: Venus (299)" in result.output
    assert "Center body name: Earth (399)" in result.output
    assert "2025-Mar-19 20:00:00.000" in result.output
    # Verify we got the expected columns
    assert "delta" in result.output
    assert "deldot" in result.output
    assert "ObsEcLon" in result.output
    assert "ObsEcLat" in result.output


def test_time_range_query():
    """Test querying Horizons for a time range."""
    runner = CliRunner()
    result = runner.invoke(
        horizons,
        [
            "ecliptic",
            "venus",
            "--start",
            "2025-03-19T20:00:00",
            "--stop",
            "2025-03-19T22:00:00",
            "--step",
            "1h",
        ],
    )

    assert result.exit_code == 0
    # Check for expected parts of the response
    assert "Target body name: Venus (299)" in result.output
    assert "Center body name: Earth (399)" in result.output
    # Check that we got multiple data points
    assert "2025-Mar-19 20:00:00.000" in result.output
    assert "2025-Mar-19 21:00:00.000" in result.output
    assert "2025-Mar-19 22:00:00.000" in result.output
    # Verify we got the expected columns
    assert "delta" in result.output
    assert "deldot" in result.output
    assert "ObsEcLon" in result.output
    assert "ObsEcLat" in result.output


def test_elements_single_time_query():
    """Test querying Horizons for orbital elements at a single time."""
    runner = CliRunner()
    # Use a fixed date to make the test deterministic
    result = runner.invoke(
        horizons, ["elements", "mars", "--date", "2025-03-19T20:00:00"]
    )

    assert result.exit_code == 0
    # Check for expected parts of the response
    assert "Target body name: Mars (499)" in result.output
    assert "Center body name: Sun (10)" in result.output
    assert "2025-Mar-19 20:00:00.000" in result.output
    # Verify we got the expected orbital elements
    assert "EC" in result.output  # Eccentricity
    assert "QR" in result.output  # Periapsis distance
    assert "IN" in result.output  # Inclination
    assert "OM" in result.output  # Longitude of Ascending Node
    assert "W" in result.output  # Argument of Perifocus
    assert "MA" in result.output  # Mean anomaly
    assert "TA" in result.output  # True anomaly


def test_elements_time_range_query():
    """Test querying Horizons for orbital elements over a time range."""
    runner = CliRunner()
    result = runner.invoke(
        horizons,
        [
            "elements",
            "mars",
            "--start",
            "2025-03-19T20:00:00",
            "--stop",
            "2025-03-19T22:00:00",
            "--step",
            "1h",
        ],
    )

    assert result.exit_code == 0
    # Check for expected parts of the response
    assert "Target body name: Mars (499)" in result.output
    assert "Center body name: Sun (10)" in result.output
    # Check that we got multiple data points
    assert "2025-Mar-19 20:00:00.000" in result.output
    assert "2025-Mar-19 21:00:00.000" in result.output
    assert "2025-Mar-19 22:00:00.000" in result.output
    # Verify we got the expected orbital elements
    assert "EC" in result.output  # Eccentricity
    assert "QR" in result.output  # Periapsis distance
    assert "IN" in result.output  # Inclination
    assert "OM" in result.output  # Longitude of Ascending Node
    assert "W" in result.output  # Argument of Perifocus
    assert "MA" in result.output  # Mean anomaly
    assert "TA" in result.output  # True anomaly


def test_invalid_planet():
    """Test querying Horizons with an invalid planet name."""
    runner = CliRunner()
    result = runner.invoke(
        horizons, ["ecliptic", "invalid_planet", "--date", "2025-03-19T20:00:00"]
    )

    assert result.exit_code != 0
    assert "Invalid planet" in result.output


def test_invalid_date_format():
    """Test querying Horizons with an invalid date format."""
    runner = CliRunner()
    result = runner.invoke(horizons, ["ecliptic", "venus", "--date", "invalid_date"])

    assert result.exit_code != 0
