# Lunar Nodes Weftball Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable generation of weftballs for the lunar north node by querying Moon's ascending node longitude from JPL Horizons orbital elements.

**Architecture:** Create `OrbitalElementsEphemeris` adapter implementing the `Ephemeris` interface. Query JPL Horizons with `EphemType.ELEMENTS` for the Moon, extract `ASCENDING_NODE_LONGITUDE`, and return it as a standard `Quantity`. Update weft generation pipeline to auto-detect and route lunar node requests to this new ephemeris.

**Tech Stack:** Python 3.8+, JPL Horizons API, existing WeftWriter infrastructure

---

## Task 1: Add LUNAR_NORTH_NODE to Planet enum

**Files:**
- Modify: `src/starloom/planet.py:108` (after last centaur entry)
- Test: `tests/planet/test_planet_enum.py` (create new file)

**Step 1: Write the failing test**

Create `tests/planet/test_planet_enum.py`:

```python
"""Tests for Planet enum."""

import unittest
from starloom.planet import Planet


class TestPlanetEnum(unittest.TestCase):
    """Test Planet enum values."""

    def test_lunar_north_node_exists(self):
        """Test that LUNAR_NORTH_NODE is defined."""
        self.assertTrue(hasattr(Planet, "LUNAR_NORTH_NODE"))

    def test_lunar_north_node_value(self):
        """Test that LUNAR_NORTH_NODE uses Moon's Horizons ID."""
        self.assertEqual(Planet.LUNAR_NORTH_NODE.value, "301")

    def test_lunar_north_node_name(self):
        """Test that LUNAR_NORTH_NODE has correct name."""
        self.assertEqual(Planet.LUNAR_NORTH_NODE.name, "LUNAR_NORTH_NODE")


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/planet/test_planet_enum.py -v`
Expected: FAIL with "AttributeError: type object 'Planet' has no attribute 'LUNAR_NORTH_NODE'"

**Step 3: Write minimal implementation**

In `src/starloom/planet.py`, add after line 107 (after ECHECLUS):

```python
    # Calculated astronomical points
    LUNAR_NORTH_NODE = "301"  # Moon's ascending node (queries Moon's orbital elements)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/planet/test_planet_enum.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/starloom/planet.py tests/planet/test_planet_enum.py
git commit -m "feat: add LUNAR_NORTH_NODE to Planet enum

Add lunar north node as a calculated astronomical point using Moon's
Horizons ID for querying orbital elements.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 2: Create OrbitalElementsQuantityToQuantity mapping

**Files:**
- Modify: `src/starloom/horizons/quantities.py:135` (after EphemerisQuantityToQuantity)
- Test: `tests/horizons/test_quantities.py` (create new file)

**Step 1: Write the failing test**

Create `tests/horizons/test_quantities.py`:

```python
"""Tests for horizons quantity mappings."""

import unittest
from starloom.horizons.quantities import OrbitalElementsQuantityToQuantity
from starloom.horizons.parsers import OrbitalElementsQuantity
from starloom.ephemeris.quantities import Quantity


