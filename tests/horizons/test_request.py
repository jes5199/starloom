import pytest
import requests
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from starloom.horizons.request import HorizonsRequest
from starloom.horizons.location import Location
from starloom.horizons.planet import Planet
from starloom.ephemeris.quantities import Quantity

def test_location_validation():
    """Test Location class validation."""
    # Valid locations
    Location(0, 0)  # Should not raise
    Location(90, 180)  # Should not raise
    Location(-90, -180)  # Should not raise
    
    # Invalid locations
    with pytest.raises(ValueError, match="Latitude must be between -90 and 90 degrees"):
        Location(91, 0)
    with pytest.raises(ValueError, match="Longitude must be between -180 and 180 degrees"):
        Location(0, 181)
    with pytest.raises(ValueError, match="Elevation cannot be less than -500 meters"):
        Location(0, 0, -501)

def test_location_format():
    """Test Location class formatting."""
    loc = Location(40.7128, -74.0060, 10.0)  # New York City
    assert loc.to_horizons_format() == "-74.0060,40.7128,10.0"

def test_request_initialization():
    """Test HorizonsRequest initialization."""
    # Basic request
    req = HorizonsRequest(Planet.SUN)
    assert req.planet == Planet.SUN
    assert req.location is None
    assert req.quantities == []
    assert req.start_time is None
    assert req.stop_time is None
    assert req.step_size is None
    assert req.dates == []
    
    # Request with location
    loc = Location(40.7128, -74.0060)
    req = HorizonsRequest(Planet.SUN, location=loc)
    assert req.location == loc
    
    # Request with quantities
    quantities = [Quantity.RIGHT_ASCENSION, Quantity.DECLINATION]
    req = HorizonsRequest(Planet.SUN, quantities=quantities)
    assert req.quantities == quantities
    
    # Request with time range
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    stop = datetime(2024, 1, 2, tzinfo=timezone.utc)
    req = HorizonsRequest(Planet.SUN, start_time=start, stop_time=stop, step_size="1h")
    assert req.start_time == start
    assert req.stop_time == stop
    assert req.step_size == "1h"
    
    # Request with dates
    dates = [start, stop]
    req = HorizonsRequest(Planet.SUN, dates=dates)
    assert req.dates == dates

def test_request_url_generation():
    """Test URL generation for requests."""
    # Basic request
    req = HorizonsRequest(Planet.SUN)
    url = req.get_url()
    assert "COMMAND=10" in url  # SUN's value
    assert "format=text" in url
    
    # Request with location
    loc = Location(40.7128, -74.0060)
    req = HorizonsRequest(Planet.SUN, location=loc)
    url = req.get_url()
    assert "CENTER=coord%40399" in url  # EARTH's value, URL encoded
    assert "SITE_COORD=%27-74.0060%2C40.7128%2C0.0%27" in url  # Quoted because it contains commas
    assert "COORD_TYPE=GEODETIC" in url
    
    # Request with quantities
    quantities = [Quantity.RIGHT_ASCENSION, Quantity.DECLINATION]
    req = HorizonsRequest(Planet.SUN, quantities=quantities)
    url = req.get_url()
    assert "QUANTITIES=1" in url  # Both RA and DEC use quantity 1
    
    # Request with time range
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    stop = datetime(2024, 1, 2, tzinfo=timezone.utc)
    req = HorizonsRequest(Planet.SUN, start_time=start, stop_time=stop, step_size="1h")
    url = req.get_url()
    assert "START_TIME=JD2460310.5" in url
    assert "STOP_TIME=JD2460311.5" in url
    assert "STEP_SIZE=1h" in url

@patch('requests.get')
def test_request_making(mock_get):
    """Test making requests to the API."""
    # Mock successful response
    mock_response = MagicMock()
    mock_response.text = "Success"
    mock_get.return_value = mock_response
    
    # Basic request
    req = HorizonsRequest(Planet.SUN)
    response = req.make_request()
    assert response == "Success"
    mock_get.assert_called_once()
    
    # Reset mock
    mock_get.reset_mock()
    
    # Request with error and retry
    mock_get.side_effect = [
        requests.exceptions.HTTPError("500"),
        MagicMock(text="Success after retry")
    ]
    response = req.make_request()
    assert response == "Success after retry"
    assert mock_get.call_count == 2

@patch('requests.post')
def test_post_request_fallback(mock_post):
    """Test falling back to POST request when URL is too long."""
    # Create request with many dates to trigger POST
    dates = [datetime(2024, 1, 1, tzinfo=timezone.utc) for _ in range(50)]
    req = HorizonsRequest(Planet.SUN, dates=dates)
    
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
    assert 'files' in call_args[1]  # Files parameter present
    assert 'input' in call_args[1]['files']  # Input file present
    assert 'input.txt' in call_args[1]['files']['input'][0]  # Correct filename
    assert '!$$SOF' in call_args[1]['files']['input'][1]  # Start of file marker
    assert "COMMAND='10'" in call_args[1]['files']['input'][1]  # Planet command (quoted)
    assert call_args[1]['data']['format'] == 'text'  # Data parameter 