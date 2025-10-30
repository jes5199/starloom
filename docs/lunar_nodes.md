# Lunar Nodes Weftball

## Overview

The lunar nodes are calculated astronomical points where the Moon's orbital plane intersects the ecliptic plane. The **north node** (ascending node) is where the Moon crosses the ecliptic from south to north. The **south node** (descending node) is 180 degrees opposite.

## Implementation

Lunar nodes are implemented using the Moon's orbital elements from JPL Horizons:

- **Query target**: Moon (Horizons ID: 301)
- **Ephemeris type**: ELEMENTS (orbital elements)
- **Quantity**: ASCENDING_NODE_LONGITUDE (OM field)
- **Adapter**: `OrbitalElementsEphemeris`

The ascending node longitude represents the ecliptic longitude of the north node. The south node is computed as:

```python
south_node = (north_node + 180) % 360
```

## Usage

### Generate Weftball

```bash
# Full century weftball (1900-2100)
python -m scripts.make_weftball lunar_north_node

# Custom time range
starloom weft generate lunar_north_node longitude \
  --start 2024-01-01 \
  --stop 2025-01-01 \
  --step 1h \
  --output lunar_north_node.weft
```

### Read Values

```python
from starloom.weft.weft_reader import WeftReader
from datetime import datetime, timezone

reader = WeftReader()
reader.load("lunar_north_node_longitude.weft")

# Get north node position
date = datetime(2024, 3, 15, 12, 0, 0, tzinfo=timezone.utc)
north_node = reader.get_value(date)

# Calculate south node
south_node = (north_node + 180) % 360

print(f"North Node: {north_node:.2f} degrees")
print(f"South Node: {south_node:.2f} degrees")
```

### Query Directly via API

```python
from starloom.horizons.orbital_elements_ephemeris import OrbitalElementsEphemeris
from starloom.ephemeris.quantities import Quantity
from datetime import datetime, timezone

ephemeris = OrbitalElementsEphemeris()
date = datetime(2024, 3, 15, 12, 0, 0, tzinfo=timezone.utc)

# Query Moon's orbital elements
result = ephemeris.get_planet_position("301", date)

# Extract ascending node longitude
north_node = result[Quantity.ASCENDING_NODE_LONGITUDE]
print(f"North Node: {north_node:.2f} degrees")
```

## Technical Details

### Why Query Moon's Orbital Elements?

Lunar nodes are not independent celestial bodies in JPL Horizons. They are geometric points derived from the Moon's orbital plane. The most accurate way to obtain node positions is to query the Moon's orbital elements, where the ascending node longitude is provided directly.

### Coordinate System

- **Reference frame**: Ecliptic coordinates (J2000)
- **Origin**: Vernal equinox (0 degrees Aries)
- **Range**: 0-360 degrees
- **Precision**: Sub-arcsecond accuracy from JPL Horizons

### Mean vs True Node

JPL Horizons provides the **mean ascending node**, which is the average position accounting for short-period perturbations. For most astrological and astronomical calculations, the mean node is appropriate.

The **true node** (instantaneous position) differs from the mean node by typically less than 1-2 degrees due to lunar perturbations. If true node precision is needed, use higher-frequency sampling (e.g., hourly steps) and interpolate.

## Extending to Other Orbital Elements

The `OrbitalElementsEphemeris` infrastructure supports querying any orbital element:

```python
from starloom.horizons.orbital_elements_ephemeris import OrbitalElementsEphemeris
from starloom.ephemeris.quantities import Quantity

ephemeris = OrbitalElementsEphemeris()
result = ephemeris.get_planet_position("499", date)  # Mars

# Available quantities:
# - ASCENDING_NODE_LONGITUDE
# - ECCENTRICITY
# - INCLINATION
# - SEMI_MAJOR_AXIS
# - PERIAPSIS_DISTANCE
# - APOAPSIS_DISTANCE
# - ARGUMENT_OF_PERIFOCUS
# - MEAN_ANOMALY
# - TRUE_ANOMALY
# - ORBITAL_PERIOD
```

## References

- JPL Horizons System: https://ssd.jpl.nasa.gov/horizons/
- Orbital Elements Documentation: `docs/horizons/horizons.txt`
- Weft Format Specification: `docs/weft_format2.txt`
