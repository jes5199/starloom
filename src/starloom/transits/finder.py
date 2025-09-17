"""Tools for computing angular transits (aspects) between celestial bodies."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union

from ..ephemeris.ephemeris import Ephemeris
from ..ephemeris.quantities import Quantity
from ..ephemeris.time_spec import TimeSpec
from ..planet import Planet
from ..space_time.julian import julian_to_datetime

# Primary aspects to detect between bodies and their target angular separations.
ASPECT_ANGLES: Dict[str, float] = {
    "CONJUNCTION": 0.0,
    "SEXTILE": 60.0,
    "SQUARE": 90.0,
    "TRINE": 120.0,
    "OPPOSITION": 180.0,
}

# Tolerance in degrees for considering an aspect "exact" during refinement.
ANGLE_TOLERANCE_DEGREES = 1e-3  # ~3.6 arc-seconds
# Minimum separation between recorded events in days (to avoid duplicate detections).
MIN_EVENT_SEPARATION_DAYS = 30.0 / (24 * 60 * 60)  # 30 seconds
# Maximum number of refinement iterations when bisecting between samples.
MAX_REFINEMENT_ITERATIONS = 40


@dataclass
class _TransitState:
    """Intermediate state for a specific aspect detection."""

    julian_date: float
    diff_degrees: float
    primary_longitude: float
    secondary_longitude: float


@dataclass
class TransitEvent:
    """Represents an exact angular aspect between two celestial bodies."""

    primary: Planet
    secondary: Planet
    aspect: str
    target_angle: float
    julian_date: float
    primary_longitude: float
    secondary_longitude: float

    @property
    def exact_datetime(self) -> datetime:
        """Return the event timestamp as a timezone-aware datetime in UTC."""
        return julian_to_datetime(self.julian_date)

    @property
    def relative_angle(self) -> float:
        """Return the normalized angular separation between the bodies (0–360°)."""
        return normalize_angle(self.secondary_longitude - self.primary_longitude)

    @property
    def orb(self) -> float:
        """Return the signed deviation from the target aspect angle in degrees."""
        return normalize_difference(self.relative_angle, self.target_angle)

    def to_dict(self) -> Dict[str, Union[str, float]]:
        """Return a serializable dictionary representation of the event."""
        dt = self.exact_datetime.astimezone(timezone.utc)
        return {
            "primary": self.primary.name,
            "secondary": self.secondary.name,
            "aspect": self.aspect,
            "target_angle": self.target_angle,
            "exact_time": dt.isoformat(),
            "julian_date": self.julian_date,
            "primary_longitude": self.primary_longitude,
            "secondary_longitude": self.secondary_longitude,
            "relative_angle": self.relative_angle,
            "orb_degrees": self.orb,
        }


def normalize_angle(angle: float) -> float:
    """Normalize an angle to the range [0, 360)."""
    return angle % 360.0


def normalize_difference(value: float, target: float) -> float:
    """Return the signed difference between two angles in the range [-180, 180)."""
    diff = (value - target + 180.0) % 360.0 - 180.0
    return diff


class TransitFinder:
    """Compute angular aspect transits between two celestial bodies."""

    def __init__(
        self,
        primary_ephemeris: Ephemeris,
        secondary_ephemeris: Optional[Ephemeris] = None,
    ) -> None:
        self.primary_ephemeris = primary_ephemeris
        self.secondary_ephemeris = secondary_ephemeris or primary_ephemeris

    def find_transits(
        self,
        primary: Planet,
        secondary: Planet,
        start_date: Union[datetime, float],
        end_date: Union[datetime, float],
        step: str = "6h",
        aspects: Optional[Dict[str, float]] = None,
    ) -> List[TransitEvent]:
        """Find exact aspect transits between two bodies within a time range.

        Args:
            primary: The leading planet/body.
            secondary: The other planet/body.
            start_date: Start datetime or Julian date for the search window.
            end_date: End datetime or Julian date for the search window.
            step: Step size string (e.g. "6h", "1d") for coarse scanning.
            aspects: Optional mapping of aspect names to target angles. Defaults to
                     the major aspects defined in :data:`ASPECT_ANGLES`.

        Returns:
            List of :class:`TransitEvent` objects ordered by occurrence time.
        """

        aspect_map = aspects or ASPECT_ANGLES
        if not aspect_map:
            return []

        start_dt = self._ensure_datetime(start_date)
        end_dt = self._ensure_datetime(end_date)

        if start_dt > end_dt:
            raise ValueError("start_date must be before end_date")

        time_spec = TimeSpec.from_range(start_dt, end_dt, step)

        primary_positions = self.primary_ephemeris.get_planet_positions(
            primary.name, time_spec
        )
        secondary_positions = self.secondary_ephemeris.get_planet_positions(
            secondary.name, time_spec
        )

        common_dates = sorted(
            set(primary_positions.keys()) & set(secondary_positions.keys())
        )
        if not common_dates:
            return []

        states: Dict[str, Optional[_TransitState]] = {
            name: None for name in aspect_map
        }
        last_event_jd: Dict[str, Optional[float]] = {name: None for name in aspect_map}
        events: List[TransitEvent] = []

        for jd in common_dates:
            primary_lon = normalize_angle(
                primary_positions[jd][Quantity.ECLIPTIC_LONGITUDE]
            )
            secondary_lon = normalize_angle(
                secondary_positions[jd][Quantity.ECLIPTIC_LONGITUDE]
            )
            relative_angle = normalize_angle(secondary_lon - primary_lon)

            for aspect_name, target_angle in aspect_map.items():
                diff = normalize_difference(relative_angle, target_angle)
                prev_state = states[aspect_name]
                current_state = _TransitState(jd, diff, primary_lon, secondary_lon)

                if prev_state is not None:
                    if self._has_crossing(prev_state.diff_degrees, diff):
                        event = self._refine_event(
                            primary,
                            secondary,
                            target_angle,
                            aspect_name,
                            prev_state,
                            current_state,
                        )
                        if event is not None:
                            last_jd = last_event_jd[aspect_name]
                            if (
                                last_jd is None
                                or abs(event.julian_date - last_jd)
                                > MIN_EVENT_SEPARATION_DAYS
                            ):
                                events.append(event)
                                last_event_jd[aspect_name] = event.julian_date
                states[aspect_name] = current_state

        events.sort(key=lambda ev: ev.julian_date)
        return events

    def _has_crossing(self, previous: float, current: float) -> bool:
        """Determine whether an aspect difference crosses zero between samples."""
        if abs(previous) <= ANGLE_TOLERANCE_DEGREES or abs(current) <= ANGLE_TOLERANCE_DEGREES:
            return True
        if previous * current < 0 and abs(previous - current) < 180:
            return True
        return False

    def _refine_event(
        self,
        primary: Planet,
        secondary: Planet,
        target_angle: float,
        aspect_name: str,
        left_state: _TransitState,
        right_state: _TransitState,
    ) -> Optional[TransitEvent]:
        """Refine an aspect crossing using bisection between two samples."""

        left = left_state
        right = right_state

        if abs(left.diff_degrees) <= ANGLE_TOLERANCE_DEGREES:
            return self._build_event(primary, secondary, aspect_name, target_angle, left)
        if abs(right.diff_degrees) <= ANGLE_TOLERANCE_DEGREES:
            return self._build_event(primary, secondary, aspect_name, target_angle, right)

        for _ in range(MAX_REFINEMENT_ITERATIONS):
            mid_jd = (left.julian_date + right.julian_date) / 2.0
            mid_state = self._compute_state(
                primary, secondary, target_angle, mid_jd
            )

            if abs(mid_state.diff_degrees) <= ANGLE_TOLERANCE_DEGREES:
                return self._build_event(
                    primary, secondary, aspect_name, target_angle, mid_state
                )

            if right.julian_date - left.julian_date <= MIN_EVENT_SEPARATION_DAYS / 2:
                return self._build_event(
                    primary, secondary, aspect_name, target_angle, mid_state
                )

            if left.diff_degrees * mid_state.diff_degrees <= 0:
                right = mid_state
            else:
                left = mid_state

        # Fall back to midpoint after max iterations
        final_state = self._compute_state(
            primary,
            secondary,
            target_angle,
            (left.julian_date + right.julian_date) / 2.0,
        )
        return self._build_event(
            primary, secondary, aspect_name, target_angle, final_state
        )

    def _compute_state(
        self,
        primary: Planet,
        secondary: Planet,
        target_angle: float,
        jd: float,
    ) -> _TransitState:
        """Compute the aspect difference and longitudes at a specific time."""
        time_spec = TimeSpec.from_dates([jd])
        primary_pos = self.primary_ephemeris.get_planet_positions(primary.name, time_spec)
        secondary_pos = self.secondary_ephemeris.get_planet_positions(
            secondary.name, time_spec
        )

        # get_planet_positions may return a key very slightly different due to
        # internal rounding. Use the first available key from each dictionary.
        primary_jd, primary_data = next(iter(primary_pos.items()))
        secondary_jd, secondary_data = next(iter(secondary_pos.items()))

        primary_lon = normalize_angle(primary_data[Quantity.ECLIPTIC_LONGITUDE])
        secondary_lon = normalize_angle(secondary_data[Quantity.ECLIPTIC_LONGITUDE])
        relative = normalize_angle(secondary_lon - primary_lon)
        diff = normalize_difference(relative, target_angle)

        # Prefer the requested JD if both calculations agree closely.
        jd_value = (primary_jd + secondary_jd) / 2.0
        if abs(primary_jd - secondary_jd) < 5e-10:
            jd_value = (primary_jd + secondary_jd) / 2.0
        elif abs(primary_jd - jd) < 5e-10:
            jd_value = jd

        return _TransitState(jd_value, diff, primary_lon, secondary_lon)

    def _build_event(
        self,
        primary: Planet,
        secondary: Planet,
        aspect_name: str,
        target_angle: float,
        state: _TransitState,
    ) -> TransitEvent:
        """Create a :class:`TransitEvent` from a computed state."""
        return TransitEvent(
            primary=primary,
            secondary=secondary,
            aspect=aspect_name,
            target_angle=target_angle,
            julian_date=state.julian_date,
            primary_longitude=state.primary_longitude,
            secondary_longitude=state.secondary_longitude,
        )

    def _ensure_datetime(self, value: Union[datetime, float]) -> datetime:
        """Normalize datetime or Julian date inputs to timezone-aware datetimes."""
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        return julian_to_datetime(float(value))


__all__ = ["TransitFinder", "TransitEvent", "ASPECT_ANGLES"]
