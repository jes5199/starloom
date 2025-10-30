# Lunar Nodes Weftball Design

**Date:** 2025-10-28
**Status:** Approved for implementation

## Overview

Enable generation of weftballs for the lunar north node by creating an orbital elements ephemeris adapter that queries the Moon's ascending node longitude from JPL Horizons.

## Background

**Current State:**
- Weftballs currently use `EphemType.OBSERVER` to query JPL Horizons for ecliptic positions (longitude, latitude, distance)
- Infrastructure: `make_weftball.py` → `starloom weft generate` CLI → `HorizonsEphemeris` → `WeftWriter`
- Orbital elements support exists but isn't connected to weft generation: `ElementsParser` can parse orbital elements from `EphemType.ELEMENTS` responses

**The Challenge:**
- Lunar nodes aren't bodies in JPL Horizons - you can't query "north node" as a target
- Instead, query Moon (301) with `EphemType.ELEMENTS` to get its orbital elements
- The Moon's `ASCENDING_NODE_LONGITUDE` (the "OM" field) **is** the ecliptic longitude of the lunar north node
- South node = (ascending_node_longitude + 180) % 360, computed at runtime as needed

## Goals

1. Create a clean entry point to query the Moon's ascending node longitude from JPL Horizons
2. Generate a weftball where this orbital element is stored as "longitude" data
3. Reuse existing weft infrastructure (Chebyshev polynomials, binary format)
4. Maintain architectural integrity for future orbital element weftballs

## Architecture

### Approach: OrbitalElementsEphemeris Adapter

Create a new ephemeris adapter that implements the `Ephemeris` interface but queries orbital elements instead of observer positions.

### New Components

#### 1. `src/starloom/horizons/orbital_elements_ephemeris.py`

Implements the `Ephemeris` interface:
- `get_planet_position()` - single time point
- `get_planet_positions()` - time range

**Behavior:**
- Queries JPL Horizons with `EphemType.ELEMENTS` for the specified body
- Uses `ElementsParser` to extract orbital elements
- Returns orbital element values as `Quantity` enum values (matching `Ephemeris` interface contract)
- Maps `OrbitalElementsQuantity` → `Quantity` using a new mapping dictionary

**Key implementation details:**
- Accept planet ID (e.g., "301" for Moon)
- Query with `center="10"` (Sun) for heliocentric orbital elements
- Extract all available orbital elements but primarily focused on `ASCENDING_NODE_LONGITUDE`
- Return data in same format as `HorizonsEphemeris` for seamless integration

#### 2. Planet Enum Extension

Add to `src/starloom/planet.py`:
```python
# Calculated points
LUNAR_NORTH_NODE = "301"  # Queries Moon's ascending node longitude
```

**Note:** Uses Moon's Horizons ID because we query the Moon's orbital elements to get the node position.

#### 3. Quantity Mapping

Create mapping in `src/starloom/horizons/quantities.py`:
```python
# Map OrbitalElementsQuantity to standard Quantity enum
OrbitalElementsQuantityToQuantity = {
    OrbitalElementsQuantity.ASCENDING_NODE_LONGITUDE: Quantity.ASCENDING_NODE_LONGITUDE,
    OrbitalElementsQuantity.ECCENTRICITY: Quantity.ECCENTRICITY,
    OrbitalElementsQuantity.INCLINATION: Quantity.INCLINATION,
    # ... other mappings as needed
}
```

This mirrors the existing `EphemerisQuantityToQuantity` mapping pattern.

### Integration with Existing Systems

#### Weft Generation Pipeline

The `ephemeris_weft_generator.py` already accepts an optional `ephemeris` parameter:
```python
def generate_weft_file(
    planet: Union[str, Planet],
    quantity: Union["Quantity", "EphemerisQuantity", "OrbitalElementsQuantity"],
    # ...
    ephemeris: Optional[Ephemeris] = None,
    # ...
)
```

**Enhancement needed:**
- Detect when planet is `LUNAR_NORTH_NODE` or quantity is an orbital element
- Auto-instantiate `OrbitalElementsEphemeris` instead of default `HorizonsEphemeris`
- Pass through seamlessly to existing `WeftWriter`

