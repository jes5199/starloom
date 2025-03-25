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
                
            current_period = None
            
            for i in range(1, len(fine_dates)):
                prev_jd = fine_dates[i-1]
                curr_jd = fine_dates[i]
                
                prev_vel = fine_velocities[prev_jd]
                curr_vel = fine_velocities[curr_jd]
                
                # Detect station retrograde
                if prev_vel > 0 and curr_vel < 0:
                    frac = prev_vel / (prev_vel - curr_vel)
                    station_jd = prev_jd + (curr_jd - prev_jd) * frac
                    prev_lon = fine_positions[prev_jd][Quantity.ECLIPTIC_LONGITUDE]
                    curr_lon = fine_positions[curr_jd][Quantity.ECLIPTIC_LONGITUDE]
                    station_lon = interpolate_angle(prev_lon, curr_lon, frac)
                    
                    current_period = {'station_retrograde': (station_jd, station_lon)}
                    
                    # Find pre_shadow_start
                    for j in range(i-1, 0, -1):
                        lon1 = fine_positions[fine_dates[j-1]][Quantity.ECLIPTIC_LONGITUDE]
                        lon2 = fine_positions[fine_dates[j]][Quantity.ECLIPTIC_LONGITUDE]
                        if (lon1 - station_lon) * (lon2 - station_lon) <= 0:
                            if lon2 != lon1:
                                frac_cross = (station_lon - lon1) / angle_diff(lon2, lon1)
                            else:
                                frac_cross = 0
                            pre_jd = fine_dates[j-1] + (fine_dates[j] - fine_dates[j-1]) * frac_cross
                            current_period['pre_shadow_start'] = (pre_jd, station_lon)
                            break
                            
                # Detect station direct
                elif prev_vel < 0 and curr_vel > 0 and current_period is not None:
                    frac = abs(prev_vel) / (curr_vel - prev_vel)
                    station_jd = prev_jd + (curr_jd - prev_jd) * frac
                    prev_lon = fine_positions[prev_jd][Quantity.ECLIPTIC_LONGITUDE]
                    curr_lon = fine_positions[curr_jd][Quantity.ECLIPTIC_LONGITUDE]
                    station_lon = interpolate_angle(prev_lon, curr_lon, frac)
                    
                    current_period['station_direct'] = (station_jd, station_lon)
                    
                    # Find post_shadow_end
                    for j in range(i, len(fine_dates)-1):
                        lon1 = fine_positions[fine_dates[j]][Quantity.ECLIPTIC_LONGITUDE]
                        lon2 = fine_positions[fine_dates[j+1]][Quantity.ECLIPTIC_LONGITUDE]
                        if (lon1 - station_lon) * (lon2 - station_lon) <= 0:
                            if lon2 != lon1:
                                frac_cross = (station_lon - lon1) / angle_diff(lon2, lon1)
                            else:
                                frac_cross = 0
                            post_jd = fine_dates[j] + (fine_dates[j+1] - fine_dates[j]) * frac_cross
                            current_period['post_shadow_end'] = (post_jd, station_lon)
                            break
                    
                    # Determine Sun aspect
                    if planet != Planet.SUN:
                        is_inner = planet in [Planet.MERCURY, Planet.VENUS]
                        if is_inner:
                            # For inner planets, find precise conjunction (0° difference)
                            mid_jd = (current_period['station_retrograde'][0] + station_jd) / 2
                            refined_jd = None
                            window = 15  # days window for search
                            for j in range(len(fine_dates)-1):
                                if abs(fine_dates[j] - mid_jd) > window:
                                    continue
                                planet_lon1 = fine_positions[fine_dates[j]][Quantity.ECLIPTIC_LONGITUDE]
                                sun_lon1 = fine_sun_positions[fine_dates[j]][Quantity.ECLIPTIC_LONGITUDE]
                                diff1 = angle_diff(planet_lon1, sun_lon1)
                                planet_lon2 = fine_positions[fine_dates[j+1]][Quantity.ECLIPTIC_LONGITUDE]
                                sun_lon2 = fine_sun_positions[fine_dates[j+1]][Quantity.ECLIPTIC_LONGITUDE]
                                diff2 = angle_diff(planet_lon2, sun_lon2)
                                if diff1 * diff2 < 0:  # crossing detected
                                    frac_aspect = abs(diff1) / (abs(diff1) + abs(diff2))
                                    refined_jd = fine_dates[j] + (fine_dates[j+1] - fine_dates[j]) * frac_aspect
                                    refined_lon = interpolate_angle(planet_lon1, planet_lon2, frac_aspect)
                                    current_period['sun_aspect'] = (refined_jd, refined_lon)
                                    break
                        else:
                            # For outer planets, use opposition (target 180°)
                            target_angle = 180
                            mid_jd = (current_period['station_retrograde'][0] + station_jd) / 2
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
                                current_period['sun_aspect'] = (
                                    closest_jd, fine_positions[closest_jd][Quantity.ECLIPTIC_LONGITUDE]
                                )
                    
                    # Create RetrogradePeriod object and add to list
                    retrograde_periods.append(RetrogradePeriod(
                        planet=planet,
                        station_retrograde=current_period['station_retrograde'],
                        station_direct=current_period['station_direct'],
                        pre_shadow_start=current_period.get('pre_shadow_start'),
                        post_shadow_end=current_period.get('post_shadow_end'),
                        sun_aspect=current_period.get('sun_aspect')
                    ))
                    
                    current_period = None
        
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