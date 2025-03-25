"""Module for detecting planetary retrograde periods."""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union
import json

from ..ephemeris.quantities import Quantity
from ..ephemeris.time_spec import TimeSpec
from ..planet import Planet
from ..space_time.julian import julian_to_datetime, datetime_to_julian


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
    pre_shadow_start: Optional[Tuple[float, float]] = None  # (julian_date, longitude) [ingress]
    post_shadow_end: Optional[Tuple[float, float]] = None  # (julian_date, longitude) [egress]
    sun_aspect: Optional[Tuple[float, float]] = None  # (julian_date, longitude) for cazimi/opposition

    def to_dict(self) -> Dict:
        """Convert the retrograde period to a dictionary for JSON serialization."""
        result = {
            "planet": self.planet.name,
            "station_retrograde": {
                "date": julian_to_datetime(self.station_retrograde[0]).isoformat(),
                "julian_date": self.station_retrograde[0],
                "longitude": self.station_retrograde[1],
            },
            "station_direct": {
                "date": julian_to_datetime(self.station_direct[0]).isoformat(),
                "julian_date": self.station_direct[0],
                "longitude": self.station_direct[1],
            },
            "pre_shadow_start": None,
            "post_shadow_end": None,
            "sun_aspect": None
        }
        
        if self.pre_shadow_start:
            result["pre_shadow_start"] = {
                "date": julian_to_datetime(self.pre_shadow_start[0]).isoformat(),
                "julian_date": self.pre_shadow_start[0],
                "longitude": self.pre_shadow_start[1],
            }
            
        if self.post_shadow_end:
            result["post_shadow_end"] = {
                "date": julian_to_datetime(self.post_shadow_end[0]).isoformat(),
                "julian_date": self.post_shadow_end[0],
                "longitude": self.post_shadow_end[1],
            }
            
        if self.sun_aspect:
            result["sun_aspect"] = {
                "date": julian_to_datetime(self.sun_aspect[0]).isoformat(),
                "julian_date": self.sun_aspect[0],
                "longitude": self.sun_aspect[1],
            }
            
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
        self, positions: Dict[float, Dict[str, float]], jd: float
    ) -> float:
        """Calculate apparent velocity (degrees/day) using proper angle differences."""
        dates = sorted(positions.keys())
        idx = dates.index(jd)
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
        is_velocity: bool = False
    ) -> Optional[Tuple[float, float]]:
        """Find a zero-crossing using binary search.
        
        Args:
            dates: List of sorted Julian dates
            positions: Dictionary of positions/velocities indexed by Julian date
            target_lon: Target longitude to find crossing for (if None, looks for velocity zero-crossing)
            is_velocity: Whether we're looking for velocity zero-crossing
            
        Returns:
            Tuple of (julian_date, longitude) at crossing, or None if not found
        """
        if len(dates) < 2:
            return None
            
        def get_value(jd: float) -> float:
            if is_velocity:
                return positions[jd]
            else:
                return positions[jd][Quantity.ECLIPTIC_LONGITUDE]
                
        # Find a bracket where the sign changes
        left = 0
        right = len(dates) - 1
        
        while left <= right:
            mid = (left + right) // 2
            mid_jd = dates[mid]
            mid_val = get_value(mid_jd)
            
            if mid == 0:
                # Check if we have a crossing at the start
                if mid_val * get_value(dates[1]) <= 0:
                    left = 0
                    right = 1
                    break
                left = 1
                continue
                
            if mid == len(dates) - 1:
                # Check if we have a crossing at the end
                if mid_val * get_value(dates[-2]) <= 0:
                    left = len(dates) - 2
                    right = len(dates) - 1
                    break
                right = len(dates) - 2
                continue
                
            # Check if we have a crossing
            prev_val = get_value(dates[mid - 1])
            next_val = get_value(dates[mid + 1])
            
            if mid_val * prev_val <= 0:
                left = mid - 1
                right = mid
                break
            elif mid_val * next_val <= 0:
                left = mid
                right = mid + 1
                break
                
            # No crossing found, continue binary search
            if mid_val > 0:
                if prev_val > 0:
                    right = mid - 1
                else:
                    left = mid + 1
            else:
                if prev_val < 0:
                    right = mid - 1
                else:
                    left = mid + 1
                    
        if left > right:
            return None
            
        # We found a bracket, now interpolate to find the exact crossing
        left_jd = dates[left]
        right_jd = dates[right]
        left_val = get_value(left_jd)
        right_val = get_value(right_jd)
        
        if left_val == right_val:
            return None
            
        if target_lon is not None:
            # For longitude crossings, we want to find where we cross the target longitude
            frac = (target_lon - left_val) / angle_diff(right_val, left_val)
        else:
            # For velocity zero-crossings, we want to find where velocity crosses zero
            frac = abs(left_val) / (abs(left_val) + abs(right_val))
            
        crossing_jd = left_jd + (right_jd - left_jd) * frac
        
        if is_velocity:
            crossing_val = 0  # At zero-crossing, velocity is 0
        else:
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
        coarse_time_spec = TimeSpec.from_range(start_date, end_date, step)
        coarse_positions = self.planet_ephemeris.get_planet_positions(planet.name, coarse_time_spec)
        
        # Calculate velocities for coarse sampling
        coarse_velocities = {
            jd: self._calculate_velocity(coarse_positions, jd)
            for jd in coarse_positions.keys()
        }
        
        # Find potential retrograde periods
        potential_periods = []
        current_period = None
        coarse_dates = sorted(coarse_positions.keys())
        
        for i in range(1, len(coarse_dates)):
            prev_jd = coarse_dates[i-1]
            curr_jd = coarse_dates[i]
            
            prev_vel = coarse_velocities[prev_jd]
            curr_vel = coarse_velocities[curr_jd]
            
            # Detect potential station retrograde
            if prev_vel > 0 and curr_vel < 0:
                current_period = {
                    'start_jd': prev_jd,
                    'end_jd': curr_jd + 15  # Add 15 days buffer for safety
                }
                
            # Detect potential station direct
            elif prev_vel < 0 and curr_vel > 0 and current_period is not None:
                current_period['end_jd'] = curr_jd + 15  # Add 15 days buffer for safety
                potential_periods.append(current_period)
                current_period = None
        
        # Second pass: Use finer sampling for each potential period
        retrograde_periods = []
        fine_step = "1h"  # Use 1-hour sampling for precise timing
        
        for period in potential_periods:
            # Create time spec for this period
            period_start = julian_to_datetime(period['start_jd'])
            period_end = julian_to_datetime(period['end_jd'])
            
            # Ensure we don't exceed the overall date range
            period_start = max(period_start, start_date)
            period_end = min(period_end, end_date)
            
            # Skip if period is too short
            if (period_end - period_start).total_seconds() < 3600:  # Less than 1 hour
                continue
                
            fine_time_spec = TimeSpec.from_range(period_start, period_end, fine_step)
            
            # Get fine-grained positions
            fine_positions = self.planet_ephemeris.get_planet_positions(planet.name, fine_time_spec)
            if planet != Planet.SUN:
                fine_sun_positions = self.sun_ephemeris.get_planet_positions("SUN", fine_time_spec)
            
            # Calculate fine-grained velocities
            fine_velocities = {
                jd: self._calculate_velocity(fine_positions, jd)
                for jd in fine_positions.keys()
            }
            
            # Find precise station points
            fine_dates = sorted(fine_positions.keys())
            if not fine_dates:  # Skip if no fine-grained data
                continue
                
            # Find station retrograde using binary search
            station_retrograde = self._find_zero_crossing(fine_dates, fine_velocities, is_velocity=True)
            if not station_retrograde:
                continue
                
            station_jd, _ = station_retrograde
            # Get position at interpolated Julian date using ephemeris
            station_pos = self.planet_ephemeris.get_planet_positions(
                planet.name,
                TimeSpec.from_julian_dates([station_jd])
            )
            station_lon = station_pos[station_jd][Quantity.ECLIPTIC_LONGITUDE]
            
            # Find pre_shadow_start using binary search
            pre_shadow_start = self._find_zero_crossing(fine_dates, fine_positions, target_lon=station_lon)
            
            # Find station direct using binary search
            station_direct = self._find_zero_crossing(fine_dates, fine_velocities, is_velocity=True)
            if not station_direct:
                continue
                
            direct_jd, _ = station_direct
            # Get position at interpolated Julian date using ephemeris
            direct_pos = self.planet_ephemeris.get_planet_positions(
                planet.name,
                TimeSpec.from_julian_dates([direct_jd])
            )
            direct_lon = direct_pos[direct_jd][Quantity.ECLIPTIC_LONGITUDE]
            
            # Find post_shadow_end using binary search
            post_shadow_end = self._find_zero_crossing(fine_dates, fine_positions, target_lon=direct_lon)
            
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
                            planet.name,
                            TimeSpec.from_julian_dates([closest_jd])
                        )
                        sun_aspect = (
                            closest_jd, closest_pos[closest_jd][Quantity.ECLIPTIC_LONGITUDE]
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
                            planet.name,
                            TimeSpec.from_julian_dates([closest_jd])
                        )
                        sun_aspect = (
                            closest_jd, closest_pos[closest_jd][Quantity.ECLIPTIC_LONGITUDE]
                        )
            
            # Create RetrogradePeriod object and add to list
            retrograde_periods.append(RetrogradePeriod(
                planet=planet,
                station_retrograde=station_retrograde,
                station_direct=station_direct,
                pre_shadow_start=pre_shadow_start,
                post_shadow_end=post_shadow_end,
                sun_aspect=sun_aspect
            ))
        
        return retrograde_periods

    def save_to_json(
        self, periods: List[RetrogradePeriod], output_file: str
    ) -> None:
        """Save retrograde periods to a JSON file.
        
        Args:
            periods: List of RetrogradePeriod objects
            output_file: Path to save JSON file
        """
        data = {
            "retrograde_periods": [period.to_dict() for period in periods]
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2) 