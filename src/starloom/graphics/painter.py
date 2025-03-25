"""SVG painter for visualizing planetary positions."""

import svgwrite
from typing import Tuple
from datetime import datetime
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
        self, longitude: float, distance: float
    ) -> Tuple[float, float]:
        """Convert ecliptic coordinates to SVG coordinates.

        Args:
            longitude: Ecliptic longitude in degrees
            distance: Distance from Earth in AU

        Returns:
            Tuple of (x, y) coordinates in SVG space
        """
        # Convert longitude to radians
        lon_rad = math.radians(longitude)

        # Scale distance to fit in plot (assuming max distance of 5 AU)
        max_distance = 5.0
        scaled_distance = min(distance / max_distance, 1.0) * min(self.plot_width, self.plot_height) / 2

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
                dwg.circle(center=(x, y), r=4, fill=self.planet_color, stroke="none")
            )

            # Add date label for first and last points
            if jd == min(positions.keys()) or jd == max(positions.keys()):
                dt = datetime.fromtimestamp(jd * 86400 - 2440587.5 * 86400)
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
            dt = datetime.fromtimestamp(jd * 86400 - 2440587.5 * 86400)
            date_str = dt.strftime("%Y-%m-%d")
            dwg.add(
                dwg.text(date_str, insert=(x + 8, y), fill="#666666", font_size="12px")
            )

        # Save the SVG
        dwg.save()
