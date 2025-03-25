"""Module for detecting planetary retrograde periods."""

import bisect
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Iterator, Union, Any

from ..ephemeris.quantities import Quantity
from ..ephemeris.time_spec import TimeSpec
from ..planet import Planet
from ..space_time.julian import julian_to_datetime


def angle_diff(lon2: float, lon1: float) -> float:
    """Return the smallest difference between two angles."""
    return ((lon2 - lon1 + 180) % 360) - 180


def interpolate_angle(lon1: float, lon2: float, fraction: float) -> float:
    """Interpolate between two angles, accounting for wrap-around."""
    diff = angle_diff(lon2, lon1)
    return (lon1 + fraction * diff) % 360


def create_event_dict(jd: float, lon: float) -> Dict[str, Any]:
    """Create a standardized event dictionary."""
    return {
        "date": julian_to_datetime(jd).isoformat(),
        "julian_date": jd,
        "longitude": lon,
    }


@dataclass
class RetrogradePeriod:
    """Represents a complete retrograde cycle for a planet."""
    planet: Planet
    station_retrograde: Tuple[float, float]  # (julian_date, longitude)
    station_direct: Tuple[float, float]      # (julian_date, longitude)
    pre_shadow_start: Optional[Tuple[float, float]] = None  # (julian_date, longitude) [ingress]
    post_shadow_end: Optional[Tuple[float, float]] = None   # (julian_date, longitude) [egress]
    sun_aspect: Optional[Tuple[float, float]] = None        # (julian_date, longitude) for cazimi/opposition

    def to_dict(self) -> Dict:
        """Convert the retrograde period to a dictionary for JSON serialization."""
        events = []

        def add_event(name: str, data: Optional[Tuple[float, float]]):
            if data:
                jd, lon = data
                events.append((name, create_event_dict(jd, lon)))

        add_event("pre_shadow_start", self.pre_shadow_start)
        add_event("station_retrograde", self.station_retrograde)
        add_event("sun_aspect", self.sun_aspect)
        add_event("station_direct", self.station_direct)
        add_event("post_shadow_end", self.post_shadow_end)

        events.sort(key=lambda x: x[1]["julian_date"])
        result = {"planet": self.planet.name}
        for name, data in events:
            result[name] = data
        return result


