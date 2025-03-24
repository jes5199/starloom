import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import os

from starloom.horizons.ephemeris import HorizonsEphemeris
from starloom.planet import Planet
from starloom.horizons.location import Location
from starloom.horizons.quantities import EphemerisQuantity
from starloom.ephemeris import Quantity
from starloom.ephemeris.time_spec import TimeSpec


def read_fixture_file(filename):
    """Read a fixture file from the tests/fixtures directory."""
    fixture_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "fixtures", filename
    )
    with open(fixture_path, "r") as f:
        return f.read()


@pytest.fixture
def mars_single_response():
    """Return the Mars single position fixture response."""
    return read_fixture_file("ecliptic/mars_single.txt")


@pytest.fixture
def venus_single_response():
    """Return the Venus single position fixture response."""
    return read_fixture_file("ecliptic/venus_single.txt")


@pytest.fixture
def mars_range_response():
    """Return the Mars range position fixture response."""
    return read_fixture_file("ecliptic/mars_range.txt")


@pytest.fixture
def mock_parser_result():
    """Return a mock parser result with some data."""
    # Create a dict with some test values
    values = {
        EphemerisQuantity.ECLIPTIC_LONGITUDE: "110.1170172",
        EphemerisQuantity.ECLIPTIC_LATITUDE: "2.9890069",
        EphemerisQuantity.DISTANCE: "1.02563816",
    }
    # The parser returns a list of tuples (julian_date, values_dict)
    return [(2460754.333333333, values)]


@pytest.fixture
def mock_parser_range_result():
    """Return a mock parser result with multiple data points."""
    base_jd = 2460754.333333333
    base_values = {
        EphemerisQuantity.ECLIPTIC_LONGITUDE: "110.1170172",
        EphemerisQuantity.ECLIPTIC_LATITUDE: "2.9890069",
        EphemerisQuantity.DISTANCE: "1.02563816",
    }

    # Create three data points with slightly different values
    data_points = []
    for i in range(3):
        values = {
            EphemerisQuantity.ECLIPTIC_LONGITUDE: f"{float(base_values[EphemerisQuantity.ECLIPTIC_LONGITUDE]) + i}",
            EphemerisQuantity.ECLIPTIC_LATITUDE: f"{float(base_values[EphemerisQuantity.ECLIPTIC_LATITUDE]) + i / 10}",
            EphemerisQuantity.DISTANCE: f"{float(base_values[EphemerisQuantity.DISTANCE]) + i / 100}",
        }
        data_points.append((base_jd + i / 24, values))  # Add 1 hour between points
    return data_points


