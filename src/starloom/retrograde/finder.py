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
        precision_seconds: int = 30,
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
            precision_seconds: Desired precision in seconds
            
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
                    segments.append((prev_jd, curr_jd, prev_vel, curr_vel))
            elif target_angle is not None:
                # Check for crossing of target angle
                prev_lon = positions[prev_jd][Quantity.ECLIPTIC_LONGITUDE]
                curr_lon = positions[curr_jd][Quantity.ECLIPTIC_LONGITUDE]
                
                prev_diff = angle_diff(target_angle, prev_lon)
                curr_diff = angle_diff(target_angle, curr_lon)
                
                if prev_diff * curr_diff <= 0:  # Sign change indicates crossing
                    # Store additional info for better interpolation
                    segments.append((prev_jd, curr_jd, prev_lon, curr_lon, prev_diff, curr_diff))
        
        if not segments:
            return None
            
        # For multiple segments, choose the most central one if looking for velocity crossing,
        # otherwise use the segment with the smallest value difference for target angle crossing
        if len(segments) > 1:
            if find_velocity_crossing:
                # For velocity, choose the segment closest to the middle of the date range
                mid_date = (dates[0] + dates[-1]) / 2
                segments.sort(key=lambda seg: abs((seg[0] + seg[1])/2 - mid_date))
            else:
                # For target angle, choose the segment with smallest angle difference
                segments.sort(key=lambda seg: abs(seg[4]) + abs(seg[5]))
            
        # Convert precision to days
        precision_days = precision_seconds / (24.0 * 60.0 * 60.0)
        
        if find_velocity_crossing:
            # For velocity crossings, use smart interpolation first
            left_jd, right_jd, left_vel, right_vel = segments[0]
            
            # Estimate zero crossing point using linear interpolation of velocities
            # This gives a very good initial guess
            if abs(left_vel - right_vel) > 1e-10:
                # Interpolate based on velocities to find where velocity = 0
                fraction = abs(left_vel) / (abs(left_vel) + abs(right_vel))
                initial_guess = left_jd + fraction * (right_jd - left_jd)
            else:
                # Equal velocities (unusual case)
                initial_guess = (left_jd + right_jd) / 2
                
            # Now refine with binary search using higher precision
            # Start with a window around our initial guess
            window_size = min(0.1, (right_jd - left_jd) / 2)  # ~2.4 hours or less
            left_jd = max(initial_guess - window_size, left_jd)
            right_jd = min(initial_guess + window_size, right_jd)
            
            # Function to compute velocity at a given time
            def compute_velocity(jd):
                # Use 30-second interval for velocity calculation
                time_delta = 30.0 / (24.0 * 60.0 * 60.0)
                
                try:
                    # Get three points for central difference
                    time_spec = TimeSpec.from_dates([jd - time_delta, jd, jd + time_delta])
                    pos_data = self.planet_ephemeris.get_planet_positions(
                        self.planet.name, time_spec
                    )
                    
                    # Extract longitudes
                    lon_before = pos_data[jd - time_delta][Quantity.ECLIPTIC_LONGITUDE]
                    lon_at = pos_data[jd][Quantity.ECLIPTIC_LONGITUDE]
                    lon_after = pos_data[jd + time_delta][Quantity.ECLIPTIC_LONGITUDE]
                    
                    # Calculate velocity using central difference
                    vel_before = angle_diff(lon_at, lon_before) / time_delta
                    vel_after = angle_diff(lon_after, lon_at) / time_delta
                    velocity = (vel_before + vel_after) / 2
                    
                    return velocity, lon_at
                except Exception:
                    # Fallback to linear interpolation between known points
                    return 0.0, None
            
            # Use binary search with adaptive refinement
            iterations = 0
            max_iterations = 15  # Prevent infinite loop
            best_jd = initial_guess
            best_vel = float('inf')
            
            while (right_jd - left_jd) > precision_days and iterations < max_iterations:
                iterations += 1
                
                mid_jd = (left_jd + right_jd) / 2
                mid_vel, mid_lon = compute_velocity(mid_jd)
                
                # Track best point found so far
                if abs(mid_vel) < abs(best_vel):
                    best_jd = mid_jd
                    best_vel = mid_vel
                    best_lon = mid_lon
                
                # Narrow search window based on velocity sign
                if (find_pos_to_neg and mid_vel > 0) or (not find_pos_to_neg and mid_vel < 0):
                    left_jd = mid_jd
                else:
                    right_jd = mid_jd
                    
                # If velocity is very close to zero, we can stop early
                if abs(mid_vel) < 0.0001:  # Very close to station point
                    break
                
            # Final result - use best point found
            cross_jd = best_jd
            cross_lon = best_lon if best_lon is not None else self._get_position_at_time(best_jd)
            
            # If we still don't have longitude, interpolate
            if cross_lon is None:
                try:
                    time_spec = TimeSpec.from_dates([cross_jd])
                    pos_data = self.planet_ephemeris.get_planet_positions(
                        self.planet.name, time_spec
                    )
                    cross_lon = pos_data[cross_jd][Quantity.ECLIPTIC_LONGITUDE]
                except Exception:
                    # Last resort: linear interpolation from original segment
                    fraction = (cross_jd - segments[0][0]) / (segments[0][1] - segments[0][0])
                    left_lon = positions[segments[0][0]][Quantity.ECLIPTIC_LONGITUDE]
                    right_lon = positions[segments[0][1]][Quantity.ECLIPTIC_LONGITUDE]
                    cross_lon = interpolate_angle(left_lon, right_lon, fraction)
            
        else:
            # For target angle crossing
            left_jd, right_jd, left_lon, right_lon, left_diff, right_diff = segments[0]
            
            # Estimate crossing using linear interpolation of angle differences
            if abs(left_diff - right_diff) > 1e-10:
                # Interpolate based on angle differences to find where difference = 0
                fraction = abs(left_diff) / (abs(left_diff) + abs(right_diff))
                initial_guess = left_jd + fraction * (right_jd - left_jd)
            else:
                # Equal differences (unusual case)
                initial_guess = (left_jd + right_jd) / 2
            
            # Now refine with binary search
            window_size = min(0.1, (right_jd - left_jd) / 2)  # ~2.4 hours or less
            left_jd = max(initial_guess - window_size, left_jd)
            right_jd = min(initial_guess + window_size, right_jd)
            
            # Function to compute angle difference at a given time
            def compute_difference(jd):
                try:
                    time_spec = TimeSpec.from_dates([jd])
                    pos_data = self.planet_ephemeris.get_planet_positions(
                        self.planet.name, time_spec
                    )
                    longitude = pos_data[jd][Quantity.ECLIPTIC_LONGITUDE]
                    difference = angle_diff(target_angle, longitude)
                    return difference, longitude
                except Exception:
                    # Fallback to interpolation
                    return 0.0, None
            
            # Binary search for point where angle difference crosses zero
            iterations = 0
            max_iterations = 15
            best_jd = initial_guess
            best_diff = float('inf')
            
            while (right_jd - left_jd) > precision_days and iterations < max_iterations:
                iterations += 1
                
                mid_jd = (left_jd + right_jd) / 2
                mid_diff, mid_lon = compute_difference(mid_jd)
                
                # Track best point found so far
                if abs(mid_diff) < abs(best_diff):
                    best_jd = mid_jd
                    best_diff = mid_diff
                    best_lon = mid_lon
                
                # Adjust search window based on difference sign
                if left_diff * mid_diff <= 0:
                    right_jd = mid_jd
                    right_diff = mid_diff
                else:
                    left_jd = mid_jd
                    left_diff = mid_diff
                
                # If difference is very close to zero, we can stop early
                if abs(mid_diff) < 0.0001:  # Very close to target angle
                    break
            
            # Final result - use best point found
            cross_jd = best_jd
            cross_lon = best_lon if best_lon is not None else target_angle
            
            # If we still don't have longitude, get it directly
            if cross_lon is None:
                try:
                    time_spec = TimeSpec.from_dates([cross_jd])
                    pos_data = self.planet_ephemeris.get_planet_positions(
                        self.planet.name, time_spec
                    )
                    cross_lon = pos_data[cross_jd][Quantity.ECLIPTIC_LONGITUDE]
                except Exception:
                    # Last resort: just use target angle
                    cross_lon = target_angle
        
        return (cross_jd, cross_lon)

    def _calculate_exact_angular_rate(
        self, 
        jd: float, 
        planet_name: str,
        is_sun: bool = False
    ) -> float:
        """Calculate the exact angular rate (degrees/day) of a planet at specific time.
        
        Uses high-precision differential to get accurate velocity at a specific instant.
        
        Args:
            jd: Julian date to calculate velocity at
            planet_name: Name of the planet
            is_sun: Whether this is calculating for the Sun
            
        Returns:
            Angular rate in degrees per day
        """
        # Use a small time step for accurate differentiation (30 seconds)
        time_delta = 30.0 / (24.0 * 60.0 * 60.0)  # 30 seconds in days
        
        # Get positions just before and after the time point
        jd_before = jd - time_delta
        jd_after = jd + time_delta
        
        try:
            # Choose the appropriate ephemeris
            ephemeris = self.sun_ephemeris if is_sun else self.planet_ephemeris
            
            # Get positions at three points
            time_spec = TimeSpec.from_dates([jd_before, jd, jd_after])
            positions = ephemeris.get_planet_positions(planet_name, time_spec)
            
            # Extract longitudes
            lon_before = positions[jd_before][Quantity.ECLIPTIC_LONGITUDE]
            lon_at = positions[jd][Quantity.ECLIPTIC_LONGITUDE]
            lon_after = positions[jd_after][Quantity.ECLIPTIC_LONGITUDE]
            
            # Calculate rates of change
            rate_before = angle_diff(lon_at, lon_before) / time_delta
            rate_after = angle_diff(lon_after, lon_at) / time_delta
            
            # Average for better accuracy (central difference)
            return (rate_before + rate_after) / 2
        except Exception as e:
            logging.debug(f"Error calculating angular rate: {e}")
            return 0.0

    def _find_sun_aspect(
        self,
        planet: Planet,
        jd_range: Tuple[float, float],
        planet_positions: Dict[float, Dict[str, float]] = None,
        dates: List[float] = None,
        precision_seconds: int = 30
    ) -> Optional[Tuple[float, float]]:
        """Find the precise time of cazimi (conjunction) or opposition with the Sun.
        
        Args:
            planet: The planet to find aspect for
            jd_range: (start_jd, end_jd) for the search window
            planet_positions: Optional dict of planet positions (if already available)
            dates: Optional list of Julian dates (if already available)
            precision_seconds: Desired precision in seconds (default: 30 seconds)
            
        Returns:
            Tuple of (julian_date, longitude) at the aspect point
        """
        if planet == Planet.SUN:
            return None
            
        # Get the date range
        start_jd, end_jd = jd_range
        aspect_start = julian_to_datetime(start_jd)
        aspect_end = julian_to_datetime(end_jd)
        
        # Define the time specification with 30-minute step for initial search
        time_spec = TimeSpec.from_range(aspect_start, aspect_end, "30m")
        
        # Get planet and sun positions if not provided
        if planet_positions is None or dates is None:
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
        target_angle = 0.0 if is_inner else 180.0
        
        # Initial search to narrow down the time window
        min_diff = 360.0
        aspect_jd = None
        aspect_lon = None
        
        # First pass: Find the approximate aspect time
        for jd in dates:
            if jd < start_jd or jd > end_jd or jd not in sun_positions:
                continue
                
            planet_lon = planet_positions[jd][Quantity.ECLIPTIC_LONGITUDE]
            sun_lon = sun_positions[jd][Quantity.ECLIPTIC_LONGITUDE]
            
            # Calculate angular separation
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
        
        # Second pass: Refine with higher precision
        try:
            # Set up for binary search with improved precision
            precision_days = precision_seconds / (24.0 * 60.0 * 60.0)  # Convert seconds to days
            
            # Start with a 2-hour window
            left_jd = aspect_jd - (1.0 / 12.0)  # 2 hours before
            right_jd = aspect_jd + (1.0 / 12.0)  # 2 hours after
            
            # Function to compute angular difference at a given time
            def compute_difference(jd):
                time_spec = TimeSpec.from_dates([jd])
                try:
                    planet_pos = self.planet_ephemeris.get_planet_positions(
                        planet.name, time_spec
                    )[jd][Quantity.ECLIPTIC_LONGITUDE]
                    
                    sun_pos = self.sun_ephemeris.get_planet_positions(
                        "SUN", time_spec
                    )[jd][Quantity.ECLIPTIC_LONGITUDE]
                    
                    angle_separation = abs(angle_diff(planet_pos, sun_pos))
                    
                    # For opposition, we want to be closest to 180°
                    if not is_inner:
                        return abs(angle_separation - 180.0), planet_pos
                    
                    # For conjunction, we want to be closest to 0°
                    return angle_separation, planet_pos
                except Exception:
                    return min_diff, aspect_lon  # Fall back to our best estimate
            
            # Refined binary search with dynamic narrowing
            iterations = 0
            max_iterations = 20  # Prevent infinite loop
            
            while (right_jd - left_jd) > precision_days and iterations < max_iterations:
                iterations += 1
                
                # Use quadratic interpolation to predict where minimum might be
                # Sample three points
                left_diff, _ = compute_difference(left_jd)
                mid_jd = (left_jd + right_jd) / 2
                mid_diff, mid_lon = compute_difference(mid_jd)
                right_diff, _ = compute_difference(right_jd)
                
                # If mid point is already better than our previous best
                if mid_diff < min_diff:
                    min_diff = mid_diff
                    aspect_jd = mid_jd
                    aspect_lon = mid_lon
                
                # Try to predict where the minimum is using quadratic interpolation
                # If the function is well-behaved, this converges much faster than simple bisection
                try:
                    # Handle multiple scenarios
                    if left_diff < mid_diff and left_diff < right_diff:
                        # Minimum is to the left
                        right_jd = mid_jd
                    elif right_diff < mid_diff and right_diff < left_diff:
                        # Minimum is to the right
                        left_jd = mid_jd
                    elif mid_diff < left_diff and mid_diff < right_diff:
                        # We have a minimum around the middle point, narrow both sides
                        quarter1_jd = (left_jd + mid_jd) / 2
                        quarter3_jd = (mid_jd + right_jd) / 2
                        
                        quarter1_diff, _ = compute_difference(quarter1_jd)
                        quarter3_diff, _ = compute_difference(quarter3_jd)
                        
                        if quarter1_diff < quarter3_diff:
                            right_jd = mid_jd
                            mid_jd = quarter1_jd
                        else:
                            left_jd = mid_jd
                            mid_jd = quarter3_jd
                    else:
                        # Default to simple bisection if we can't determine the pattern
                        left_jd = (left_jd + mid_jd) / 2
                        right_jd = (mid_jd + right_jd) / 2
                except Exception:
                    # If interpolation fails, fall back to simple bisection
                    if left_diff < right_diff:
                        right_jd = mid_jd
                    else:
                        left_jd = mid_jd
                
                # Use rate of change to estimate direction to minimum
                # This helps with planets that have rapidly changing velocities
                if iterations % 3 == 0:  # Apply this every few iterations
                    try:
                        # Calculate current rates of both planet and Sun
                        planet_rate = self._calculate_exact_angular_rate(mid_jd, planet.name)
                        sun_rate = self._calculate_exact_angular_rate(mid_jd, "SUN", is_sun=True)
                        
                        # The minimum occurs when the rates match (for conjunction)
                        # or when they're exactly opposite (for opposition)
                        relative_rate = planet_rate - sun_rate
                        
                        if (is_inner and relative_rate < 0) or (not is_inner and relative_rate > 0):
                            # Planet is moving slower than Sun (or faster for opposition)
                            # So the aspect is likely coming up
                            left_jd = mid_jd
                        else:
                            # Planet is moving faster than Sun (or slower for opposition)
                            # So the aspect likely just passed
                            right_jd = mid_jd
                    except Exception:
                        pass  # Fall back to regular binary search
            
            # Final precision refinement using linear interpolation between closest points
            final_points = []
            samples = 5
            interval = (right_jd - left_jd) / samples
            
            for i in range(samples + 1):
                sample_jd = left_jd + i * interval
                diff, lon = compute_difference(sample_jd)
                final_points.append((sample_jd, diff, lon))
            
            # Find the sample with minimum difference
            final_points.sort(key=lambda p: p[1])
            best_point = final_points[0]
            
            if best_point[1] < min_diff:
                aspect_jd = best_point[0]
                aspect_lon = best_point[2]
                min_diff = best_point[1]
            
            # Final position check
            try:
                final_spec = TimeSpec.from_dates([aspect_jd])
                final_pos = self.planet_ephemeris.get_planet_positions(
                    planet.name, final_spec
                )
                aspect_lon = final_pos[aspect_jd][Quantity.ECLIPTIC_LONGITUDE]
            except Exception:
                # Keep the best longitude we have if this fails
                pass
                
            return (aspect_jd, aspect_lon)
            
        except Exception as e:
            logging.error(f"Error refining aspect: {e}")
            
        # If refinement fails but we still have a basic estimate, return it
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
            # Using 30-second precision
            station_retrograde = self._find_zero_crossing(
                fine_dates, fine_positions, fine_velocities,
                find_velocity_crossing=True, find_pos_to_neg=True,
                precision_seconds=30
            )
            
            if not station_retrograde:
                continue
                
            # Find precise station direct (velocity crosses from negative to positive)
            # Using 30-second precision
            station_direct = self._find_zero_crossing(
                fine_dates, fine_positions, fine_velocities,
                find_velocity_crossing=True, find_pos_to_neg=False,
                precision_seconds=30
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
                    precision_seconds=30
                )
            
            # If we couldn't find pre-shadow, try extending search earlier
            if not pre_shadow_start:
                # Use a longer search window for slower moving outer planets
                lookback_days = 60
                if planet in [Planet.JUPITER, Planet.SATURN, Planet.URANUS, Planet.NEPTUNE, Planet.PLUTO]:
                    lookback_days = 120  # Outer planets move more slowly
                elif planet == Planet.MARS:
                    lookback_days = 90   # Mars needs a longer window too
                
                extended_start = julian_to_datetime(station_retro_jd - lookback_days)
                
                # Don't limit by start_date - for historical periods we need to look back 
                # far enough to find the shadow entry, even if it's before requested start
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
                        precision_seconds=30
                    )
                except Exception as e:
                    logging.debug(f"Error finding pre-shadow start: {e}")
                    # Continue without pre-shadow start
            
            # Find post-shadow end (when planet crosses retrograde station longitude)
            # This happens after station direct
            post_shadow_dates = [jd for jd in fine_dates if jd > station_direct_jd]
            post_shadow_positions = {jd: fine_positions[jd] for jd in post_shadow_dates}
            
            post_shadow_end = None
            if post_shadow_dates:
                post_shadow_end = self._find_zero_crossing(
                    post_shadow_dates, post_shadow_positions,
                    target_angle=station_retro_lon,
                    precision_seconds=30
                )
            
            # If we couldn't find post-shadow, try extending search later
            if not post_shadow_end:
                # Use a longer search window for slower moving outer planets
                lookahead_days = 60
                if planet in [Planet.JUPITER, Planet.SATURN, Planet.URANUS, Planet.NEPTUNE, Planet.PLUTO]:
                    lookahead_days = 120  # Outer planets move more slowly
                elif planet == Planet.MARS:
                    lookahead_days = 90   # Mars needs a longer window too
                
                extended_end = julian_to_datetime(station_direct_jd + lookahead_days)
                
                # Don't limit by end_date - for historical periods we need to look ahead
                # far enough to find the shadow exit, even if it's after requested end
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
                        precision_seconds=30
                    )
                except Exception as e:
                    logging.debug(f"Error finding post-shadow end: {e}")
                    # Continue without post-shadow end
                        
            # For cazimi detection (inner planets) or opposition (outer planets)
            # Use high-precision aspect finder with 30-second accuracy
            sun_aspect = None
            if planet != Planet.SUN:
                # Set up aspect window - centered around the retrograde period
                aspect_window_start = station_retro_jd - 10  # 10 days before retrograde
                aspect_window_end = station_direct_jd + 10   # 10 days after direct
                aspect_window = (aspect_window_start, aspect_window_end)
                
                # Get high-precision data specifically for the aspect
                # This is important since the cazimi happens at a very specific moment
                aspect_start = julian_to_datetime(aspect_window_start)
                aspect_end = julian_to_datetime(aspect_window_end)
                
                try:
                    # Get 1-hour precision data for the aspect window
                    aspect_time_spec = TimeSpec.from_range(aspect_start, aspect_end, "1h")
                    aspect_planet_pos = self.planet_ephemeris.get_planet_positions(
                        planet.name, aspect_time_spec
                    )
                    aspect_sun_pos = self.sun_ephemeris.get_planet_positions(
                        "SUN", aspect_time_spec
                    )
                    
                    # Find the approximate cazimi/opposition time first
                    is_inner = planet in [Planet.MERCURY, Planet.VENUS]
                    min_diff = 360.0
                    aspect_approx_jd = None
                    
                    for jd in sorted(aspect_planet_pos.keys()):
                        if jd not in aspect_sun_pos:
                            continue
                            
                        planet_lon = aspect_planet_pos[jd][Quantity.ECLIPTIC_LONGITUDE]
                        sun_lon = aspect_sun_pos[jd][Quantity.ECLIPTIC_LONGITUDE]
                        
                        # Calculate angular separation
                        diff = abs(angle_diff(planet_lon, sun_lon))
                        
                        if is_inner:
                            curr_diff = diff  # Want closest to 0°
                        else:
                            curr_diff = abs(diff - 180.0)  # Want closest to 180°
                            
                        if curr_diff < min_diff:
                            min_diff = curr_diff
                            aspect_approx_jd = jd
                    
                    if aspect_approx_jd is not None:
                        # Now get very high precision using a narrower window
                        narrow_window_start = aspect_approx_jd - 1  # 1 day before approx
                        narrow_window_end = aspect_approx_jd + 1    # 1 day after approx
                        narrow_window = (narrow_window_start, narrow_window_end)
                        
                        # Use precise aspect finder on narrow window
                        sun_aspect = self._find_sun_aspect(
                            planet, 
                            narrow_window,
                            precision_seconds=30  # 30-second precision
                        )
                    
                except Exception as e:
                    logging.error(f"Error finding sun aspect: {str(e)}")
                    
                # If we still don't have an aspect, fall back to using existing positions
                if sun_aspect is None:
                    sun_aspect = self._find_sun_aspect(
                        planet, 
                        aspect_window,
                        fine_positions,  # Use the existing positions as fallback
                        fine_dates,
                        precision_seconds=30
                    )
            
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