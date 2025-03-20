"""
Utility function to generate .weft files using CachedHorizonsEphemeris.

This module provides a convenient wrapper around WeftGenerator that
uses CachedHorizonsEphemeris as a data source for generating .weft files.
"""

from datetime import datetime
from typing import Dict, Any, Optional, Union
import os

from ..cached_horizons import CachedHorizonsEphemeris
from ..horizons.planet import Planet
from ..ephemeris.quantities import Quantity
from ..horizons.quantities import EphemerisQuantity
from ..horizons.parsers import OrbitalElementsQuantity
from .weft_generator import WeftGenerator


def generate_weft_file(
    planet: Union[str, Planet],
    quantity: Union[Quantity, EphemerisQuantity, OrbitalElementsQuantity],
    start_date: datetime,
    end_date: datetime,
    output_path: str,
    data_dir: str = "./data",
    config: Optional[Dict[str, Any]] = None,
    prefetch: bool = True,
    prefetch_step_hours: int = 24,
) -> str:
    """
    Generate a .weft file for a planet and quantity using CachedHorizonsEphemeris.

    Args:
        planet: The planet to generate data for (can be a Planet enum or a string name)
        quantity: The quantity to generate data for
        start_date: The start date for the ephemeris data
        end_date: The end date for the ephemeris data
        output_path: Path where the .weft file should be saved
        data_dir: Directory for the cached_horizons data
        config: Configuration for the WEFT generator
        prefetch: Whether to prefetch data before generating
        prefetch_step_hours: Step size in hours for prefetching data

    Returns:
        The path to the generated .weft file

    Raises:
        ValueError: If the planet or quantity is invalid
    """
    # Convert string planet to Planet enum if needed
    if isinstance(planet, str):
        try:
            if planet.isdigit() or (planet.startswith("-") and planet[1:].isdigit()):
                # It's a Horizons ID like "499" for Mars
                planet_id = planet
                planet_name = planet  # Use ID as name
            else:
                # Try as enum name
                planet_enum = Planet[planet.upper()]
                planet_id = planet_enum.value
                planet_name = planet_enum.name.lower()
        except KeyError:
            raise ValueError(f"Unknown planet: {planet}")
    else:
        # It's already a Planet enum
        planet_id = planet.value
        planet_name = planet.name.lower()

    # Convert Quantity to EphemerisQuantity if needed
    ephemeris_quantity = None
    for eq in EphemerisQuantity:
        if isinstance(quantity, Quantity) and eq.name == quantity.name:
            ephemeris_quantity = eq
            break
        elif isinstance(quantity, EphemerisQuantity) and eq == quantity:
            ephemeris_quantity = eq
            break
        elif isinstance(quantity, OrbitalElementsQuantity) and eq.name == quantity.name:
            ephemeris_quantity = eq
            break

    if ephemeris_quantity is None:
        raise ValueError(f"Unsupported quantity: {quantity}")

    # Create the ephemeris client
    ephemeris = CachedHorizonsEphemeris(data_dir=data_dir)

    # Prefetch data if requested
    if prefetch:
        print(f"Prefetching data for {planet_name} from {start_date} to {end_date}...")
        ephemeris.prefetch_data(
            planet=planet_id,
            start_time=start_date,
            end_time=end_date,
            step_hours=prefetch_step_hours,
        )

    # Create default config if none provided
    if config is None:
        # Default to a configuration with century, monthly, and daily blocks
        config = {
            "century": {"enabled": True, "samples_per_year": 12, "degree": 20},
            "monthly": {
                "enabled": True,
                "samples_per_month": 30,
                "degree": 10,
            },
            "daily": {
                "enabled": True,
                "samples_per_day": 48,
                "degree": 8,
            },
        }

    # Create the generator
    generator = WeftGenerator(quantity=ephemeris_quantity)

    # Create a value function that fetches data from the ephemeris
    def value_func(dt: datetime) -> float:
        try:
            data = ephemeris.get_planet_position(planet_id, dt)
            # Convert EphemerisQuantity to Quantity for lookup
            for q, value in data.items():
                if q.name == ephemeris_quantity.name:
                    return value
            return None
        except Exception as e:
            print(f"Error fetching data for {planet_name} at {dt}: {e}")
            return None

    # Generate the file
    print(f"Generating .weft file for {planet_name} {ephemeris_quantity.name}...")
    weft_file = generator.create_multi_precision_file(
        value_func=value_func,
        body=Planet[planet_name.upper()]
        if planet_name.upper() in Planet.__members__
        else None,
        quantity=ephemeris_quantity,
        start_date=start_date,
        end_date=end_date,
        config=config,
    )

    # Ensure the output directory exists
    output_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(output_dir, exist_ok=True)

    # Save the file
    generator.save_file(weft_file, output_path)

    print(f"Successfully generated .weft file at {output_path}")
    return output_path
