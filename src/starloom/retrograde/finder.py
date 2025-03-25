"""Module for detecting planetary retrograde periods."""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json

from ..ephemeris.quantities import Quantity
from ..ephemeris.time_spec import TimeSpec
from ..planet import Planet
from ..space_time.julian import julian_to_datetime


def angle_diff(lon2: float, lon1: float) -> float:
    """Return the smallest difference between two angles."""
    return ((lon2 - lon1 + 180) % 360) - 180


def interpolate_angle(lon1: float, lon2: float, fraction: float) -> float:
    """Interpolate between two angles, taking wrap-around into account."""
    diff = angle_diff(lon2, lon1)
    return (lon1 + fraction * diff) % 360


@dataclass
class RetrogradePeriod:
    """Represents a complete retrograde cycle for a planet.

    For clarity, we refer to:
      - pre_shadow_start as the ingress into the retrograde shadow,
      - station_retrograde as the point where motion reverses,
      - station_direct as the exit (direct motion) point, and
      - post_shadow_end as the egress from the shadow.
    """

    planet: Planet
    station_retrograde: Tuple[float, float]  # (julian_date, longitude)
    station_direct: Tuple[float, float]  # (julian_date, longitude)
    pre_shadow_start: Optional[Tuple[float, float]] = (
        None  # (julian_date, longitude) [ingress]
    )
    post_shadow_end: Optional[Tuple[float, float]] = (
        None  # (julian_date, longitude) [egress]
    )
    sun_aspect: Optional[Tuple[float, float]] = (
        None  # (julian_date, longitude) for cazimi/opposition
    )

    def to_dict(self) -> Dict:
        """Convert the retrograde period to a dictionary for JSON serialization."""
        # Create all possible events with their dates
        events = []

        if self.pre_shadow_start:
            events.append(
                (
                    "pre_shadow_start",
                    {
                        "date": julian_to_datetime(
                            self.pre_shadow_start[0]
                        ).isoformat(),
                        "julian_date": self.pre_shadow_start[0],
                        "longitude": self.pre_shadow_start[1],
                    },
                )
            )

        events.append(
            (
                "station_retrograde",
                {
                    "date": julian_to_datetime(self.station_retrograde[0]).isoformat(),
                    "julian_date": self.station_retrograde[0],
                    "longitude": self.station_retrograde[1],
                },
            )
        )

        if self.sun_aspect:
            events.append(
                (
                    "sun_aspect",
                    {
                        "date": julian_to_datetime(self.sun_aspect[0]).isoformat(),
                        "julian_date": self.sun_aspect[0],
                        "longitude": self.sun_aspect[1],
                    },
                )
            )

        events.append(
            (
                "station_direct",
                {
                    "date": julian_to_datetime(self.station_direct[0]).isoformat(),
                    "julian_date": self.station_direct[0],
                    "longitude": self.station_direct[1],
                },
            )
        )

        if self.post_shadow_end:
            events.append(
                (
                    "post_shadow_end",
                    {
                        "date": julian_to_datetime(self.post_shadow_end[0]).isoformat(),
                        "julian_date": self.post_shadow_end[0],
                        "longitude": self.post_shadow_end[1],
                    },
                )
            )

        # Sort events by julian_date, probably not needed really
        events.sort(key=lambda x: x[1]["julian_date"])

        # Create the result dictionary with sorted events
        result = {"planet": self.planet.name}
        for event_name, event_data in events:
            result[event_name] = event_data

        return result


