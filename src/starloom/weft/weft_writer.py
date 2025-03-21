"""
A class to write .weft binary ephemeris files with multiple levels of precision.

This module provides functionality to write .weft files with century, year, month,
and daily blocks, using Chebyshev polynomials for efficient storage.
"""

from datetime import datetime, timedelta, date
from typing import List, Dict, Tuple, Optional, Any, Union, TypeVar, cast
from zoneinfo import ZoneInfo
import os
from numpy.polynomial import chebyshev

from .weft import (
    MultiYearBlock,
    MonthlyBlock,
    FortyEightHourSectionHeader,
    FortyEightHourBlock,
    WeftFile,
    BlockType,
    RangedBehavior,
    UnboundedBehavior,
)
from ..horizons.quantities import (
    EphemerisQuantity,
)
from ..horizons.parsers import OrbitalElementsQuantity
from ..horizons.planet import Planet
from .ephemeris_data_source import EphemerisDataSource

T = TypeVar("T", bound=BlockType)


class WeftWriter:
    """
    A class to write .weft binary ephemeris files with multiple levels of precision.
    This class can create files with century, year, month, and daily blocks.
    """

    def __init__(self, quantity: EphemerisQuantity):
        """Initialize the WeftWriter.

        Args:
            quantity: The type of quantity to generate
        """
        self.quantity = quantity
        self.wrapping_behavior = (
            "wrapping"
            if quantity
            in [
                EphemerisQuantity.ECLIPTIC_LONGITUDE,
                EphemerisQuantity.RIGHT_ASCENSION,
                EphemerisQuantity.APPARENT_AZIMUTH,
            ]
            else "bounded"
        )

        # Initialize value behavior based on quantity
        if self.wrapping_behavior == "wrapping":
            if quantity == EphemerisQuantity.RIGHT_ASCENSION:
                # Right ascension is in hours [0, 24)
                self.value_behavior: Union[RangedBehavior, UnboundedBehavior] = (
                    RangedBehavior(
                        type="wrapping",
                        range=(0.0, 24.0),
                    )
                )
            else:
                # Other angles are in degrees [0, 360)
                self.value_behavior = RangedBehavior(
                    type="wrapping",
                    range=(0.0, 360.0),
                )
        elif quantity == EphemerisQuantity.ECLIPTIC_LATITUDE:
            # Latitude is bounded [-90, 90]
            self.value_behavior = RangedBehavior(
                type="bounded",
                range=(-90.0, 90.0),
            )
        elif quantity == EphemerisQuantity.PHASE_ANGLE:
            # Phase angle is bounded [0, 180]
            self.value_behavior = RangedBehavior(
                type="bounded",
                range=(0.0, 180.0),
            )
        elif quantity == EphemerisQuantity.ILLUMINATED_FRACTION:
            # Illumination is bounded [0, 1]
            self.value_behavior = RangedBehavior(
                type="bounded",
                range=(0.0, 1.0),
            )
        else:
            # Other quantities are unbounded
            self.value_behavior = UnboundedBehavior(type="unbounded")

    def _generate_samples(
        self,
        data_source: EphemerisDataSource,
        start_dt: datetime,
        end_dt: datetime,
        sample_count: int,
        quantity: Optional[Union[EphemerisQuantity, OrbitalElementsQuantity]] = None,
    ) -> Tuple[List[float], List[float]]:
        """
        Generate sample points for fitting.

        Args:
            data_source: The data source to get values from
            start_dt: Start datetime
            end_dt: End datetime
            sample_count: Number of sample points to generate
            quantity: Optional quantity override

        Returns:
            Tuple of (x_values, values)
        """
        # Generate evenly spaced sample points
        total_seconds = (end_dt - start_dt).total_seconds()
        step_seconds = total_seconds / (sample_count - 1)

        x_values = []
        values = []

        # Generate samples
        for i in range(sample_count):
            # Calculate x value in [-1, 1] range
            x = -1.0 + 2.0 * i / (sample_count - 1)
            x_values.append(x)

            # Calculate datetime for this sample
            current_dt = start_dt + timedelta(seconds=i * step_seconds)
            # Ensure we don't exceed the data range
            if current_dt > end_dt:
                current_dt = end_dt

            # Get value at this time
            value = data_source.get_value_at(current_dt)
            values.append(value)

        return x_values, values

    def create_multi_year_block(
        self,
        data_source: EphemerisDataSource,
        start_year: int,
        duration: int,
        samples_per_year: int,
        degree: int,
        quantity: Union[EphemerisQuantity, OrbitalElementsQuantity],
    ) -> MultiYearBlock:
        """
        Create a multi-year block covering the specified years.

        Args:
            data_source: The data source to get values from
            start_year: Starting year
            duration: Number of years to cover
            samples_per_year: Number of sample points per year
            degree: Degree of Chebyshev polynomial to fit
            quantity: The quantity being computed

        Returns:
            A MultiYearBlock
        """
        start_dt = datetime(start_year, 1, 1, tzinfo=ZoneInfo("UTC"))
        end_dt = datetime(start_year + duration, 1, 1, tzinfo=ZoneInfo("UTC"))

        sample_count = samples_per_year * duration
        x_values, values = self._generate_samples(
            data_source, start_dt, end_dt, sample_count, quantity
        )

        # Fit Chebyshev coefficients
        coeffs = chebyshev.chebfit(x_values, values, deg=degree)
        coeffs_list = cast(List[float], coeffs.tolist())

        return MultiYearBlock(
            start_year=start_year, duration=duration, coeffs=coeffs_list
        )

    def create_monthly_blocks(
        self,
        data_source: EphemerisDataSource,
        year: int,
        month_range: Tuple[int, int],
        samples_per_month: int,
        degree: int,
        quantity: Optional[Union[EphemerisQuantity, OrbitalElementsQuantity]] = None,
        end_date: Optional[datetime] = None,
    ) -> List[MonthlyBlock]:
        """
        Create monthly blocks for the specified months.

        Args:
            data_source: The data source to get values from
            year: Year to create blocks for
            month_range: Tuple of (start_month, end_month) inclusive
            samples_per_month: Number of sample points per month
            degree: Degree of Chebyshev polynomial to fit
            quantity: Optional quantity override
            end_date: Optional end date to limit sampling within the last month

        Returns:
            List of MonthlyBlock objects
        """
        blocks = []
        start_month, end_month = month_range

        for month in range(start_month, end_month + 1):
            # Calculate days in month
            if month == 12:
                next_month = datetime(year + 1, 1, 1, tzinfo=ZoneInfo("UTC"))
            else:
                next_month = datetime(year, month + 1, 1, tzinfo=ZoneInfo("UTC"))
            current_month = datetime(year, month, 1, tzinfo=ZoneInfo("UTC"))

            # If this is the last month and we have an end date, use it
            block_end = next_month
            if end_date and month == end_month and end_date < next_month:
                block_end = end_date

            day_count = (next_month - current_month).days

            # Generate samples
            x_values, values = self._generate_samples(
                data_source,
                current_month,
                block_end - timedelta(microseconds=1),
                samples_per_month,
                quantity,
            )

            # Fit Chebyshev coefficients
            coeffs = chebyshev.chebfit(x_values, values, deg=degree)
            coeffs_list = cast(List[float], coeffs.tolist())

            blocks.append(
                MonthlyBlock(
                    year=year,
                    month=month,
                    day_count=day_count,
                    coeffs=coeffs_list,
                )
            )

        return blocks

    def create_forty_eight_hour_blocks(
        self,
        data_source: EphemerisDataSource,
        start_date: datetime,
        end_date: datetime,
        samples_per_day: int,
        degree: int,
        block_size: Optional[int] = None,
        quantity: Optional[Union[EphemerisQuantity, OrbitalElementsQuantity]] = None,
    ) -> Tuple[FortyEightHourSectionHeader, List[FortyEightHourBlock]]:
        """
        Create a section of forty-eight hour blocks.

        Args:
            data_source: The data source to get values from
            start_date: Start date
            end_date: End date (inclusive)
            samples_per_day: Number of sample points per day
            degree: Degree of Chebyshev polynomial to fit
            block_size: Fixed size for each block (computed if None)
            quantity: Optional quantity override

        Returns:
            Tuple of (FortyEightHourSectionHeader, List[FortyEightHourBlock])
        """
        # Ensure we're working with dates at day boundaries
        start_date = datetime(
            start_date.year, start_date.month, start_date.day, tzinfo=ZoneInfo("UTC")
        )
        end_date = datetime(
            end_date.year, end_date.month, end_date.day, tzinfo=ZoneInfo("UTC")
        )

        # If block_size not specified, compute it based on coefficient count
        if block_size is None:
            # Header bytes: marker(2) + year(2) + month(1) + day(1) = 6 bytes
            header_size = 6
            # Each coefficient is a 4-byte float
            coeff_size = (degree + 1) * 4
            # Add padding for alignment (to 16 bytes)
            block_size = header_size + coeff_size
            if block_size % 16 != 0:
                block_size += 16 - (block_size % 16)

        # Create blocks
        blocks = []
        current_date = start_date
        while (
            current_date < end_date
        ):  # Changed from <= to < to avoid going past end_date
            # Calculate block end date
            block_end = min(current_date + timedelta(days=1), end_date)

            # Create header for this block
            header = FortyEightHourSectionHeader(
                start_day=date(current_date.year, current_date.month, current_date.day),
                end_day=date(block_end.year, block_end.month, block_end.day),
            )
            blocks.append(header)

            # Generate samples for this 48-hour period
            x_values, values = self._generate_samples(
                data_source,
                current_date,
                block_end,
                samples_per_day,
                quantity,
            )

            # Fit Chebyshev coefficients
            coeffs = chebyshev.chebfit(x_values, values, deg=degree)
            coeffs_list = cast(List[float], coeffs.tolist())

            # Pad coefficients to fixed size if needed
            if block_size is not None:
                coeff_size = block_size - 6  # Subtract header size
                coeff_count = coeff_size // 4  # Each coefficient is 4 bytes
                while len(coeffs_list) < coeff_count:
                    coeffs_list.append(0.0)

            blocks.append(
                FortyEightHourBlock(
                    header=header,
                    coeffs=coeffs_list,
                )
            )

            current_date = block_end

        # Return the first header (for compatibility) and all blocks
        return blocks[0], blocks[1:]

    def create_multi_precision_file(
        self,
        data_source: EphemerisDataSource,
        body: Planet,
        quantity: Union[EphemerisQuantity, OrbitalElementsQuantity],
        start_date: datetime,
        end_date: datetime,
        config: Dict[str, Any],
    ) -> WeftFile:
        """
        Create a .weft file with multiple precision levels.

        Args:
            data_source: The data source to get values from
            body: The celestial body
            quantity: The quantity being computed
            start_date: Start date
            end_date: End date
            config: Configuration dictionary with settings for different precision levels
                Example:
                {
                    "century": {
                        "enabled": True,
                        "samples_per_year": 12,
                        "degree": 20
                    },
                    "yearly": {
                        "enabled": False
                    },
                    "monthly": {
                        "enabled": True,
                        "samples_per_month": 30,
                        "degree": 10,
                        "years": [2023, 2024]
                    },
                    "daily": {
                        "enabled": True,
                        "samples_per_day": 48,
                        "degree": 8,
                        "date_ranges": [
                            ("2023-01-01", "2023-01-31"),
                            ("2023-06-01", "2023-06-30")
                        ]
                    },
                    "forty_eight_hour": {
                        "enabled": True,
                        "samples_per_day": 48,
                        "degree": 5
                    }
                }

        Returns:
            A WeftFile with blocks at the specified precision levels
        """
        blocks: List[BlockType] = []

        # Create century/multi-year blocks if enabled
        if config.get("century", {}).get("enabled", False):
            century_config = config["century"]

            # Calculate years covered
            start_year = start_date.year
            end_year = end_date.year
            duration = end_year - start_year + 1

            # Create a multi-year block
            multi_year = self.create_multi_year_block(
                data_source=data_source,
                start_year=start_year,
                duration=duration,
                samples_per_year=century_config.get("samples_per_year", 12),
                degree=century_config.get("degree", 20),
                quantity=quantity,
            )
            blocks.append(multi_year)

        # Create yearly blocks if enabled
        if config.get("yearly", {}).get("enabled", False):
            yearly_config = config["yearly"]
            years = yearly_config.get(
                "years", range(start_date.year, end_date.year + 1)
            )

            for year in years:
                if year < start_date.year or year > end_date.year:
                    continue

                # Create a multi-year block for a single year
                yearly = self.create_multi_year_block(
                    data_source=data_source,
                    start_year=year,
                    duration=1,
                    samples_per_year=yearly_config.get("samples_per_year", 365),
                    degree=yearly_config.get("degree", 15),
                    quantity=quantity,
                )
                blocks.append(yearly)

        # Create monthly blocks if enabled
        if config.get("monthly", {}).get("enabled", False):
            monthly_config = config["monthly"]
            years = monthly_config.get(
                "years", range(start_date.year, end_date.year + 1)
            )

            for year in years:
                if year < start_date.year or year > end_date.year:
                    continue

                # Calculate month range for this year
                if year == start_date.year:
                    start_month = start_date.month
                else:
                    start_month = 1

                if year == end_date.year:
                    end_month = end_date.month
                else:
                    end_month = 12

                # Create monthly blocks
                monthly_blocks = self.create_monthly_blocks(
                    data_source=data_source,
                    year=year,
                    month_range=(start_month, end_month),
                    samples_per_month=monthly_config.get("samples_per_month", 30),
                    degree=monthly_config.get("degree", 10),
                    quantity=quantity,
                    end_date=end_date if year == end_date.year else None,
                )
                blocks.extend(monthly_blocks)

        # Create daily blocks if enabled
        if config.get("daily", {}).get("enabled", False):
            daily_config = config["daily"]
            # Create daily blocks for the entire span
            header, daily_blocks = self.create_forty_eight_hour_blocks(
                data_source=data_source,
                start_date=start_date,
                end_date=end_date,
                samples_per_day=daily_config.get("samples_per_day", 48),
                degree=daily_config.get("degree", 8),
                quantity=quantity,
            )
            blocks.append(header)
            blocks.extend(daily_blocks)

        # Create forty-eight hour blocks if enabled
        if config.get("forty_eight_hour", {}).get("enabled", False):
            forty_eight_hour_config = config["forty_eight_hour"]
            # Create forty-eight hour blocks for the entire span
            header, forty_eight_hour_blocks = self.create_forty_eight_hour_blocks(
                data_source=data_source,
                start_date=start_date,
                end_date=end_date,
                samples_per_day=forty_eight_hour_config.get("samples_per_day", 48),
                degree=forty_eight_hour_config.get("degree", 5),
                quantity=quantity,
            )
            blocks.append(header)
            blocks.extend(forty_eight_hour_blocks)

        # Create preamble
        now = datetime.utcnow()
        timespan = f"{start_date.year}-{end_date.year}"

        # Add value behavior range to preamble if applicable
        behavior_str = self.wrapping_behavior
        if self.value_behavior["type"] in ("wrapping", "bounded"):
            min_val, max_val = self.value_behavior["range"]
            behavior_str = f"{behavior_str}[{min_val},{max_val}]"

        preamble = (
            f"#weft! v0.02 {body.name} jpl:horizons {timespan} "
            f"32bit {quantity.name} {behavior_str} chebychevs "
            f"generated@{now.isoformat()}\n"
        )

        return WeftFile(
            preamble=preamble,
            blocks=blocks,
            value_behavior=self.value_behavior,
        )

    def save_file(self, weft_file: WeftFile, output_path: str) -> None:
        """
        Save a WeftFile to disk.

        Args:
            weft_file: The WeftFile to save
            output_path: Path to save the file
        """
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Save the file
        weft_file.write_to_file(output_path)