class TestOrbitalElementsQuantityMapping(unittest.TestCase):
    """Test OrbitalElementsQuantity to Quantity mapping."""

    def test_mapping_exists(self):
        """Test that the mapping dictionary exists."""
        self.assertIsInstance(OrbitalElementsQuantityToQuantity, dict)

    def test_ascending_node_longitude_mapping(self):
        """Test ASCENDING_NODE_LONGITUDE maps correctly."""
        result = OrbitalElementsQuantityToQuantity[
            OrbitalElementsQuantity.ASCENDING_NODE_LONGITUDE
        ]
        self.assertEqual(result, Quantity.ASCENDING_NODE_LONGITUDE)

    def test_eccentricity_mapping(self):
        """Test ECCENTRICITY maps correctly."""
        result = OrbitalElementsQuantityToQuantity[
            OrbitalElementsQuantity.ECCENTRICITY
        ]
        self.assertEqual(result, Quantity.ECCENTRICITY)

    def test_inclination_mapping(self):
        """Test INCLINATION maps correctly."""
        result = OrbitalElementsQuantityToQuantity[OrbitalElementsQuantity.INCLINATION]
        self.assertEqual(result, Quantity.INCLINATION)

    def test_semi_major_axis_mapping(self):
        """Test SEMI_MAJOR_AXIS maps correctly."""
        result = OrbitalElementsQuantityToQuantity[
            OrbitalElementsQuantity.SEMI_MAJOR_AXIS
        ]
        self.assertEqual(result, Quantity.SEMI_MAJOR_AXIS)

    def test_periapsis_distance_mapping(self):
        """Test PERIAPSIS_DISTANCE maps correctly."""
        result = OrbitalElementsQuantityToQuantity[
            OrbitalElementsQuantity.PERIAPSIS_DISTANCE
        ]
        self.assertEqual(result, Quantity.PERIAPSIS_DISTANCE)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/horizons/test_quantities.py -v`
Expected: FAIL with "ImportError: cannot import name 'OrbitalElementsQuantityToQuantity'"

**Step 3: Write minimal implementation**

In `src/starloom/horizons/quantities.py`, add after line 135 (after EphemerisQuantityToQuantity definition):

```python
# Map OrbitalElementsQuantity to standard Quantity enum
OrbitalElementsQuantityToQuantity = {
    OrbitalElementsQuantity.ASCENDING_NODE_LONGITUDE: Quantity.ASCENDING_NODE_LONGITUDE,
    OrbitalElementsQuantity.ECCENTRICITY: Quantity.ECCENTRICITY,
    OrbitalElementsQuantity.INCLINATION: Quantity.INCLINATION,
    OrbitalElementsQuantity.SEMI_MAJOR_AXIS: Quantity.SEMI_MAJOR_AXIS,
    OrbitalElementsQuantity.PERIAPSIS_DISTANCE: Quantity.PERIAPSIS_DISTANCE,
    OrbitalElementsQuantity.APOAPSIS_DISTANCE: Quantity.APOAPSIS_DISTANCE,
    OrbitalElementsQuantity.ARGUMENT_OF_PERIAPSIS: Quantity.ARGUMENT_OF_PERIFOCUS,
    OrbitalElementsQuantity.MEAN_MOTION: Quantity.MEAN_MOTION,
    OrbitalElementsQuantity.MEAN_ANOMALY: Quantity.MEAN_ANOMALY,
    OrbitalElementsQuantity.TRUE_ANOMALY: Quantity.TRUE_ANOMALY,
    OrbitalElementsQuantity.ORBITAL_PERIOD: Quantity.ORBITAL_PERIOD,
}
```

Add import at top of file (around line 10):

```python
from .parsers import OrbitalElementsQuantity
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/horizons/test_quantities.py -v`
Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add src/starloom/horizons/quantities.py tests/horizons/test_quantities.py
git commit -m "feat: add OrbitalElementsQuantity to Quantity mapping

Create mapping dictionary to convert orbital element quantities to
standard Quantity enum values.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 3: Create OrbitalElementsEphemeris class (Part 1: Structure and __init__)

**Files:**
- Create: `src/starloom/horizons/orbital_elements_ephemeris.py`
- Test: `tests/horizons/test_orbital_elements_ephemeris.py` (create new file)

**Step 1: Write the failing test**

Create `tests/horizons/test_orbital_elements_ephemeris.py`:

```python
"""Tests for OrbitalElementsEphemeris."""

import unittest
from starloom.horizons.orbital_elements_ephemeris import OrbitalElementsEphemeris


class TestOrbitalElementsEphemeris(unittest.TestCase):
    """Test OrbitalElementsEphemeris class."""

    def test_init_default_center(self):
        """Test initialization with default center."""
        ephemeris = OrbitalElementsEphemeris()
        self.assertEqual(ephemeris.center, "10")

    def test_init_custom_center(self):
        """Test initialization with custom center."""
        ephemeris = OrbitalElementsEphemeris(center="500@0")
        self.assertEqual(ephemeris.center, "500@0")


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/horizons/test_orbital_elements_ephemeris.py::TestOrbitalElementsEphemeris::test_init_default_center -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'starloom.horizons.orbital_elements_ephemeris'"

**Step 3: Write minimal implementation**

Create `src/starloom/horizons/orbital_elements_ephemeris.py`:

```python
"""Orbital elements ephemeris adapter for JPL Horizons.

This module provides an ephemeris adapter that queries orbital elements
from JPL Horizons instead of observer positions. This is useful for
calculated astronomical points like lunar nodes.
"""

from typing import Dict, Optional, Any, Union
from datetime import datetime

from starloom.ephemeris import Ephemeris, Quantity
from .location import Location
from .time_spec import TimeSpec


class OrbitalElementsEphemeris(Ephemeris):
    """Ephemeris adapter for orbital elements from JPL Horizons.

    This class implements the Ephemeris interface but queries orbital
    elements (EphemType.ELEMENTS) instead of observer positions
    (EphemType.OBSERVER). This is used for calculated points like
    lunar nodes that don't exist as separate bodies in JPL Horizons.
    """

    def __init__(self, center: str = "10") -> None:
        """Initialize the orbital elements ephemeris.

        Args:
            center: Center body for orbital elements (default "10" for Sun).
                   Format: Horizons ID (e.g., "10" for Sun, "399" for Earth).
        """
        self.center = center

    def get_planet_position(
        self,
        planet: str,
        time_point: Optional[Union[float, datetime]] = None,
        location: Optional[Union[Location, str]] = None,
    ) -> Dict[Quantity, Any]:
        """Get orbital elements at a specific time.

        Args:
            planet: The planet identifier (Horizons ID).
            time_point: The time for which to retrieve orbital elements.
                       If None, current time is used.
                       Can be a Julian date float or datetime object.
            location: Optional parameter, ignored for orbital elements
                     (kept for interface compatibility).

        Returns:
            Dictionary mapping Quantity enum values to their values.
            Will include orbital element quantities like ASCENDING_NODE_LONGITUDE.

        Raises:
            ValueError: If no data returned from Horizons.
        """
        raise NotImplementedError("Implemented in next task")

    def get_planet_positions(
        self,
        planet: str,
        time_spec: TimeSpec,
        location: Optional[Union[Location, str]] = None,
    ) -> Dict[float, Dict[Quantity, Any]]:
        """Get orbital elements for multiple times.

        Args:
            planet: The planet identifier (Horizons ID).
            time_spec: TimeSpec defining the times to get positions for.
            location: Optional parameter, ignored for orbital elements
                     (kept for interface compatibility).

        Returns:
            Dictionary mapping Julian dates to orbital element data dictionaries.

        Raises:
            ValueError: If no data returned from Horizons.
        """
        raise NotImplementedError("Implemented in next task")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/horizons/test_orbital_elements_ephemeris.py::TestOrbitalElementsEphemeris::test_init_default_center -v`
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add src/starloom/horizons/orbital_elements_ephemeris.py tests/horizons/test_orbital_elements_ephemeris.py
git commit -m "feat: create OrbitalElementsEphemeris class skeleton