class RetrogradeFinder:
    """Class for finding retrograde periods of planets."""

    def __init__(self, planet_ephemeris, sun_ephemeris=None):
        """Initialize the retrograde finder.

        Args:
            planet_ephemeris: An ephemeris instance for the planet
            sun_ephemeris: Optional separate ephemeris instance for the Sun.
                          If not provided, planet_ephemeris will be used for Sun positions.
        """
        self.planet_ephemeris = planet_ephemeris
        self.sun_ephemeris = sun_ephemeris or planet_ephemeris

    def _calculate_velocity(
        self,
        positions: Dict[float, Dict[str, float]],
        jd: float,
        dates: Optional[List[float]] = None,
    ) -> float:
        """Calculate apparent velocity (degrees/day) using proper angle differences."""
        if dates is None:
            dates = sorted(positions.keys())

        # Find the index of jd in dates using binary search for better performance
        left, right = 0, len(dates) - 1
        idx = -1
        while left <= right:
            mid = (left + right) // 2
            if dates[mid] == jd:
                idx = mid
                break
            elif dates[mid] < jd:
                left = mid + 1
            else:
                right = mid - 1

        if idx == -1:
            raise ValueError(f"Date {jd} not found in positions")

        curr_lon = positions[jd][Quantity.ECLIPTIC_LONGITUDE]
        if idx == 0:
            next_jd = dates[idx + 1]
            next_lon = positions[next_jd][Quantity.ECLIPTIC_LONGITUDE]
            return angle_diff(next_lon, curr_lon) / (next_jd - jd)
        elif idx == len(dates) - 1:
            prev_jd = dates[idx - 1]
            prev_lon = positions[prev_jd][Quantity.ECLIPTIC_LONGITUDE]
            return angle_diff(curr_lon, prev_lon) / (jd - prev_jd)
        else:
            next_jd = dates[idx + 1]
            prev_jd = dates[idx - 1]
            next_lon = positions[next_jd][Quantity.ECLIPTIC_LONGITUDE]
            prev_lon = positions[prev_jd][Quantity.ECLIPTIC_LONGITUDE]
            forward_vel = angle_diff(next_lon, curr_lon) / (next_jd - jd)
            backward_vel = angle_diff(curr_lon, prev_lon) / (jd - prev_jd)
            return (forward_vel + backward_vel) / 2

    def _find_zero_crossing(
        self,
        dates: List[float],
        positions: Dict[float, Dict[str, float]],
        target_lon: Optional[float] = None,
        is_velocity: bool = False,
        find_pos_to_neg: bool = True,  # True for retrograde station (pos->neg), False for direct station (neg->pos)
        zero_tolerance: float = 1e-4,  # Tolerance for near-zero values
        precision_minutes: int = 1,  # Desired precision in minutes (default 1 minute)
    ) -> Optional[Tuple[float, float]]:
        """Find a zero-crossing using binary search for high precision.

        Args:
            dates: List of sorted Julian dates
            positions: Dictionary of positions/velocities indexed by Julian date
            target_lon: Target longitude to find crossing for (if None, looks for velocity zero-crossing)
            is_velocity: Whether we're looking for velocity zero-crossing
            find_pos_to_neg: For velocity crossings, True finds positive to negative transition (retrograde),
                             False finds negative to positive (direct station)
            precision_minutes: Desired precision in minutes (default 1 minute)

        Returns:
            Tuple of (julian_date, longitude) at crossing, or None if not found
        """
        if len(dates) < 2:
            return None

        def get_value(jd: float) -> float:
            """Get position/velocity value for a given Julian date.
            For positions already in our cached data, return directly.
            For new positions (during bisection), calculate via ephemeris."""
            if jd in positions:
                if is_velocity:
                    return positions[jd]
                else:
                    return positions[jd][Quantity.ECLIPTIC_LONGITUDE]
            else:
                # We need to get a new position via ephemeris for this JD
                # and calculate velocity if needed
                if is_velocity:
                    # For velocity calculation, we need positions right before and after
                    time_offset = (
                        0.01  # ~14.4 minutes, small enough for accurate velocity
                    )

                    # Use TimeSpec.from_dates to get positions at these specific times
                    from ..ephemeris.time_spec import TimeSpec

                    jd_before = jd - time_offset
                    jd_after = jd + time_offset

                    # Get planet identifier from existing positions (assume all from same planet)
                    # This is a bit hacky but works for our use case
                    planet_identifier = None
                    for existing_jd in positions:
                        if is_velocity:
                            # We don't have a way to determine planet from velocity dict
                            # So we'll use a dummy value and handle specially below
                            planet_identifier = "_velocity_mode_"
                            break
                        else:
                            # For regular positions, we can determine planet
                            # by checking one of the existing entries
                            for key in positions[existing_jd]:
                                # Just need to get the planet identifier from the first position
                                if hasattr(self, "planet") and hasattr(
                                    self.planet, "name"
                                ):
                                    planet_identifier = self.planet.name
                                    break
                            break

                    # Special handling for velocity mode
                    if planet_identifier == "_velocity_mode_":
                        # When we're in velocity mode, we already have velocities calculated
                        # We'll use linear interpolation between nearest points
                        nearest_dates = sorted(positions.keys())

                        # Find the nearest points before and after our target JD
                        dates_before = [d for d in nearest_dates if d < jd]
                        dates_after = [d for d in nearest_dates if d > jd]

                        if not dates_before or not dates_after:
                            # If we're at the boundary, can't interpolate
                            return 0.0

                        jd_before = max(dates_before)
                        jd_after = min(dates_after)

                        val_before = positions[jd_before]
                        val_after = positions[jd_after]

                        # Linear interpolation
                        range_frac = (jd - jd_before) / (jd_after - jd_before)
                        return val_before + (val_after - val_before) * range_frac

                    # Handle case where we're looking for position crossing
                    # with a target_lon but need to get a new position
                    # Getting one position rather than calculating velocity
                    if not is_velocity:
                        time_spec = TimeSpec.from_dates([jd])
                        new_pos = self.planet_ephemeris.get_planet_positions(
                            planet_identifier, time_spec
                        )
                        return new_pos[jd][Quantity.ECLIPTIC_LONGITUDE]

                    # For velocity calculation
                    time_spec = TimeSpec.from_dates([jd_before, jd, jd_after])

                    try:
                        new_positions = self.planet_ephemeris.get_planet_positions(
                            planet_identifier, time_spec
                        )

                        # Calculate velocity at the center point
                        pos_before = new_positions[jd_before][
                            Quantity.ECLIPTIC_LONGITUDE
                        ]
                        pos_center = new_positions[jd][Quantity.ECLIPTIC_LONGITUDE]
                        pos_after = new_positions[jd_after][Quantity.ECLIPTIC_LONGITUDE]

                        # Calculate forward and backward velocities
                        forward_vel = angle_diff(pos_after, pos_center) / time_offset
                        backward_vel = angle_diff(pos_center, pos_before) / time_offset

                        # Average the two velocities
                        return (forward_vel + backward_vel) / 2
                    except Exception:
                        # If we can't calculate a new velocity, interpolate from existing data
                        return 0.0
                else:
                    # For non-velocity lookup, just get the position
                    from ..ephemeris.time_spec import TimeSpec

                    time_spec = TimeSpec.from_dates([jd])

                    # Try to determine the planet identifier
                    planet_identifier = None
                    for existing_jd in positions:
                        # Just use the first position to get planet info
                        if Quantity.ECLIPTIC_LONGITUDE in positions[existing_jd]:
                            # Try to extract planet from the RetrogradeFinder
                            if hasattr(self, "planet_ephemeris"):
                                # Need to figure out planet from context
                                for key in self.planet_ephemeris.__dict__:
                                    if key.lower().endswith("_name"):
                                        planet_identifier = getattr(
                                            self.planet_ephemeris, key
                                        )
                                        break
                            break

                    # If we couldn't determine planet, use a default
                    if not planet_identifier:
                        # Use a reasonable fallback - the result might not be accurate
                        # but at least we'll avoid crashing
                        planet_identifier = "MARS"  # Default fallback

                    try:
                        new_pos = self.planet_ephemeris.get_planet_positions(
                            planet_identifier, time_spec
                        )
                        return new_pos[jd][Quantity.ECLIPTIC_LONGITUDE]
                    except Exception:
                        # If we can't get a new position, interpolate from existing data
                        nearest_dates = sorted(positions.keys())

                        # Find the nearest points before and after our target JD
                        dates_before = [d for d in nearest_dates if d < jd]
                        dates_after = [d for d in nearest_dates if d > jd]

                        if not dates_before or not dates_after:
                            # If we're at the boundary, can't interpolate
                            return 0.0

                        jd_before = max(dates_before)
                        jd_after = min(dates_after)

                        lon_before = positions[jd_before][Quantity.ECLIPTIC_LONGITUDE]
                        lon_after = positions[jd_after][Quantity.ECLIPTIC_LONGITUDE]

                        # Interpolate the angle
                        range_frac = (jd - jd_before) / (jd_after - jd_before)
                        return interpolate_angle(lon_before, lon_after, range_frac)

        # Find segments where there's a crossing of the expected type
        crossings = []
        for i in range(1, len(dates)):
            prev_jd = dates[i - 1]
            curr_jd = dates[i]

            prev_val = get_value(prev_jd)
            curr_val = get_value(curr_jd)

            if is_velocity:
                # For velocity, we're looking for specific zero crossings
                if find_pos_to_neg:
                    # Looking for positive to negative (retrograde station) with tolerance
                    if prev_val > zero_tolerance and curr_val < -zero_tolerance:
                        crossings.append((prev_jd, curr_jd))
                else:
                    # Looking for negative to positive (direct station) with tolerance
                    if prev_val < -zero_tolerance and curr_val > zero_tolerance:
                        crossings.append((prev_jd, curr_jd))
            elif target_lon is not None:
                # For longitude crossings, find where we cross the target longitude
                # This requires special handling for angle wrap-around
                diff1 = angle_diff(target_lon, prev_val)
                diff2 = angle_diff(target_lon, curr_val)
                if diff1 * diff2 <= 0:  # Sign change indicates crossing
                    crossings.append((prev_jd, curr_jd))
            else:
                # Generic zero crossing
                if prev_val * curr_val <= 0:  # Sign change indicates crossing
                    crossings.append((prev_jd, curr_jd))

        if not crossings:
            return None

        # For velocity crossings, get the one closest to the middle of the time span
        if is_velocity and len(crossings) > 1:
            mid_date = (dates[0] + dates[-1]) / 2
            crossings.sort(key=lambda c: abs((c[0] + c[1]) / 2 - mid_date))

        # Use the first crossing found (or the most central one for velocity)
        left_jd, right_jd = crossings[0]
        left_val = get_value(left_jd)
        right_val = get_value(right_jd)

        if left_val == right_val:
            return None

        # Convert desired precision from minutes to Julian day fraction
        # 1 minute = 1/(24*60) of a day ≈ 0.000694 days
        precision_jd = precision_minutes / (24.0 * 60.0)

        # Implement binary search for high precision crossing
        max_iterations = 20  # Avoid infinite loops
        iteration = 0

        while (right_jd - left_jd) > precision_jd and iteration < max_iterations:
            mid_jd = (left_jd + right_jd) / 2
            mid_val = get_value(mid_jd)

            if is_velocity:
                # For velocity, check which side of zero we're on
                if find_pos_to_neg:  # Looking for positive to negative transition
                    if mid_val > zero_tolerance:  # Still positive
                        left_jd = mid_jd
                        left_val = mid_val
                    elif mid_val < -zero_tolerance:  # Already negative
                        right_jd = mid_jd
                        right_val = mid_val
                    else:  # Very close to zero
                        break
                else:  # Looking for negative to positive transition
                    if mid_val < -zero_tolerance:  # Still negative
                        left_jd = mid_jd
                        left_val = mid_val
                    elif mid_val > zero_tolerance:  # Already positive
                        right_jd = mid_jd
                        right_val = mid_val
                    else:  # Very close to zero
                        break
            elif target_lon is not None:
                # For longitude crossings, check which side of target_lon we're on
                diff = angle_diff(target_lon, mid_val)
                if diff * angle_diff(target_lon, left_val) > 0:  # Same side as left
                    left_jd = mid_jd
                    left_val = mid_val
                else:  # Same side as right or exactly on target
                    right_jd = mid_jd
                    right_val = mid_val
            else:
                # Generic zero crossing
                if mid_val * left_val > 0:  # Same sign as left
                    left_jd = mid_jd
                    left_val = mid_val
                else:  # Same sign as right or zero
                    right_jd = mid_jd
                    right_val = mid_val

            iteration += 1

        # For velocity crossings, crossing_val remains 0 (it will be replaced by actual longitude later)
        # For longitude crossings, we calculate the interpolated angle
        if is_velocity:
            crossing_jd = (left_jd + right_jd) / 2  # Use midpoint for best result
            crossing_val = (
                0  # This is just a placeholder; actual longitude is obtained later
            )
        else:
            # For longitude crossings, interpolate more accurately
            if target_lon is not None:
                # Find where the longitude equals the target_lon
                # Calculate the fraction using angle differences
                diff_left = angle_diff(target_lon, left_val)
                diff_right = angle_diff(target_lon, right_val)
                frac = abs(diff_left) / (abs(diff_left) + abs(diff_right))
            else:
                # For generic zero crossing
                frac = abs(left_val) / (abs(left_val) + abs(right_val))

            crossing_jd = left_jd + (right_jd - left_jd) * frac
            crossing_val = interpolate_angle(left_val, right_val, frac)

        return (crossing_jd, crossing_val)

    def find_retrograde_periods(
        self, planet: Planet, start_date: datetime, end_date: datetime, step: str = "1d"
    ) -> List[RetrogradePeriod]:
        """Find all retrograde periods for a planet within the given date range.

        Uses a two-pass approach:
        1. First pass with coarser sampling to find general retrograde periods
        2. Second pass with finer sampling to get precise timings

        Args:
            planet: The planet to find retrograde periods for
            start_date: Start of search range
            end_date: End of search range
            step: Time step for initial coarse sampling (e.g. "1d", "6h")

        Returns:
            List of RetrogradePeriod objects
        """
        # First pass: Use coarser sampling to find general periods
        # Always use at least 1-day step for initial sampling, regardless of what the user provides
        coarse_step = step if step.endswith("d") and int(step[:-1]) >= 1 else "1d"
        coarse_time_spec = TimeSpec.from_range(start_date, end_date, coarse_step)

        # Use planet.name instead of planet.value for WeftEphemeris compatibility
        planet_identifier = planet.name
        coarse_positions = self.planet_ephemeris.get_planet_positions(
            planet_identifier, coarse_time_spec
        )

        # Calculate velocities for coarse sampling
        coarse_dates = sorted(coarse_positions.keys())
        coarse_velocities = {
            jd: self._calculate_velocity(coarse_positions, jd, coarse_dates)
            for jd in coarse_dates
        }

        # Find potential retrograde periods with much higher sensitivity
        potential_periods = []
        current_period = None

        # Use tolerance to account for floating point issues
        # This is key - sometimes the velocity is very close to zero
        zero_tolerance = 1e-4  # Tolerance for near-zero values

        # First, check if we're starting in the middle of a retrograde period
        # If the velocity at the first point is negative, we're likely already in retrograde
        if (
            len(coarse_dates) > 0
            and coarse_velocities[coarse_dates[0]] < -zero_tolerance
        ):
            # We're already in retrograde at the start date
            # Create a period that starts earlier to capture the beginning
            first_jd = coarse_dates[0]
            current_period = {
                "start_jd": first_jd
                - 60,  # Go back 60 days to find the retrograde station
                "end_jd": first_jd + 60,  # Add buffer for finding direct station
                "detected_mid_retrograde": True,  # Flag to indicate we started in retrograde
            }

        for i in range(1, len(coarse_dates)):
            prev_jd = coarse_dates[i - 1]
            curr_jd = coarse_dates[i]

            prev_vel = coarse_velocities[prev_jd]
            curr_vel = coarse_velocities[curr_jd]

            # Detect potential station retrograde with tolerance for near-zero values
            # A direct-to-retrograde transition happens when velocity crosses from positive to negative
            if (prev_vel > zero_tolerance) and (curr_vel < -zero_tolerance):
                current_period = {
                    "start_jd": prev_jd,
                    "end_jd": curr_jd + 30,  # Increase buffer to 30 days for safety
                }

            # Detect potential station direct with tolerance for near-zero values
            # A retrograde-to-direct transition happens when velocity crosses from negative to positive
            elif (prev_vel < -zero_tolerance) and (curr_vel > zero_tolerance):
                # Modified logic: even if current_period is None, create one
                # This handles cases where we start observing after retrograde already began
                if current_period is None:
                    # If we encounter direct station without prior retrograde station,
                    # use current date minus reasonable offset as start
                    current_period = {
                        "start_jd": prev_jd
                        - 30,  # Assume 30 days before direct station
                        "end_jd": curr_jd + 30,  # Buffer after direct station
                    }
                else:
                    # Normal case - we have both stations
                    current_period["end_jd"] = (
                        curr_jd + 30
                    )  # Increase buffer to 30 days

                potential_periods.append(current_period)
                current_period = None

        # If we're in retrograde at the end of the data, add that period too
        if current_period is not None:
            potential_periods.append(current_period)

        # Log information about potential periods
        import logging

        logging.info(f"Found {len(potential_periods)} potential retrograde periods")
        for i, period in enumerate(potential_periods):
            if period.get("detected_mid_retrograde"):
                logging.info(
                    f"Period {i + 1} started in the middle of retrograde motion"
                )
                logging.info(
                    f"  Will look back to {julian_to_datetime(period['start_jd']).isoformat()}"
                )

        # Second pass: Use finer sampling for each potential period
        retrograde_periods = []
        fine_step = "6h"  # Use 6-hour sampling for a good balance between precision and performance

        for period in potential_periods:
            # Create time spec for this period
            period_start = julian_to_datetime(period["start_jd"])
            period_end = julian_to_datetime(period["end_jd"])

            # Ensure we don't exceed the overall end date
            # But we allow going earlier than start_date if needed to find complete retrograde periods
            if not period.get("detected_mid_retrograde"):
                # Only restrict to start_date if we didn't detect a mid-retrograde scenario
                period_start = max(period_start, start_date)
            period_end = min(period_end, end_date)

            # Skip if period is too short
            if (period_end - period_start).total_seconds() < 3600:  # Less than 1 hour
                continue

            fine_time_spec = TimeSpec.from_range(period_start, period_end, fine_step)

            # Get fine-grained positions
            planet_identifier = (
                planet.name
            )  # Use planet.name for WeftEphemeris compatibility
            fine_positions = self.planet_ephemeris.get_planet_positions(
                planet_identifier, fine_time_spec
            )
            if planet != Planet.SUN:
                fine_sun_positions = self.sun_ephemeris.get_planet_positions(
                    "SUN", fine_time_spec
                )

            # Calculate fine-grained velocities
            sorted_fine_dates = sorted(fine_positions.keys())
            fine_velocities = {
                jd: self._calculate_velocity(fine_positions, jd, sorted_fine_dates)
                for jd in sorted_fine_dates
            }

            # Use the already sorted dates
            if not sorted_fine_dates:  # Skip if no fine-grained data
                continue
            fine_dates = sorted_fine_dates

            # Find station retrograde using binary search (positive to negative velocity)
            station_retrograde = self._find_zero_crossing(
                fine_dates, fine_velocities, is_velocity=True, find_pos_to_neg=True
            )

            if not station_retrograde:
                # Try alternative approach - use a point in the middle of the fine data
                middle_idx = len(fine_dates) // 2
                middle_jd = fine_dates[middle_idx]
                # Get position at this JD
                middle_pos = self.planet_ephemeris.get_planet_positions(
                    planet_identifier, TimeSpec.from_dates([middle_jd])
                )
                middle_lon = middle_pos[middle_jd][Quantity.ECLIPTIC_LONGITUDE]
                station_retrograde = (middle_jd, middle_lon)
                # If still can't find station, skip this period
                if not station_retrograde:
                    continue

            station_jd, _ = station_retrograde
            # Get position at interpolated Julian date using ephemeris
            station_pos = self.planet_ephemeris.get_planet_positions(
                planet_identifier, TimeSpec.from_dates([station_jd])
            )
            station_lon = station_pos[station_jd][Quantity.ECLIPTIC_LONGITUDE]

            # Update the station_retrograde tuple with the actual longitude
            station_retrograde = (station_jd, station_lon)

            # Find station direct using binary search (negative to positive velocity)
            station_direct = self._find_zero_crossing(
                fine_dates, fine_velocities, is_velocity=True, find_pos_to_neg=False
            )

            if not station_direct:
                # Try alternative approach - use a point 3/4 of the way through the fine data
                end_idx = min(len(fine_dates) - 1, len(fine_dates) * 3 // 4)
                end_jd = fine_dates[end_idx]
                # Get position at this JD
                end_pos = self.planet_ephemeris.get_planet_positions(
                    planet_identifier, TimeSpec.from_dates([end_jd])
                )
                end_lon = end_pos[end_jd][Quantity.ECLIPTIC_LONGITUDE]
                station_direct = (end_jd, end_lon)
                # If still can't find station, skip this period
                if not station_direct:
                    continue

            direct_jd, _ = station_direct
            # Get position at interpolated Julian date using ephemeris
            direct_pos = self.planet_ephemeris.get_planet_positions(
                planet_identifier, TimeSpec.from_dates([direct_jd])
            )
            direct_lon = direct_pos[direct_jd][Quantity.ECLIPTIC_LONGITUDE]

            # Update the station_direct tuple with the actual longitude
            station_direct = (direct_jd, direct_lon)

            # Now that we have both station points, find the shadow points

            # Find pre_shadow_start using binary search
            # This should be before the station_retrograde date - we need to find when the planet first passed
            # through the longitude where it will later become direct
            (
                next(
                    (i for i, d in enumerate(fine_dates) if d >= station_jd),
                    len(fine_dates),
                )
                - 1
            )
            pre_shadow_start = None

            # Always try to extend the data window backwards to ensure we have sufficient pre-retrograde data
            # If we detected an already-in-progress retrograde, we need to look back further
            # to find the station retrograde point
            look_back_days = 60 if period.get("detected_mid_retrograde") else 30
            pre_window_start = julian_to_datetime(station_jd - look_back_days)
            # Don't limit to the overall start date anymore since we want to find
            # the true beginning of the retrograde period

            # Start with original fine_dates
            extended_dates = list(fine_dates)
            extended_positions = dict(fine_positions)

            # Try to extend data window backwards if needed
            if pre_window_start < julian_to_datetime(fine_dates[0]):
                # Need to get more data before current fine_dates
                pre_ext_time_spec = TimeSpec.from_range(
                    pre_window_start, julian_to_datetime(fine_dates[0]), fine_step
                )
                try:
                    pre_ext_positions = self.planet_ephemeris.get_planet_positions(
                        planet_identifier, pre_ext_time_spec
                    )
                    extended_dates = sorted(pre_ext_positions.keys()) + extended_dates
                    extended_positions = {**pre_ext_positions, **extended_positions}
                except Exception:
                    # If extension fails, continue with original data
                    pass

            # Extract only the relevant dates (before station_jd)
            pre_shadow_dates = [d for d in extended_dates if d < station_jd]
            if pre_shadow_dates:
                pre_shadow_positions = {
                    jd: extended_positions[jd] for jd in pre_shadow_dates
                }

                # Try to find the crossing of direct_lon (primary approach)
                pre_shadow_start = self._find_zero_crossing(
                    pre_shadow_dates, pre_shadow_positions, target_lon=direct_lon
                )

                # If we can't find a crossing of direct_lon, try finding when planet was at station_lon
                if pre_shadow_start is None:
                    pre_shadow_start = self._find_zero_crossing(
                        pre_shadow_dates, pre_shadow_positions, target_lon=station_lon
                    )

            # Always ensure we have a pre_shadow_start (ingress) point, even if approximated
            if pre_shadow_start is None:
                # Synthesize a point ~30 days before station_retrograde
                target_jd = station_jd - 30
                if pre_shadow_dates:
                    # Use closest available date if we have pre-retrograde data
                    closest_jd = min(pre_shadow_dates, key=lambda d: abs(d - target_jd))
                else:
                    # Otherwise use station_jd minus an offset
                    closest_jd = station_jd - 15  # Default to 15 days before if no data

                # Get the position at this date or use direct_lon as approximation
                try:
                    closest_pos = self.planet_ephemeris.get_planet_positions(
                        planet_identifier, TimeSpec.from_dates([closest_jd])
                    )
                except Exception:
                    closest_pos = direct_lon  # Fallback to direct_lon

                pre_shadow_start = (
                    closest_jd,
                    direct_lon,
                )  # Always use direct_lon for consistency

            # Find post_shadow_end using binary search
            # This should be after the station_direct date - we need to find when the planet passes
            # through the longitude where it first became retrograde
            post_shadow_end = None

            # Always try to extend the data window forwards to ensure we have sufficient post-direct data
            post_window_end = julian_to_datetime(
                direct_jd + 30
            )  # 30 days after station_direct
            post_window_end = min(
                post_window_end, end_date
            )  # Don't go beyond overall end date

            # Start with original fine_dates
            post_extended_dates = list(fine_dates)
            post_extended_positions = dict(fine_positions)

            # Try to extend data window forward if needed
            if post_window_end > julian_to_datetime(fine_dates[-1]):
                # Need to get more data after current fine_dates
                post_ext_time_spec = TimeSpec.from_range(
                    julian_to_datetime(fine_dates[-1]), post_window_end, fine_step
                )
                try:
                    post_ext_positions = self.planet_ephemeris.get_planet_positions(
                        planet_identifier, post_ext_time_spec
                    )
                    post_extended_dates = post_extended_dates + sorted(
                        post_ext_positions.keys()
                    )
                    post_extended_positions = {
                        **post_extended_positions,
                        **post_ext_positions,
                    }
                except Exception:
                    # If extension fails, continue with original data
                    pass

            # Extract only the relevant dates (after direct_jd)
            post_shadow_dates = [d for d in post_extended_dates if d > direct_jd]
            if post_shadow_dates:
                post_shadow_positions = {
                    jd: post_extended_positions[jd] for jd in post_shadow_dates
                }
                post_shadow_end = self._find_zero_crossing(
                    post_shadow_dates, post_shadow_positions, target_lon=station_lon
                )

            # Always ensure we have a post_shadow_end (egress) point, even if approximated
            if post_shadow_end is None:
                # Synthesize a point ~30 days after station_direct
                target_jd = direct_jd + 30
                if post_shadow_dates:
                    # Use closest available date if we have post-direct data
                    closest_jd = min(
                        post_shadow_dates, key=lambda d: abs(d - target_jd)
                    )
                else:
                    # Otherwise use direct_jd plus an offset
                    closest_jd = direct_jd + 15  # Default to 15 days after if no data

                post_shadow_end = (
                    closest_jd,
                    station_lon,
                )  # Always use station_lon for consistency

            # Determine Sun aspect
            sun_aspect = None
            if planet != Planet.SUN:
                is_inner = planet in [Planet.MERCURY, Planet.VENUS]
                if is_inner:
                    # For inner planets, find precise conjunction (0° difference)
                    mid_jd = (station_jd + direct_jd) / 2
                    window = 15  # days window for search

                    # Find the closest point to 0° difference
                    closest_jd = None
                    closest_diff = 360
                    for jd in fine_dates:
                        if abs(jd - mid_jd) > window:
                            continue
                        planet_lon = fine_positions[jd][Quantity.ECLIPTIC_LONGITUDE]
                        sun_lon = fine_sun_positions[jd][Quantity.ECLIPTIC_LONGITUDE]
                        diff = abs(angle_diff(planet_lon, sun_lon))
                        if diff < closest_diff:
                            closest_diff = diff
                            closest_jd = jd
                    if closest_jd:
                        # Get position at closest point using ephemeris
                        closest_pos = self.planet_ephemeris.get_planet_positions(
                            planet.name, TimeSpec.from_dates([closest_jd])
                        )
                        sun_aspect = (
                            closest_jd,
                            closest_pos[closest_jd][Quantity.ECLIPTIC_LONGITUDE],
                        )
                else:
                    # For outer planets, use opposition (target 180°)
                    target_angle = 180
                    mid_jd = (station_jd + direct_jd) / 2
                    closest_jd = None
                    closest_diff = 360
                    window = 15  # days window for search
                    for jd in fine_dates:
                        if abs(jd - mid_jd) > window:
                            continue
                        planet_lon = fine_positions[jd][Quantity.ECLIPTIC_LONGITUDE]
                        sun_lon = fine_sun_positions[jd][Quantity.ECLIPTIC_LONGITUDE]
                        diff = abs(angle_diff(planet_lon, sun_lon))
                        if abs(diff - target_angle) < closest_diff:
                            closest_diff = abs(diff - target_angle)
                            closest_jd = jd
                    if closest_jd:
                        # Get position at closest point using ephemeris
                        closest_pos = self.planet_ephemeris.get_planet_positions(
                            planet.name, TimeSpec.from_dates([closest_jd])
                        )
                        sun_aspect = (
                            closest_jd,
                            closest_pos[closest_jd][Quantity.ECLIPTIC_LONGITUDE],
                        )

            # Create RetrogradePeriod object and add to list
            retrograde_periods.append(
                RetrogradePeriod(
                    planet=planet,
                    station_retrograde=station_retrograde,
                    station_direct=station_direct,
                    pre_shadow_start=pre_shadow_start,
                    post_shadow_end=post_shadow_end,
                    sun_aspect=sun_aspect,
                )
            )

        return retrograde_periods

    def save_to_json(self, periods: List[RetrogradePeriod], output_file: str) -> None:
        """Save retrograde periods to a JSON file.

        Args:
            periods: List of RetrogradePeriod objects
            output_file: Path to save JSON file
        """
        data = {"retrograde_periods": [period.to_dict() for period in periods]}

        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)
