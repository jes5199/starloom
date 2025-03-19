import pytest
import requests
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from starloom.horizons.request import HorizonsRequest
from starloom.horizons.location import Location
from starloom.horizons.planet import Planet
from starloom.horizons.time_spec import TimeSpec, TimeSpecType
from starloom.ephemeris.quantities import Quantity

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
    assert req.quantities == []
    assert req.time_spec is None
    
    # Request with location
    loc = Location(latitude=40.0, longitude=-75.0, elevation=0.0)
    req = HorizonsRequest(Planet.SUN, location=loc)
    assert req.location == loc
    
    # Request with quantities
    quantities = [Quantity.ECLIPTIC_LATITUDE, Quantity.ECLIPTIC_LONGITUDE]
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
    assert "SITE_COORD=%27-75.000000%2C40.000000%2C0.000000%27" in url  # URL-encoded quoted value
    
    # Request with multiple quantities
    quantities = [Quantity.ECLIPTIC_LATITUDE, Quantity.ECLIPTIC_LONGITUDE, Quantity.DELTA]
    req = HorizonsRequest(Planet.SUN, quantities=quantities)
    url = req.get_url()
    assert "QUANTITIES=%2720%2C31%27" in url  # URL-encoded quoted value with commas (deduplicated and sorted)
    
    # Request with time range
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    stop = datetime(2024, 1, 2, tzinfo=timezone.utc)
    time_spec = TimeSpec.from_range(start, stop, "1h")
    req = HorizonsRequest(Planet.SUN, time_spec=time_spec)
    url = req.get_url()
    assert "START_TIME=" in url
    assert "STOP_TIME=" in url
    assert "STEP_SIZE=1h" in url
    
    # Request with specific dates
    dates = [datetime(2024, 1, 1, tzinfo=timezone.utc)]
    time_spec = TimeSpec.from_dates(dates)
    req = HorizonsRequest(Planet.SUN, time_spec=time_spec)
    url = req.get_url()
    assert "TLIST=" in url

@patch('requests.get')
def test_request_making(mock_get):
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

@patch('requests.post')
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
    assert 'files' in call_args[1]  # Files parameter present
    assert 'input' in call_args[1]['files']  # Input file present
    assert 'input.txt' in call_args[1]['files']['input'][0]  # Correct filename
    assert '!$$SOF' in call_args[1]['files']['input'][1]  # Start of file marker
    assert "COMMAND='10'" in call_args[1]['files']['input'][1]  # Planet command (quoted)
    assert call_args[1]['data']['format'] == 'text'  # Data parameter 