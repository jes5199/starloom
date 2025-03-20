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
starloom horizons ecliptic venus --date now
```

Get Mars's position over a time range:

```bash
starloom horizons ecliptic mars \
    --start 2025-03-19T20:00:00 \
    --stop 2025-03-19T22:00:00 \
    --step 1h
```

## Command Line Interface

### Planetary Positions

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

## Development

### Project Structure

```
/src/starloom/
├── shared/     # Shared interfaces and constants
├── horizons/   # JPL Horizons API integration
├── weft/       # Weft binary ephemeris tools
└── time/       # Datetime and Julian date utilities

/scripts/       # Command-line tools and utilities
```

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

## License

[Add license information here]
