"""Functions for finding retrograde periods from CSV data."""

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from ...planet import Planet


@dataclass
class RetrogradePeriod:
    """Represents a period of retrograde motion for a planet."""

    planet: Planet
    station_retrograde: datetime
    opposition: Optional[datetime]  # None for inner planets
    station_direct: datetime
    shadow_start: datetime
    shadow_end: datetime


def find_nearest_retrograde(planet: Planet, target_date: datetime) -> Optional[RetrogradePeriod]:
    """Find the nearest retrograde period to the given date.

    Args:
        planet: The planet to find retrograde periods for
        target_date: The date to find the nearest retrograde period to

    Returns:
        The nearest RetrogradePeriod, or None if no retrograde periods are found
    """
    # Convert target date to Julian date for comparison
    target_jd = target_date.timestamp() / 86400 + 2440587.5

    # Get the CSV file path
    csv_path = Path(__file__).parent.parent.parent.parent / "knowledge" / "retrogrades" / f"{planet.name.lower()}.csv"
    if not csv_path.exists():
        return None

    # Read the CSV file
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        periods = []
        for row in reader:
            # Convert Julian dates to datetime objects
            station_retrograde = datetime.fromtimestamp((float(row["station_retrograde"]) - 2440587.5) * 86400)
            station_direct = datetime.fromtimestamp((float(row["station_direct"]) - 2440587.5) * 86400)
            shadow_start = datetime.fromtimestamp((float(row["shadow_start"]) - 2440587.5) * 86400)
            shadow_end = datetime.fromtimestamp((float(row["shadow_end"]) - 2440587.5) * 86400)
            
            # Handle opposition date (may be empty for inner planets)
            opposition = None
            if row.get("opposition"):
                opposition = datetime.fromtimestamp((float(row["opposition"]) - 2440587.5) * 86400)

            periods.append(
                RetrogradePeriod(
                    planet=planet,
                    station_retrograde=station_retrograde,
                    opposition=opposition,
                    station_direct=station_direct,
                    shadow_start=shadow_start,
                    shadow_end=shadow_end,
                )
            )

    if not periods:
        return None

    # Find the nearest period by comparing the target date to the station_retrograde date
    nearest = min(periods, key=lambda p: abs((p.station_retrograde - target_date).total_seconds()))
    return nearest 