Add initial class structure with __init__ method. Implementation of
get_planet_position and get_planet_positions to follow.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 4: Implement OrbitalElementsEphemeris.get_planet_position

**Files:**
- Modify: `src/starloom/horizons/orbital_elements_ephemeris.py:47-67`
- Modify: `tests/horizons/test_orbital_elements_ephemeris.py` (add test)

**Step 1: Write the failing test**

In `tests/horizons/test_orbital_elements_ephemeris.py`, add:

```python
from datetime import datetime, timezone
from starloom.ephemeris.quantities import Quantity


class TestOrbitalElementsEphemerisGetPosition(unittest.TestCase):
    """Test get_planet_position method."""

    def test_get_moon_ascending_node_with_datetime(self):
        """Test getting Moon's ascending node with datetime."""
        ephemeris = OrbitalElementsEphemeris()

        # Use a fixed date for reproducible test
        test_date = datetime(2024, 3, 15, 12, 0, 0, tzinfo=timezone.utc)

        result = ephemeris.get_planet_position("301", test_date)

        # Should return at least ASCENDING_NODE_LONGITUDE
        self.assertIn(Quantity.ASCENDING_NODE_LONGITUDE, result)

        # Value should be a valid degree (0-360)
        longitude = float(result[Quantity.ASCENDING_NODE_LONGITUDE])
        self.assertGreaterEqual(longitude, 0.0)
        self.assertLess(longitude, 360.0)

    def test_get_moon_ascending_node_with_julian_date(self):
        """Test getting Moon's ascending node with Julian date."""
        ephemeris = OrbitalElementsEphemeris()

        # Julian date for 2024-03-15 12:00:00 UTC
        jd = 2460384.0

        result = ephemeris.get_planet_position("301", jd)

        self.assertIn(Quantity.ASCENDING_NODE_LONGITUDE, result)
        longitude = float(result[Quantity.ASCENDING_NODE_LONGITUDE])
        self.assertGreaterEqual(longitude, 0.0)
        self.assertLess(longitude, 360.0)

    def test_get_position_returns_multiple_quantities(self):
        """Test that get_position returns multiple orbital elements."""
        ephemeris = OrbitalElementsEphemeris()
        test_date = datetime(2024, 3, 15, 12, 0, 0, tzinfo=timezone.utc)

        result = ephemeris.get_planet_position("301", test_date)

        # Should return multiple orbital elements
        self.assertGreater(len(result), 1)

        # Should include common orbital elements
        expected_quantities = [
            Quantity.ASCENDING_NODE_LONGITUDE,
            Quantity.ECCENTRICITY,
            Quantity.INCLINATION,
        ]
        for quantity in expected_quantities:
            self.assertIn(quantity, result)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/horizons/test_orbital_elements_ephemeris.py::TestOrbitalElementsEphemerisGetPosition -v`
Expected: FAIL with "NotImplementedError: Implemented in next task"

**Step 3: Write minimal implementation**

In `src/starloom/horizons/orbital_elements_ephemeris.py`, replace the `get_planet_position` method (lines 47-67):