class TestHorizonsEphemeris:
    """Tests for the HorizonsEphemeris class."""

    @patch("starloom.horizons.request.HorizonsRequest.make_request")
    def test_get_planet_position_with_string_id(
        self, mock_make_request, mars_single_response
    ):
        """Test getting a planet position with a string identifier."""
        # Setup
        mock_make_request.return_value = mars_single_response
        ephemeris = HorizonsEphemeris()

        # Execute
        result = ephemeris.get_planet_position("499")  # Mars ID

        # Verify
        assert mock_make_request.called
        assert Quantity.ECLIPTIC_LONGITUDE in result
        assert Quantity.ECLIPTIC_LATITUDE in result
        assert Quantity.DELTA in result

        # Check the actual values for Mars
        assert round(result[Quantity.ECLIPTIC_LONGITUDE], 7) == 110.1170172
        assert round(result[Quantity.ECLIPTIC_LATITUDE], 7) == 2.9890069
        assert round(result[Quantity.DELTA], 8) == 1.02563816

    @patch("starloom.horizons.request.HorizonsRequest.make_request")
    def test_get_planet_position_with_enum(
        self, mock_make_request, mars_single_response
    ):
        """Test getting a planet position with a Planet enum."""
        # Setup
        mock_make_request.return_value = mars_single_response
        ephemeris = HorizonsEphemeris()

        # Execute
        result = ephemeris.get_planet_position(Planet.MARS)

        # Verify
        assert mock_make_request.called
        assert Quantity.ECLIPTIC_LONGITUDE in result
        assert Quantity.ECLIPTIC_LATITUDE in result
        assert Quantity.DELTA in result

        # Check the actual values for Mars
        assert round(result[Quantity.ECLIPTIC_LONGITUDE], 7) == 110.1170172
        assert round(result[Quantity.ECLIPTIC_LATITUDE], 7) == 2.9890069
        assert round(result[Quantity.DELTA], 8) == 1.02563816

    @patch("starloom.horizons.request.HorizonsRequest.make_request")
    def test_get_planet_position_with_enum_name(
        self, mock_make_request, mars_single_response
    ):
        """Test getting a planet position with a string enum name."""
        # Setup
        mock_make_request.return_value = mars_single_response
        ephemeris = HorizonsEphemeris()

        # Execute
        result = ephemeris.get_planet_position("MARS")

        # Verify
        assert mock_make_request.called
        assert Quantity.ECLIPTIC_LONGITUDE in result
        assert Quantity.ECLIPTIC_LATITUDE in result
        assert Quantity.DELTA in result

        # Check the actual values for Mars
        assert round(result[Quantity.ECLIPTIC_LONGITUDE], 7) == 110.1170172
        assert round(result[Quantity.ECLIPTIC_LATITUDE], 7) == 2.9890069
        assert round(result[Quantity.DELTA], 8) == 1.02563816

    @patch("starloom.horizons.request.HorizonsRequest.make_request")
    def test_get_planet_position_with_datetime(
        self, mock_make_request, venus_single_response
    ):
        """Test getting a planet position with a datetime object."""
        # Setup
        mock_make_request.return_value = venus_single_response
        ephemeris = HorizonsEphemeris()
        test_time = datetime(2025, 3, 19, 20, 0, 0, tzinfo=timezone.utc)

        # Execute
        result = ephemeris.get_planet_position(Planet.VENUS, test_time)

        # Verify
        assert mock_make_request.called
        assert Quantity.ECLIPTIC_LONGITUDE in result
        assert Quantity.ECLIPTIC_LATITUDE in result
        assert Quantity.DELTA in result

        # Check that we got some reasonable values for Venus
        assert isinstance(result[Quantity.ECLIPTIC_LONGITUDE], float)
        assert isinstance(result[Quantity.ECLIPTIC_LATITUDE], float)
        assert isinstance(result[Quantity.DELTA], float)

    @patch("starloom.horizons.request.HorizonsRequest.make_request")
    def test_get_planet_position_with_julian_date(
        self, mock_make_request, venus_single_response
    ):
        """Test getting a planet position with a Julian date."""
        # Setup
        mock_make_request.return_value = venus_single_response
        ephemeris = HorizonsEphemeris()
        julian_date = 2460754.333333333  # Corresponds to 2025-03-19 20:00:00 UTC

        # Execute
        result = ephemeris.get_planet_position(Planet.VENUS, julian_date)

        # Verify
        assert mock_make_request.called
        assert Quantity.ECLIPTIC_LONGITUDE in result
        assert Quantity.ECLIPTIC_LATITUDE in result
        assert Quantity.DELTA in result

        # Check that we got some reasonable values for Venus
        assert isinstance(result[Quantity.ECLIPTIC_LONGITUDE], float)
        assert isinstance(result[Quantity.ECLIPTIC_LATITUDE], float)
        assert isinstance(result[Quantity.DELTA], float)

    def test_get_planet_position_with_custom_location(self):
        """Test getting a planet position with a custom location."""
        # Create our mock data
        mock_data = [
            (
                2460754.333333333,
                {
                    EphemerisQuantity.ECLIPTIC_LONGITUDE: "110.1170172",
                    EphemerisQuantity.ECLIPTIC_LATITUDE: "2.9890069",
                    EphemerisQuantity.DISTANCE: "1.02563816",
                },
            )
        ]

        # We need to patch exactly where the method is used in ephemeris.py
        with patch(
            "starloom.horizons.parsers.observer_parser.ObserverParser.parse",
            return_value=mock_data,
        ):
            with patch(
                "starloom.horizons.ephemeris.HorizonsRequest"
            ) as mock_request_class:
                mock_request = MagicMock()
                mock_request.make_request.return_value = "some response"
                mock_request_class.return_value = mock_request

                ephemeris = HorizonsEphemeris()
                custom_location = Location(
                    latitude=40.7128, longitude=-74.0060, elevation=0.0
                )  # NYC

                # Execute
                result = ephemeris.get_planet_position(
                    Planet.VENUS, location=custom_location
                )

                # Verify
                mock_request_class.assert_called_once()
                args, kwargs = mock_request_class.call_args
                assert kwargs["location"] == custom_location
                assert Quantity.ECLIPTIC_LONGITUDE in result
                assert Quantity.ECLIPTIC_LATITUDE in result
                assert Quantity.DELTA in result

    def test_get_planet_position_with_location_string(self):
        """Test getting a planet position with a location string."""
        # Create our mock data
        mock_data = [
            (
                2460754.333333333,
                {
                    EphemerisQuantity.ECLIPTIC_LONGITUDE: "110.1170172",
                    EphemerisQuantity.ECLIPTIC_LATITUDE: "2.9890069",
                    EphemerisQuantity.DISTANCE: "1.02563816",
                },
            )
        ]

        # We need to patch exactly where the method is used in ephemeris.py
        with patch(
            "starloom.horizons.parsers.observer_parser.ObserverParser.parse",
            return_value=mock_data,
        ):
            with patch(
                "starloom.horizons.ephemeris.HorizonsRequest"
            ) as mock_request_class:
                mock_request = MagicMock()
                mock_request.make_request.return_value = "some response"
                mock_request_class.return_value = mock_request

                ephemeris = HorizonsEphemeris()
                location_string = "@399/1"  # Geocentric with aberration correction

                # Execute
                result = ephemeris.get_planet_position(
                    Planet.VENUS, location=location_string
                )

                # Verify
                mock_request_class.assert_called_once()
                args, kwargs = mock_request_class.call_args
                assert kwargs["location"] == location_string
                assert Quantity.ECLIPTIC_LONGITUDE in result
                assert Quantity.ECLIPTIC_LATITUDE in result
                assert Quantity.DELTA in result

    @patch("starloom.horizons.request.HorizonsRequest.make_request")
    def test_error_handling_for_empty_response(self, mock_make_request):
        """Test error handling for an empty response."""
        # Setup
        mock_make_request.return_value = "$$SOE\n$$EOE"  # Empty data section
        ephemeris = HorizonsEphemeris()

        # Execute and verify
        with pytest.raises(
            ValueError, match="No data returned from Horizons for planet"
        ):
            ephemeris.get_planet_position(Planet.MARS)

    @patch("starloom.horizons.request.HorizonsRequest.make_request")
    def test_error_handling_for_invalid_planet(self, mock_make_request):
        """Test error handling for an invalid planet name."""
        # Setup
        mock_make_request.return_value = "$$SOE\n$$EOE"  # Empty data section
        ephemeris = HorizonsEphemeris()

        # Execute and verify
        with pytest.raises(
            ValueError, match="No data returned from Horizons for planet INVALID_PLANET"
        ):
            ephemeris.get_planet_position("INVALID_PLANET")

    def test_default_location_is_geocentric(self):
        """Test that default location is geocentric."""
        # Create our mock data
        mock_data = [
            (
                2460754.333333333,
                {
                    EphemerisQuantity.ECLIPTIC_LONGITUDE: "110.1170172",
                    EphemerisQuantity.ECLIPTIC_LATITUDE: "2.9890069",
                    EphemerisQuantity.DISTANCE: "1.02563816",
                },
            )
        ]

        # We need to patch exactly where the method is used in ephemeris.py
        with patch(
            "starloom.horizons.parsers.observer_parser.ObserverParser.parse",
            return_value=mock_data,
        ):
            with patch(
                "starloom.horizons.ephemeris.HorizonsRequest"
            ) as mock_request_class:
                mock_request = MagicMock()
                mock_request.make_request.return_value = "some response"
                mock_request_class.return_value = mock_request

                ephemeris = HorizonsEphemeris()

                # Execute
                ephemeris.get_planet_position(Planet.VENUS)

                # Verify
                mock_request_class.assert_called_once()
                args, kwargs = mock_request_class.call_args
                assert kwargs["location"] == "@399"  # Geocentric location

    @patch("starloom.horizons.request.HorizonsRequest.make_request")
    def test_get_planet_positions_with_time_spec(
        self, mock_make_request, mock_parser_range_result
    ):
        """Test getting planet positions for a time range."""
        # Setup
        mock_make_request.return_value = "mock response"
        with patch(
            "starloom.horizons.parsers.observer_parser.ObserverParser.parse",
            return_value=mock_parser_range_result,
        ):
            ephemeris = HorizonsEphemeris()

            # Create a TimeSpec for the test
            start_time = datetime(2025, 3, 19, 20, 0, 0, tzinfo=timezone.utc)
            stop_time = datetime(2025, 3, 19, 22, 0, 0, tzinfo=timezone.utc)
            time_spec = TimeSpec(
                start_time=start_time, stop_time=stop_time, step_size="1h"
            )

            # Execute
            result = ephemeris.get_planet_positions(Planet.MARS, time_spec)

            # Verify
            assert len(result) == 3  # Should have 3 data points

            # Check that each data point has the required quantities
            for jd, position_data in result.items():
                assert Quantity.ECLIPTIC_LONGITUDE in position_data
                assert Quantity.ECLIPTIC_LATITUDE in position_data
                assert Quantity.DELTA in position_data

                # Verify values are floats
                assert isinstance(position_data[Quantity.ECLIPTIC_LONGITUDE], float)
                assert isinstance(position_data[Quantity.ECLIPTIC_LATITUDE], float)
                assert isinstance(position_data[Quantity.DELTA], float)

    @patch("starloom.horizons.request.HorizonsRequest.make_request")
    def test_get_planet_positions_with_custom_location(
        self, mock_make_request, mock_parser_range_result
    ):
        """Test getting planet positions with a custom location."""
        # Setup
        mock_make_request.return_value = "mock response"
        with patch(
            "starloom.horizons.parsers.observer_parser.ObserverParser.parse",
            return_value=mock_parser_range_result,
        ):
            with patch(
                "starloom.horizons.ephemeris.HorizonsRequest"
            ) as mock_request_class:
                mock_request = MagicMock()
                mock_request.make_request.return_value = "some response"
                mock_request_class.return_value = mock_request

                ephemeris = HorizonsEphemeris()

                # Create a TimeSpec and Location for the test
                time_spec = TimeSpec(
                    start_time=datetime(2025, 3, 19, 20, 0, 0, tzinfo=timezone.utc),
                    stop_time=datetime(2025, 3, 19, 22, 0, 0, tzinfo=timezone.utc),
                    step_size="1h",
                )
                custom_location = Location(
                    latitude=40.7128, longitude=-74.0060, elevation=0.0
                )  # NYC

                # Execute
                result = ephemeris.get_planet_positions(
                    Planet.MARS, time_spec, location=custom_location
                )

                # Verify
                assert len(result) == 3  # Should have 3 data points

                # Verify the request was made with the custom location
                mock_request_class.assert_called_once()
                args, kwargs = mock_request_class.call_args
                assert kwargs["location"] == custom_location

    @patch("starloom.horizons.request.HorizonsRequest.make_request")
    def test_get_planet_positions_with_location_string(
        self, mock_make_request, mock_parser_range_result
    ):
        """Test getting planet positions with a location string."""
        # Setup
        mock_make_request.return_value = "mock response"
        with patch(
            "starloom.horizons.parsers.observer_parser.ObserverParser.parse",
            return_value=mock_parser_range_result,
        ):
            with patch(
                "starloom.horizons.ephemeris.HorizonsRequest"
            ) as mock_request_class:
                mock_request = MagicMock()
                mock_request.make_request.return_value = "some response"
                mock_request_class.return_value = mock_request

                ephemeris = HorizonsEphemeris()

                time_spec = TimeSpec(
                    start_time=datetime(2025, 3, 19, 20, 0, 0, tzinfo=timezone.utc),
                    stop_time=datetime(2025, 3, 19, 22, 0, 0, tzinfo=timezone.utc),
                    step_size="1h",
                )
                location_string = "@399/1"  # Geocentric with aberration correction

                # Execute
                result = ephemeris.get_planet_positions(
                    Planet.MARS, time_spec, location=location_string
                )

                # Verify
                assert len(result) == 3  # Should have 3 data points

                # Verify the request was made with the location string
                mock_request_class.assert_called_once()
                args, kwargs = mock_request_class.call_args
                assert kwargs["location"] == location_string

    def test_default_location_is_geocentric_for_positions(self):
        """Test that default location is geocentric for get_planet_positions."""
        # Create our mock data
        mock_data = [
            (
                2460754.333333333,
                {
                    EphemerisQuantity.ECLIPTIC_LONGITUDE: "110.1170172",
                    EphemerisQuantity.ECLIPTIC_LATITUDE: "2.9890069",
                    EphemerisQuantity.DISTANCE: "1.02563816",
                },
            )
        ]

        # We need to patch exactly where the method is used in ephemeris.py
        with patch(
            "starloom.horizons.parsers.observer_parser.ObserverParser.parse",
            return_value=mock_data,
        ):
            with patch(
                "starloom.horizons.ephemeris.HorizonsRequest"
            ) as mock_request_class:
                mock_request = MagicMock()
                mock_request.make_request.return_value = "some response"
                mock_request_class.return_value = mock_request

                ephemeris = HorizonsEphemeris()
                time_spec = TimeSpec(
                    start_time=datetime(2025, 3, 19, 20, 0, 0, tzinfo=timezone.utc),
                    stop_time=datetime(2025, 3, 19, 22, 0, 0, tzinfo=timezone.utc),
                    step_size="1h",
                )

                # Execute
                ephemeris.get_planet_positions(Planet.VENUS, time_spec)

                # Verify
                mock_request_class.assert_called_once()
                args, kwargs = mock_request_class.call_args
                assert kwargs["location"] == "@399"  # Geocentric location

    @patch("starloom.horizons.request.HorizonsRequest.make_request")
    def test_get_planet_positions_empty_response(self, mock_make_request):
        """Test error handling for an empty response."""
        # Setup
        mock_make_request.return_value = "$$SOE\n$$EOE"  # Empty data section
        ephemeris = HorizonsEphemeris()
        time_spec = TimeSpec(
            start_time=datetime(2025, 3, 19, 20, 0, 0, tzinfo=timezone.utc),
            stop_time=datetime(2025, 3, 19, 22, 0, 0, tzinfo=timezone.utc),
            step_size="1h",
        )

        # Execute and verify
        with pytest.raises(
            ValueError, match="No data returned from Horizons for planet"
        ):
            ephemeris.get_planet_positions(Planet.MARS, time_spec)
