# Starloom 2025

A streamlined Python toolkit for precise astronomical ephemeris calculations, data retrieval, and visualization, optimized for speed and ease of use.

## Features

- **JPL Horizons Integration**: Fetch precise planetary positions and orbital elements
- **Weft Binary Ephemeris**: Efficiently handle binary ephemeris data for rapid calculations
- **Advanced Time Utilities**: Accurate astronomical time conversions and manipulations
- **Retrograde Analysis**: Find and analyze planetary retrograde periods
- **Data Visualization**: Generate SVG visualizations of planetary positions
- **Flexible Storage**: Multiple storage options including SQLite and binary formats
- **Smart Caching**: Efficient data caching for improved performance

## Quick Start

### Installation

```bash
pip install -e .
```

### Basic Usage

Get current planetary positions effortlessly:

```bash
starloom ephemeris venus
starloom ephemeris mars --date 2025-03-19T20:00:00
starloom ephemeris jupiter --location 34.0522,-118.2437,0
```

Example output:
```
2025-03-20 05:12:45 UTC
Venus Aries 4°, 8.5°N, 0.28 AU
```

## Command Reference

### Ephemeris Commands

#### Basic Position Queries
```bash
# Current position
starloom ephemeris venus --date now

# Specific date/time
starloom ephemeris mars --date 2025-03-19T20:00:00

# With location
starloom ephemeris jupiter --location 34.0522,-118.2437,0
```

#### Detailed Horizons Queries
```bash
# Get ecliptic coordinates
starloom horizons ecliptic venus --date now

# Get orbital elements
starloom horizons elements mars --date 2025-03-19T20:00:00

# Time range query
starloom horizons ecliptic venus \
    --start 2025-03-19T20:00:00 \
    --stop 2025-03-19T22:00:00 \
    --step 1h
```

### Weft Binary Ephemeris Commands

#### Generate Weft Files
```bash
# Generate a weft file for a planet's quantity
starloom weft generate mars longitude \
    --start 2025-01-01 \
    --stop 2025-02-01 \
    --step 1h \
    --output mars_longitude.weft

# Combine weft files
starloom weft combine mars1.weft mars2.weft combined_mars.weft \
    --timespan 2020-2040
```

#### Using Weftballs
```bash
# Generate comprehensive planetary data (1900-2100)
python -m scripts.make_weftball mars

# Use weftball for calculations
starloom ephemeris mars \
    --source weft \
    --data mars_weftball.tar.gz \
    --date 2025-03-19T20:00:00
```

### Retrograde Analysis

Find planetary retrograde periods with shadow periods and key aspects:

```bash
# Basic retrograde search
starloom retrograde mercury \
    --start 2024-01-01 \
    --stop 2024-12-31 \
    --output mercury_2024.json

# High precision with weftballs
starloom retrograde mars \
    --start 2024-01-01 \
    --stop 2025-12-31 \
    --source weft \
    --data mars_weftball.tar.gz \
    --sun-data sun_weftball.tar.gz \
    --step 6h \
    --output mars_retro.json
```

## Data Types and Formats

### Ephemeris Output

Basic position output includes:
- Date/time (UTC)
- Zodiac position (° and sign)
- Ecliptic latitude (°N/S)
- Distance from Earth (AU)

### Orbital Elements

Detailed elements include:
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

### Retrograde Data Format

JSON output includes for each period:
```json
{
  "retrograde_periods": [
    {
      "planet": "MARS",
      "pre_shadow_start": {
        "date": "2024-12-06T12:00:00",
        "julian_date": 2460289.0,
        "longitude": 295.5
      },
      "station_retrograde": {
        "date": "2024-12-31T18:00:00",
        "julian_date": 2460314.25,
        "longitude": 298.2
      },
      "station_direct": {
        "date": "2025-03-02T06:00:00",
        "julian_date": 2460375.75,
        "longitude": 282.4
      },
      "post_shadow_end": {
        "date": "2025-03-27T12:00:00",
        "julian_date": 2460401.0,
        "longitude": 285.1
      },
      "sun_aspect": {
        "date": "2025-01-15T00:00:00",
        "julian_date": 2460328.5,
        "longitude": 290.3
      }
    }
  ]
}
```

## Advanced Usage

### Data Storage & Caching

```python
from starloom.cached_horizons.ephemeris import CachedHorizonsEphemeris
from datetime import datetime, timedelta

# Create a cached ephemeris instance
ephemeris = CachedHorizonsEphemeris(data_dir="./data")

# Prefetch data for future use
start_time = datetime.utcnow()
end_time = start_time + timedelta(days=30)
ephemeris.prefetch_data("mars", start_time, end_time, step_hours=24)
```

### Using Weftballs Programmatically

```python
from starloom.weft_ephemeris import WeftEphemeris
from datetime import datetime, timezone

# Create an ephemeris instance using a weftball
ephemeris = WeftEphemeris(data="mars_weftball.tar.gz")

# Get a planet's position
time_point = datetime(2025, 3, 22, tzinfo=timezone.utc)
position = ephemeris.get_planet_position("mars", time_point)

# Access position data
longitude = position[Quantity.ECLIPTIC_LONGITUDE]  # Degrees [0, 360)
latitude = position[Quantity.ECLIPTIC_LATITUDE]    # Degrees [-90, 90]
distance = position[Quantity.DELTA]                # Distance in AU
```

## Project Structure

```
src/starloom/
├── cli/                # Command-line interface modules
│   ├── ephemeris.py   # Ephemeris calculation commands
│   ├── graphics.py    # SVG visualization commands
│   ├── horizons.py    # JPL Horizons API commands
│   ├── retrograde.py  # Retrograde period finder
│   └── weft.py        # Weft file manipulation commands
│
├── ephemeris/         # Abstract ephemeris interface and utilities
├── graphics/         # SVG visualization tools
├── horizons/         # JPL Horizons API integration
├── retrograde/       # Retrograde period detection and analysis
├── weft/            # Weft binary ephemeris tools
├── weft_ephemeris/  # Weft-based ephemeris implementation
├── cached_horizons/ # Cached JPL Horizons data access
├── local_horizons/  # Local SQLite-based data storage
├── space_time/      # Datetime and Julian date utilities
└── linting/         # Code quality tools
```

## Development

### Testing

Run all tests:
```bash
python -m pytest
```

Run specific test modules:
```bash
python -m pytest tests/local_horizons
python -m pytest tests/cached_horizons
```

### Profiling

Profile any command for performance analysis:
```bash
python -m starloom.profile ephemeris mars --date 2025-03-19T20:00:00
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the tests: `python -m pytest tests/`
5. Submit a pull request

## Supported Objects

- Mercury
- Venus
- Earth
- Mars
- Jupiter
- Saturn
- Uranus
- Neptune
- Pluto
- Sun
- Moon

## Date and Time Formats

- ISO format: `YYYY-MM-DDTHH:MM:SS`
- "now" for current time
- UTC assumed if no timezone specified

Step sizes for time ranges:
- `1d`: 1 day
- `1h`: 1 hour
- `30m`: 30 minutes
- `1m`: 1 minute

## License

[Add license information here] 