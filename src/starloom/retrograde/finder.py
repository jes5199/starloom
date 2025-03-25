"""Module for detecting planetary retrograde periods."""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json

from ..ephemeris.quantities import Quantity
from ..ephemeris.time_spec import TimeSpec
from ..planet import Planet
from ..space_time.julian import julian_to_datetime, datetime_to_julian


@dataclass
class RetrogradePeriod:
    """Represents a complete retrograde cycle for a planet."""
    
    planet: Planet
    pre_shadow_start: Tuple[float, float]  # (julian_date, longitude)
    station_retrograde: Tuple[float, float]  # (julian_date, longitude)
    station_direct: Tuple[float, float]  # (julian_date, longitude)
    post_shadow_end: Tuple[float, float]  # (julian_date, longitude)
    sun_aspect: Optional[Tuple[float, float]] = None  # (julian_date, longitude) for cazimi/opposition

    def to_dict(self) -> Dict:
        """Convert the retrograde period to a dictionary for JSON serialization."""
        return {
            "planet": self.planet.name,
            "pre_shadow_start": {
                "date": julian_to_datetime(self.pre_shadow_start[0]).isoformat(),
                "julian_date": self.pre_shadow_start[0],
                "longitude": self.pre_shadow_start[1],
            },
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
            "post_shadow_end": {
                "date": julian_to_datetime(self.post_shadow_end[0]).isoformat(),
                "julian_date": self.post_shadow_end[0],
                "longitude": self.post_shadow_end[1],
            },
            "sun_aspect": {
                "date": julian_to_datetime(self.sun_aspect[0]).isoformat(),
                "julian_date": self.sun_aspect[0],
                "longitude": self.sun_aspect[1],
            } if self.sun_aspect else None,
        }