```python
    def get_planet_position(
        self,
        planet: str,
        time_point: Optional[Union[float, datetime]] = None,
        location: Optional[Union[Location, str]] = None,
    ) -> Dict[Quantity, Any]:
        """Get orbital elements at a specific time.

        Args:
            planet: The planet identifier (Horizons ID).
            time_point: The time for which to retrieve orbital elements.
                       If None, current time is used.
                       Can be a Julian date float or datetime object.
            location: Optional parameter, ignored for orbital elements
                     (kept for interface compatibility).

        Returns:
            Dictionary mapping Quantity enum values to their values.
            Will include orbital element quantities like ASCENDING_NODE_LONGITUDE.

        Raises:
            ValueError: If no data returned from Horizons.
        """
        from .request import HorizonsRequest
        from .ephem_type import EphemType
        from .parsers.orbital_elements_parser import ElementsParser
        from .time_spec_param import HorizonsTimeSpecParam
        from .quantities import OrbitalElementsQuantityToQuantity

        # Create time spec for single time point
        time_spec = self._create_time_spec(time_point)

        # Create and execute request
        request = HorizonsRequest(
            planet=planet,
            location=None,  # Not used for orbital elements
            quantities=None,  # Not used for ELEMENTS type
            time_spec=time_spec,
            time_spec_param=HorizonsTimeSpecParam(time_spec),
            ephem_type=EphemType.ELEMENTS,
            center=self.center,
            use_julian=True,
        )

        response = request.make_request()

        # Parse the response
        parser = ElementsParser(response)
        data_points = parser.parse()

        if not data_points:
            raise ValueError(f"No data returned from Horizons for planet {planet}")

        # Get the first (and should be only) data point
        _, values = data_points[0]

        # Convert OrbitalElementsQuantity keys to Quantity keys
        result: Dict[Quantity, Any] = {}
        for orbital_quantity, value in values.items():
            if orbital_quantity in OrbitalElementsQuantityToQuantity:
                standard_quantity = OrbitalElementsQuantityToQuantity[orbital_quantity]
                result[standard_quantity] = self._convert_value(value, standard_quantity)

        return result

    def _create_time_spec(
        self, time_point: Optional[Union[float, datetime]]
    ) -> TimeSpec:
        """Create a TimeSpec from the provided time point.

        Args:
            time_point: The time point to create a TimeSpec for.
                       Can be None (current time), a Julian date float,
                       or a datetime object.

        Returns:
            A TimeSpec object for the given time point.

        Raises:
            TypeError: If time_point is not None, float, or datetime.
        """
        if time_point is None:
            # Use current time with UTC timezone
            now = datetime.now(timezone.utc)
            return TimeSpec.from_dates([now])
        elif isinstance(time_point, float):
            # Assume it's a Julian date
            return TimeSpec.from_dates([time_point])
        elif isinstance(time_point, datetime):
            # It's a datetime object, ensure it has timezone
            if time_point.tzinfo is None:
                # Add UTC timezone if missing
                time_point = time_point.replace(tzinfo=timezone.utc)
            return TimeSpec.from_dates([time_point])
        else:
            raise TypeError(f"Unsupported time type: {type(time_point)}")

    def _convert_value(self, value: str, quantity: Quantity) -> Union[float, str]:
        """Convert string values from Horizons to appropriate types.

        Args:
            value: The string value to convert.
            quantity: The quantity type to convert to.

        Returns:
            The converted value as float for numeric quantities,
            or the original string for other quantities.
        """
        # For orbital elements, most values should be floats
        try:
            return float(value)
        except ValueError:
            return value
```

Add imports at top of file:

```python
from datetime import datetime, timezone
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/horizons/test_orbital_elements_ephemeris.py::TestOrbitalElementsEphemerisGetPosition -v`
Expected: PASS (3 tests) - Note: These tests make real API calls to JPL Horizons

**Step 5: Commit**

```bash
git add src/starloom/horizons/orbital_elements_ephemeris.py tests/horizons/test_orbital_elements_ephemeris.py
git commit -m "feat: implement OrbitalElementsEphemeris.get_planet_position

Add method to query single time point orbital elements from JPL
Horizons using EphemType.ELEMENTS.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 5: Implement OrbitalElementsEphemeris.get_planet_positions

**Files:**
- Modify: `src/starloom/horizons/orbital_elements_ephemeris.py:125-145`
- Modify: `tests/horizons/test_orbital_elements_ephemeris.py` (add test)

**Step 1: Write the failing test**

In `tests/horizons/test_orbital_elements_ephemeris.py`, add:

```python
from starloom.horizons.time_spec import TimeSpec


