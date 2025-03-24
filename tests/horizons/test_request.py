import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from starloom.horizons.request import HorizonsRequest
from starloom.horizons.location import Location
from starloom.planet import Planet
from starloom.horizons.time_spec import TimeSpec
from starloom.horizons.time_spec_param import HorizonsTimeSpecParam
from starloom.horizons.quantities import Quantities


def test_location_validation():
    """Test location validation."""
    # Valid location
    loc = Location(latitude=40.0, longitude=-75.0, elevation=0.0)
    assert loc.latitude == 40.0
    assert loc.longitude == -75.0
    assert loc.elevation == 0.0

    # Invalid latitude
    with pytest.raises(ValueError, match="Latitude must be between -90 and 90"):
        Location(latitude=91.0, longitude=-75.0, elevation=0.0)

    # Invalid longitude
    with pytest.raises(ValueError, match="Longitude must be between -180 and 180"):
        Location(latitude=40.0, longitude=181.0, elevation=0.0)


def test_location_format():
    """Test location formatting for Horizons API."""
    loc = Location(latitude=40.0, longitude=-75.0, elevation=0.0)
    assert loc.to_horizons_format() == "-75.000000,40.000000,0.000000"

    # Test with different precision
    loc = Location(latitude=40.123456, longitude=-75.123456, elevation=123.456)
    assert loc.to_horizons_format() == "-75.123456,40.123456,123.456000"


def test_request_initialization():
    """Test request initialization."""
    # Basic request
    req = HorizonsRequest(Planet.SUN)
    assert req.planet == Planet.SUN
    assert req.location is None
    assert req.quantities.values == [20, 31]  # Default quantities

    # Request with location
    loc = Location(latitude=40.0, longitude=-75.0, elevation=0.0)
    req = HorizonsRequest(Planet.SUN, location=loc)
    assert req.location == loc

    # Request with time spec
    time_spec = TimeSpec.from_dates([datetime(2024, 1, 1, tzinfo=timezone.utc)])
    req = HorizonsRequest(Planet.SUN, time_spec=time_spec)
    assert req.time_spec == time_spec
    assert isinstance(req.time_spec_param, HorizonsTimeSpecParam)

    # Request with explicit time spec param
    time_spec_param = HorizonsTimeSpecParam(time_spec)
    req = HorizonsRequest(
        Planet.SUN, time_spec=time_spec, time_spec_param=time_spec_param
    )
    assert req.time_spec_param == time_spec_param

    # Request with quantities
    quantities = Quantities(values=[1, 2, 3])
    req = HorizonsRequest(Planet.SUN, quantities=quantities)
    assert req.quantities == quantities


def test_request_url_generation():
    """Test URL generation for requests."""
    # Basic request
    req = HorizonsRequest(Planet.SUN)
    url = req.get_url()
    assert "COMMAND=10" in url  # 10 is the Horizons ID for the Sun
    assert "format=text" in url

    # Request with location
    loc = Location(latitude=40.0, longitude=-75.0, elevation=0.0)
    req = HorizonsRequest(Planet.SUN, location=loc)
    url = req.get_url()
    assert "SITE_COORD=-75.000000%2C40.000000%2C0.000000" in url  # URL-encoded value

    # Request with time spec
    time_spec = TimeSpec.from_dates([datetime(2024, 1, 1, tzinfo=timezone.utc)])
    req = HorizonsRequest(Planet.SUN, time_spec=time_spec)
    url = req.get_url()
    assert "TLIST=2460310.5" in url  # Julian date

    # Request with quantities
    quantities = Quantities(values=[1, 2, 3])
    req = HorizonsRequest(Planet.SUN, quantities=quantities)
    url = req.get_url()
    assert "QUANTITIES='1%2C2%2C3'" in url  # URL-encoded quoted value


@patch("requests.get")
@patch.object(HorizonsRequest, "_get_cached_response", return_value=None)
def test_request_making(mock_get_cached, mock_get):
    """Test making requests."""
    # Mock successful response
    mock_response = MagicMock()
    mock_response.text = "Success"
    mock_get.return_value = mock_response

    # Make request
    req = HorizonsRequest(Planet.SUN)
    response = req.make_request()
    assert response == "Success"
    mock_get.assert_called_once()


