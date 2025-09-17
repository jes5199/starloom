"""Unit tests for the transit finder."""

from datetime import datetime, timedelta, timezone
import unittest

from starloom.planet import Planet
from starloom.transits.finder import ASPECT_ANGLES, TransitFinder
from starloom.ephemeris.ephemeris import Ephemeris
from starloom.ephemeris.quantities import Quantity
from starloom.ephemeris.time_spec import TimeSpec
from starloom.space_time.julian import julian_from_datetime, julian_to_datetime


BASE_DATETIME = datetime(2024, 1, 1, tzinfo=timezone.utc)


class LinearEphemeris(Ephemeris):
    """Simple ephemeris with linear longitude progression for testing."""

    def __init__(self, offset: float, rate: float) -> None:
        self.offset = offset
        self.rate = rate

    def get_planet_position(self, planet: str, time=None):  # type: ignore[override]
        if time is None:
            time = BASE_DATETIME
        positions = self.get_planet_positions(planet, TimeSpec.from_dates([time]))
        return next(iter(positions.values()))

    def get_planet_positions(self, planet: str, time_spec: TimeSpec):  # type: ignore[override]
        positions = {}
        for time_point in time_spec.get_time_points():
            if isinstance(time_point, datetime):
                dt = time_point.astimezone(timezone.utc)
                jd = julian_from_datetime(dt)
            else:
                jd = float(time_point)
                dt = julian_to_datetime(jd)
            delta_days = (dt - BASE_DATETIME).total_seconds() / 86400.0
            longitude = (self.offset + self.rate * delta_days) % 360.0
            positions[jd] = {Quantity.ECLIPTIC_LONGITUDE: longitude}
        return positions


class TransitFinderTest(unittest.TestCase):
    """Tests for the :class:`TransitFinder` algorithm."""

    def test_finder_detects_all_major_aspects(self) -> None:
        primary_ephemeris = LinearEphemeris(offset=0.0, rate=1.0)
        secondary_ephemeris = LinearEphemeris(offset=-10.0, rate=1.5)
        finder = TransitFinder(primary_ephemeris, secondary_ephemeris)

        start = BASE_DATETIME
        stop = BASE_DATETIME + timedelta(days=400)

        events = finder.find_transits(
            Planet.MARS,
            Planet.JUPITER,
            start,
            stop,
            step="10d",
        )

        aspect_order = [event.aspect for event in events]
        self.assertEqual(
            aspect_order,
            ["CONJUNCTION", "SEXTILE", "SQUARE", "TRINE", "OPPOSITION"],
        )

        for event in events:
            expected_days = ((ASPECT_ANGLES[event.aspect] - 350.0) % 360.0) / 0.5
            expected_dt = BASE_DATETIME + timedelta(days=expected_days)
            self.assertLess(
                abs(event.exact_datetime - expected_dt),
                timedelta(minutes=1),
                msg=f"{event.aspect} timing mismatch",
            )
            self.assertAlmostEqual(
                event.relative_angle,
                ASPECT_ANGLES[event.aspect],
                places=3,
                msg=f"{event.aspect} angle mismatch",
            )


if __name__ == "__main__":
    unittest.main()
