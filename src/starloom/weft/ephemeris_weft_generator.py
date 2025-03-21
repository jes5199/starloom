"""
Utility function to generate .weft files from ephemeris data.

This module provides a wrapper around WeftWriter that
uses an ephemeris source to generate .weft files.
"""

from datetime import datetime
from typing import Dict, Any, Optional, Union
import os

from ..cached_horizons import CachedHorizonsEphemeris
from ..horizons.planet import Planet
from ..ephemeris.quantities import Quantity
from ..horizons.quantities import EphemerisQuantity
from ..horizons.parsers import OrbitalElementsQuantity
from .weft_writer import WeftWriter
from ..ephemeris.ephemeris import Ephemeris
from .ephemeris_data_source import EphemerisDataSource
from .block_selection import get_recommended_blocks


def generate_weft_file(
    planet: Union[str, Planet],
    quantity: Union[Quantity, EphemerisQuantity, OrbitalElementsQuantity],
    start_date: datetime,
    end_date: datetime,
    output_path: str,
    ephemeris: Optional[Ephemeris] = None,
    data_dir: str = "./data",
    config: Optional[Dict[str, Any]] = None,
    step_hours: int = 24,
) -> str:
    """
    Generate a .weft file for a planet and quantity using an ephemeris source.

    Args:
        planet: The planet to generate data for (can be a Planet enum or a string name)
        quantity: The quantity to generate data for
        start_date: The start date for the ephemeris data
        end_date: The end date for the ephemeris data
        output_path: Path where the .weft file should be saved
        ephemeris: Optional ephemeris source to use. If None, CachedHorizonsEphemeris will be used
        data_dir: Directory for data storage (only used if ephemeris is None)
        config: Configuration for the WEFT generator (if None, will be auto-configured)
        step_hours: Step size in hours for sampling ephemeris data

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

    # Create or use provided ephemeris client
    if ephemeris is None:
        ephemeris = CachedHorizonsEphemeris(data_dir=data_dir)

    # Create the writer
    writer = WeftWriter(quantity=ephemeris_quantity)

    # Create data source
    data_source = EphemerisDataSource(
        ephemeris=ephemeris,
        planet_id=planet_id,
        quantity=ephemeris_quantity,
        start_date=start_date,
        end_date=end_date,
        step_hours=step_hours,
    )

    # Generate the file
    print(f"Generating .weft file for {planet_name} {ephemeris_quantity.name}...")
    try:
        planet_enum = Planet[planet_name.upper()]
    except KeyError:
        raise ValueError(f"Planet {planet_name} is not a valid Planet enum member")

    # Use provided config or get recommended blocks based on data
    if config is None:
        config = get_recommended_blocks(data_source)
        print("Using auto-configured blocks based on data availability:")
        for block_type, settings in config.items():
            if settings.get("enabled", False):
                print(f"  {block_type}: {settings}")

    weft_file = writer.create_multi_precision_file(
        data_source=data_source,
        body=planet_enum,
        quantity=ephemeris_quantity,
        start_date=start_date,
        end_date=end_date,
        config=config,
    )

    # Ensure the output directory exists
    output_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(output_dir, exist_ok=True)

    # Save the file
    writer.save_file(weft_file, output_path)

    return output_path