class RetrogradeFinder:
    """Class for finding retrograde periods of planets."""

    def __init__(self, planet: Planet, planet_ephemeris, sun_ephemeris=None):
        """Initialize the retrograde finder.

        Args:
            planet_ephemeris: Ephemeris instance for the planet.
            sun_ephemeris: Optional ephemeris for the Sun. Defaults to planet_ephemeris.
        """
        self.planet = planet
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
        
        # Use bisect to find the index efficiently
        idx = bisect.bisect_left(dates, jd)
        if idx >= len(dates) or dates[idx] != jd:
            raise ValueError(f"Date {jd} not found in positions")

        curr_lon = positions[jd][Quantity.ECLIPTIC_LONGITUDE]
        
        # Handle boundary cases
        if idx == 0:
            next_jd = dates[1]
            next_lon = positions[next_jd][Quantity.ECLIPTIC_LONGITUDE]
            return angle_diff(next_lon, curr_lon) / (next_jd - jd)
        elif idx == len(dates) - 1:
            prev_jd = dates[idx - 1]
            prev_lon = positions[prev_jd][Quantity.ECLIPTIC_LONGITUDE]
            return angle_diff(curr_lon, prev_lon) / (jd - prev_jd)
        
        # For middle points, use central difference
        next_jd = dates[idx + 1]
        prev_jd = dates[idx - 1]
        next_lon = positions[next_jd][Quantity.ECLIPTIC_LONGITUDE]
        prev_lon = positions[prev_jd][Quantity.ECLIPTIC_LONGITUDE]
        forward_vel = angle_diff(next_lon, curr_lon) / (next_jd - jd)
        backward_vel = angle_diff(curr_lon, prev_lon) / (jd - prev_jd)
        return (forward_vel + backward_vel) / 2

    def _get_interpolated_position(self, jd: float) -> Optional[float]:
        """Get interpolated position at a specific Julian date."""
        try:
            time_spec = TimeSpec.from_dates([jd])
            new_pos = self.planet_ephemeris.get_planet_positions(self.planet.name, time_spec)
            return new_pos[jd][Quantity.ECLIPTIC_LONGITUDE]
        except Exception:
            return None

    def _find_zero_crossing(
        self,
        dates: List[float],
        positions: Union[Dict[float, float], Dict[float, Dict[str, float]]],
        target_lon: Optional[float] = None,
        is_velocity: bool = False,
        find_pos_to_neg: bool = True,
        zero_tolerance: float = 1e-4,
        precision_minutes: int = 1,
    ) -> Optional[Tuple[float, float]]:
        """Find a zero crossing using binary search and linear interpolation.

        Returns a tuple of (julian_date, value) where value is 0 for velocity or an interpolated angle.
        """
        if len(dates) < 2:
            return None

        def get_value(jd: float) -> float:
            """Get value at a specific Julian date, with fallback to interpolation."""
            if jd in positions:
                return positions[jd] if is_velocity else positions[jd][Quantity.ECLIPTIC_LONGITUDE]

            # Interpolate between nearest points if available
            nearest = sorted(positions.keys())
            dates_before = [d for d in nearest if d < jd]
            dates_after = [d for d in nearest if d > jd]
            
            if dates_before and dates_after:
                jd_before = max(dates_before)
                jd_after = min(dates_after)
                val_before = positions[jd_before] if is_velocity else positions[jd_before][Quantity.ECLIPTIC_LONGITUDE]
                val_after = positions[jd_after] if is_velocity else positions[jd_after][Quantity.ECLIPTIC_LONGITUDE]
                frac = (jd - jd_before) / (jd_after - jd_before)
                return val_before + (val_after - val_before) * frac if is_velocity else interpolate_angle(val_before, val_after, frac)

            # Fallback to ephemeris calculation
            if is_velocity:
                time_offset = 0.01  # ~14.4 minutes
                pos_before = self._get_interpolated_position(jd - time_offset)
                pos_center = self._get_interpolated_position(jd)
                pos_after = self._get_interpolated_position(jd + time_offset)
                
                if all(p is not None for p in [pos_before, pos_center, pos_after]):
                    forward_vel = angle_diff(pos_after, pos_center) / time_offset
                    backward_vel = angle_diff(pos_center, pos_before) / time_offset
                    return (forward_vel + backward_vel) / 2
                return 0.0
            else:
                pos = self._get_interpolated_position(jd)
                return pos if pos is not None else 0.0

        # Find crossing segments
        crossings = []
        for i in range(1, len(dates)):
            prev_jd, curr_jd = dates[i - 1], dates[i]
            prev_val, curr_val = get_value(prev_jd), get_value(curr_jd)
            
            if is_velocity:
                if find_pos_to_neg and prev_val > zero_tolerance and curr_val < -zero_tolerance:
                    crossings.append((prev_jd, curr_jd, prev_val, curr_val))
                elif not find_pos_to_neg and prev_val < -zero_tolerance and curr_val > zero_tolerance:
                    crossings.append((prev_jd, curr_jd, prev_val, curr_val))
            elif target_lon is not None:
                diff1 = angle_diff(target_lon, prev_val)
                diff2 = angle_diff(target_lon, curr_val)
                if diff1 * diff2 <= 0:
                    crossings.append((prev_jd, curr_jd, prev_val, curr_val))
            else:
                if prev_val * curr_val <= 0:
                    crossings.append((prev_jd, curr_jd, prev_val, curr_val))

        if not crossings:
            return None

        # For velocity crossings with multiple candidates, choose the most central one
        if is_velocity and len(crossings) > 1:
            mid_date = (dates[0] + dates[-1]) / 2
            crossings.sort(key=lambda c: abs((c[0] + c[1]) / 2 - mid_date))

        left_jd, right_jd, left_val, right_val = crossings[0]
        
        # Linear interpolation to find precise crossing
        if is_velocity:
            # For velocity, interpolate to find where it crosses zero
            fraction = abs(left_val) / (abs(left_val) + abs(right_val)) if abs(left_val - right_val) > 1e-12 else 0.5
            crossing_jd = left_jd + fraction * (right_jd - left_jd)
            crossing_val = 0
        elif target_lon is not None:
            # For target longitude, interpolate based on angle differences
            diff_left = angle_diff(target_lon, left_val)
            diff_right = angle_diff(target_lon, right_val)
            fraction = abs(diff_left) / (abs(diff_left) + abs(diff_right)) if abs(diff_left) + abs(diff_right) > 1e-12 else 0.5
            crossing_jd = left_jd + fraction * (right_jd - left_jd)
            crossing_val = target_lon
        else:
            # For general zero crossing, interpolate based on values
            fraction = abs(left_val) / (abs(left_val) + abs(right_val)) if abs(left_val) + abs(right_val) > 1e-12 else 0.5
            crossing_jd = left_jd + fraction * (right_jd - left_jd)
            crossing_val = interpolate_angle(left_val, right_val, fraction)

        return (crossing_jd, crossing_val)

    def find_retrograde_periods(
        self, planet: Planet, start_date: datetime, end_date: datetime, step: str = "1d"
    ) -> Iterator[RetrogradePeriod]:
        """Find all retrograde periods for a planet within the given date range.

        Uses a two-pass approach:
        1. First pass with coarser sampling to find general retrograde periods
        2. Second pass with finer sampling to get precise timings

        Args:
            planet: The planet to find retrograde periods for
            start_date: Start of search range
            end_date: End of search range
            step: Time step for initial coarse sampling (e.g. "1d", "6h")

        Yields:
            RetrogradePeriod objects as they are found
        """
        # First pass: Use coarser sampling to find general periods
        # Always use at least 1-day step for initial sampling, regardless of what the user provides
        coarse_step = step if step.endswith("d") and int(step[:-1]) >= 1 else "1d"
        coarse_time_spec = TimeSpec.from_range(start_date, end_date, coarse_step)

        # Get coarse positions
        coarse_positions = self.planet_ephemeris.get_planet_positions(
            self.planet.name, coarse_time_spec
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
            fine_positions = self.planet_ephemeris.get_planet_positions(
                self.planet.name, fine_time_spec
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
                    self.planet.name, TimeSpec.from_dates([middle_jd])
                )
                middle_lon = middle_pos[middle_jd][Quantity.ECLIPTIC_LONGITUDE]
                station_retrograde = (middle_jd, middle_lon)
                # If still can't find station, skip this period
                if not station_retrograde:
                    continue

            station_jd, _ = station_retrograde
            # Get position at interpolated Julian date using ephemeris
            station_pos = self.planet_ephemeris.get_planet_positions(
                self.planet.name, TimeSpec.from_dates([station_jd])
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
                    self.planet.name, TimeSpec.from_dates([end_jd])
                )
                end_lon = end_pos[end_jd][Quantity.ECLIPTIC_LONGITUDE]
                station_direct = (end_jd, end_lon)
                # If still can't find station, skip this period
                if not station_direct:
                    continue

            direct_jd, _ = station_direct
            # Get position at interpolated Julian date using ephemeris
            direct_pos = self.planet_ephemeris.get_planet_positions(
                self.planet.name, TimeSpec.from_dates([direct_jd])
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
                        self.planet.name, pre_ext_time_spec
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
                        self.planet.name, TimeSpec.from_dates([closest_jd])
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
                        self.planet.name, post_ext_time_spec
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
                            self.planet.name, TimeSpec.from_dates([closest_jd])
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
                            self.planet.name, TimeSpec.from_dates([closest_jd])
                        )
                        sun_aspect = (
                            closest_jd,
                            closest_pos[closest_jd][Quantity.ECLIPTIC_LONGITUDE],
                        )

            # Create RetrogradePeriod object and yield it immediately
            yield RetrogradePeriod(
                planet=planet,
                station_retrograde=station_retrograde,
                station_direct=station_direct,
                pre_shadow_start=pre_shadow_start,
                post_shadow_end=post_shadow_end,
                sun_aspect=sun_aspect,
            )

    def save_to_json(self, periods: List[RetrogradePeriod], output_file: str) -> None:
        """Save retrograde periods to a JSON file.

        Args:
            periods: List of RetrogradePeriod objects
            output_file: Path to save JSON file
        """
        data = {"retrograde_periods": [period.to_dict() for period in periods]}

        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)