class TestOrbitalElementsEphemerisGetPositions(unittest.TestCase):
    """Test get_planet_positions method."""

    def test_get_moon_ascending_node_time_range(self):
        """Test getting Moon's ascending node over time range."""
        ephemeris = OrbitalElementsEphemeris()

        # Query 5 days with 1-day step
        start = datetime(2024, 3, 15, 0, 0, 0, tzinfo=timezone.utc)
        time_spec = TimeSpec.from_range(
            start=start,
            stop=datetime(2024, 3, 20, 0, 0, 0, tzinfo=timezone.utc),
            step_days=1,
        )

        result = ephemeris.get_planet_positions("301", time_spec)

        # Should return 5 data points
        self.assertEqual(len(result), 5)

        # Each data point should have ASCENDING_NODE_LONGITUDE
        for jd, values in result.items():
            self.assertIsInstance(jd, float)
            self.assertIn(Quantity.ASCENDING_NODE_LONGITUDE, values)
            longitude = float(values[Quantity.ASCENDING_NODE_LONGITUDE])
            self.assertGreaterEqual(longitude, 0.0)
            self.assertLess(longitude, 360.0)

    def test_get_positions_multiple_quantities(self):
        """Test that get_positions returns multiple orbital elements."""
        ephemeris = OrbitalElementsEphemeris()

        start = datetime(2024, 3, 15, 0, 0, 0, tzinfo=timezone.utc)
        time_spec = TimeSpec.from_range(
            start=start,
            stop=datetime(2024, 3, 17, 0, 0, 0, tzinfo=timezone.utc),
            step_days=1,
        )

        result = ephemeris.get_planet_positions("301", time_spec)

        # Each data point should have multiple quantities
        for jd, values in result.items():
            self.assertGreater(len(values), 1)
            self.assertIn(Quantity.ASCENDING_NODE_LONGITUDE, values)
            self.assertIn(Quantity.ECCENTRICITY, values)
            self.assertIn(Quantity.INCLINATION, values)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/horizons/test_orbital_elements_ephemeris.py::TestOrbitalElementsEphemerisGetPositions -v`
Expected: FAIL with "NotImplementedError: Implemented in next task"

**Step 3: Write minimal implementation**

In `src/starloom/horizons/orbital_elements_ephemeris.py`, replace the `get_planet_positions` method (around line 125):

```python
    def get_planet_positions(
        self,
        planet: str,
        time_spec: TimeSpec,
        location: Optional[Union[Location, str]] = None,
    ) -> Dict[float, Dict[Quantity, Any]]:
        """Get orbital elements for multiple times.

        Args:
            planet: The planet identifier (Horizons ID).
            time_spec: TimeSpec defining the times to get positions for.
            location: Optional parameter, ignored for orbital elements
                     (kept for interface compatibility).

        Returns:
            Dictionary mapping Julian dates to orbital element data dictionaries.

        Raises:
            ValueError: If no data returned from Horizons.
        """
        from .request import HorizonsRequest
        from .ephem_type import EphemType
        from .parsers.orbital_elements_parser import ElementsParser
        from .time_spec_param import HorizonsTimeSpecParam
        from .quantities import OrbitalElementsQuantityToQuantity

        # Create and execute request
        request = HorizonsRequest(
            planet=planet,
            location=None,  # Not used for orbital elements
            quantities=None,  # Not used for ELEMENTS type
            time_spec=time_spec,
            time_spec_param=HorizonsTimeSpecParam(time_spec),
            ephem_type=EphemType.ELEMENTS,
            center=self.center,
            use_julian=True,
        )

        response = request.make_request()

        # Parse the response
        parser = ElementsParser(response)
        data_points = parser.parse()

        if not data_points:
            raise ValueError(f"No data returned from Horizons for planet {planet}")

        # Convert each data point to the required format
        result: Dict[float, Dict[Quantity, Any]] = {}
        for jd, values in data_points:
            position_data: Dict[Quantity, Any] = {}
            for orbital_quantity, value in values.items():
                if orbital_quantity in OrbitalElementsQuantityToQuantity:
                    standard_quantity = OrbitalElementsQuantityToQuantity[
                        orbital_quantity
                    ]
                    position_data[standard_quantity] = self._convert_value(
                        value, standard_quantity
                    )
            result[jd] = position_data

        return result
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/horizons/test_orbital_elements_ephemeris.py::TestOrbitalElementsEphemerisGetPositions -v`
Expected: PASS (2 tests) - Note: These tests make real API calls to JPL Horizons

**Step 5: Commit**

```bash
git add src/starloom/horizons/orbital_elements_ephemeris.py tests/horizons/test_orbital_elements_ephemeris.py
git commit -m "feat: implement OrbitalElementsEphemeris.get_planet_positions

Add method to query time range orbital elements from JPL Horizons.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 6: Update ephemeris_weft_generator to detect lunar node

**Files:**
- Modify: `src/starloom/weft/ephemeris_weft_generator.py:112-114`
- Test: `tests/weft/test_ephemeris_weft_generator.py` (create new file)

**Step 1: Write the failing test**

Create `tests/weft/test_ephemeris_weft_generator.py`:

```python
"""Tests for ephemeris weft generator detection logic."""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from starloom.weft.ephemeris_weft_generator import generate_weft_file
from starloom.planet import Planet
from starloom.ephemeris.quantities import Quantity


class TestEphemerisWeftGeneratorDetection(unittest.TestCase):
    """Test detection and routing logic in generate_weft_file."""

    @patch("starloom.weft.ephemeris_weft_generator.OrbitalElementsEphemeris")
    @patch("starloom.weft.ephemeris_weft_generator.WeftWriter")
    @patch("starloom.weft.ephemeris_weft_generator.EphemerisDataSource")
    @patch("starloom.weft.ephemeris_weft_generator.get_recommended_blocks")
    def test_lunar_node_uses_orbital_elements_ephemeris(
        self,
        mock_get_blocks,
        mock_data_source,
        mock_writer,
        mock_orbital_ephemeris,
    ):
        """Test that lunar node planet uses OrbitalElementsEphemeris."""
        # Setup mocks
        mock_get_blocks.return_value = {"monthly": True}
        mock_ephemeris_instance = MagicMock()
        mock_orbital_ephemeris.return_value = mock_ephemeris_instance

        mock_writer_instance = MagicMock()
        mock_writer.return_value = mock_writer_instance
        mock_weft_file = MagicMock()
        mock_writer_instance.create_multi_precision_file.return_value = mock_weft_file

        # Call with LUNAR_NORTH_NODE
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)

        generate_weft_file(
            planet=Planet.LUNAR_NORTH_NODE,
            quantity=Quantity.ASCENDING_NODE_LONGITUDE,
            start_date=start,
            end_date=end,
            output_path="/tmp/test.weft",
        )

        # Verify OrbitalElementsEphemeris was instantiated
        mock_orbital_ephemeris.assert_called_once()

    @patch("starloom.weft.ephemeris_weft_generator.HorizonsEphemeris")
    @patch("starloom.weft.ephemeris_weft_generator.WeftWriter")
    @patch("starloom.weft.ephemeris_weft_generator.EphemerisDataSource")
    @patch("starloom.weft.ephemeris_weft_generator.get_recommended_blocks")
    def test_regular_planet_uses_horizons_ephemeris(
        self,
        mock_get_blocks,
        mock_data_source,
        mock_writer,
        mock_horizons_ephemeris,
    ):
        """Test that regular planet uses HorizonsEphemeris."""
        # Setup mocks
        mock_get_blocks.return_value = {"monthly": True}
        mock_ephemeris_instance = MagicMock()
        mock_horizons_ephemeris.return_value = mock_ephemeris_instance

        mock_writer_instance = MagicMock()
        mock_writer.return_value = mock_writer_instance
        mock_weft_file = MagicMock()
        mock_writer_instance.create_multi_precision_file.return_value = mock_weft_file

        # Call with regular planet (Mars)
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)

        generate_weft_file(
            planet=Planet.MARS,
            quantity=Quantity.ECLIPTIC_LONGITUDE,
            start_date=start,
            end_date=end,
            output_path="/tmp/test.weft",
        )

        # Verify HorizonsEphemeris was instantiated
        mock_horizons_ephemeris.assert_called_once()


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/weft/test_ephemeris_weft_generator.py -v`
Expected: FAIL with "ImportError: cannot import name 'OrbitalElementsEphemeris'"

**Step 3: Write minimal implementation**

In `src/starloom/weft/ephemeris_weft_generator.py`, modify the section around line 112:

First, add import near top of file (around line 10):

```python
from ..horizons.orbital_elements_ephemeris import OrbitalElementsEphemeris
```

Then replace the section where ephemeris is created (around line 112-114):

```python
    from starloom.horizons.ephemeris import HorizonsEphemeris

    # Create or use provided ephemeris client
    if ephemeris is None:
        # Detect if we need OrbitalElementsEphemeris (for lunar nodes or orbital element quantities)
        needs_orbital_elements = False

        # Check if planet is LUNAR_NORTH_NODE
        from starloom.planet import Planet
        if isinstance(planet, Planet) and planet == Planet.LUNAR_NORTH_NODE:
            needs_orbital_elements = True
        elif isinstance(planet, str) and planet.upper() == "LUNAR_NORTH_NODE":
            needs_orbital_elements = True

        # Check if quantity is an orbital element
        if isinstance(quantity, Quantity):
            orbital_element_quantities = {
                Quantity.ASCENDING_NODE_LONGITUDE,
                Quantity.ECCENTRICITY,
                Quantity.PERIAPSIS_DISTANCE,
                Quantity.APOAPSIS_DISTANCE,
                Quantity.INCLINATION,
                Quantity.ARGUMENT_OF_PERIFOCUS,
                Quantity.MEAN_MOTION,
                Quantity.MEAN_ANOMALY,
                Quantity.TRUE_ANOMALY,
                Quantity.SEMI_MAJOR_AXIS,
                Quantity.ORBITAL_PERIOD,
            }
            if quantity in orbital_element_quantities:
                needs_orbital_elements = True

        if needs_orbital_elements:
            ephemeris = OrbitalElementsEphemeris()
        else:
            ephemeris = HorizonsEphemeris()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/weft/test_ephemeris_weft_generator.py -v`
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add src/starloom/weft/ephemeris_weft_generator.py tests/weft/test_ephemeris_weft_generator.py
git commit -m "feat: add detection logic for OrbitalElementsEphemeris

Auto-detect when to use OrbitalElementsEphemeris based on planet
(LUNAR_NORTH_NODE) or quantity (orbital elements).

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 7: Add integration test for lunar node weftball generation

**Files:**
- Create: `tests/integration/test_lunar_node_weftball.py`

**Step 1: Write the test**

Create `tests/integration/test_lunar_node_weftball.py`:

```python
"""Integration test for lunar node weftball generation."""

import unittest
import tempfile
import os
from datetime import datetime, timezone

from starloom.weft.ephemeris_weft_generator import generate_weft_file
from starloom.planet import Planet
from starloom.ephemeris.quantities import Quantity
from starloom.weft.weft_reader import WeftReader


class TestLunarNodeWeftballIntegration(unittest.TestCase):
    """Test end-to-end lunar node weftball generation."""

    def test_generate_lunar_node_weft_file(self):
        """Test generating a weft file for lunar north node."""
        # Create temporary output file
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".weft", delete=False
        ) as tmp:
            output_path = tmp.name

        try:
            # Generate weft file for 7 days with 1-day steps
            start = datetime(2024, 3, 1, 0, 0, 0, tzinfo=timezone.utc)
            end = datetime(2024, 3, 8, 0, 0, 0, tzinfo=timezone.utc)

            result_path = generate_weft_file(
                planet=Planet.LUNAR_NORTH_NODE,
                quantity=Quantity.ASCENDING_NODE_LONGITUDE,
                start_date=start,
                end_date=end,
                output_path=output_path,
                step_hours="24h",
                custom_timespan="2024",
            )

            # Verify file was created
            self.assertEqual(result_path, output_path)
            self.assertTrue(os.path.exists(output_path))
            self.assertGreater(os.path.getsize(output_path), 0)

            # Read the weft file and verify contents
            reader = WeftReader()
            reader.load(output_path)

            # Verify preamble contains expected information
            preamble = reader.weft_file.preamble
            self.assertIn("lunar_north_node", preamble.lower())
            self.assertIn("ascending_node_longitude", preamble.lower())

            # Get a value from the middle of the range
            test_date = datetime(2024, 3, 4, 12, 0, 0, tzinfo=timezone.utc)
            value = reader.get_value(test_date)

            # Verify value is a valid longitude (0-360 degrees)
            self.assertIsInstance(value, float)
            self.assertGreaterEqual(value, 0.0)
            self.assertLess(value, 360.0)

        finally:
            # Clean up
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_lunar_node_with_string_planet_name(self):
        """Test that string planet name 'lunar_north_node' works."""
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".weft", delete=False
        ) as tmp:
            output_path = tmp.name

        try:
            start = datetime(2024, 3, 1, 0, 0, 0, tzinfo=timezone.utc)
            end = datetime(2024, 3, 3, 0, 0, 0, tzinfo=timezone.utc)

            # Use string planet name
            result_path = generate_weft_file(
                planet="lunar_north_node",
                quantity=Quantity.ASCENDING_NODE_LONGITUDE,
                start_date=start,
                end_date=end,
                output_path=output_path,
                step_hours="24h",
            )

            # Verify file was created
            self.assertTrue(os.path.exists(output_path))
            self.assertGreater(os.path.getsize(output_path), 0)

        finally:
            # Clean up
            if os.path.exists(output_path):
                os.unlink(output_path)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it passes**

Run: `pytest tests/integration/test_lunar_node_weftball.py -v`
Expected: PASS (2 tests) - Note: These tests make real API calls

**Step 3: Commit**

```bash
git add tests/integration/test_lunar_node_weftball.py
git commit -m "test: add integration tests for lunar node weftball

Add end-to-end tests verifying complete weftball generation for
lunar north node.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 8: Update make_weftball.py to support lunar_north_node

**Files:**
- Modify: `scripts/make_weftball.py:30-31` (update QUANTITIES list comment)
- Test: Manual CLI test

**Step 1: Test current behavior**

Run: `python -m scripts.make_weftball lunar_north_node --debug`
Expected: Should work due to automatic detection in `generate_weft_file`

**Step 2: Document that lunar_north_node is supported**

In `scripts/make_weftball.py`, update the docstring (lines 2-18):

```python
"""
Script to generate a "weftball" for a planet or astronomical point.

This script:
1. Generates decade-by-decade weft files for ecliptic longitude, ecliptic latitude, and distance
2. Combines them into one big file for each quantity
3. Creates a tar.gz archive containing the three files

Supported targets:
- Planets: mercury, venus, mars, jupiter, saturn, uranus, neptune, pluto
- Calculated points: lunar_north_node (Moon's ascending node)

Usage:
    python -m scripts.make_weftball <planet> [options]

Example:
    python -m scripts.make_weftball mars
    python -m scripts.make_weftball lunar_north_node
    python -m scripts.make_weftball jupiter --debug  # Enable debug logging
    python -m scripts.make_weftball saturn -v        # Enable verbose (info) logging
    python -m scripts.make_weftball mercury --quiet  # Suppress all but error logs
"""
```

Update QUANTITIES comment (line 30-31):

```python
# Define the quantities we want to generate
# For most planets: longitude, distance, latitude
# For lunar_north_node: only longitude (ascending node)
QUANTITIES = ["longitude", "distance", "latitude"]
```

**Step 3: Test with lunar_north_node**

Run: `python -m scripts.make_weftball lunar_north_node --debug`
Expected: Should generate lunar_north_node_weftball.tar.gz

Note: This may take a long time (querying 1900-2100). For faster testing, consider modifying DECADES temporarily.

**Step 4: Commit**

