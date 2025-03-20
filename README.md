# Starloom 2025

A Python toolkit for astronomical ephemeris calculations and data retrieval.

## Features

- **JPL Horizons API Integration**: Query planetary positions and orbital elements
- **Weft Binary Ephemeris Support**: Work with Weft binary ephemeris files
- **Time Utilities**: Handle astronomical time calculations and conversions
- **Command Line Interface**: Easy-to-use tools for common astronomical calculations

## Quick Start

### Installation

```bash
pip install -e .
```

### Basic Usage

Get Venus's current position:

```bash
starloom ephemeris venus
```

Get Mars's position at a specific time:

```bash
starloom ephemeris mars --date 2025-03-19T20:00:00
```

Get Jupiter's position from a specific location:

```bash
starloom ephemeris jupiter --location 34.0522,-118.2437,0
```

## Command Line Interface

### Planetary Positions

#### Simplified Ephemeris Command

The `ephemeris` command provides a user-friendly way to get planetary positions with human-readable output:

```bash
# Get current position
starloom ephemeris venus

# Get position at a specific time
starloom ephemeris mars --date 2025-03-19T20:00:00

# Get position from a specific location
starloom ephemeris jupiter --location 34.0522,-118.2437,0
```

The output includes:
- Date and time (UTC)
- Planet name
- Zodiac position (degrees and sign)
- Ecliptic latitude (degrees with N/S direction)
- Distance from Earth in AU

Example output:
```
2025-03-20 05:12:45 UTC
Venus Aries 4°, 8.5°N, 0.28 AU
```

#### Horizons Ephemeris Commands

The `horizons` commands provide more detailed astronomical data:

The `ecliptic` command retrieves ecliptic coordinates for planets. You can query for a single time or a range of times.

#### Single Time Query

```bash
# Get current position
starloom horizons ecliptic venus --date now

# Get position at a specific time (ISO format)
starloom horizons ecliptic venus --date 2025-03-19T20:00:00
```

#### Time Range Query

```bash
starloom horizons ecliptic venus \
    --start 2025-03-19T20:00:00 \
    --stop 2025-03-19T22:00:00 \
    --step 1h
```

The output includes:
- Distance from Earth (delta) in AU
- Velocity relative to Earth (deldot) in km/s
- Ecliptic longitude (ObsEcLon) in degrees
- Ecliptic latitude (ObsEcLat) in degrees

### Orbital Elements

The `elements` command retrieves heliocentric orbital elements for planets. Like the `ecliptic` command, you can query for a single time or a range of times.

#### Single Time Query

```bash
# Get current orbital elements
starloom horizons elements mars --date now

# Get orbital elements at a specific time (ISO format)
starloom horizons elements mars --date 2025-03-19T20:00:00
```

#### Time Range Query

```bash
starloom horizons elements mars \
    --start 2025-03-19T20:00:00 \
    --stop 2025-03-19T22:00:00 \
    --step 1h
```

The output includes:
- Eccentricity (EC)
- Periapsis distance (QR) in km
- Inclination (IN) in degrees
- Longitude of Ascending Node (OM) in degrees
- Argument of Perifocus (W) in degrees
- Time of periapsis (Tp) as Julian Day Number
- Mean motion (N) in degrees/sec
- Mean anomaly (MA) in degrees
- True anomaly (TA) in degrees
- Semi-major axis (A) in km
- Apoapsis distance (AD) in km
- Sidereal orbit period (PR) in seconds

All elements are geometric osculating elements with respect to the Sun, referenced to the ecliptic and mean equinox of J2000.0.

### Supported Planets

- Mercury
- Venus
- Earth
- Mars
- Jupiter
- Saturn
- Uranus
- Neptune
- Pluto

### Date Format

Dates should be provided in ISO format: `YYYY-MM-DDTHH:MM:SS`. If no timezone is specified, UTC is assumed. You can also use "now" to get the current time.

### Step Sizes

When using time ranges, step sizes can be specified in various formats:
- `1d` for 1 day
- `1h` for 1 hour
- `30m` for 30 minutes
- `1m` for 1 minute

## Data Storage and Caching

### Local Data Storage

The library provides classes for local storage and caching of ephemeris data:

```python
from starloom.local_horizons.storage import LocalHorizonsStorage
from starloom.local_horizons.ephemeris import LocalHorizonsEphemeris
from starloom.ephemeris.quantities import Quantity
from datetime import datetime

# Store ephemeris data locally
storage = LocalHorizonsStorage(data_dir="./data")
data = {
    Quantity.ECLIPTIC_LONGITUDE: 120.5,
    Quantity.ECLIPTIC_LATITUDE: 1.5,
    Quantity.DELTA: 1.5,
}
storage.store_ephemeris_quantities("mars", datetime.utcnow(), data)

# Retrieve data using the Ephemeris interface
ephemeris = LocalHorizonsEphemeris(data_dir="./data")
position = ephemeris.get_planet_position("mars")
```

### Cached API Access

For efficient API usage, the library provides a caching layer:

```python
from starloom.cached_horizons.ephemeris import CachedHorizonsEphemeris
from datetime import datetime, timedelta

# Create a cached ephemeris instance
ephemeris = CachedHorizonsEphemeris(data_dir="./data")

# Get a planet's position - will fetch from API if not in cache
position = ephemeris.get_planet_position("venus", datetime.utcnow())

# Prefetch data for future use
start_time = datetime.utcnow()
end_time = start_time + timedelta(days=30)
ephemeris.prefetch_data("mars", start_time, end_time, step_hours=24)
```

## Development

### Project Structure

```
/src/starloom/
├── ephemeris/  # Abstract ephemeris interface and utilities
├── horizons/   # JPL Horizons API integration
├── weft/       # Weft binary ephemeris tools
└── space_time/ # Datetime and Julian date utilities

/scripts/       # Command-line tools and utilities
/tests/
└── fixtures/   # Test fixture data
    ├── ecliptic/   # Planetary position data
    └── elements/   # Orbital elements data
```

### Test Fixtures

The project includes test fixtures for planetary positions and orbital elements. These are stored in `tests/fixtures/` and include:

- Ecliptic positions for Venus and Mars
- Orbital elements for Mars and Jupiter

Each planet has both single-time and time-range data files.

To regenerate the test fixtures:

1. Ensure you have the package installed in development mode:
   ```bash
   pip install -e .
   ```

2. Run the fixture generation script:
   ```bash
   ./scripts/generate_fixtures.py
   ```

This will create or update the following files:
- `tests/fixtures/ecliptic/*.txt`: Position data for Venus and Mars
- `tests/fixtures/elements/*.txt`: Orbital elements for Mars and Jupiter

The fixtures use the following time parameters:
- Single time point: 2025-03-19T20:00:00
- Time range: 2025-03-19T20:00:00 to 2025-03-19T22:00:00 (1-hour steps)

### Key Design Principles

1. **Timezone Awareness**: All datetime operations use timezone-aware objects, defaulting to UTC
2. **Modular Design**: Clear separation between different astronomical data sources
3. **Type Safety**: Comprehensive type hints and validation
4. **Extensible**: Easy to add new features and data sources

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the tests: `python -m pytest tests/`
5. Submit a pull request

### Running Tests

Run all tests:

```bash
python -m pytest
```

Run specific test modules:

```bash
# Run local_horizons tests
python -m pytest tests/local_horizons

# Run cached_horizons tests
python -m pytest tests/cached_horizons
```

The test suite includes comprehensive tests for:
- Local storage operations
- Ephemeris interface implementation
- Caching behavior
- Error handling

## License

[Add license information here]
