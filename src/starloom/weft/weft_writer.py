"""
A class to write .weft binary ephemeris files with multiple levels of precision.

This module provides functionality to write .weft files with century, year, month,
and daily blocks, using Chebyshev polynomials for efficient storage.
"""

from datetime import datetime, timedelta, date
from typing import List, Dict, Tuple, Optional, Any, Callable, Union, TypeVar, cast
from zoneinfo import ZoneInfo
import os
from numpy.polynomial import chebyshev

from .blocks.utils import unwrap_angles
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
        Generate sample points for fitting Chebyshev polynomials.

        Args:
            data_source: The data source to get values from
            start_dt: Start datetime
            end_dt: End datetime
            sample_count: Number of sample points to generate
            quantity: Optional quantity override

        Returns:
            Tuple of (normalized x values, y values)
        """
        # Calculate time step
        total_seconds = (end_dt - start_dt).total_seconds()
        step_seconds = total_seconds / (sample_count - 1)

        # Generate sample points
        values = []
        x_values = []
        current_dt = start_dt

        for i in range(sample_count):
            value = data_source.get_value_at(current_dt)
            values.append(value)
            x_values.append(-1.0 + 2.0 * i / (sample_count - 1))
            current_dt += timedelta(seconds=step_seconds)

        # Handle wrapping for angular quantities
        if self.wrapping_behavior == "wrapping":
            values = unwrap_angles(values)

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
            day_count = (next_month - current_month).days

            # Generate samples
            x_values, values = self._generate_samples(
                data_source,
                current_month,
                next_month - timedelta(microseconds=1),
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

        # Create header
        header = FortyEightHourSectionHeader(
            start_day=date(start_date.year, start_date.month, start_date.day),
            end_day=date(end_date.year, end_date.month, end_date.day),
        )

        # Create blocks
        blocks = []
        current_date = start_date
        while current_date <= end_date:
            # Generate samples for this 48-hour period
            x_values, values = self._generate_samples(
                data_source,
                current_date,
                current_date + timedelta(days=1),
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

            current_date += timedelta(days=1)

        return header, blocks

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
                )
                blocks.extend(monthly_blocks)

        # Create daily blocks if enabled
        if config.get("daily", {}).get("enabled", False):
            daily_config = config["daily"]
            date_ranges = daily_config.get("date_ranges", [])

            for date_range in date_ranges:
                start_str, end_str = date_range
                range_start = datetime.strptime(start_str, "%Y-%m-%d").replace(
                    tzinfo=ZoneInfo("UTC")
                )
                range_end = datetime.strptime(end_str, "%Y-%m-%d").replace(
                    tzinfo=ZoneInfo("UTC")
                )

                # Clip to overall start/end dates
                range_start = max(range_start, start_date)
                range_end = min(range_end, end_date)

                if range_start > range_end:
                    continue

                # Create daily blocks for this range
                header, daily_blocks = self.create_forty_eight_hour_blocks(
                    data_source=data_source,
                    start_date=range_start,
                    end_date=range_end,
                    samples_per_day=daily_config.get("samples_per_day", 48),
                    degree=daily_config.get("degree", 8),
                    quantity=quantity,
                )
                blocks.append(header)
                blocks.extend(daily_blocks)

        # Create preamble
        now = datetime.utcnow()
        timespan = f"{start_date.year}-{end_date.year}"

        # Add value behavior range to preamble if applicable
        behavior_str = self.wrapping_behavior
        if isinstance(self.value_behavior, RangedBehavior):
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