@patch("requests.post")
def test_post_request_fallback(mock_post):
    """Test falling back to POST request when URL is too long."""
    # Create request with many dates to trigger POST
    dates = [datetime(2024, 1, 1, tzinfo=timezone.utc) for _ in range(50)]
    time_spec = TimeSpec.from_dates(dates)
    req = HorizonsRequest(Planet.SUN, time_spec=time_spec)

    # Mock successful response
    mock_response = MagicMock()
    mock_response.text = "Success"
    mock_post.return_value = mock_response

    # Force a POST request by setting a very low max_url_length
    req.max_url_length = 10
    response = req.make_request()
    assert response == "Success"
    mock_post.assert_called_once()

    # Verify the POST request was made with correct data
    call_args = mock_post.call_args
    assert call_args[0][0] == req.post_url  # URL
    assert "files" in call_args[1]  # Files parameter present
    assert "input" in call_args[1]["files"]  # Input file present
    assert "input.txt" in call_args[1]["files"]["input"][0]  # Correct filename
    assert "!$$SOF" in call_args[1]["files"]["input"][1]  # Start of file marker
    assert "COMMAND=10" in call_args[1]["files"]["input"][1]  # Planet command


def test_request_with_julian_dates():
    """Test requests with Julian date output."""
    # Test single date
    date = datetime(2024, 3, 15, 20, 0, tzinfo=timezone.utc)
    time_spec = TimeSpec.from_dates([date])

    # Request with Julian output
    req = HorizonsRequest(Planet.SUN, time_spec=time_spec, use_julian=True)
    url = req.get_url()
    assert "CAL_FORMAT=JD" in url

    # Request with Gregorian output (default)
    req = HorizonsRequest(Planet.SUN, time_spec=time_spec, use_julian=False)
    url = req.get_url()
    assert "CAL_FORMAT=JD" not in url

    # Test date range
    start = datetime(2024, 3, 15, 20, 0, tzinfo=timezone.utc)
    stop = datetime(2024, 3, 16, 20, 0, tzinfo=timezone.utc)
    time_spec = TimeSpec.from_range(start, stop, "1h")

    # Request with Julian output
    req = HorizonsRequest(Planet.SUN, time_spec=time_spec, use_julian=True)
    url = req.get_url()
    assert "CAL_FORMAT=JD" in url

    # Request with Gregorian output (default)
    req = HorizonsRequest(Planet.SUN, time_spec=time_spec, use_julian=False)
    url = req.get_url()
    assert "CAL_FORMAT=JD" not in url


def test_request_with_julian_input():
    """Test requests with Julian date input."""
    # Test single Julian date
    time_spec = TimeSpec.from_dates([2460385.333333333])

    # Request with Julian output
    req = HorizonsRequest(Planet.SUN, time_spec=time_spec, use_julian=True)
    url = req.get_url()
    assert "CAL_FORMAT=JD" in url
    assert "TLIST=2460385.333333333" in url

    # Request with Gregorian output (default)
    req = HorizonsRequest(Planet.SUN, time_spec=time_spec, use_julian=False)
    url = req.get_url()
    assert "CAL_FORMAT=JD" not in url
    assert "TLIST=2460385.333333333" in url

    # Test Julian date range
    time_spec = TimeSpec.from_range(2460385.333333333, 2460386.333333333, "1h")

    # Request with Julian output
    req = HorizonsRequest(Planet.SUN, time_spec=time_spec, use_julian=True)
    url = req.get_url()
    assert "CAL_FORMAT=JD" in url
    assert "START_TIME=2460385.333333333" in url
    assert "STOP_TIME=2460386.333333333" in url

    # Request with Gregorian output (default)
    req = HorizonsRequest(Planet.SUN, time_spec=time_spec, use_julian=False)
    url = req.get_url()
    assert "CAL_FORMAT=JD" not in url
    assert "START_TIME=2460385.333333333" in url
    assert "STOP_TIME=2460386.333333333" in url