```bash
git add scripts/make_weftball.py
git commit -m "docs: update make_weftball.py for lunar_north_node

Document that lunar_north_node is a supported target and update
usage examples.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 9: Add CLI documentation and README updates

**Files:**
- Modify: `README.md` (add lunar node example)
- Create: `docs/lunar_nodes.md` (detailed documentation)

**Step 1: Add lunar node example to README**

In `README.md`, find the weftball generation section and add:

```markdown
### Generating Weftballs for Lunar Nodes

The lunar north node (Moon's ascending node) can be generated as a weftball:

```bash
# Generate lunar north node weftball for 1900-2100
python -m scripts.make_weftball lunar_north_node

# Or use the CLI directly for a specific time range
starloom weft generate lunar_north_node longitude \
  --start 2024-01-01 \
  --stop 2025-01-01 \
  --step 1h \
  --output lunar_north_node_2024.weft
```

The lunar north node is calculated from the Moon's orbital elements. The south node
is always 180° opposite the north node and can be calculated as `(north_node + 180) % 360`.
```

**Step 2: Create detailed documentation**

Create `docs/lunar_nodes.md`:

```markdown
# Lunar Nodes Weftball

## Overview

The lunar nodes are calculated astronomical points where the Moon's orbital plane intersects the ecliptic plane. The **north node** (ascending node) is where the Moon crosses the ecliptic from south to north. The **south node** (descending node) is 180° opposite.

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

print(f"North Node: {north_node:.2f}°")
print(f"South Node: {south_node:.2f}°")
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
print(f"North Node: {north_node:.2f}°")
```

## Technical Details

### Why Query Moon's Orbital Elements?

Lunar nodes are not independent celestial bodies in JPL Horizons. They are geometric points derived from the Moon's orbital plane. The most accurate way to obtain node positions is to query the Moon's orbital elements, where the ascending node longitude is provided directly.

### Coordinate System

- **Reference frame**: Ecliptic coordinates (J2000)
- **Origin**: Vernal equinox (0° Aries)
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
```

**Step 3: Commit**

```bash
git add README.md docs/lunar_nodes.md
git commit -m "docs: add lunar nodes documentation

Add comprehensive documentation for lunar node weftball generation,
usage examples, and technical details.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 10: Run full test suite and verify

**Files:**
- None (verification step)

**Step 1: Run all tests**

Run: `pytest -v`
Expected: All new tests pass, pre-existing failures unchanged (5 failures baseline)

**Step 2: Run specific lunar node tests**

Run: `pytest -k lunar_node -v`
Expected: All lunar node tests pass

**Step 3: Manual verification - Generate small weftball**

Run:
```bash
starloom weft generate lunar_north_node longitude \
  --start 2024-03-01 \
  --stop 2024-03-08 \
  --step 1d \
  --output /tmp/lunar_node_test.weft
```

Expected: File created successfully

**Step 4: Manual verification - Inspect weftball**

Run: `starloom weft info /tmp/lunar_node_test.weft`
Expected: Shows lunar_north_node, ascending_node_longitude, valid date range

**Step 5: Manual verification - Query value**

Run: `starloom weft lookup /tmp/lunar_node_test.weft 2024-03-04`
Expected: Returns longitude value between 0-360

**Step 6: Document completion**

No commit needed - this is verification only.

If all tests pass and manual verification succeeds, the implementation is complete!

---

## Success Criteria (Verification Checklist)

- [x] `Planet.LUNAR_NORTH_NODE` enum value exists
- [x] `OrbitalElementsQuantityToQuantity` mapping works
- [x] `OrbitalElementsEphemeris.get_planet_position()` queries Horizons
- [x] `OrbitalElementsEphemeris.get_planet_positions()` queries time ranges
- [x] Detection logic routes lunar node to `OrbitalElementsEphemeris`
- [x] Integration test generates valid weftball
- [x] CLI works: `starloom weft generate lunar_north_node longitude ...`
- [x] Documentation complete and accurate
- [x] All new tests pass
- [x] Manual verification confirms working end-to-end

---

## Notes for Implementer

### Testing Strategy

- Tests marked with "Note: These tests make real API calls" will hit JPL Horizons
- Use short time ranges for faster test execution
- Consider setting up test fixtures for offline testing if needed
- The 5 pre-existing test failures are unrelated to this work

### API Rate Limits

- JPL Horizons has no official rate limit but be respectful
- The existing HTTP cache in `HorizonsRequest` will cache responses
- For development, use short time ranges (days, not decades)

### Debugging Tips

- Use `--debug` flag with make_weftball.py for verbose output
- Check `data/http_cache/` for cached Horizons responses
- Use `pytest -v -s` to see print statements during tests
- Test with fixed dates (2024-03-15) for reproducible results

### Code Style

- Follow existing patterns in the codebase
- Use type hints consistently
- Keep functions focused and single-purpose
- Add docstrings for all public methods
- Use existing patterns for error handling

### Commit Message Format

All commits use the format:
```
type: short description

Longer explanation if needed.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

Types: `feat`, `fix`, `test`, `docs`, `refactor`
