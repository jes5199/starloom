"""SVG painter for visualizing planetary positions."""

import svgwrite
from typing import Tuple
from datetime import datetime, timezone
import math

from ..ephemeris.quantities import Quantity
from ..planet import Planet


def angle_distance(a: float, b: float) -> float:
    """
    Returns the 'forward' distance in degrees from angle a to angle b,
    each in [0..360). The result is also in [0..360).
    """
    return (b - a) % 360


def is_in_angular_range(x: float, start: float, end: float) -> bool:
    """
    Returns True if angle x is in the forward range from start to end
    (wrapping at 360). If end < start, the range passes 0/360 boundary.
    """
    return angle_distance(start, x) <= angle_distance(start, end)


def is_near_angle(x: float, ref: float, tolerance: float = 5.0) -> bool:
    """Returns True if angle x is within `tolerance` degrees of ref."""
    diff = min(abs(x - ref), 360 - abs(x - ref))
    return diff <= tolerance


class PlanetaryPainter:
    """SVG painter for visualizing planetary positions."""

    # Planet-specific background colors
    PLANET_BACKGROUND_COLORS = {
        Planet.VENUS: "#00AF00",  # Green for Venus
        Planet.MARS: "#8B0000",   # Dark red for Mars
        # Default to black for other planets
        Planet.MERCURY: "#000000",
        Planet.JUPITER: "#000000",
        Planet.SATURN: "#000000",
        Planet.URANUS: "#000000",
        Planet.NEPTUNE: "#000000",
        Planet.PLUTO: "#000000",
        Planet.MOON: "#000000",
        Planet.SUN: "#000000",
    }

    def __init__(
        self,
        width: int = 800,
        height: int = 600,
        margin: int = 50,
        planet_color: str = "#FFFFFF",  # White
        background_color: str = None,  # Will be set based on planet
    ):
        """Initialize the painter.

        Args:
            width: SVG canvas width in pixels
            height: SVG canvas height in pixels
            margin: Margin around the plot in pixels
            planet_color: Color for the planet dots
            background_color: Background color of the canvas (if None, will use planet-specific color)
        """
        self.width = width
        self.height = height
        self.margin = margin
        self.planet_color = planet_color
        self.background_color = background_color
        self.plot_width = width - 2 * margin
        self.plot_height = height - 2 * margin

    def _get_background_color(self, planet: Planet) -> str:
        """Get the background color for a specific planet."""
        if self.background_color is not None:
            return self.background_color
        return self.PLANET_BACKGROUND_COLORS.get(planet, "#000000")

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
    
    def _normalize_distance(self, distance: float) -> float:
        """Normalize distance to fit in plot."""
        max_distance = 2.0  # Reduced from 5 AU to 2 AU to make planets appear larger
        plot_radius = min(self.plot_width, self.plot_height) / 2
        return min(distance / max_distance, 1.0) * plot_radius * 0.9

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
            style=f"background-color: {self._get_background_color(planet)}; font-family: Helvetica, Arial, sans-serif;",
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
                dt = datetime.fromtimestamp(
                    jd * 86400 - 2440587.5 * 86400, tz=timezone.utc
                )
                date_str = dt.strftime("%Y-%m-%d")
                dwg.add(
                    dwg.text(
                        date_str, insert=(x + 8, y), fill="#666666", font_size="12px", font_family="Helvetica, Arial, sans-serif"
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
            style=f"background-color: {self._get_background_color(planet)}; font-family: Helvetica, Arial, sans-serif;",
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
                dwg.text(date_str, insert=(x + 8, y), fill="#666666", font_size="12px", font_family="Helvetica, Arial, sans-serif")
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
        target_datetime = datetime.fromtimestamp(
            target_date * 86400 - 2440587.5 * 86400, tz=timezone.utc
        )

        # Find the nearest retrograde period
        from ..knowledge.retrogrades import find_nearest_retrograde

        retrograde_period = find_nearest_retrograde(planet, target_datetime)
        if not retrograde_period:
            raise ValueError(f"No retrograde periods found for {planet.name}")

        # Get the sun aspect longitude for rotation offset
        sun_aspect_jd = (
            retrograde_period.sun_aspect_date.timestamp() / 86400 + 2440587.5
        )

        # Find the closest available Julian date in positions
        available_jds = sorted(positions.keys())
        closest_jd = min(available_jds, key=lambda x: abs(x - sun_aspect_jd))
        sun_aspect_longitude = positions[closest_jd].get(
            Quantity.ECLIPTIC_LONGITUDE, 0.0
        )
        sun_aspect_distance = positions[closest_jd].get(Quantity.DELTA, 0.0)

        # Add 90 degrees to rotate counterclockwise
        sun_aspect_longitude += 90.0

        # Convert retrograde period dates to Julian dates
        shadow_start_jd = (
            retrograde_period.pre_shadow_start_date.timestamp() / 86400 + 2440587.5
        )
        shadow_end_jd = (
            retrograde_period.post_shadow_end_date.timestamp() / 86400 + 2440587.5
        )
        

        # Get daily positions for both planet and Sun
        from ..weft_ephemeris.ephemeris import WeftEphemeris
        from ..ephemeris.time_spec import TimeSpec

        # Load ephemeris data
        planet_ephemeris = WeftEphemeris(
            data_dir=f"weftballs/{planet.name.lower()}_weftball.tar.gz"
        )
        sun_ephemeris = WeftEphemeris(data_dir="weftballs/sun_weftball.tar.gz")

        # Generate daily timestamps at midnight UTC
        daily_times = []
        current_jd = math.floor(shadow_start_jd - 60) - 0.5  # Start 60 days before
        while current_jd <= math.floor(shadow_end_jd + 60) + 0.5:  # End 60 days after
            daily_times.append(current_jd)
            current_jd += 1.0  # Add one day

        # Get positions for both planet and Sun
        time_spec = TimeSpec.from_dates(daily_times)
        planet_positions = planet_ephemeris.get_planet_positions(planet.name, time_spec)
        sun_positions = sun_ephemeris.get_planet_positions("SUN", time_spec)

        shadow_positions = planet_ephemeris.get_planet_positions(
            planet.name,
            TimeSpec.from_dates([shadow_start_jd, shadow_end_jd])
        )

        shadow_max_distance = max(shadow_positions.values(), key=lambda x: x[Quantity.DELTA])[Quantity.DELTA]
        shadow_min_distance = min(shadow_positions.values(), key=lambda x: x[Quantity.DELTA])[Quantity.DELTA]
        shadow_average_distance = sum(x[Quantity.DELTA] for x in shadow_positions.values()) / len(shadow_positions)

        station_positions = planet_ephemeris.get_planet_positions(
            planet.name,
            TimeSpec.from_dates([retrograde_period.station_retrograde_date, retrograde_period.station_direct_date])
        )

        station_retrograde_longitude = station_positions[retrograde_period.station_retrograde_date.timestamp() / 86400 + 2440587.5].get(Quantity.ECLIPTIC_LONGITUDE, 0.0)
        station_direct_longitude = station_positions[retrograde_period.station_direct_date.timestamp() / 86400 + 2440587.5].get(Quantity.ECLIPTIC_LONGITUDE, 0.0)
        station_retrograde_distance = station_positions[retrograde_period.station_retrograde_date.timestamp() / 86400 + 2440587.5].get(Quantity.DELTA, 0.0)
        station_direct_distance = station_positions[retrograde_period.station_direct_date.timestamp() / 86400 + 2440587.5].get(Quantity.DELTA, 0.0)

        # Track min/max coordinates for viewbox calculation
        min_x = float("inf")
        max_x = float("-inf")
        min_y = float("inf")
        max_y = float("-inf")
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
                    if isinstance(longitude, (int, float)) and isinstance(
                        distance, (int, float)
                    ):
                        x, y = self._normalize_coordinates(
                            longitude, distance, sun_aspect_longitude
                        )
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
                    if isinstance(longitude, (int, float)) and isinstance(
                        distance, (int, float)
                    ):
                        aspect_x, aspect_y = self._normalize_coordinates(
                            longitude, distance, sun_aspect_longitude
                        )

        # Add padding (10% of the range)
        x_range = max_x - min_x
        y_range = max_y - min_y
        padding_x = x_range * 0.4  # Increased to 20% for more horizontal space
        padding_y = y_range * 0.15  # Keep vertical padding at 15%
        min_x -= padding_x
        max_x += padding_x
        min_y -= padding_y
        max_y += padding_y

        # Add additional padding for the outer background
        outer_padding = 1  # Fixed padding in SVG units
        outer_min_x = min_x - outer_padding
        outer_max_x = max_x + outer_padding
        outer_min_y = min_y - outer_padding
        outer_max_y = max_y + outer_padding

        # Calculate viewbox dimensions
        viewbox_width = outer_max_x - outer_min_x
        viewbox_height = outer_max_y - outer_min_y

        # Create SVG drawing with dynamic viewbox
        dwg = svgwrite.Drawing(
            output_path,
            size=(self.width, self.height),
            viewBox=f"{outer_min_x} {outer_min_y} {viewbox_width} {viewbox_height}",
            style="background-color: transparent; font-family: Helvetica, Arial, sans-serif;",
        )

        # Create clip path for rounded rectangle
        clip_path = dwg.defs.add(dwg.clipPath(id='rounded-rect'))
        clip_path.add(
            dwg.rect(
                insert=(min_x, min_y),
                size=(max_x - min_x, max_y - min_y),
                rx=5,
                ry=5,
            )
        )

        # Add rounded rectangle background
        corner_radius = 5  # Reduced from 20 to 5 for more subtle rounding
        
        # Create gradient for background
        bg_gradient = dwg.defs.add(dwg.linearGradient(id='bg-gradient'))
        base_color = self._get_background_color(planet)
        # Create a darker version of the base color by reducing RGB values by 20%
        darker_color = f"#{int(int(base_color[1:3], 16) * 0.8):02x}{int(int(base_color[3:5], 16) * 0.8):02x}{int(int(base_color[5:7], 16) * 0.8):02x}"
        bg_gradient.add_stop_color(offset=0, color=base_color)
        bg_gradient.add_stop_color(offset=1, color=darker_color)
        bg_gradient['x1'] = '0%'
        bg_gradient['y1'] = '0%'
        bg_gradient['x2'] = '0%'
        bg_gradient['y2'] = '100%'
        
        dwg.add(
            dwg.rect(
                insert=(min_x, min_y),
                size=(max_x - min_x, max_y - min_y),
                rx=corner_radius,
                ry=corner_radius,
                fill=bg_gradient.get_paint_server(),
                stroke="none",
            )
        )

        # Create a group for all elements that should be clipped
        clip_group = dwg.g(clip_path='url(#rounded-rect)')

        # Define gradients for sun fade in/out effects
        gradient = dwg.defs.add(dwg.linearGradient(id='sun-fade-out'))
        gradient.add_stop_color(offset=0, color='#FFD700', opacity=0)
        gradient.add_stop_color(offset=1, color='#FFD700', opacity=1)
        # Set gradient direction from center to end of line
        gradient['x1'] = '0%'
        gradient['y1'] = '0%'
        gradient['x2'] = '0%'
        gradient['y2'] = '100%'

        gradient = dwg.defs.add(dwg.linearGradient(id='sun-fade-in'))
        gradient.add_stop_color(offset=0, color='#FFD700', opacity=1)
        gradient.add_stop_color(offset=1, color='#FFD700', opacity=0)
        # Set gradient direction from center to end of line
        gradient['x1'] = '0%'
        gradient['y1'] = '0%'
        gradient['x2'] = '0%'
        gradient['y2'] = '100%'


        # Draw line at station retrograde longitude
        # Where is Earth's center, in final coords?
        earth_x, earth_y = self._normalize_coordinates(0.0, 0.0, sun_aspect_longitude)
        # Where is the station retrograde longitude at 1 AU, in final coords?
        sx, sy = self._normalize_coordinates(
            retrograde_period.station_retrograde_longitude,
            1,
            sun_aspect_longitude
        )
        # Draw solid line from Earth center to station retrograde point
        clip_group.add(
            dwg.line(
                start=(earth_x, earth_y),
                end=(sx, sy),
                stroke="#000000",
                stroke_width=0.15,  # Made even thinner
                opacity=0.6
            )
        )

        # Add station retrograde label
        station_retrograde_date = retrograde_period.station_retrograde_date
        station_retrograde_x, station_retrograde_y = self._normalize_coordinates(
            station_retrograde_longitude,
            station_retrograde_distance,
            sun_aspect_longitude
        )

        text_x = station_retrograde_x + 0.5
        text_y = station_retrograde_y

        text_elem = dwg.text(
            text="",
            insert=(text_x, text_y),
            fill="#FFFFFF",
            font_size="0.8",
            dominant_baseline="hanging"
        )

        text_elem.add(dwg.tspan("Stations Retrograde", x=[text_x], dy=['0em']))
        text_elem.add(dwg.tspan(station_retrograde_date.strftime('%Y-%m-%d'), x=[text_x], dy=['1em']))
        text_elem.add(dwg.tspan(station_retrograde_date.strftime('%H:%M UTC'), x=[text_x], dy=['1em']))

        clip_group.add(text_elem)



        # Add station direct label
        station_direct_date = retrograde_period.station_direct_date
        station_direct_x, station_direct_y = self._normalize_coordinates(
            station_direct_longitude,
            station_direct_distance,
            sun_aspect_longitude
        )

        text_x = station_direct_x - 0.5
        text_y = station_direct_y

        text_elem = dwg.text(
            text="",
            insert=(text_x, text_y),
            fill="#FFFFFF",
            font_size="0.8",
            dominant_baseline="hanging",
            text_anchor="end"
        )

        text_elem.add(dwg.tspan("Stations Direct", x=[text_x], dy=['0em']))
        text_elem.add(dwg.tspan(station_direct_date.strftime('%Y-%m-%d'), x=[text_x], dy=['1em']))
        text_elem.add(dwg.tspan(station_direct_date.strftime('%H:%M UTC'), x=[text_x], dy=['1em']))

        clip_group.add(text_elem)


        # Add shadow period labels
        # Shadow start label
        shadow_start_date = retrograde_period.pre_shadow_start_date
        shadow_start_x, shadow_start_y = self._normalize_coordinates(
            station_direct_longitude,
            shadow_positions[shadow_start_date.timestamp() / 86400 + 2440587.5].get(Quantity.DELTA, 0.0),
            sun_aspect_longitude
        )

        text_x = shadow_start_x - 0.25
        text_y = shadow_start_y

        text_elem = dwg.text(
            text="",
            insert=(text_x, text_y),
            fill="#FFFFFF",
            font_size="0.8",
            dominant_baseline="hanging",
            text_anchor="end"
        )

        text_elem.add(dwg.tspan("Shadow Begins", x=[text_x], dy=['0em']))
        text_elem.add(dwg.tspan(shadow_start_date.strftime('%Y-%m-%d'), x=[text_x], dy=['1em']))
        text_elem.add(dwg.tspan(shadow_start_date.strftime('%H:%M UTC'), x=[text_x], dy=['1em']))

        clip_group.add(text_elem)

        # Shadow end label
        shadow_end_date = retrograde_period.post_shadow_end_date
        shadow_end_x, shadow_end_y = self._normalize_coordinates(
            station_retrograde_longitude,
            shadow_positions[shadow_end_date.timestamp() / 86400 + 2440587.5].get(Quantity.DELTA, 0.0),
            sun_aspect_longitude
        )

        text_x = shadow_end_x + 0.25
        text_y = shadow_end_y

        text_elem = dwg.text(
            text="",
            insert=(text_x, text_y),
            fill="#FFFFFF",
            font_size="0.8",
            dominant_baseline="hanging",
        )

        text_elem.add(dwg.tspan("Shadow Ends", x=[text_x], dy=['0em']))
        text_elem.add(dwg.tspan(shadow_end_date.strftime('%Y-%m-%d'), x=[text_x], dy=['1em']))
        text_elem.add(dwg.tspan(shadow_end_date.strftime('%H:%M UTC'), x=[text_x], dy=['1em']))

        clip_group.add(text_elem)


        # Draw line at station direct longitude
        # Where is the station direct longitude at 1 AU, in final coords?
        dx, dy = self._normalize_coordinates(
            retrograde_period.station_direct_longitude,
            1,
            sun_aspect_longitude
        )
        # Draw solid line from Earth center to station direct point
        clip_group.add(
            dwg.line(
                start=(earth_x, earth_y),
                end=(dx, dy),
                stroke="#000000",
                stroke_width=0.15,  # Made even thinner
                opacity=0.6
            )
        )

        # Sun aspect line in two sections
        # 1. from earth center to planet (solid yellow)
        # 2. from planet towards sun (gradient)
        planet_x, planet_y = self._normalize_coordinates(
            retrograde_period.sun_aspect_longitude,
            sun_aspect_distance * 1.0,
            sun_aspect_longitude
        )

        sun_x, sun_y = self._normalize_coordinates(
            retrograde_period.sun_aspect_longitude,
            1,
            sun_aspect_longitude
        )

        dx, dy = self._normalize_coordinates(
            retrograde_period.sun_aspect_longitude,
            sun_aspect_distance * 1.1,
            sun_aspect_longitude
        )

        clip_group.add(
            dwg.line(
                start=(earth_x, earth_y),
                end=(planet_x, planet_y),
                stroke='#FFD700',
                stroke_width=0.15,
                opacity=1.0  # Set to 1.0 since opacity is handled by gradient
            )
        )

        clip_group.add(
            dwg.line(
                start=(planet_x, planet_y),
                end=(dx, dy),
                stroke='url(#sun-fade-out)',
                stroke_width=0.15,
                opacity=1.0  # Set to 1.0 since opacity is handled by gradient
            )
        )

        clip_group.add(
            dwg.line(
                start=(planet_x, planet_y),
                end=(dx, dy),
                stroke='url(#sun-fade-out)',
                stroke_width=0.15,
                opacity=1.0  # Set to 1.0 since opacity is handled by gradient
            )
        )

        # text above sun aspect line
        clip_group.add(
            dwg.text(
                f"Cazimi {retrograde_period.sun_aspect_date.strftime('%Y-%m-%d')}",
                insert=(dx, dy),
                fill="#FFFFFF",
                font_size="0.8",
                dominant_baseline="middle",
                text_anchor="start",
                transform=f"rotate({-90}, {dx}, {dy})",
            )
        )


        if planet.name.lower() in ["venus", "mercury"]:
            # draw spark towards sun

            dx, dy = self._normalize_coordinates(
                retrograde_period.sun_aspect_longitude,
                shadow_average_distance,
                sun_aspect_longitude
            )

            d2x, d2y = self._normalize_coordinates(
                retrograde_period.sun_aspect_longitude,
                shadow_max_distance + sun_aspect_distance * 0.1,
                sun_aspect_longitude
            )

            clip_group.add(
                dwg.line(
                    start=(dx, dy),
                    end=(d2x, d2y),
                    stroke='url(#sun-fade-in)',
                    stroke_width=0.15,
                    opacity=1.0  # Set to 1.0 since opacity is handled by gradient
                )
            )

            clip_group.add(
                dwg.line(
                    start=(sun_x, sun_y),
                    end=(d2x, d2y),
                    stroke='#FFD700',
                    stroke_width=0.15,
                    opacity=1.0
                )
            )

        zodiac_distance = shadow_max_distance + sun_aspect_distance * 0.1

        # Define zodiac signs and their starting longitudes
        zodiac_signs = {
            0: "Aries",
            30: "Taurus",
            60: "Gemini",
            90: "Cancer",
            120: "Leo",
            150: "Virgo",
            180: "Libra",
            210: "Scorpio",
            240: "Sagittarius",
            270: "Capricorn",
            300: "Aquarius",
            330: "Pisces",
        }

        for ecliptic_degrees in range(0, 360, 1):
            inner_distance = zodiac_distance - 0.005 # short tick default

            if ecliptic_degrees % 30 == 0:
                # Zodiac sign boundaries
                inner_distance = 0
                
                # Add zodiac sign name if this is a sign boundary
                if ecliptic_degrees in zodiac_signs:
                    # Calculate text position slightly inward from the line
                    text_distance = zodiac_distance - 0.010
                    text_x, text_y = self._normalize_coordinates(
                        ecliptic_degrees + 0.25,
                        text_distance,
                        sun_aspect_longitude
                    )
                    
                    # Calculate text rotation based on angle
                    text_angle = ecliptic_degrees - sun_aspect_longitude + 180
                    
                    # Add text with rotation
                    clip_group.add(
                        dwg.text(
                            zodiac_signs[ecliptic_degrees],
                            insert=(text_x, text_y),
                            fill="#A52A2A",
                            font_size="1.5",
                            opacity=0.5,
                            transform=f"rotate({text_angle}, {text_x}, {text_y})",
                            text_anchor="start",
                            dominant_baseline="alphabetic"
                        )
                    )

                    text2_x, text2_y = self._normalize_coordinates(
                        ecliptic_degrees - 0.25,
                        text_distance,
                        sun_aspect_longitude
                    )

                    clip_group.add(
                        dwg.text(
                            zodiac_signs[(ecliptic_degrees - 30) % 360],
                            insert=(text2_x, text2_y),
                            fill="#A52A2A",
                            font_size="1.5",
                            opacity=0.5,
                            transform=f"rotate({text_angle}, {text2_x}, {text2_y})",
                            text_anchor="start",
                            dominant_baseline="hanging"
                        )
                    )


            elif ecliptic_degrees % 10 == 0:
                # Decan boundaries, longer tick
                inner_distance = zodiac_distance - 0.01

            inner_x, inner_y = self._normalize_coordinates(
                ecliptic_degrees,
                inner_distance,
                sun_aspect_longitude
            )

            zx, zy = self._normalize_coordinates(
                ecliptic_degrees,
                zodiac_distance,
                sun_aspect_longitude
            )

            stroke_width = 0.15

            clip_group.add(
                dwg.line(
                    start=(inner_x, inner_y),
                    end=(zx, zy),
                    stroke="#A52A2A",
                    stroke_width=stroke_width,
                    opacity=0.5
                )
            )
        # Draw a circle at maximum shadow distance
        clip_group.add(
            dwg.circle(
                center=(earth_x, earth_y),
                r=self._normalize_distance(zodiac_distance),
                stroke="#A52A2A",
                stroke_width=0.15,
                opacity=0.5,
                fill="none"
            )
        )

        # Draw planet positions and path
        # Single pass for planet dots
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

            x, y = self._normalize_coordinates(
                longitude, distance, sun_aspect_longitude
            )

            # Draw dot based on period
            if not (shadow_start_jd <= jd <= shadow_end_jd):
                # Pre/post period
                clip_group.add(
                    dwg.circle(
                        center=(x, y),
                        r=0.25,
                        fill="#FFFFFF",
                        stroke="none",
                        opacity=0.3,
                    )
                )
            else:
                # Inside shadow period
                if (
                    jd
                    <= retrograde_period.station_retrograde_date.timestamp() / 86400
                    + 2440587.5
                ):
                    # Pre-shadow period
                    clip_group.add(
                        dwg.circle(
                            center=(x, y),
                            r=0.25,
                            fill="#00DDDD",  # Cyan (bright, high contrast)
                            stroke="#FFFFFF",
                            stroke_width=0.05,
                            opacity=0.9,
                        )
                    )
                elif (
                    jd
                    >= retrograde_period.station_direct_date.timestamp() / 86400
                    + 2440587.5
                ):
                    # Post-shadow period
                    clip_group.add(
                        dwg.circle(
                            center=(x, y),
                            r=0.25,
                            fill="#3399FF",  # Bright blue (high contrast)
                            stroke="#FFFFFF",
                            stroke_width=0.05,
                            opacity=0.9,
                        )
                    )
                else:
                    # Main retrograde period
                    clip_group.add(
                        dwg.circle(
                            center=(x, y),
                            r=0.25,
                            fill="#FFFFFF",
                            stroke="none",
                            opacity=0.8,
                        )
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

            x, y = self._normalize_coordinates(
                longitude, distance, sun_aspect_longitude
            )

            # Draw Sun dot
            clip_group.add(
                dwg.circle(
                    center=(x, y), r=0.375, fill="#FFD700", stroke="none", opacity=0.6
                )
            )


        # Add the clipped group to the drawing
        dwg.add(clip_group)

        # Add date labels for key points (outside the clip path so they're always visible)
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
                x, y = self._normalize_coordinates(
                    longitude, distance, sun_aspect_longitude
                )
                dwg.add(
                    dwg.text(
                        f"{label}\n{date.strftime('%Y-%m-%d')}",
                        insert=(x + 8, y),
                        fill="#666666",
                        font_size="12px",
                        font_family="Helvetica, Arial, sans-serif"
                    )
                )

        # Save the SVG
        dwg.save()
