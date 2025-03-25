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
            planet: The planet to find retrograde periods for
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
        
        # For middle points, use central difference for more accurate velocity
        next_jd = dates[idx + 1]
        prev_jd = dates[idx - 1]
        next_lon = positions[next_jd][Quantity.ECLIPTIC_LONGITUDE]
        prev_lon = positions[prev_jd][Quantity.ECLIPTIC_LONGITUDE]
        forward_vel = angle_diff(next_lon, curr_lon) / (next_jd - jd)
        backward_vel = angle_diff(curr_lon, prev_lon) / (jd - prev_jd)
        return (forward_vel + backward_vel) / 2

    def _get_position_at_time(self, jd: float) -> Optional[float]:
        """Get planet position at a specific Julian date."""
        try:
            time_spec = TimeSpec.from_dates([jd])
            positions = self.planet_ephemeris.get_planet_positions(self.planet.name, time_spec)
            return positions[jd][Quantity.ECLIPTIC_LONGITUDE]
        except Exception:
            return None

    def _find_zero_crossing(
        self,
        dates: List[float],
        positions: Dict[float, Dict[str, float]],
        velocities: Optional[Dict[float, float]] = None,
        target_angle: Optional[float] = None,
        find_velocity_crossing: bool = False,
        find_pos_to_neg: bool = True,
        precision_hours: int = 1,
    ) -> Optional[Tuple[float, float]]:
        """Find a crossing point (velocity=0 or specific angle) with high precision.
        
        Args:
            dates: List of Julian dates
            positions: Dict mapping Julian dates to position data
            velocities: Optional dict of pre-calculated velocities
            target_angle: Optional target longitude to find crossing for
            find_velocity_crossing: If True, find where velocity crosses zero
            find_pos_to_neg: If finding velocity crossing, whether to find positive-to-negative
                             or negative-to-positive crossing
            precision_hours: Desired precision in hours
            
        Returns:
            Tuple of (julian_date, longitude) at the crossing point
        """
        if len(dates) < 2:
            return None
            
        # Find potential crossing segments
        segments = []
        
        for i in range(1, len(dates)):
            prev_jd, curr_jd = dates[i-1], dates[i]
            
            if find_velocity_crossing:
                # If velocities not provided, calculate them
                if velocities is None:
                    prev_vel = self._calculate_velocity(positions, prev_jd, dates)
                    curr_vel = self._calculate_velocity(positions, curr_jd, dates)
                else:
                    prev_vel = velocities[prev_jd]
                    curr_vel = velocities[curr_jd]
                    
                # Check for velocity zero crossing
                if (find_pos_to_neg and prev_vel > 0 and curr_vel < 0) or \
                   (not find_pos_to_neg and prev_vel < 0 and curr_vel > 0):
                    segments.append((prev_jd, curr_jd))
            elif target_angle is not None:
                # Check for crossing of target angle
                prev_lon = positions[prev_jd][Quantity.ECLIPTIC_LONGITUDE]
                curr_lon = positions[curr_jd][Quantity.ECLIPTIC_LONGITUDE]
                
                prev_diff = angle_diff(target_angle, prev_lon)
                curr_diff = angle_diff(target_angle, curr_lon)
                
                if prev_diff * curr_diff <= 0:  # Sign change indicates crossing
                    segments.append((prev_jd, curr_jd))
        
        if not segments:
            return None
            
        # For multiple segments, choose the most central one
        if len(segments) > 1:
            mid_date = (dates[0] + dates[-1]) / 2
            segments.sort(key=lambda seg: abs((seg[0] + seg[1])/2 - mid_date))
            
        # Use binary search to refine the crossing with high precision
        left_jd, right_jd = segments[0]
        precision = precision_hours / 24.0  # Convert hours to days
        
        while (right_jd - left_jd) > precision:
            mid_jd = (left_jd + right_jd) / 2
            
            if find_velocity_crossing:
                # For velocity crossings, calculate velocity at midpoint
                # We need positions slightly before and after to calculate velocity
                offset = 0.01  # Small offset (~15 min) for velocity calculation
                
                pos_before = self._get_position_at_time(mid_jd - offset)
                pos_at = self._get_position_at_time(mid_jd)
                pos_after = self._get_position_at_time(mid_jd + offset)
                
                if None in (pos_before, pos_at, pos_after):
                    # Fall back to linear interpolation if we can't get precise positions
                    break
                    
                vel_before = angle_diff(pos_at, pos_before) / offset
                vel_after = angle_diff(pos_after, pos_at) / offset
                mid_vel = (vel_before + vel_after) / 2
                
                if (find_pos_to_neg and mid_vel > 0) or (not find_pos_to_neg and mid_vel < 0):
                    left_jd = mid_jd
                else:
                    right_jd = mid_jd
            elif target_angle is not None:
                # For angle crossings, check if we've crossed the target angle
                mid_lon = self._get_position_at_time(mid_jd)
                if mid_lon is None:
                    break
                    
                mid_diff = angle_diff(target_angle, mid_lon)
                
                if prev_diff * mid_diff <= 0:
                    right_jd = mid_jd
                else:
                    left_jd = mid_jd
                    prev_diff = mid_diff
        
        # Get final position at the crossing point
        cross_jd = (left_jd + right_jd) / 2
        cross_lon = self._get_position_at_time(cross_jd)
        
        if cross_lon is None:
            # Fall back to interpolation if direct query fails
            left_lon = positions[left_jd][Quantity.ECLIPTIC_LONGITUDE]
            right_lon = positions[right_jd][Quantity.ECLIPTIC_LONGITUDE]
            fraction = (cross_jd - left_jd) / (right_jd - left_jd)
            cross_lon = interpolate_angle(left_lon, right_lon, fraction)
            
        return (cross_jd, cross_lon)

    def _find_sun_aspect(
        self,
        planet: Planet,
        jd_range: Tuple[float, float],
        planet_positions: Dict[float, Dict[str, float]] = None,
        dates: List[float] = None,
        precision_hours: int = 1
    ) -> Optional[Tuple[float, float]]:
        """Find the precise time of cazimi (conjunction) or opposition with the Sun.
        
        Args:
            planet: The planet to find aspect for
            jd_range: (start_jd, end_jd) for the search window
            planet_positions: Optional dict of planet positions (if already available)
            dates: Optional list of Julian dates (if already available)
            precision_hours: Desired precision in hours
            
        Returns:
            Tuple of (julian_date, longitude) at the aspect point
        """
        if planet == Planet.SUN:
            return None
            
        # Get the date range
        start_jd, end_jd = jd_range
        aspect_start = julian_to_datetime(start_jd)
        aspect_end = julian_to_datetime(end_jd)
        
        # Define the time specification with 1-hour step
        time_spec = TimeSpec.from_range(aspect_start, aspect_end, "1h")
        
        # Get planet and sun positions if not provided
        if planet_positions is None:
            try:
                planet_positions = self.planet_ephemeris.get_planet_positions(
                    planet.name, time_spec
                )
                dates = sorted(planet_positions.keys())
            except Exception as e:
                logging.error(f"Error getting planet positions: {e}")
                return None
                
        # Get sun positions
        try:
            sun_positions = self.sun_ephemeris.get_planet_positions("SUN", time_spec)
        except Exception as e:
            logging.error(f"Error getting sun positions: {e}")
            return None
            
        # Determine the type of aspect based on whether it's an inner or outer planet
        is_inner = planet in [Planet.MERCURY, Planet.VENUS]
        
        # Find closest approach between planet and sun
        min_diff = 360.0
        aspect_jd = None
        aspect_lon = None
        
        for jd in dates:
            if jd < start_jd or jd > end_jd or jd not in sun_positions:
                continue
                
            planet_lon = planet_positions[jd][Quantity.ECLIPTIC_LONGITUDE]
            sun_lon = sun_positions[jd][Quantity.ECLIPTIC_LONGITUDE]
            
            # For inner planets, look for conjunction (where diff is closest to 0°)
            # For outer planets, look for opposition (where diff is closest to 180°)
            diff = abs(angle_diff(planet_lon, sun_lon))
            
            if is_inner:
                curr_diff = diff  # Want closest to 0°
            else:
                curr_diff = abs(diff - 180.0)  # Want closest to 180°
                
            if curr_diff < min_diff:
                min_diff = curr_diff
                aspect_jd = jd
                aspect_lon = planet_lon
        
        if aspect_jd is None:
            return None
            
        # Now refine the aspect time with higher precision
        try:
            # Use binary search around initial cazimi for precision
            left_jd = aspect_jd - 0.1  # ~2.4 hours before
            right_jd = aspect_jd + 0.1  # ~2.4 hours after
            precision = precision_hours / 24.0  # Convert hours to days
            
            while (right_jd - left_jd) > precision / 6:  # 10 minutes of precision
                mid_jd = (left_jd + right_jd) / 2
                
                # Get planet and sun positions at midpoint
                mid_time_spec = TimeSpec.from_dates([mid_jd])
                
                try:
                    mid_planet_pos = self.planet_ephemeris.get_planet_positions(
                        planet.name, mid_time_spec
                    )
                    mid_sun_pos = self.sun_ephemeris.get_planet_positions(
                        "SUN", mid_time_spec
                    )
                    
                    mid_planet_lon = mid_planet_pos[mid_jd][Quantity.ECLIPTIC_LONGITUDE]
                    mid_sun_lon = mid_sun_pos[mid_jd][Quantity.ECLIPTIC_LONGITUDE]
                    
                    # Calculate angular difference
                    diff = abs(angle_diff(mid_planet_lon, mid_sun_lon))
                    
                    if is_inner:
                        curr_diff = diff
                    else:
                        curr_diff = abs(diff - 180.0)
                    
                    if curr_diff < min_diff:
                        min_diff = curr_diff
                        aspect_jd = mid_jd
                        aspect_lon = mid_planet_lon
                    
                    # Get positions on both sides to determine direction of approach
                    try:
                        before_jd = mid_jd - 0.02  # ~30 minutes before
                        after_jd = mid_jd + 0.02   # ~30 minutes after
                        
                        before_spec = TimeSpec.from_dates([before_jd])
                        after_spec = TimeSpec.from_dates([after_jd])
                        
                        before_planet = self.planet_ephemeris.get_planet_positions(
                            planet.name, before_spec
                        )[before_jd][Quantity.ECLIPTIC_LONGITUDE]
                        
                        before_sun = self.sun_ephemeris.get_planet_positions(
                            "SUN", before_spec
                        )[before_jd][Quantity.ECLIPTIC_LONGITUDE]
                        
                        after_planet = self.planet_ephemeris.get_planet_positions(
                            planet.name, after_spec
                        )[after_jd][Quantity.ECLIPTIC_LONGITUDE]
                        
                        after_sun = self.sun_ephemeris.get_planet_positions(
                            "SUN", after_spec
                        )[after_jd][Quantity.ECLIPTIC_LONGITUDE]
                        
                        # Calculate differences before and after
                        before_diff = angle_diff(before_planet, before_sun)
                        after_diff = angle_diff(after_planet, after_sun)
                        
                        # Determine which side to search based on direction of change
                        if is_inner:
                            # For conjunction, see if difference is getting smaller or larger
                            if abs(before_diff) > abs(after_diff):
                                # Difference is decreasing, cazimi is ahead
                                left_jd = mid_jd
                            else:
                                # Difference is increasing, cazimi is behind
                                right_jd = mid_jd
                        else:
                            # For opposition, see if we're approaching or moving away from 180°
                            before_to_180 = abs(abs(before_diff) - 180.0)
                            after_to_180 = abs(abs(after_diff) - 180.0)
                            
                            if before_to_180 > after_to_180:
                                # Getting closer to 180°, opposition is ahead
                                left_jd = mid_jd
                            else:
                                # Moving away from 180°, opposition is behind
                                right_jd = mid_jd
                    except Exception:
                        # If direction detection fails, use basic approach
                        if is_inner:
                            if diff < 0.05:  # Very close already
                                break  # Stop refining if we're very close
                            
                            diff_angle = angle_diff(mid_planet_lon, mid_sun_lon)
                            if diff_angle > 0:
                                right_jd = mid_jd
                            else:
                                left_jd = mid_jd
                        else:
                            if abs(diff - 180.0) < 0.05:  # Very close to 180°
                                break
                                
                            if diff < 180.0:
                                left_jd = mid_jd
                            else:
                                right_jd = mid_jd
                except Exception:
                    # If a query fails, stop refining
                    break
            
            # Get the final position
            try:
                final_spec = TimeSpec.from_dates([aspect_jd])
                final_pos = self.planet_ephemeris.get_planet_positions(
                    planet.name, final_spec
                )
                final_lon = final_pos[aspect_jd][Quantity.ECLIPTIC_LONGITUDE]
                return (aspect_jd, final_lon)
            except Exception:
                # If we can't get the final position, use our best approximation
                if aspect_lon is not None:
                    return (aspect_jd, aspect_lon)
        except Exception as e:
            logging.error(f"Error refining aspect: {e}")
        
        # If we couldn't refine, but have a basic aspect, return it
        if aspect_jd is not None and aspect_lon is not None:
            return (aspect_jd, aspect_lon)
            
        return None

    def find_retrograde_periods(
        self, planet: Planet, start_date: datetime, end_date: datetime, step: str = "1d"
    ) -> Iterator[RetrogradePeriod]:
        """Find all retrograde periods for a planet within the given date range.
        
        Args:
            planet: The planet to find retrograde periods for
            start_date: Start of search range
            end_date: End of search range
            step: Time step for initial sampling (e.g. "1d", "6h")
            
        Yields:
            RetrogradePeriod objects as they are found
        """
        # First pass: Use at least 1-day step for initial scanning
        coarse_step = step if step.endswith("d") and int(step[:-1]) >= 1 else "1d"
        coarse_time_spec = TimeSpec.from_range(start_date, end_date, coarse_step)
        
        # Get coarse positions
        coarse_positions = self.planet_ephemeris.get_planet_positions(
            planet.name, coarse_time_spec
        )
        
        # Calculate velocities
        coarse_dates = sorted(coarse_positions.keys())
        coarse_velocities = {
            jd: self._calculate_velocity(coarse_positions, jd, coarse_dates)
            for jd in coarse_dates
        }
        
        # Find potential retrograde periods
        potential_periods = []
        current_period = None
        
        # Handle case where we start in the middle of retrograde motion
        if coarse_dates and coarse_velocities[coarse_dates[0]] < 0:
            first_jd = coarse_dates[0]
            current_period = {
                "start_jd": first_jd - 60,  # Look back 60 days to find retrograde station
                "end_jd": first_jd + 60     # Add buffer for finding direct station
            }
            
        # Scan through velocity changes to detect retrograde periods
        for i in range(1, len(coarse_dates)):
            prev_jd = coarse_dates[i-1]
            curr_jd = coarse_dates[i]
            
            prev_vel = coarse_velocities[prev_jd]
            curr_vel = coarse_velocities[curr_jd]
            
            # Detect transition to retrograde motion
            if prev_vel > 0 and curr_vel < 0:
                current_period = {
                    "start_jd": prev_jd - 30,  # Look back 30 days to ensure we capture shadow start
                    "end_jd": curr_jd + 30     # Add buffer for finding direct station
                }
                
            # Detect transition to direct motion
            elif prev_vel < 0 and curr_vel > 0:
                if current_period is None:
                    # Handle case where we start observing after retrograde already began
                    current_period = {
                        "start_jd": prev_jd - 30,  # Look back 30 days
                        "end_jd": curr_jd + 30     # Add buffer for finding post shadow
                    }
                else:
                    current_period["end_jd"] = curr_jd + 30
                    
                potential_periods.append(current_period)
                current_period = None
                
        # Handle case where we end in the middle of retrograde motion
        if current_period is not None:
            potential_periods.append(current_period)
            
        # Second pass: Analyze each potential period with higher precision
        fine_step = "3h"  # Use 3-hour sampling for higher precision
        
        for period in potential_periods:
            # Create time spec for this period with fine granularity
            period_start = julian_to_datetime(period["start_jd"])
            period_end = julian_to_datetime(period["end_jd"])
            
            # Ensure period is within overall search bounds
            period_end = min(period_end, end_date)
            
            fine_time_spec = TimeSpec.from_range(period_start, period_end, fine_step)
            
            # Get fine-grained positions
            try:
                fine_positions = self.planet_ephemeris.get_planet_positions(
                    planet.name, fine_time_spec
                )
            except Exception as e:
                logging.error(f"Error getting fine positions: {e}")
                continue
                
            fine_dates = sorted(fine_positions.keys())
            if len(fine_dates) < 2:
                continue
                
            # Calculate fine-grained velocities
            fine_velocities = {
                jd: self._calculate_velocity(fine_positions, jd, fine_dates)
                for jd in fine_dates
            }
            
            # Find precise station retrograde (velocity crosses from positive to negative)
            station_retrograde = self._find_zero_crossing(
                fine_dates, fine_positions, fine_velocities,
                find_velocity_crossing=True, find_pos_to_neg=True,
                precision_hours=1
            )
            
            if not station_retrograde:
                continue
                
            # Find precise station direct (velocity crosses from negative to positive)
            station_direct = self._find_zero_crossing(
                fine_dates, fine_positions, fine_velocities,
                find_velocity_crossing=True, find_pos_to_neg=False,
                precision_hours=1
            )
            
            if not station_direct:
                continue
                
            station_retro_jd, station_retro_lon = station_retrograde
            station_direct_jd, station_direct_lon = station_direct
            
            # Find pre-shadow start (when planet first crosses direct station longitude)
            # This happens before station retrograde
            pre_shadow_dates = [jd for jd in fine_dates if jd < station_retro_jd]
            pre_shadow_positions = {jd: fine_positions[jd] for jd in pre_shadow_dates}
            
            pre_shadow_start = None
            if pre_shadow_dates:
                pre_shadow_start = self._find_zero_crossing(
                    pre_shadow_dates, pre_shadow_positions,
                    target_angle=station_direct_lon,
                    precision_hours=1
                )
            
            # If we couldn't find pre-shadow, try extending search earlier
            if not pre_shadow_start:
                extended_start = julian_to_datetime(station_retro_jd - 60)
                if extended_start >= start_date:
                    try:
                        ext_time_spec = TimeSpec.from_range(
                            extended_start,
                            julian_to_datetime(station_retro_jd),
                            fine_step
                        )
                        ext_positions = self.planet_ephemeris.get_planet_positions(
                            planet.name, ext_time_spec
                        )
                        ext_dates = sorted(ext_positions.keys())
                        
                        pre_shadow_start = self._find_zero_crossing(
                            ext_dates, ext_positions,
                            target_angle=station_direct_lon,
                            precision_hours=1
                        )
                    except Exception:
                        pass
            
            # Find post-shadow end (when planet crosses retrograde station longitude)
            # This happens after station direct
            post_shadow_dates = [jd for jd in fine_dates if jd > station_direct_jd]
            post_shadow_positions = {jd: fine_positions[jd] for jd in post_shadow_dates}
            
            post_shadow_end = None
            if post_shadow_dates:
                post_shadow_end = self._find_zero_crossing(
                    post_shadow_dates, post_shadow_positions,
                    target_angle=station_retro_lon,
                    precision_hours=1
                )
            
            # If we couldn't find post-shadow, try extending search later
            if not post_shadow_end:
                extended_end = julian_to_datetime(station_direct_jd + 60)
                if extended_end <= end_date:
                    try:
                        ext_time_spec = TimeSpec.from_range(
                            julian_to_datetime(station_direct_jd),
                            extended_end,
                            fine_step
                        )
                        ext_positions = self.planet_ephemeris.get_planet_positions(
                            planet.name, ext_time_spec
                        )
                        ext_dates = sorted(ext_positions.keys())
                        
                        post_shadow_end = self._find_zero_crossing(
                            ext_dates, ext_positions,
                            target_angle=station_retro_lon,
                            precision_hours=1
                        )
                    except Exception:
                        pass
                        
            # For cazimi detection (inner planets) or opposition (outer planets),
            # we need more precise data centered around the retrograde period
            sun_aspect = None
            if planet != Planet.SUN:
                # Use 1-hour step for more precise cazimi detection
                aspect_start = julian_to_datetime(station_retro_jd - 5)  # 5 days before retrograde
                aspect_end = julian_to_datetime(station_direct_jd + 5)   # 5 days after direct
                
                # Ensure dates are within overall range
                aspect_start = max(aspect_start, start_date)
                aspect_end = min(aspect_end, end_date)
                
                try:
                    # Get positions with higher precision
                    aspect_time_spec = TimeSpec.from_range(aspect_start, aspect_end, "1h")
                    aspect_planet_pos = self.planet_ephemeris.get_planet_positions(
                        planet.name, aspect_time_spec
                    )
                    aspect_sun_pos = self.sun_ephemeris.get_planet_positions(
                        "SUN", aspect_time_spec
                    )
                    
                    is_inner = planet in [Planet.MERCURY, Planet.VENUS]
                    
                    # Find the closest conjunction (for inner planets) or opposition (for outer planets)
                    min_diff = 360.0
                    aspect_jd = None
                    aspect_lon = None
                    target_diff = 0.0 if is_inner else 180.0
                    
                    for jd in sorted(aspect_planet_pos.keys()):
                        if jd not in aspect_sun_pos:
                            continue
                            
                        planet_lon = aspect_planet_pos[jd][Quantity.ECLIPTIC_LONGITUDE]
                        sun_lon = aspect_sun_pos[jd][Quantity.ECLIPTIC_LONGITUDE]
                        
                        # For inner planets (conjunction), find minimum difference
                        # For outer planets (opposition), find closest to 180°
                        diff = abs(angle_diff(planet_lon, sun_lon))
                        if is_inner:
                            curr_diff = diff  # Want closest to 0°
                        else:
                            curr_diff = abs(diff - 180.0)  # Want closest to 180°
                            
                        if curr_diff < min_diff:
                            min_diff = curr_diff
                            aspect_jd = jd
                            aspect_lon = planet_lon
                    
                    if aspect_jd is not None:
                        # Further refine with binary search for 10-minute precision
                        left_jd = aspect_jd - 0.1  # ~2.4 hours before
                        right_jd = aspect_jd + 0.1  # ~2.4 hours after
                        precision = 10.0 / (24.0 * 60.0)  # 10 minutes in days
                        
                        while (right_jd - left_jd) > precision:
                            mid_jd = (left_jd + right_jd) / 2
                            
                            try:
                                # Get positions at midpoint
                                mid_time_spec = TimeSpec.from_dates([mid_jd])
                                mid_planet_pos = self.planet_ephemeris.get_planet_positions(
                                    planet.name, mid_time_spec
                                )
                                mid_sun_pos = self.sun_ephemeris.get_planet_positions(
                                    "SUN", mid_time_spec
                                )
                                
                                mid_planet_lon = mid_planet_pos[mid_jd][Quantity.ECLIPTIC_LONGITUDE]
                                mid_sun_lon = mid_sun_pos[mid_jd][Quantity.ECLIPTIC_LONGITUDE]
                                
                                # Calculate difference
                                diff = abs(angle_diff(mid_planet_lon, mid_sun_lon))
                                if is_inner:
                                    curr_diff = diff
                                else:
                                    curr_diff = abs(diff - 180.0)
                                
                                if curr_diff < min_diff:
                                    min_diff = curr_diff
                                    aspect_jd = mid_jd
                                    aspect_lon = mid_planet_lon
                                
                                # Narrow the search window
                                if is_inner:
                                    # For conjunction, check if planet is approaching or separating from sun
                                    planet_moving_faster = False
                                    try:
                                        # Check velocity difference to determine direction
                                        planet_vel = self._calculate_velocity(aspect_planet_pos, aspect_jd)
                                        sun_vel = self._calculate_velocity(aspect_sun_pos, aspect_jd)
                                        planet_moving_faster = abs(planet_vel) > abs(sun_vel)
                                    except Exception:
                                        pass
                                    
                                    # Choose which half to search based on direction
                                    diff = angle_diff(mid_planet_lon, mid_sun_lon)
                                    if (diff > 0 and planet_moving_faster) or (diff < 0 and not planet_moving_faster):
                                        right_jd = mid_jd
                                    else:
                                        left_jd = mid_jd
                                else:
                                    # For opposition, find where difference is closest to 180°
                                    if diff < 180.0:
                                        left_jd = mid_jd
                                    else:
                                        right_jd = mid_jd
                            except Exception:
                                # If we can't get positions, stop refining
                                break
                                
                        # Get final planet position
                        final_time_spec = TimeSpec.from_dates([aspect_jd])
                        try:
                            final_pos = self.planet_ephemeris.get_planet_positions(
                                planet.name, final_time_spec
                            )
                            aspect_lon = final_pos[aspect_jd][Quantity.ECLIPTIC_LONGITUDE]
                            sun_aspect = (aspect_jd, aspect_lon)
                        except Exception:
                            # If we can't get the exact position, use what we had
                            if aspect_lon is not None:
                                sun_aspect = (aspect_jd, aspect_lon)
                            
                except Exception as e:
                    logging.error(f"Error finding sun aspect: {e}")
            
            # Create RetrogradePeriod object
            yield RetrogradePeriod(
                planet=planet,
                station_retrograde=station_retrograde,
                station_direct=station_direct,
                pre_shadow_start=pre_shadow_start,
                post_shadow_end=post_shadow_end,
                sun_aspect=sun_aspect
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