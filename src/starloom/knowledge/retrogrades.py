"""Functions for finding retrograde periods from CSV data."""

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import logging

from ..planet import Planet

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@dataclass
class RetrogradePeriod:
    """Represents a period of retrograde motion for a planet."""

    planet: Planet
    pre_shadow_start_date: datetime
    station_retrograde_date: datetime
    station_retrograde_longitude: float
    sun_aspect_date: datetime
    sun_aspect_longitude: float
    station_direct_date: datetime
    station_direct_longitude: float
    post_shadow_end_date: datetime


def find_nearest_retrograde(planet: Planet, target_date: datetime) -> Optional[RetrogradePeriod]:
    """Find the nearest retrograde period to the given date.

    Args:
        planet: The planet to find retrograde periods for
        target_date: The date to find the nearest retrograde period to

    Returns:
        The nearest RetrogradePeriod, or None if no retrograde periods are found
    """
    logger.debug(f"Finding nearest retrograde for {planet.name} at {target_date}")
    
    # Get the CSV file path - look in knowledge/retrogrades instead of src/knowledge/retrogrades
    csv_path = Path(__file__).parent.parent.parent.parent.parent / "knowledge" / "retrogrades" / f"{planet.name.lower()}.csv"
    logger.debug(f"Looking for CSV file at {csv_path}")
    
    if not csv_path.exists():
        logger.error(f"CSV file not found at {csv_path}")
        return None

    # Read the CSV file
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        periods = []
        for row in reader:
            try:
                # Debug log the raw row
                logger.debug(f"Processing row: {row}")

                # Convert dates to datetime objects
                def parse_date(date_str: str) -> datetime:
                    # Strip any whitespace and ensure proper format
                    date_str = date_str.strip()
                    try:
                        # Try parsing as is (space format)
                        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        try:
                            # Try parsing ISO format (with T)
                            dt = datetime.fromisoformat(date_str)
                        except ValueError:
                            # Try converting space to T and parse
                            dt = datetime.fromisoformat(date_str.replace(" ", "T"))
                    
                    # Ensure timezone is set
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt

                # Parse dates
                station_retrograde = parse_date(row["station_retrograde_date"])
                station_direct = parse_date(row["station_direct_date"])
                shadow_start = parse_date(row["pre_shadow_start_date"])
                shadow_end = parse_date(row["post_shadow_end_date"])                
                sun_event = parse_date(row["sun_aspect_date"])

                # Parse longitudes with error handling
                try:
                    station_retrograde_longitude = float(row["station_retrograde_longitude"])
                    station_direct_longitude = float(row["station_direct_longitude"])
                    sun_aspect_longitude = float(row["sun_aspect_longitude"])
                except (ValueError, KeyError) as e:
                    logger.error(f"Error parsing longitudes: {e}")
                    logger.error(f"Row data: {row}")
                    continue

                # Validate the data
                if not all(isinstance(x, datetime) for x in [station_retrograde, station_direct, shadow_start, shadow_end, sun_event]):
                    logger.error("Invalid date format in row")
                    continue

                if not all(isinstance(x, float) for x in [station_retrograde_longitude, station_direct_longitude, sun_aspect_longitude]):
                    logger.error("Invalid longitude format in row")
                    continue

                period = RetrogradePeriod(
                    planet=planet,
                    pre_shadow_start_date=shadow_start,
                    station_retrograde_date=station_retrograde,
                    station_retrograde_longitude=station_retrograde_longitude,
                    sun_aspect_date=sun_event,
                    sun_aspect_longitude=sun_aspect_longitude,
                    station_direct_date=station_direct,
                    station_direct_longitude=station_direct_longitude,
                    post_shadow_end_date=shadow_end,
                )
                periods.append(period)
                logger.debug(f"Found period: {shadow_start} to {shadow_end}")
            except Exception as e:
                logger.error(f"Error parsing row: {e}")
                logger.error(f"Row data: {row}")
                continue

    if not periods:
        logger.error("No valid periods found in CSV")
        return None

    logger.debug(f"Found {len(periods)} periods")

    # Find the period where the target date falls between shadow_start and shadow_end
    for period in periods:
        if period.pre_shadow_start_date <= target_date <= period.post_shadow_end_date:
            logger.debug(f"Found containing period: {period.pre_shadow_start_date} to {period.post_shadow_end_date}")
            return period

    # If no period contains the target date, find the closest one
    def get_distance(period: RetrogradePeriod) -> float:
        # If the target date is before the period, use the distance to pre_shadow_start_date
        if target_date < period.pre_shadow_start_date:
            return (period.pre_shadow_start_date - target_date).total_seconds()
        # If the target date is after the period, use the distance to post_shadow_end_date
        else:
            return (target_date - period.post_shadow_end_date).total_seconds()

    nearest = min(periods, key=get_distance)
    logger.debug(f"Found nearest period: {nearest.pre_shadow_start_date} to {nearest.post_shadow_end_date}")
    return nearest 