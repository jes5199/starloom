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
        Planet.MERCURY: "#AAAA00", # Yellow for Mercury
        # Default to black for other planets
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
                date_str = dt.strftime("%B %-d")
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
            date_str = dt.strftime("%B %-d")
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

        image_rotation = retrograde_period.sun_aspect_longitude  # Use planet's position at the time of retrograde

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
        
        # Get exact Sun position at sun aspect date
        sun_aspect_position = sun_ephemeris.get_planet_positions(
            "SUN", 
            TimeSpec.from_dates([sun_aspect_jd])
        )[sun_aspect_jd]
        
        sun_aspect_longitude = sun_aspect_position.get(Quantity.ECLIPTIC_LONGITUDE, 0.0)
        sun_aspect_distance = 1.0  # Sun is at 1 AU from Earth
        
        sun_aspect_x, sun_aspect_y = self._normalize_coordinates(
            sun_aspect_longitude, 0, image_rotation
        )

        # Add 90 degrees to rotate counterclockwise
        image_rotation = (image_rotation + 90.0) % 360

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
                            longitude, distance, image_rotation
                        )
                        min_x = min(min_x, x)
                        max_x = max(max_x, x)
                        min_y = min(min_y, y)
                        max_y = max(max_y, y)

        # Calculate the center and radius of the astronomical elements
        center_x = sun_aspect_x
        center_y = (min_y + max_y) / 2
        radius = (max(max_x - min_x, max_y - min_y) / 2) * 1.5

        # Define a viewbox with dimensions (100x110 units - 10% taller)
        viewbox_width = 100
        viewbox_height = 110
        viewbox_min_x = 0
        viewbox_min_y = 0
        # Calculate scaling factor to fit astronomical elements in viewbox
        # Leave 10% padding around the elements
        scale = (viewbox_width * 0.9) / (radius * 2)

        # Create SVG drawing with rectangular viewbox
        dwg = svgwrite.Drawing(
            output_path,
            size=(self.width, self.height),
            viewBox=f"{viewbox_min_x} {viewbox_min_y} {viewbox_width} {viewbox_height}",
            style="background-color: transparent; font-family: Helvetica, Arial, sans-serif;",
        )

        # Create clip path for rounded rectangle
        clip_path = dwg.defs.add(dwg.clipPath(id='rounded-rect'))
        clip_path.add(
            dwg.rect(
                insert=(viewbox_min_x + 5, viewbox_min_y + 5),
                size=(viewbox_width - 10, viewbox_height - 10),
                rx=5,
                ry=5,
            )
        )

        # Add rounded rectangle background
        corner_radius = 5
        
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
                insert=(viewbox_min_x + 5, viewbox_min_y + 5),
                size=(viewbox_width - 10, viewbox_height - 10),
                rx=corner_radius,
                ry=corner_radius,
                fill=bg_gradient.get_paint_server(),
                stroke="none",
            )
        )

        # Create a group for all elements that should be clipped
        clip_group = dwg.g(clip_path='url(#rounded-rect)')

        # Helper function to transform astronomical coordinates to viewbox coordinates
        def transform_coordinates(x: float, y: float) -> Tuple[float, float]:
            # Translate to origin
            x = x - center_x
            y = y - center_y
            # Scale
            x = x * scale
            y = y * scale
            # Translate to viewbox center - note using viewbox_width for x center
            x = x + viewbox_width / 2
            y = y + viewbox_height / 2 - 5  # Shift up by 5 units to make room for bottom text
            return x, y

        # Define gradients for sun fade up/down effects
        gradient_down = dwg.defs.add(dwg.linearGradient(id='sun-fade-down'))
        gradient_down.add_stop_color(offset=0, color='#FFD700', opacity=1)
        gradient_down.add_stop_color(offset=1, color='#FFD700', opacity=0)
        gradient_down['x1'] = '0%'
        gradient_down['y1'] = '0%'
        gradient_down['x2'] = '0%'
        gradient_down['y2'] = '100%'

        gradient_up = dwg.defs.add(dwg.linearGradient(id='sun-fade-up'))
        gradient_up.add_stop_color(offset=0, color='#FFD700', opacity=0)
        gradient_up.add_stop_color(offset=1, color='#FFD700', opacity=1)
        gradient_up['x1'] = '0%'
        gradient_up['y1'] = '0%'
        gradient_up['x2'] = '0%'
        gradient_up['y2'] = '100%'

        # Draw line at station retrograde longitude
        # Where is Earth's center, in final coords?
        earth_x, earth_y = transform_coordinates(*self._normalize_coordinates(0.0, 0.0, image_rotation))
        # Where is the station retrograde longitude at 1 AU, in final coords?
        sx, sy = transform_coordinates(*self._normalize_coordinates(
            retrograde_period.station_retrograde_longitude,
            10,
            image_rotation
        ))
        # Draw solid line from Earth center to station retrograde point
        clip_group.add(
            dwg.line(
                start=(earth_x, earth_y),
                end=(sx, sy),
                stroke="#000000",
                stroke_width=0.5,  # Adjusted for new scale
                opacity=0.6
            )
        )

        # Draw line at station direct longitude
        # Where is the station direct longitude at 1 AU, in final coords?
        dx, dy = transform_coordinates(*self._normalize_coordinates(
            station_direct_longitude,
            10,
            image_rotation
        ))
        # Draw solid line from Earth center to station direct point
        clip_group.add(
            dwg.line(
                start=(earth_x, earth_y),
                end=(dx, dy),
                stroke="#000000",
                stroke_width=0.5,  # Adjusted for new scale
                opacity=0.6
            )
        )

        # Create a path for the triangle between Earth and the two endpoints
        path_data = []
        path_data.append(f"M {earth_x} {earth_y}")  # Start at Earth
        path_data.append(f"L {sx} {sy}")  # Line to station retrograde
        path_data.append(f"L {dx} {dy}")  # Line to station direct
        path_data.append("Z")  # Close the path back to Earth
        
        # Add the shaded triangle
        clip_group.add(
            dwg.path(
                d=" ".join(path_data),
                fill="#000000",
                fill_opacity=0.1,
                stroke="none"
            )
        )

        # Add station retrograde label
        station_retrograde_date = retrograde_period.station_retrograde_date
        station_retrograde_x, station_retrograde_y = transform_coordinates(*self._normalize_coordinates(
            station_retrograde_longitude,
            station_retrograde_distance,
            image_rotation
        ))

        text_x = station_retrograde_x + 2
        text_y = station_retrograde_y

        text_elem = dwg.text(
            text="",
            insert=(text_x, text_y),
            fill="#FFFFFF",
            font_size="3",  # Adjusted for new scale
            dominant_baseline="hanging"
        )

        text_elem.add(dwg.tspan("Stations Retrograde", x=[text_x], dy=['0em']))
        text_elem.add(dwg.tspan(station_retrograde_date.strftime("%B %-d"), x=[text_x], dy=['1em']))
        text_elem.add(dwg.tspan(station_retrograde_date.strftime('%H:%M UTC'), x=[text_x], dy=['1em']))

        clip_group.add(text_elem)

        # Add station direct label
        station_direct_date = retrograde_period.station_direct_date
        station_direct_x, station_direct_y = transform_coordinates(*self._normalize_coordinates(
            station_direct_longitude,
            station_direct_distance,
            image_rotation
        ))

        text_x = station_direct_x - 2
        text_y = station_direct_y

        text_elem = dwg.text(
            text="",
            insert=(text_x, text_y),
            fill="#FFFFFF",
            font_size="3",  # Adjusted for new scale
            dominant_baseline="hanging",
            text_anchor="end"
        )

        text_elem.add(dwg.tspan("Stations Direct", x=[text_x], dy=['0em']))
        text_elem.add(dwg.tspan(station_direct_date.strftime("%B %-d"), x=[text_x], dy=['1em']))
        text_elem.add(dwg.tspan(station_direct_date.strftime('%H:%M UTC'), x=[text_x], dy=['1em']))

        clip_group.add(text_elem)

        # Add shadow period labels
        # Shadow start label
        shadow_start_date = retrograde_period.pre_shadow_start_date
        shadow_start_x, shadow_start_y = transform_coordinates(*self._normalize_coordinates(
            station_direct_longitude,
            shadow_positions[shadow_start_date.timestamp() / 86400 + 2440587.5].get(Quantity.DELTA, 0.0),
            image_rotation
        ))

        text_x = shadow_start_x - 1
        text_y = shadow_start_y

        text_elem = dwg.text(
            text="",
            insert=(text_x, text_y),
            fill="#FFFFFF",
            font_size="3",  # Adjusted for new scale
            dominant_baseline="hanging",
            text_anchor="end"
        )

        text_elem.add(dwg.tspan("Shadow begins", x=[text_x], dy=['0em']))
        text_elem.add(dwg.tspan(shadow_start_date.strftime("%B %-d"), x=[text_x], dy=['1em']))
        text_elem.add(dwg.tspan(shadow_start_date.strftime('%H:%M UTC'), x=[text_x], dy=['1em']))

        clip_group.add(text_elem)

        # Shadow end label
        shadow_end_date = retrograde_period.post_shadow_end_date
        shadow_end_x, shadow_end_y = transform_coordinates(*self._normalize_coordinates(
            station_retrograde_longitude,
            shadow_positions[shadow_end_date.timestamp() / 86400 + 2440587.5].get(Quantity.DELTA, 0.0),
            image_rotation
        ))

        text_x = shadow_end_x + 1
        text_y = shadow_end_y

        text_elem = dwg.text(
            text="",
            insert=(text_x, text_y),
            fill="#FFFFFF",
            font_size="3",  # Adjusted for new scale
            dominant_baseline="hanging",
        )

        text_elem.add(dwg.tspan("Shadow ends", x=[text_x], dy=['0em']))
        text_elem.add(dwg.tspan(shadow_end_date.strftime("%B %-d"), x=[text_x], dy=['1em']))
        text_elem.add(dwg.tspan(shadow_end_date.strftime('%H:%M UTC'), x=[text_x], dy=['1em']))

        clip_group.add(text_elem)

        # Sun aspect line from earth center to planet (solid yellow)
        # Get the exact planet position at sun aspect time
        sun_aspect_planet_position = planet_ephemeris.get_planet_positions(
            planet.name,
            TimeSpec.from_dates([sun_aspect_jd])
        )[sun_aspect_jd]
        
        planet_longitude = sun_aspect_planet_position.get(Quantity.ECLIPTIC_LONGITUDE, 0.0)
        planet_distance = sun_aspect_planet_position.get(Quantity.DELTA, 0.0)
        
        # Transform to viewbox coordinates
        planet_x, planet_y = transform_coordinates(*self._normalize_coordinates(
            planet_longitude,
            planet_distance,
            image_rotation
        ))

        sun_x, sun_y = transform_coordinates(*self._normalize_coordinates(
            retrograde_period.sun_aspect_longitude,
            1,
            image_rotation
        ))

        # Calculate point beyond planet for gradient using a fixed extension in viewbox coordinates
        # Create a vector from earth to planet
        vector_x = planet_x - earth_x
        vector_y = planet_y - earth_y
        
        # Normalize the vector
        vector_length = math.sqrt(vector_x**2 + vector_y**2)
        if vector_length > 0:
            norm_x = vector_x / vector_length
            norm_y = vector_y / vector_length
            
            # Use a small fixed extension (5 viewbox units)
            extension_length = 5
            
            # Add a 1% clockwise rotation to the normalized vector
            # For a clockwise rotation of θ degrees:
            # x' = x*cos(θ) + y*sin(θ)
            # y' = -x*sin(θ) + y*cos(θ)
            theta = math.radians(1)  # 1 degree clockwise
            rotated_norm_x = norm_x * math.cos(theta) + norm_y * math.sin(theta)
            rotated_norm_y = -norm_x * math.sin(theta) + norm_y * math.cos(theta)
            
            # Calculate points for the gradient extensions in both directions
            # Extension beyond planet (away from Earth)
            dx_away = planet_x + rotated_norm_x * extension_length
            dy_away = planet_y + rotated_norm_y * extension_length
            
            # Extension toward Earth
            dx_toward = planet_x - rotated_norm_x * extension_length
            dy_toward = planet_y - rotated_norm_y * extension_length
        else:
            # Fallback if vector has zero length
            dx_away = planet_x
            dy_away = planet_y - 5  # Default extension upward
            dx_toward = planet_x
            dy_toward = planet_y + 5  # Default extension downward

        # Draw gradient extension toward Earth
        clip_group.add(
            dwg.line(
                start=(planet_x, planet_y),
                end=(dx_toward, dy_toward),
                stroke='url(#sun-fade-down)',
                stroke_width=0.5,  # Adjusted for new scale
                opacity=1.0
            )
        )

        # Draw gradient extension away from Earth
        clip_group.add(
            dwg.line(
                start=(planet_x, planet_y),
                end=(dx_away, dy_away),
                stroke='url(#sun-fade-up)',
                stroke_width=0.5,  # Adjusted for new scale
                opacity=1.0
            )
        )

        # Calculate zodiac wheel distance in viewbox coordinates - position it a short distance from top of viewbox
        # Instead of using astronomical distance, we'll set it as a fixed radius in viewbox coordinates
        viewbox_padding = 6  # Distance from top of viewbox (in viewbox units)
        # Calculate radius from Earth to near the top of the viewbox
        # Since Earth is outside the viewbox at the bottom, we need a large radius
        # Earth's y position is higher than viewbox height (since it's outside), so we use earth_y value directly
        zodiac_radius = earth_y - viewbox_padding  # This will reach almost to the top of the viewbox

        if planet.name.lower() in ["venus", "mercury"]:
            # Calculate the point where the zodiac circle intersects the line from Earth through the Sun
            # First, get the angle of the sun aspect
            sun_aspect_angle_rad = math.radians(retrograde_period.sun_aspect_longitude - image_rotation)
            
            # Then find the point on the zodiac circle at that angle
            wheel_x = earth_x + zodiac_radius * math.cos(sun_aspect_angle_rad)
            wheel_y = earth_y + zodiac_radius * math.sin(sun_aspect_angle_rad)

            # Draw the solid line from sun to wheel
            clip_group.add(
                dwg.line(
                    start=(sun_x, sun_y),
                    end=(wheel_x, wheel_y),
                    stroke='#FFD700',
                    stroke_width=0.5,  # Adjusted for new scale
                    opacity=1.0
                )
            )

            # Calculate points beyond the solid line endpoints for gradients
            # Vector from sun to wheel
            vec_x = wheel_x - sun_x
            vec_y = wheel_y - sun_y
            
            # Normalize vector
            length = math.sqrt(vec_x**2 + vec_y**2)
            norm_vec_x = vec_x / length
            norm_vec_y = vec_y / length
            
            # Add a 1% clockwise rotation to the normalized vector
            theta = math.radians(1)  # 1 degree clockwise
            rotated_norm_x = norm_vec_x * math.cos(theta) + norm_vec_y * math.sin(theta)
            rotated_norm_y = -norm_vec_x * math.sin(theta) + norm_vec_y * math.cos(theta)
            
            # Calculate extension distance (20% of the line length)
            ext_distance = length * 0.2
            
            # Calculate extended points beyond the wheel
            ext_wheel_x = wheel_x + rotated_norm_x * ext_distance
            ext_wheel_y = wheel_y + rotated_norm_y * ext_distance
            
            # Calculate extended points beyond the sun (in opposite direction)
            ext_sun_x = sun_x - rotated_norm_x * ext_distance
            ext_sun_y = sun_y - rotated_norm_y * ext_distance

            # Choose gradient directions based on relative positions
            # Calculate distances from Earth to wheel and from Earth to Sun
            wheel_distance_from_earth = math.sqrt((wheel_x - earth_x)**2 + (wheel_y - earth_y)**2)
            sun_distance_from_earth = math.sqrt((sun_x - earth_x)**2 + (sun_y - earth_y)**2)
            
            # If wheel is inside Sun orbit (wheel is closer to Earth than Sun)
            if wheel_distance_from_earth < sun_distance_from_earth:
                wheel_gradient = 'url(#sun-fade-down)'  # Fade gradient out from wheel
                sun_gradient = 'url(#sun-fade-up)'      # Fade gradient in towards sun
            else:
                # Default case: wheel is outside Sun orbit
                wheel_gradient = 'url(#sun-fade-up)'    # Fade gradient in towards wheel
                sun_gradient = 'url(#sun-fade-down)'    # Fade gradient out from sun

            # Draw outward fade from wheel
            clip_group.add(
                dwg.line(
                    start=(wheel_x, wheel_y),  # Start from wheel
                    end=(ext_wheel_x, ext_wheel_y),  # Extend beyond wheel
                    stroke=wheel_gradient,
                    stroke_width=0.5,  # Adjusted for new scale
                    opacity=1.0
                )
            )

            # Draw outward fade from sun
            clip_group.add(
                dwg.line(
                    start=(sun_x, sun_y),  # Start from sun
                    end=(ext_sun_x, ext_sun_y),  # Extend beyond sun
                    stroke=sun_gradient,
                    stroke_width=0.5,  # Adjusted for new scale
                    opacity=1.0
                )
            )

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

        if planet == Planet.MARS:
            zodiac_opacity = 0.5
            zodiac_color = "#FFD700"
        else:
            zodiac_opacity = 0.6
            zodiac_color = "#A52A2A"

        # Draw zodiac circle centered at Earth's position
        clip_group.add(
            dwg.circle(
                center=(earth_x, earth_y),
                r=zodiac_radius,
                stroke=zodiac_color,
                stroke_width=0.5,
                opacity=zodiac_opacity,
                fill="none"
            )
        )

        # Draw 1AU circle for Mars
        if planet == Planet.MARS:
            # Calculate radius for 1AU in viewbox coordinates 
            earth_orbit_radius = self._normalize_distance(1.0) * scale
            clip_group.add(
                dwg.circle(
                    center=(earth_x, earth_y),
                    r=earth_orbit_radius,
                    stroke=zodiac_color,  # Yellow
                    stroke_width=0.5,
                    #stroke_dasharray="1,1",  # Dashed line
                    opacity=0.3,
                    fill="none"
                )
            )

        for ecliptic_degrees in range(0, 360, 1):
            # Calculate angle in radians relative to sun aspect
            angle_rad = math.radians(ecliptic_degrees - image_rotation)
            
            # Calculate tick length in viewbox coordinates
            if ecliptic_degrees % 30 == 0:
                # Zodiac sign boundaries - full length
                inner_radius = 0  # From center of Earth
            elif ecliptic_degrees % 10 == 0:
                # Decan boundaries - longer tick
                inner_radius = zodiac_radius - 5
            else:
                # Regular degree ticks - shortest
                inner_radius = zodiac_radius - 2.5

            # Calculate tick endpoints in viewbox coordinates
            inner_x = earth_x + inner_radius * math.cos(angle_rad)
            inner_y = earth_y + inner_radius * math.sin(angle_rad)
            outer_x = earth_x + zodiac_radius * math.cos(angle_rad)
            outer_y = earth_y + zodiac_radius * math.sin(angle_rad)

            # Draw tick mark
            clip_group.add(
                dwg.line(
                    start=(inner_x, inner_y),
                    end=(outer_x, outer_y),
                    stroke=zodiac_color,
                    stroke_width=0.5,
                    opacity=zodiac_opacity
                )
            )

            # Add zodiac sign names at sign boundaries
            if ecliptic_degrees % 30 == 0 and ecliptic_degrees in zodiac_signs:
                # Calculate text position slightly inward from the line
                text_radius = zodiac_radius - 2.5 
                
                # Calculate text positions on either side of the line using small angle offsets
                # Use 0.25 degrees offset for text positioning
                text_angle_offset = 0.25
                
                # Current sign text (slightly clockwise)
                text_angle_rad = math.radians(ecliptic_degrees + text_angle_offset - image_rotation)
                text_x = earth_x + text_radius * math.cos(text_angle_rad)
                text_y = earth_y + text_radius * math.sin(text_angle_rad)
                
                # Calculate text rotation (angle in degrees)
                text_angle = ecliptic_degrees - image_rotation + 180
                
                # Add text with rotation
                clip_group.add(
                    dwg.text(
                        zodiac_signs[ecliptic_degrees],
                        insert=(text_x, text_y),
                        fill=zodiac_color,
                        font_size="4",
                        opacity=zodiac_opacity,
                        transform=f"rotate({text_angle}, {text_x}, {text_y})",
                        text_anchor="start",
                        dominant_baseline="alphabetic"
                    )
                )

                # Previous sign text (slightly counterclockwise)
                text_angle_rad = math.radians(ecliptic_degrees - text_angle_offset - image_rotation)
                text_x = earth_x + text_radius * math.cos(text_angle_rad)
                text_y = earth_y + text_radius * math.sin(text_angle_rad)
                
                clip_group.add(
                    dwg.text(
                        zodiac_signs[(ecliptic_degrees - 30) % 360],
                        insert=(text_x, text_y),
                        fill=zodiac_color,
                        font_size="4",
                        opacity=zodiac_opacity,
                        transform=f"rotate({text_angle}, {text_x}, {text_y})",
                        text_anchor="start",
                        dominant_baseline="hanging"
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

            x, y = transform_coordinates(*self._normalize_coordinates(
                longitude, distance, image_rotation
            ))

            # Draw dot based on period
            if not (shadow_start_jd <= jd <= shadow_end_jd):
                # Pre/post period
                clip_group.add(
                    dwg.circle(
                        center=(x, y),
                        r=0.75,  # Adjusted for new scale
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
                            r=0.75,  # Adjusted for new scale
                            fill="#00DDDD",  # Cyan (bright, high contrast)
                            stroke="#FFFFFF",
                            stroke_width=0.15,  # Adjusted for new scale
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
                            r=0.75,  # Adjusted for new scale
                            fill="#3399FF",  # Bright blue (high contrast)
                            stroke="#FFFFFF",
                            stroke_width=0.15,  # Adjusted for new scale
                            opacity=0.9,
                        )
                    )
                else:
                    # Main retrograde period
                    clip_group.add(
                        dwg.circle(
                            center=(x, y),
                            r=0.75,  # Adjusted for new scale
                            fill="#FFFFFF",
                            stroke="none",
                            opacity=0.8,
                        )
                    )

        # Draw Sun positions
        if planet.name.lower() in ["venus", "mercury"]:
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

                x, y = transform_coordinates(*self._normalize_coordinates(
                    longitude, distance, image_rotation
                ))

                # Draw Sun dot
                clip_group.add(
                    dwg.circle(
                        center=(x, y), r=1.0, fill="#FFD700", stroke="none", opacity=0.6  # Adjusted for new scale
                    )
                )

        # Add the clipped group to the drawing
        dwg.add(clip_group)

        # Now add the text labels on top of everything
        # Station retrograde label
        text_elem = dwg.text(
            text="",
            insert=(station_retrograde_x + 2, station_retrograde_y),
            fill="#FFFFFF",
            font_size="3",  # Adjusted for new scale
            dominant_baseline="hanging"
        )

        text_elem.add(dwg.tspan("Stations Retrograde", x=[station_retrograde_x + 2], dy=['0em']))
        text_elem.add(dwg.tspan(station_retrograde_date.strftime("%B %-d"), x=[station_retrograde_x + 2], dy=['1em']))
        text_elem.add(dwg.tspan(station_retrograde_date.strftime('%H:%M UTC'), x=[station_retrograde_x + 2], dy=['1em']))

        dwg.add(text_elem)

        # Station direct label
        text_elem = dwg.text(
            text="",
            insert=(station_direct_x - 2, station_direct_y),
            fill="#FFFFFF",
            font_size="3",  # Adjusted for new scale
            dominant_baseline="hanging",
            text_anchor="end"
        )

        text_elem.add(dwg.tspan("Stations Direct", x=[station_direct_x - 2], dy=['0em']))
        text_elem.add(dwg.tspan(station_direct_date.strftime("%B %-d"), x=[station_direct_x - 2], dy=['1em']))
        text_elem.add(dwg.tspan(station_direct_date.strftime('%H:%M UTC'), x=[station_direct_x - 2], dy=['1em']))

        dwg.add(text_elem)

        # Shadow start label
        text_elem = dwg.text(
            text="",
            insert=(shadow_start_x - 1, shadow_start_y),
            fill="#FFFFFF",
            font_size="3",  # Adjusted for new scale
            dominant_baseline="hanging",
            text_anchor="end"
        )

        text_elem.add(dwg.tspan("Shadow begins", x=[shadow_start_x - 1], dy=['0em']))
        text_elem.add(dwg.tspan(shadow_start_date.strftime("%B %-d"), x=[shadow_start_x - 1], dy=['1em']))
        text_elem.add(dwg.tspan(shadow_start_date.strftime('%H:%M UTC'), x=[shadow_start_x - 1], dy=['1em']))

        dwg.add(text_elem)

        # Shadow end label
        text_elem = dwg.text(
            text="",
            insert=(shadow_end_x + 1, shadow_end_y),
            fill="#FFFFFF",
            font_size="3",  # Adjusted for new scale
            dominant_baseline="hanging",
        )

        text_elem.add(dwg.tspan("Shadow ends", x=[shadow_end_x + 1], dy=['0em']))
        text_elem.add(dwg.tspan(shadow_end_date.strftime("%B %-d"), x=[shadow_end_x + 1], dy=['1em']))
        text_elem.add(dwg.tspan(shadow_end_date.strftime('%H:%M UTC'), x=[shadow_end_x + 1], dy=['1em']))

        dwg.add(text_elem)

        # Add date labels for key points (outside the clip path so they're always visible)
        key_dates = [
            (retrograde_period.station_retrograde_date, "Station Retrograde"),
            (retrograde_period.station_direct_date, "Station Direct"),
            (retrograde_period.sun_aspect_date, 
             "Opposition" if planet not in [Planet.MERCURY, Planet.VENUS] else "Sun Aspect"),
        ]

        for date, label in key_dates:
            jd = date.timestamp() / 86400 + 2440587.5
            if jd in positions:
                pos_data = positions[jd]
                longitude = pos_data.get(Quantity.ECLIPTIC_LONGITUDE, 0.0)
                distance = pos_data.get(Quantity.DELTA, 0.0)
                x, y = transform_coordinates(*self._normalize_coordinates(
                    longitude, distance, image_rotation
                ))
                dwg.add(
                    dwg.text(
                        f"{label}\n{date.strftime('%B %-d')}",
                        insert=(x + 4, y),  # Adjusted for new scale
                        fill="#666666",
                        font_size="3",  # Adjusted for new scale
                        font_family="Helvetica, Arial, sans-serif"
                    )
                )

        # Determine the zodiac signs where the retrograde occurs
        # Get the zodiac sign for station retrograde and direct points
        def get_zodiac_sign(longitude):
            for start_deg, sign in zodiac_signs.items():
                end_deg = (start_deg + 30) % 360
                if is_in_angular_range(longitude, start_deg, end_deg):
                    return sign
            return "Unknown"
        
        station_retro_sign = get_zodiac_sign(station_retrograde_longitude)
        station_direct_sign = get_zodiac_sign(station_direct_longitude)
        
        # Format the month range
        start_month = retrograde_period.station_retrograde_date.strftime("%B")
        end_month = retrograde_period.station_direct_date.strftime("%B")
        start_year = retrograde_period.station_retrograde_date.year
        end_year = retrograde_period.station_direct_date.year
        
        if start_year == end_year:
            if start_month == end_month:
                month_range = f"{start_month} {start_year}"
            else:
                month_range = f"{start_month}-{end_month} {start_year}"
        else:
            month_range = f"{start_month} {start_year} - {end_month} {end_year}"
            
        # Format the Cazimi/Opposition information
        aspect_date = retrograde_period.sun_aspect_date.strftime("%B %-d")
        aspect_time = retrograde_period.sun_aspect_date.strftime("%-H:%M UTC")
        aspect_label = "Cazimi" if planet in [Planet.MERCURY, Planet.VENUS] else "Solar Opposition"
        
        # Calculate center for text alignment
        center_x = viewbox_width / 2
        
        # Position the text near the bottom of the rectangle
        # The bottom of the rectangle is at viewbox_height - 5 = 105
        bottom_y = viewbox_height - 12  # 7 units from the bottom edge of the rectangle
        
        # Calculate total height of text block (4 lines with 1.5em spacing = ~7.5em total)
        text_block_height = 7.5
        
        # Calculate exact positions relative to the rounded rectangle
        rectangle_bottom = viewbox_height - 5  # Bottom edge of the rounded rectangle
        bottom_padding = 0.5  # Fixed padding from the bottom edge
        
        # Calculate line heights and spacing
        cazimi_line_height = 2.5  # Font size of cazimi text
        heading_line_height = 4.5  # Font size of heading
        subheading_line_height = 3.5  # Font size of subheading
        url_line_height = 2.5  # Font size of URL text
        
        # Calculate spacings
        first_spacing = 1.25  # Space between cazimi and heading
        second_spacing = 1.5  # Space between heading and subheading
        third_spacing = 1.75  # Space between subheading and URL
        
        # Calculate total text block height
        total_height = cazimi_line_height + heading_line_height + subheading_line_height + url_line_height + first_spacing + second_spacing + third_spacing
        
        # Calculate the y position for the first line so that the bottom of the text block
        # is exactly at rectangle_bottom - bottom_padding
        first_line_y = rectangle_bottom - bottom_padding - total_height
        
        # Create text element for the bottom information
        bottom_text = dwg.text("", insert=(center_x, first_line_y), fill="#FFFFFF", font_size="3", text_anchor="middle")
        
        # First line - Cazimi/Opposition info (smaller)
        bottom_text.add(dwg.tspan(f"{aspect_label} {aspect_date} {aspect_time}", 
                                 x=[center_x], dy=['0em'], font_size="2.5"))
        
        # Second line - Planet Retrograde heading (larger)
        bottom_text.add(dwg.tspan(f"{planet.name.capitalize()} Retrograde in {station_retro_sign}" + 
                                 (f" & {station_direct_sign}" if station_retro_sign != station_direct_sign else ""), 
                                 x=[center_x], dy=[f'{first_spacing}em'], font_size=f"{heading_line_height}", font_weight="bold"))
        
        # Third line - Month-year subheading
        bottom_text.add(dwg.tspan(month_range, x=[center_x], dy=['1.5em'], font_size=f"{subheading_line_height}"))
        
        # Fourth line - retrograde.observer (blue, like a hyperlink, fixed width font)
        url_text = dwg.tspan("retrograde.observer", x=[center_x], dy=[f'{third_spacing}em'], font_size="2.5", font_family="monospace", font_weight="bold")
        url_text['fill'] = "#5599FF"  # Blue color
        url_text['style'] = "text-shadow: 1px 1px 2px #000000;"  # Add drop shadow
        bottom_text.add(url_text)
        
        # Add the text to the drawing
        dwg.add(bottom_text)

        # Save the SVG
        dwg.save()