#### CLI Integration

The `starloom weft generate` command calls `generate_weft_file()`. No changes needed to CLI itself - the detection logic in `generate_weft_file()` handles routing.

**Example usage:**
```bash
starloom weft generate lunar_north_node longitude --start 1900-01-01 --stop 2100-01-01 --step 1h --output north_node.weft
```

### Data Flow

```
User invokes make_weftball.py with "lunar_north_node"
    ↓
generate_weft_file() detects lunar node planet
    ↓
Instantiates OrbitalElementsEphemeris instead of HorizonsEphemeris
    ↓
EphemerisDataSource calls ephemeris.get_planet_positions()
    ↓
OrbitalElementsEphemeris queries Horizons with EphemType.ELEMENTS for Moon
    ↓
ElementsParser extracts ASCENDING_NODE_LONGITUDE
    ↓
Returns as Quantity.ASCENDING_NODE_LONGITUDE
    ↓
WeftWriter generates .weft file with "longitude" data type
    ↓
Tarball created with lunar_north_node_weftball.tar.gz
```

## Implementation Details

### OrbitalElementsEphemeris Class Structure

```python
class OrbitalElementsEphemeris(Ephemeris):
    """Ephemeris adapter for orbital elements from JPL Horizons."""

    def __init__(self, center: str = "10"):
        """
        Args:
            center: Center body for orbital elements (default "10" for Sun)
        """
        self.center = center

    def get_planet_position(
        self,
        planet: str,
        time_point: Optional[Union[float, datetime]] = None,
        location: Optional[Union[Location, str]] = None,
    ) -> Dict[Quantity, Any]:
        """Get orbital elements at a specific time."""
        # Create HorizonsRequest with EphemType.ELEMENTS
        # Parse with ElementsParser
        # Map OrbitalElementsQuantity → Quantity
        # Return dict matching Ephemeris interface

    def get_planet_positions(
        self,
        planet: str,
        time_spec: TimeSpec,
        location: Optional[Union[Location, str]] = None,
    ) -> Dict[float, Dict[Quantity, Any]]:
        """Get orbital elements for multiple times."""
        # Same as above but for time range
```

**Note:** `location` parameter is ignored for orbital elements (not applicable), but kept for interface compatibility.

### Error Handling

- If planet doesn't have orbital elements available from Horizons, raise clear error
- If requested quantity isn't in orbital elements response, raise `KeyError` with helpful message
- Cache orbital elements queries same as observer queries (reuse existing HTTP cache)

### Testing Strategy

1. **Unit tests for OrbitalElementsEphemeris:**
   - Test querying Moon's ascending node longitude
   - Test time range queries
   - Test quantity mapping
   - Use fixtures from `tests/fixtures/elements/`

2. **Integration test for weft generation:**
   - Generate small weft file for lunar north node (1 month)
   - Verify file format and preamble
   - Verify data values are reasonable (0-360 degrees)

3. **End-to-end test:**
   - Run `make_weftball.py lunar_north_node` for short time period
   - Verify tarball creation
   - Extract and validate weft file contents

## Migration Path

This is additive-only - no breaking changes to existing code:
- Existing weftballs continue to work
- Existing `HorizonsEphemeris` unchanged
- New functionality only activated when using lunar node planet or orbital element quantities

## Future Extensions

This design enables future orbital element weftballs:
- Mercury's perihelion longitude (for general relativity studies)
- Planetary eccentricities over time
- Inclination variations
- Any other orbital element from JPL Horizons

Simply specify the quantity and the system routes to `OrbitalElementsEphemeris`.

## Success Criteria

1. ✅ Can generate weftball for lunar north node via CLI
2. ✅ Weft file contains ascending node longitude as "longitude" quantity
3. ✅ Data values match JPL Horizons orbital elements output
4. ✅ Integration with existing infrastructure requires no changes to WeftWriter
5. ✅ Pattern is extensible to other orbital elements

## Open Questions

None - design approved for implementation.
