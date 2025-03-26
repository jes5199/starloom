"""SVG painter for visualizing planetary positions."""

import svgwrite
from typing import Tuple
from datetime import datetime, timezone
import math

from ..ephemeris.quantities import Quantity
from ..planet import Planet


class PlanetaryPainter:
    """SVG painter for visualizing planetary positions."""

    def __init__(
        self,
        width: int = 800,
        height: int = 600,
        margin: int = 50,
        planet_color: str = "#FF0000",
        background_color: str = "#FFFFFF",
    ):
        """Initialize the painter.

        Args:
            width: SVG canvas width in pixels
            height: SVG canvas height in pixels
            margin: Margin around the plot in pixels
            planet_color: Color for the planet dots
            background_color: Background color of the canvas
        """
        self.width = width
        self.height = height
        self.margin = margin
        self.planet_color = planet_color
        self.background_color = background_color
        self.plot_width = width - 2 * margin
        self.plot_height = height - 2 * margin

    def _normalize_coordinates(
        self, longitude: float, distance: float, rotation_offset: float = 0.0
    ) -> Tuple[float, float]:
        """Convert ecliptic coordinates to SVG coordinates.

        Args:
            longitude: Ecliptic longitude in degrees
            distance: Distance from Earth in AU
            rotation_offset: Degrees to rotate the coordinate system (default: 0)

        Returns:
            Tuple of (x, y) coordinates in SVG space
        """
        # Convert longitude to radians, applying rotation offset
        lon_rad = math.radians(longitude - rotation_offset)

        # Scale distance to fit in plot (now using 2 AU as max for better visibility)
        max_distance = 2.0  # Reduced from 5 AU to 2 AU to make planets appear larger
        plot_radius = min(self.plot_width, self.plot_height) / 2
        scaled_distance = (
            min(distance / max_distance, 1.0) * plot_radius * 0.9
        )  # 90% of radius to leave margin

        # Calculate x, y coordinates using trigonometry
        # x = r * cos(θ), y = r * sin(θ)
        center_x = self.width / 2
        center_y = self.height / 2

        x = center_x + scaled_distance * math.cos(lon_rad)
        y = center_y + scaled_distance * math.sin(lon_rad)

        return x, y

    def draw_planet_positions(
        self,
        positions: dict[float, dict[str, float]],
        planet: Planet,
        output_path: str,
    ) -> None:
        """Draw planet positions to an SVG file.

        Args:
            positions: Dictionary mapping Julian dates to position data
            planet: The planet being plotted
            output_path: Path to save the SVG file
        """
        # Create SVG drawing
        dwg = svgwrite.Drawing(
            output_path,
            size=(self.width, self.height),
            style=f"background-color: {self.background_color}",
        )

        # Draw zodiac circle
        center_x = self.width / 2
        center_y = self.height / 2
        radius = min(self.plot_width, self.plot_height) / 2
        dwg.add(
            dwg.circle(
                center=(center_x, center_y),
                r=radius,
                fill="none",
                stroke="#CCCCCC",
                stroke_width=1,
            )
        )

        # Draw zodiac divisions
        for i in range(12):
            angle = math.radians(i * 30)
            x1 = center_x + radius * math.cos(angle)
            y1 = center_y + radius * math.sin(angle)
            x2 = center_x + (radius - 20) * math.cos(angle)
            y2 = center_y + (radius - 20) * math.sin(angle)
            dwg.add(
                dwg.line(start=(x1, y1), end=(x2, y2), stroke="#CCCCCC", stroke_width=1)
            )

        # Draw planet positions
        for jd, pos_data in sorted(positions.items()):
            longitude = pos_data.get(Quantity.ECLIPTIC_LONGITUDE, 0.0)
            distance = pos_data.get(Quantity.DELTA, 0.0)

            if not isinstance(longitude, (int, float)) or not isinstance(
                distance, (int, float)
            ):
                continue

            x, y = self._normalize_coordinates(longitude, distance)

            # Draw planet dot
            dwg.add(
                dwg.circle(center=(x, y), r=2, fill=self.planet_color, stroke="none")
            )

            # Add date label for first and last points
            if jd == min(positions.keys()) or jd == max(positions.keys()):
                dt = datetime.fromtimestamp(jd * 86400 - 2440587.5 * 86400, tz=timezone.utc)
                date_str = dt.strftime("%Y-%m-%d")
                dwg.add(
                    dwg.text(
                        date_str, insert=(x + 8, y), fill="#666666", font_size="12px"
                    )
                )

        # Save the SVG
        dwg.save()

    def draw_planet_path(
        self,
        positions: dict[float, dict[str, float]],
        planet: Planet,
        output_path: str,
    ) -> None:
        """Draw planet positions as a continuous path.

        Args:
            positions: Dictionary mapping Julian dates to position data
            planet: The planet being plotted
            output_path: Path to save the SVG file
        """
        # Create SVG drawing
        dwg = svgwrite.Drawing(
            output_path,
            size=(self.width, self.height),
            style=f"background-color: {self.background_color}",
        )

        # Draw zodiac circle
        center_x = self.width / 2
        center_y = self.height / 2
        radius = min(self.plot_width, self.plot_height) / 2
        dwg.add(
            dwg.circle(
                center=(center_x, center_y),
                r=radius,
                fill="none",
                stroke="#CCCCCC",
                stroke_width=1,
            )
        )

        # Draw zodiac divisions
        for i in range(12):
            angle = math.radians(i * 30)
            x1 = center_x + radius * math.cos(angle)
            y1 = center_y + radius * math.sin(angle)
            x2 = center_x + (radius - 20) * math.cos(angle)
            y2 = center_y + (radius - 20) * math.sin(angle)
            dwg.add(
                dwg.line(start=(x1, y1), end=(x2, y2), stroke="#CCCCCC", stroke_width=1)
            )

        # Create path data
        path_data = []
        for jd, pos_data in sorted(positions.items()):
            longitude = pos_data.get(Quantity.ECLIPTIC_LONGITUDE, 0.0)
            distance = pos_data.get(Quantity.DELTA, 0.0)

            if not isinstance(longitude, (int, float)) or not isinstance(
                distance, (int, float)
            ):
                continue

            x, y = self._normalize_coordinates(longitude, distance)

            if not path_data:
                path_data.append(f"M {x} {y}")
            else:
                path_data.append(f"L {x} {y}")

        # Draw the path
        if path_data:
            dwg.add(
                dwg.path(
                    d=" ".join(path_data),
                    fill="none",
                    stroke=self.planet_color,
                    stroke_width=2,
                )
            )

        # Add date labels for first and last points
        for jd in [min(positions.keys()), max(positions.keys())]:
            pos_data = positions[jd]
            longitude = pos_data.get(Quantity.ECLIPTIC_LONGITUDE, 0.0)
            distance = pos_data.get(Quantity.DELTA, 0.0)

            if not isinstance(longitude, (int, float)) or not isinstance(
                distance, (int, float)
            ):
                continue

            x, y = self._normalize_coordinates(longitude, distance)
            dt = datetime.fromtimestamp(jd * 86400 - 2440587.5 * 86400, tz=timezone.utc)
            date_str = dt.strftime("%Y-%m-%d")
            dwg.add(
                dwg.text(date_str, insert=(x + 8, y), fill="#666666", font_size="12px")
            )

        # Save the SVG
        dwg.save()

    def draw_retrograde(
        self,
        positions: dict[float, dict[str, float]],
        planet: Planet,
        output_path: str,
        target_date: float,
    ) -> None:
        """Draw planet positions with retrograde motion highlighted.

        Args:
            positions: Dictionary mapping Julian dates to position data
            planet: The planet being plotted
            output_path: Path to save the SVG file
            target_date: Julian date of the target date to analyze
        """
        # Convert target_date to datetime with UTC timezone
        target_datetime = datetime.fromtimestamp(target_date * 86400 - 2440587.5 * 86400, tz=timezone.utc)

        # Find the nearest retrograde period
        from ..knowledge.retrogrades import find_nearest_retrograde
        retrograde_period = find_nearest_retrograde(planet, target_datetime)
        if not retrograde_period:
            raise ValueError(f"No retrograde periods found for {planet.name}")

        # Get the sun aspect longitude for rotation offset
        sun_aspect_jd = retrograde_period.sun_aspect_date.timestamp() / 86400 + 2440587.5
        
        # Find the closest available Julian date in positions
        available_jds = sorted(positions.keys())
        closest_jd = min(available_jds, key=lambda x: abs(x - sun_aspect_jd))
        sun_aspect_longitude = positions[closest_jd].get(Quantity.ECLIPTIC_LONGITUDE, 0.0)
        
        # Add 90 degrees to rotate counterclockwise
        sun_aspect_longitude += 90.0

        # Convert retrograde period dates to Julian dates
        shadow_start_jd = retrograde_period.pre_shadow_start_date.timestamp() / 86400 + 2440587.5
        shadow_end_jd = retrograde_period.post_shadow_end_date.timestamp() / 86400 + 2440587.5

        # Get daily positions for both planet and Sun
        from ..weft_ephemeris.ephemeris import WeftEphemeris
        from ..ephemeris.time_spec import TimeSpec

        # Load ephemeris data
        planet_ephemeris = WeftEphemeris(data_dir=f"weftballs/{planet.name.lower()}_weftball.tar.gz")
        sun_ephemeris = WeftEphemeris(data_dir="weftballs/sun_weftball.tar.gz")

        # Generate daily timestamps at midnight UTC
        daily_times = []
        current_jd = shadow_start_jd - 60  # Start 60 days before
        while current_jd <= shadow_end_jd + 60:  # End 60 days after
            daily_times.append(current_jd)
            current_jd += 1.0  # Add one day

        # Get positions for both planet and Sun
        time_spec = TimeSpec.from_dates(daily_times)
        planet_positions = planet_ephemeris.get_planet_positions(planet.name, time_spec)
        sun_positions = sun_ephemeris.get_planet_positions("SUN", time_spec)

        # Track min/max coordinates for viewbox calculation
        min_x = float('inf')
        max_x = float('-inf')
        min_y = float('inf')
        max_y = float('-inf')
        aspect_x = 0
        aspect_y = 0

        # First pass: calculate coordinates and find bounds
        for jd in daily_times:
            # Only use planet dots during retrograde period for bounds
            if shadow_start_jd <= jd <= shadow_end_jd:
                if jd in planet_positions:
                    pos_data = planet_positions[jd]
                    longitude = pos_data.get(Quantity.ECLIPTIC_LONGITUDE, 0.0)
                    distance = pos_data.get(Quantity.DELTA, 0.0)
                    if isinstance(longitude, (int, float)) and isinstance(distance, (int, float)):
                        x, y = self._normalize_coordinates(longitude, distance, sun_aspect_longitude)
                        min_x = min(min_x, x)
                        max_x = max(max_x, x)
                        min_y = min(min_y, y)
                        max_y = max(max_y, y)

            # Store aspect coordinates
            if jd == sun_aspect_jd:
                if jd in planet_positions:
                    pos_data = planet_positions[jd]
                    longitude = pos_data.get(Quantity.ECLIPTIC_LONGITUDE, 0.0)
                    distance = pos_data.get(Quantity.DELTA, 0.0)
                    if isinstance(longitude, (int, float)) and isinstance(distance, (int, float)):
                        aspect_x, aspect_y = self._normalize_coordinates(longitude, distance, sun_aspect_longitude)

        # Add padding (10% of the range)
        x_range = max_x - min_x
        y_range = max_y - min_y
        padding_x = x_range * 0.1  # Increased to 10%
        padding_y = y_range * 0.1  # Increased to 10%
        min_x -= padding_x
        max_x += padding_x
        min_y -= padding_y
        max_y += padding_y

        # Calculate viewbox dimensions
        viewbox_width = max_x - min_x
        viewbox_height = max_y - min_y

        # Create SVG drawing with dynamic viewbox
        dwg = svgwrite.Drawing(
            output_path,
            size=(self.width, self.height),
            viewBox=f"{min_x} {min_y} {viewbox_width} {viewbox_height}",
            style=f"background-color: {self.background_color}",
        )

        # Draw planet positions and path
        # First pass: draw grey dots for pre/post period
        for jd in daily_times:
            if jd not in planet_positions:
                continue

            pos_data = planet_positions[jd]
            longitude = pos_data.get(Quantity.ECLIPTIC_LONGITUDE, 0.0)
            distance = pos_data.get(Quantity.DELTA, 0.0)

            if not isinstance(longitude, (int, float)) or not isinstance(
                distance, (int, float)
            ):
                continue

            x, y = self._normalize_coordinates(longitude, distance, sun_aspect_longitude)

            # Draw grey dots for pre/post period
            if not (shadow_start_jd <= jd <= shadow_end_jd):
                dwg.add(
                    dwg.circle(center=(x, y), r=0.25, fill="#CCCCCC", stroke="none")
                )

        # Second pass: draw colored dots for retrograde period
        for jd in daily_times:
            if jd not in planet_positions:
                continue

            pos_data = planet_positions[jd]
            longitude = pos_data.get(Quantity.ECLIPTIC_LONGITUDE, 0.0)
            distance = pos_data.get(Quantity.DELTA, 0.0)

            if not isinstance(longitude, (int, float)) or not isinstance(
                distance, (int, float)
            ):
                continue

            x, y = self._normalize_coordinates(longitude, distance, sun_aspect_longitude)

            # Draw colored dots for retrograde period
            if shadow_start_jd <= jd <= shadow_end_jd:
                dwg.add(
                    dwg.circle(center=(x, y), r=0.25, fill=self.planet_color, stroke="none")
                )

        # Draw Sun positions
        for jd in daily_times:
            if jd not in sun_positions:
                continue

            pos_data = sun_positions[jd]
            longitude = pos_data.get(Quantity.ECLIPTIC_LONGITUDE, 0.0)
            distance = pos_data.get(Quantity.DELTA, 0.0)

            if not isinstance(longitude, (int, float)) or not isinstance(
                distance, (int, float)
            ):
                continue

            x, y = self._normalize_coordinates(longitude, distance, sun_aspect_longitude)

            # Draw Sun dot
            dwg.add(
                dwg.circle(center=(x, y), r=0.375, fill="#FFD700", stroke="none")  # Gold color for Sun
            )

        # Add date labels for key points
        key_dates = [
            (retrograde_period.station_retrograde_date, "Station Retrograde"),
            (retrograde_period.station_direct_date, "Station Direct"),
            (retrograde_period.sun_aspect_date, "Sun Aspect"),
        ]

        for date, label in key_dates:
            jd = date.timestamp() / 86400 + 2440587.5
            if jd in positions:
                pos_data = positions[jd]
                longitude = pos_data.get(Quantity.ECLIPTIC_LONGITUDE, 0.0)
                distance = pos_data.get(Quantity.DELTA, 0.0)
                x, y = self._normalize_coordinates(longitude, distance, sun_aspect_longitude)
                dwg.add(
                    dwg.text(
                        f"{label}\n{date.strftime('%Y-%m-%d')}",
                        insert=(x + 8, y),
                        fill="#666666",
                        font_size="12px",
                    )
                )

        # Save the SVG
        dwg.save()