class RetrogradeFinder:
    """Class for finding retrograde periods of planets."""

    def __init__(self, ephemeris):
        """Initialize the retrograde finder.
        
        Args:
            ephemeris: An ephemeris instance conforming to EphemerisProtocol
        """
        self.ephemeris = ephemeris

    def _calculate_velocity(
        self, positions: Dict[float, Dict[str, float]], jd: float
    ) -> float:
        """Calculate apparent velocity at a given point by comparing adjacent points.
        
        Args:
            positions: Dictionary of position data keyed by Julian date
            jd: Julian date to calculate velocity for
            
        Returns:
            Apparent daily motion in degrees/day
        """
        dates = sorted(positions.keys())
        idx = dates.index(jd)
        
        if idx == 0:
            # For first point, look forward
            next_jd = dates[idx + 1]
            next_lon = positions[next_jd][Quantity.ECLIPTIC_LONGITUDE]
            curr_lon = positions[jd][Quantity.ECLIPTIC_LONGITUDE]
            return (next_lon - curr_lon) / (next_jd - jd)
        elif idx == len(dates) - 1:
            # For last point, look backward
            prev_jd = dates[idx - 1]
            prev_lon = positions[prev_jd][Quantity.ECLIPTIC_LONGITUDE]
            curr_lon = positions[jd][Quantity.ECLIPTIC_LONGITUDE]
            return (curr_lon - prev_lon) / (jd - prev_jd)
        else:
            # For middle points, average the forward and backward velocities
            next_jd = dates[idx + 1]
            prev_jd = dates[idx - 1]
            next_lon = positions[next_jd][Quantity.ECLIPTIC_LONGITUDE]
            prev_lon = positions[prev_jd][Quantity.ECLIPTIC_LONGITUDE]
            curr_lon = positions[jd][Quantity.ECLIPTIC_LONGITUDE]
            
            forward_vel = (next_lon - curr_lon) / (next_jd - jd)
            backward_vel = (curr_lon - prev_lon) / (jd - prev_jd)
            return (forward_vel + backward_vel) / 2

    def find_retrograde_periods(
        self, planet: Planet, start_date: datetime, end_date: datetime, step: str = "1d"
    ) -> List[RetrogradePeriod]:
        """Find all retrograde periods for a planet within the given date range.
        
        Args:
            planet: The planet to find retrograde periods for
            start_date: Start of search range
            end_date: End of search range
            step: Time step for calculations (e.g. "1d", "6h")
            
        Returns:
            List of RetrogradePeriod objects
        """
        # Create time specification for the range
        time_spec = TimeSpec.from_range(start_date, end_date, step)
        
        # Get planet positions
        positions = self.ephemeris.get_planet_positions(planet.name, time_spec)
        
        # Also get Sun positions if needed for cazimi/opposition
        if planet != Planet.SUN:
            sun_positions = self.ephemeris.get_planet_positions("SUN", time_spec)
        
        # Calculate velocities for each point
        velocities = {
            jd: self._calculate_velocity(positions, jd)
            for jd in positions.keys()
        }
        
        # Find station points where velocity crosses zero
        retrograde_periods = []
        current_period = None
        
        dates = sorted(positions.keys())
        for i in range(1, len(dates)):
            prev_jd = dates[i-1]
            curr_jd = dates[i]
            
            prev_vel = velocities[prev_jd]
            curr_vel = velocities[curr_jd]
            
            # Detect station retrograde (velocity goes from positive to negative)
            if prev_vel > 0 and curr_vel < 0:
                # Interpolate exact station point
                station_jd = prev_jd + (curr_jd - prev_jd) * (prev_vel / (prev_vel - curr_vel))
                station_lon = positions[prev_jd][Quantity.ECLIPTIC_LONGITUDE]
                
                # Start tracking a new retrograde period
                current_period = {
                    'station_retrograde': (station_jd, station_lon)
                }
                
                # Look backwards for pre-shadow start (when planet first reaches station degree)
                for j in range(i-1, -1, -1):
                    if positions[dates[j]][Quantity.ECLIPTIC_LONGITUDE] <= station_lon:
                        current_period['pre_shadow_start'] = (
                            dates[j],
                            positions[dates[j]][Quantity.ECLIPTIC_LONGITUDE]
                        )
                        break
                        
            # Detect station direct (velocity goes from negative to positive)
            elif prev_vel < 0 and curr_vel > 0 and current_period is not None:
                # Interpolate exact station point
                station_jd = prev_jd + (curr_jd - prev_jd) * (prev_vel / (prev_vel - curr_vel))
                station_lon = positions[prev_jd][Quantity.ECLIPTIC_LONGITUDE]
                
                current_period['station_direct'] = (station_jd, station_lon)
                
                # Look forwards for post-shadow end (when planet last reaches station degree)
                for j in range(i+1, len(dates)):
                    if positions[dates[j]][Quantity.ECLIPTIC_LONGITUDE] >= station_lon:
                        current_period['post_shadow_end'] = (
                            dates[j],
                            positions[dates[j]][Quantity.ECLIPTIC_LONGITUDE]
                        )
                        break
                
                # Find cazimi/opposition point if applicable
                if planet != Planet.SUN:
                    # For inner planets (Mercury/Venus), find cazimi
                    # For outer planets, find opposition
                    is_inner = planet in [Planet.MERCURY, Planet.VENUS]
                    target_angle = 0 if is_inner else 180
                    
                    # Search around the midpoint of the retrograde period
                    mid_jd = (current_period['station_retrograde'][0] + station_jd) / 2
                    closest_jd = None
                    closest_diff = 360
                    
                    # Look in a window around the midpoint
                    window = 30  # days
                    for jd in dates:
                        if abs(jd - mid_jd) > window:
                            continue
                            
                        planet_lon = positions[jd][Quantity.ECLIPTIC_LONGITUDE]
                        sun_lon = sun_positions[jd][Quantity.ECLIPTIC_LONGITUDE]
                        
                        # Calculate smallest angle between planet and sun
                        diff = abs((planet_lon - sun_lon + 180) % 360 - 180)
                        
                        if abs(diff - target_angle) < closest_diff:
                            closest_diff = abs(diff - target_angle)
                            closest_jd = jd
                    
                    if closest_jd:
                        current_period['sun_aspect'] = (
                            closest_jd,
                            positions[closest_jd][Quantity.ECLIPTIC_LONGITUDE]
                        )
                
                # Create RetrogradePeriod object and add to list
                retrograde_periods.append(RetrogradePeriod(
                    planet=planet,
                    pre_shadow_start=current_period['pre_shadow_start'],
                    station_retrograde=current_period['station_retrograde'],
                    station_direct=current_period['station_direct'],
                    post_shadow_end=current_period['post_shadow_end'],
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