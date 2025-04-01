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
        Planet.VENUS: "#2e6327",  # Green for Venus
        Planet.MERCURY: "#e18601", # Yellow for Mercury
        Planet.MARS: "#721209",   # Dark red for Mars
    }

    PLANET_BACKGROUND_COLORS_2 = {
        Planet.VENUS: "#0c4516",
        Planet.MERCURY: "#db8001", # Yellow for Mercury
        Planet.MARS: "#560e08",
    }

    def __init__(
        self,
        width: int = 545,
        height: int = 600,
        margin: int = 50,
        planet_color: str = "#FFFFFF",  # White
        background_color: str = None,  # Will be set based on planet
        display_timezone: str = "UTC",  # Timezone for displaying dates and times
    ):
        """Initialize the painter.

        Args:
            width: SVG canvas width in pixels
            height: SVG canvas height in pixels
            margin: Margin around the plot in pixels
            planet_color: Color for the planet dots
            background_color: Background color of the canvas (if None, will use planet-specific color)
            display_timezone: Timezone for displaying dates and times (e.g. 'America/New_York')
        """
        self.width = width
        self.height = height
        self.margin = margin
        self.planet_color = planet_color
        self.background_color = background_color
        self.display_timezone = display_timezone
        self.plot_width = width - 2 * margin
        self.plot_height = height - 2 * margin

    def _format_datetime(self, dt: datetime) -> Tuple[str, str]:
        """Format a datetime object for display in the specified timezone.
        
        Args:
            dt: UTC datetime to format
            
        Returns:
            Tuple of (date_str, time_str) in the specified timezone
        """
        try:
            from zoneinfo import ZoneInfo
            tz = ZoneInfo(self.display_timezone)
            local_dt = dt.astimezone(tz)
            
            # Format date consistently
            date_str = local_dt.strftime("%B %-d")
            
            # Format time based on timezone
            if self.display_timezone == "UTC":
                # UTC uses 24-hour format with leading zeros
                time_str = local_dt.strftime("%H:%M UTC")
            else:
                # Non-UTC uses 12-hour format with AM/PM and no leading zeros
                time_str = local_dt.strftime("%-I:%M%p %Z")
                # Convert only the am/pm part to lowercase
                time_str = time_str.replace("AM", "am").replace("PM", "pm")
            
            return date_str, time_str
        except Exception:
            # Fallback to UTC if timezone conversion fails
            return dt.strftime("%B %-d"), dt.strftime("%H:%M UTC")

    def _get_background_color(self, planet: Planet) -> str:
        """Get the background color for a specific planet."""
        if self.background_color is not None:
            return self.background_color
        return self.PLANET_BACKGROUND_COLORS.get(planet, "#000000")

    def _get_background_color_2(self, planet: Planet) -> str:
        """Get the background color for a specific planet."""
        color = self.PLANET_BACKGROUND_COLORS_2.get(planet, None)

        if color is not None:
            return color
        
        color = self._get_background_color(planet)
        # Create a darker version of the base color by reducing RGB values by 20%
        darker_color = f"#{int(int(color[1:3], 16) * 0.8):02x}{int(int(color[3:5], 16) * 0.8):02x}{int(int(color[5:7], 16) * 0.8):02x}"
        return darker_color

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

    def _get_closest_position(self, positions: dict, target_jd: float, tolerance: float = 0.001) -> dict:
        """Get position data for the closest Julian date in the dictionary.
        
        Args:
            positions: Dictionary mapping Julian dates to position data
            target_jd: Target Julian date to find
            tolerance: Maximum difference allowed between target and closest date
            
        Returns:
            Position data for the closest Julian date
            
        Raises:
            KeyError: If no date is within tolerance of the target
        """
        # Try exact match first
        try:
            return positions[target_jd]
        except KeyError:
            # Find closest key
            if not positions:
                raise KeyError(f"No positions available for JD {target_jd}")
            
            closest_jd = min(positions.keys(), key=lambda jd: abs(jd - target_jd))
            
            # Check if the closest is within tolerance
            if abs(closest_jd - target_jd) <= tolerance:
                return positions[closest_jd]
            
            raise KeyError(f"No position within {tolerance} days of JD {target_jd}. Closest is {abs(closest_jd - target_jd):.6f} days away.")

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
                date_str, time_str = self._format_datetime(dt)
                dwg.add(
                    dwg.text(
                        f"{date_str}\n{time_str}", insert=(x + 8, y), fill="#666666", font_size="12px", font_family="Helvetica, Arial, sans-serif"
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
            date_str, time_str = self._format_datetime(dt)
            dwg.add(
                dwg.text(
                    f"{date_str}\n{time_str}",
                    insert=(x + 8, y),
                    fill="#666666",
                    font_size="12px",
                    font_family="Helvetica, Arial, sans-serif"
                )
            )

        # Save the SVG
        dwg.save()

    def _generate_svg_xml(self, content: str) -> str:
        """Generate SVG XML with proper header and namespace."""
        return f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{self.width}"
     height="{self.height}"
     viewBox="0 0 100 110"
     style="background-color: transparent; font-family: Helvetica, Arial, sans-serif;">
{content}
</svg>'''

    def draw_retrograde(
        self,
        positions: dict[float, dict[str, float]],
        planet: Planet,
        output_path: str,
        target_date: float,
    ) -> None:
        """Draw planet positions with retrograde motion highlighted."""
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
        sun_aspect_distance = sun_aspect_position.get(Quantity.DELTA, 0.0)  # Sun is at approx 1 AU from Earth but it moves
        
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

        station_jd_retrograde = retrograde_period.station_retrograde_date.timestamp() / 86400 + 2440587.5
        station_jd_direct = retrograde_period.station_direct_date.timestamp() / 86400 + 2440587.5
        
        station_positions = planet_ephemeris.get_planet_positions(
            planet.name,
            TimeSpec.from_dates([station_jd_retrograde, station_jd_direct])
        )

        # Use helper method to get closest positions
        station_retrograde_position = self._get_closest_position(station_positions, station_jd_retrograde)
        station_direct_position = self._get_closest_position(station_positions, station_jd_direct)
        
        station_retrograde_longitude = station_retrograde_position.get(Quantity.ECLIPTIC_LONGITUDE, 0.0)
        station_direct_longitude = station_direct_position.get(Quantity.ECLIPTIC_LONGITUDE, 0.0)
        station_retrograde_distance = station_retrograde_position.get(Quantity.DELTA, 0.0)
        station_direct_distance = station_direct_position.get(Quantity.DELTA, 0.0)

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

        # Instead of using svgwrite, we'll build XML strings
        svg_content = []
        
        # Add definitions section
        defs = []
        defs.append('  <defs>')
        defs.append('    <filter id="url-shadow">')
        defs.append('      <feGaussianBlur in="SourceAlpha" stdDeviation="0.1"/>')
        defs.append('      <feOffset dx="0.15" dy="0.15"/>')
        defs.append('      <feFlood flood-color="black" flood-opacity="0.5"/>')
        defs.append('      <feComposite in="SourceAlpha" operator="in"/>')
        defs.append('      <feMerge>')
        defs.append('        <feMergeNode in="SourceGraphic"/>')
        defs.append('        <feMergeNode in="SourceAlpha"/>')
        defs.append('      </feMerge>')
        defs.append('    </filter>')
        
        # Add gradient definitions
        # Background gradient
        base_color = self._get_background_color(planet)
        darker_color = self._get_background_color_2(planet)
        defs.append('    <linearGradient id="bg-gradient" x1="0%" y1="0%" x2="0%" y2="100%">')
        defs.append(f'      <stop offset="0%" style="stop-color:{base_color};stop-opacity:1"/>')
        defs.append(f'      <stop offset="100%" style="stop-color:{darker_color};stop-opacity:1"/>')
        defs.append('    </linearGradient>')

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
        
        # background image
        # Define helper function to get zodiac sign
        def get_zodiac_sign(longitude):
            for start_deg, sign in zodiac_signs.items():
                end_deg = (start_deg + 30) % 360
                if is_in_angular_range(longitude, start_deg, end_deg):
                    return sign
            return "Unknown"
            
        # Get zodiac signs for the retrograde
        station_retro_sign = get_zodiac_sign(station_retrograde_longitude)
        station_direct_sign = get_zodiac_sign(station_direct_longitude)
        
        # Create bg filename based on zodiac signs
        if station_retro_sign == station_direct_sign:
            bg_filename = f"./slop/{station_retro_sign.lower()}.png"
        else:
            bg_filename = f"./slop/{station_retro_sign.lower()}-{station_direct_sign.lower()}.png"
            
        # defs.append('    <pattern id="bg-image" patternUnits="userSpaceOnUse" width="90" height="100" x="5" y="5">')
        # defs.append(f'      <image href="{bg_filename}" width="90" height="100" preserveAspectRatio="xMidYMid slice"/>')
        # defs.append('    </pattern>')
        # Sun fade gradients
        defs.append('    <linearGradient id="sun-fade-down" x1="0%" y1="0%" x2="0%" y2="100%">')
        defs.append('      <stop offset="0%" style="stop-color:#FFD700;stop-opacity:1"/>')
        defs.append('      <stop offset="100%" style="stop-color:#FFD700;stop-opacity:0"/>')
        defs.append('    </linearGradient>')

        defs.append('    <linearGradient id="sun-fade-up" x1="0%" y1="0%" x2="0%" y2="100%">')
        defs.append('      <stop offset="0%" style="stop-color:#FFD700;stop-opacity:0"/>')
        defs.append('      <stop offset="100%" style="stop-color:#FFD700;stop-opacity:1"/>')
        defs.append('    </linearGradient>')

        defs.append('    <linearGradient id="opposition-spark" x1="0%" y1="0%" x2="0%" y2="100%">')
        defs.append('      <stop offset="0%" style="stop-color:#000000;stop-opacity:0.95"/>')
        defs.append('      <stop offset="100%" style="stop-color:#000000;stop-opacity:0"/>')
        defs.append('    </linearGradient>')

        defs.append('  </defs>')
        svg_content.extend(defs)

        # Add background rectangle with gradient/image/gradient-over-image
        svg_content.append('  <rect x="5" y="5" width="90" height="100" rx="5" ry="5" fill="url(#bg-gradient)" stroke="none" opacity="1"/>')
        # svg_content.append('  <rect x="5" y="5" width="90" height="100" rx="5" ry="5" fill="url(#bg-image)" stroke="none" opacity="1"/>')
        # svg_content.append('  <rect x="5" y="5" width="90" height="100" rx="5" ry="5" fill="url(#bg-gradient)" stroke="none" opacity="0.75"/>')

        # Add clip path
        svg_content.append('  <clipPath id="rounded-rect">')
        svg_content.append('    <rect x="5" y="5" width="90" height="100" rx="5" ry="5"/>')
        svg_content.append('  </clipPath>')

        # Add clipped group
        svg_content.append('  <g clip-path="url(#rounded-rect)">')
        
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
        svg_content.append(f'    <line x1="{earth_x}" y1="{earth_y}" x2="{sx}" y2="{sy}" stroke="#000000" stroke-width="0.5" opacity="0.6"/>')

        # Draw line at station direct longitude
        # Where is the station direct longitude at 1 AU, in final coords?
        dx, dy = transform_coordinates(*self._normalize_coordinates(
            station_direct_longitude,
            10,
            image_rotation
        ))
        # Draw solid line from Earth center to station direct point
        svg_content.append(f'    <line x1="{earth_x}" y1="{earth_y}" x2="{dx}" y2="{dy}" stroke="#000000" stroke-width="0.5" opacity="0.6"/>')

        # Create a path for the triangle between Earth and the two endpoints
        path_data = []
        path_data.append(f"M {earth_x} {earth_y}")  # Start at Earth
        path_data.append(f"L {sx} {sy}")  # Line to station retrograde
        path_data.append(f"L {dx} {dy}")  # Line to station direct
        path_data.append("Z")  # Close the path back to Earth
        
        # Add the shaded triangle
        svg_content.append(f'    <path d="{" ".join(path_data)}" fill="#000000" fill-opacity="0.1" stroke="none"/>')

        # Add station retrograde label
        station_retrograde_date = retrograde_period.station_retrograde_date
        station_retrograde_x, station_retrograde_y = transform_coordinates(*self._normalize_coordinates(
            station_retrograde_longitude,
            station_retrograde_distance,
            image_rotation
        ))

        text_x = station_retrograde_x + 2
        text_y = station_retrograde_y

        svg_content.append(f'    <text x="{text_x}" y="{text_y}" fill="#FFFFFF" font-size="3" dominant-baseline="hanging">')
        date_str, time_str = self._format_datetime(station_retrograde_date)
        svg_content.append(f'      <tspan x="{text_x}" dy="0em">Stations Retrograde</tspan>')
        svg_content.append(f'      <tspan x="{text_x}" dy="1em">{date_str}</tspan>')
        svg_content.append(f'      <tspan x="{text_x}" dy="1em">{time_str}</tspan>')
        svg_content.append('    </text>')

        # Add station direct label
        station_direct_date = retrograde_period.station_direct_date
        station_direct_x, station_direct_y = transform_coordinates(*self._normalize_coordinates(
            station_direct_longitude,
            station_direct_distance,
            image_rotation
        ))

        text_x = station_direct_x - 2
        text_y = station_direct_y

        svg_content.append(f'    <text x="{text_x}" y="{text_y}" fill="#FFFFFF" font-size="3" dominant-baseline="hanging" text-anchor="end">')
        date_str, time_str = self._format_datetime(station_direct_date)
        svg_content.append(f'      <tspan x="{text_x}" dy="0em">Stations Direct</tspan>')
        svg_content.append(f'      <tspan x="{text_x}" dy="1em">{date_str}</tspan>')
        svg_content.append(f'      <tspan x="{text_x}" dy="1em">{time_str}</tspan>')
        svg_content.append('    </text>')

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

        svg_content.append(f'    <text x="{text_x}" y="{text_y}" fill="#FFFFFF" font-size="3" dominant-baseline="hanging" text-anchor="end">')
        date_str, time_str = self._format_datetime(shadow_start_date)
        svg_content.append(f'      <tspan x="{text_x}" dy="0em">Shadow begins</tspan>')
        svg_content.append(f'      <tspan x="{text_x}" dy="1em">{date_str}</tspan>')
        svg_content.append(f'      <tspan x="{text_x}" dy="1em">{time_str}</tspan>')
        svg_content.append('    </text>')

        # Shadow end label
        shadow_end_date = retrograde_period.post_shadow_end_date
        shadow_end_x, shadow_end_y = transform_coordinates(*self._normalize_coordinates(
            station_retrograde_longitude,
            shadow_positions[shadow_end_date.timestamp() / 86400 + 2440587.5].get(Quantity.DELTA, 0.0),
            image_rotation
        ))

        text_x = shadow_end_x + 1
        text_y = shadow_end_y

        svg_content.append(f'    <text x="{text_x}" y="{text_y}" fill="#FFFFFF" font-size="3" dominant-baseline="hanging">')
        date_str, time_str = self._format_datetime(shadow_end_date)
        svg_content.append(f'      <tspan x="{text_x}" dy="0em">Shadow ends</tspan>')
        svg_content.append(f'      <tspan x="{text_x}" dy="1em">{date_str}</tspan>')
        svg_content.append(f'      <tspan x="{text_x}" dy="1em">{time_str}</tspan>')
        svg_content.append('    </text>')

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
            sun_aspect_distance,
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
        svg_content.append(f'    <line x1="{planet_x}" y1="{planet_y}" x2="{dx_toward}" y2="{dy_toward}" stroke="url(#sun-fade-down)" stroke-width="0.5" opacity="1.0"/>')

        # Draw gradient extension away from Earth
        svg_content.append(f'    <line x1="{planet_x}" y1="{planet_y}" x2="{dx_away}" y2="{dy_away}" stroke="url(#sun-fade-up)" stroke-width="0.5" opacity="1.0"/>')

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

            # Instead of a continuous line, create separate "sparks" at the zodiac and sun
            
            # Create spark at the zodiac wheel point
            spark_length = 10  # Length of the spark in viewbox units
            
            # Apply a small 1% rotation to ensure bounding box has nonzero width
            theta = math.radians(1)  # 1 degree rotation
            # Calculate rotated offsets for vertical lines
            dx = spark_length/2 * math.sin(theta)  # Small x offset from rotation
            dy = spark_length/2 * math.cos(theta)  # Slightly less than spark_length/2 due to rotation
            
            # Calculate up and down points from the wheel position with rotation
            wheel_up_x = wheel_x - dx
            wheel_up_y = wheel_y - dy
            wheel_down_x = wheel_x + dx
            wheel_down_y = wheel_y + dy
            
            # Draw up-and-down gradient spark at the zodiac wheel
            svg_content.append(f'    <line x1="{wheel_up_x}" y1="{wheel_up_y}" x2="{wheel_x}" y2="{wheel_y}" stroke="url(#sun-fade-up)" stroke-width="0.5" opacity="1.0"/>')
            svg_content.append(f'    <line x1="{wheel_x}" y1="{wheel_y}" x2="{wheel_down_x}" y2="{wheel_down_y}" stroke="url(#sun-fade-down)" stroke-width="0.5" opacity="1.0"/>')
            
            # Create spark at the sun position with the same rotation
            sun_up_x = sun_x - dx
            sun_up_y = sun_y - dy
            sun_down_x = sun_x + dx
            sun_down_y = sun_y + dy
            
            # Draw up-and-down gradient spark at the sun
            svg_content.append(f'    <line x1="{sun_up_x}" y1="{sun_up_y}" x2="{sun_x}" y2="{sun_y}" stroke="url(#sun-fade-up)" stroke-width="0.5" opacity="1.0"/>')
            svg_content.append(f'    <line x1="{sun_x}" y1="{sun_y}" x2="{sun_down_x}" y2="{sun_down_y}" stroke="url(#sun-fade-down)" stroke-width="0.5" opacity="1.0"/>')

        # Add solar opposition spark for planets other than Mercury and Venus
        if planet not in [Planet.MERCURY, Planet.VENUS]:
            # Calculate the point on the zodiac wheel at the solar aspect longitude
            sun_aspect_angle_rad = math.radians(retrograde_period.sun_aspect_longitude - image_rotation)
            wheel_x = earth_x + zodiac_radius * math.cos(sun_aspect_angle_rad)
            wheel_y = earth_y + zodiac_radius * math.sin(sun_aspect_angle_rad)

            # Create vector from wheel to Earth center
            vector_x = earth_x - wheel_x
            vector_y = earth_y - wheel_y
            
            # Normalize the vector
            vector_length = math.sqrt(vector_x**2 + vector_y**2)
            if vector_length > 0:
                norm_x = vector_x / vector_length
                norm_y = vector_y / vector_length
                
                # Calculate extension points for gradient (longer extension)
                extension_length = 6  # Increased from 4 to 6 viewbox units
                
                # Add a 1% clockwise rotation to the normalized vector
                theta = math.radians(1)  # 1 degree clockwise
                rotated_norm_x = norm_x * math.cos(theta) + norm_y * math.sin(theta)
                rotated_norm_y = -norm_x * math.sin(theta) + norm_y * math.cos(theta)
                
                # Calculate point for the gradient extension towards Earth
                dx_toward = wheel_x + rotated_norm_x * extension_length
                dy_toward = wheel_y + rotated_norm_y * extension_length
            else:
                # Fallback if vector has zero length
                dx_toward = wheel_x
                dy_toward = wheel_y + 6  # Increased from 4 to 6 viewbox units

            # Draw gradient extension towards Earth
            svg_content.append(f'    <line x1="{wheel_x}" y1="{wheel_y}" x2="{dx_toward}" y2="{dy_toward}" stroke="url(#opposition-spark)" stroke-width="0.75" opacity="0.95"/>')

        # Draw zodiac circle centered at Earth's position
        svg_content.append(f'    <circle cx="{earth_x}" cy="{earth_y}" r="{zodiac_radius}" stroke="{zodiac_color}" stroke-width="0.5" opacity="{zodiac_opacity}" fill="none"/>')

        # Draw 1AU circle for Mars
        if planet == Planet.MARS or planet == Planet.MERCURY or planet == Planet.VENUS:
            # Calculate radius for 1AU in viewbox coordinates 
            earth_orbit_radius = self._normalize_distance(1.0) * scale
            svg_content.append(f'    <circle cx="{earth_x}" cy="{earth_y}" r="{earth_orbit_radius}" stroke="{zodiac_color}" stroke-width="0.5" opacity="0.3" fill="none"/>')

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
            svg_content.append(f'    <line x1="{inner_x}" y1="{inner_y}" x2="{outer_x}" y2="{outer_y}" stroke="{zodiac_color}" stroke-width="0.5" opacity="{zodiac_opacity}"/>')

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
                svg_content.append(f'    <text x="{text_x}" y="{text_y}" fill="{zodiac_color}" font-size="4" opacity="{zodiac_opacity}" transform="rotate({text_angle}, {text_x}, {text_y})" text-anchor="start" dominant-baseline="alphabetic">{zodiac_signs[ecliptic_degrees]}</text>')

                # Previous sign text (slightly counterclockwise)
                text_angle_rad = math.radians(ecliptic_degrees - text_angle_offset - image_rotation)
                text_x = earth_x + text_radius * math.cos(text_angle_rad)
                text_y = earth_y + text_radius * math.sin(text_angle_rad)
                
                svg_content.append(f'    <text x="{text_x}" y="{text_y}" fill="{zodiac_color}" font-size="4" opacity="{zodiac_opacity}" transform="rotate({text_angle}, {text_x}, {text_y})" text-anchor="start" dominant-baseline="hanging">{zodiac_signs[(ecliptic_degrees - 30) % 360]}</text>')

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
                svg_content.append(f'    <circle cx="{x}" cy="{y}" r="0.75" fill="#FFFFFF" stroke="none" opacity="0.3"/>')
            else:
                # Inside shadow period
                if (
                    jd
                    <= retrograde_period.station_retrograde_date.timestamp() / 86400
                    + 2440587.5
                ):
                    # Pre-shadow period
                    svg_content.append(f'    <circle cx="{x}" cy="{y}" r="0.75" fill="#00DDDD" stroke="#FFFFFF" stroke-width="0.15" opacity="0.9"/>')
                elif (
                    jd
                    >= retrograde_period.station_direct_date.timestamp() / 86400
                    + 2440587.5
                ):
                    # Post-shadow period
                    svg_content.append(f'    <circle cx="{x}" cy="{y}" r="0.75" fill="#3399FF" stroke="#FFFFFF" stroke-width="0.15" opacity="0.9"/>')
                else:
                    # Main retrograde period
                    svg_content.append(f'    <circle cx="{x}" cy="{y}" r="0.75" fill="#FFFFFF" stroke="none" opacity="0.8"/>')

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
                svg_content.append(f'    <circle cx="{x}" cy="{y}" r="1.0" fill="#FFD700" stroke="none" opacity="0.6"/>')

        # Close clipped group
        svg_content.append('  </g>')

        # Add the text labels on top of everything
        # Station retrograde label
        svg_content.append(f'  <text x="{station_retrograde_x + 2}" y="{station_retrograde_y}" fill="#FFFFFF" font-size="3" dominant-baseline="hanging">')
        date_str, time_str = self._format_datetime(station_retrograde_date)
        svg_content.append(f'    <tspan x="{station_retrograde_x + 2}" dy="0em">Stations Retrograde</tspan>')
        svg_content.append(f'    <tspan x="{station_retrograde_x + 2}" dy="1em">{date_str}</tspan>')
        svg_content.append(f'    <tspan x="{station_retrograde_x + 2}" dy="1em">{time_str}</tspan>')
        svg_content.append('  </text>')

        # Station direct label
        svg_content.append(f'  <text x="{station_direct_x - 2}" y="{station_direct_y}" fill="#FFFFFF" font-size="3" dominant-baseline="hanging" text-anchor="end">')
        date_str, time_str = self._format_datetime(station_direct_date)
        svg_content.append(f'    <tspan x="{station_direct_x - 2}" dy="0em">Stations Direct</tspan>')
        svg_content.append(f'    <tspan x="{station_direct_x - 2}" dy="1em">{date_str}</tspan>')
        svg_content.append(f'    <tspan x="{station_direct_x - 2}" dy="1em">{time_str}</tspan>')
        svg_content.append('  </text>')

        # Shadow start label
        svg_content.append(f'  <text x="{shadow_start_x - 1}" y="{shadow_start_y}" fill="#FFFFFF" font-size="3" dominant-baseline="hanging" text-anchor="end">')
        date_str, time_str = self._format_datetime(shadow_start_date)
        svg_content.append(f'    <tspan x="{shadow_start_x - 1}" dy="0em">Shadow begins</tspan>')
        svg_content.append(f'    <tspan x="{shadow_start_x - 1}" dy="1em">{date_str}</tspan>')
        svg_content.append(f'    <tspan x="{shadow_start_x - 1}" dy="1em">{time_str}</tspan>')
        svg_content.append('  </text>')

        # Shadow end label
        svg_content.append(f'  <text x="{shadow_end_x + 1}" y="{shadow_end_y}" fill="#FFFFFF" font-size="3" dominant-baseline="hanging">')
        date_str, time_str = self._format_datetime(shadow_end_date)
        svg_content.append(f'    <tspan x="{shadow_end_x + 1}" dy="0em">Shadow ends</tspan>')
        svg_content.append(f'    <tspan x="{shadow_end_x + 1}" dy="1em">{date_str}</tspan>')
        svg_content.append(f'    <tspan x="{shadow_end_x + 1}" dy="1em">{time_str}</tspan>')
        svg_content.append('  </text>')

        # Add date labels for key points
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
                date_str, time_str = self._format_datetime(date)
                svg_content.append(f'  <text x="{x + 4}" y="{y}" fill="#666666" font-size="3" font-family="Helvetica, Arial, sans-serif">')
                svg_content.append(f'    <tspan x="{x + 4}" dy="0em">{label}</tspan>')
                svg_content.append(f'    <tspan x="{x + 4}" dy="1em">{date_str}</tspan>')
                svg_content.append(f'    <tspan x="{x + 4}" dy="1em">{time_str}</tspan>')
                svg_content.append('  </text>')

        # Determine the zodiac signs where the retrograde occurs
        # Get the zodiac sign for station retrograde and direct points
        station_retro_sign = get_zodiac_sign(station_retrograde_longitude)
        station_direct_sign = get_zodiac_sign(station_direct_longitude)
        
        # Format the month range
        try:
            from zoneinfo import ZoneInfo
            tz = ZoneInfo(self.display_timezone)
            start_dt = retrograde_period.station_retrograde_date.astimezone(tz)
            end_dt = retrograde_period.station_direct_date.astimezone(tz)
            
            start_month = start_dt.strftime("%B")
            end_month = end_dt.strftime("%B")
            start_year = start_dt.year
            end_year = end_dt.year
            
            if start_year == end_year:
                if start_month == end_month:
                    month_range = f"{start_month} {start_year}"
                else:
                    month_range = f"{start_month}-{end_month} {start_year}"
            else:
                month_range = f"{start_month} {start_year} - {end_month} {end_year}"
        except Exception:
            # Fallback to UTC if timezone conversion fails
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
        aspect_date, aspect_time = self._format_datetime(retrograde_period.sun_aspect_date)
        aspect_label = "Cazimi" if planet in [Planet.MERCURY, Planet.VENUS] else "Solar Opposition"
        
        # Calculate center for text alignment
        center_x = viewbox_width / 2
        
        # Calculate positions for bottom text information
        rectangle_bottom = viewbox_height - 2.5  # Bottom edge of the rounded rectangle
        bottom_padding = 2  # Fixed padding from the bottom edge
        
        # Calculate line heights
        cazimi_line_height = 2.5  # Font size of cazimi text
        heading_line_height = 4.5  # Font size of heading
        subheading_line_height = 3.5  # Font size of subheading
        url_line_height = 2.5  # Font size of URL text
        
        # Calculate spacings
        first_spacing = 3  # Space between cazimi and heading
        second_spacing = 0.25  # Space between heading and subheading
        third_spacing = 1.25  # Space between subheading and URL
        
        # Calculate total text block height
        total_height = cazimi_line_height + heading_line_height + subheading_line_height + url_line_height + first_spacing + second_spacing + third_spacing
        
        # Calculate the y position for the first line
        first_line_y = rectangle_bottom - bottom_padding - total_height
        
        # Add bottom text elements
        # First line - Cazimi/Opposition info (smaller)
        svg_content.append(f'  <text x="{center_x}" y="{first_line_y}" fill="#FFFFFF" font-size="{cazimi_line_height}" text-anchor="middle">')
        svg_content.append(f'    <tspan x="{center_x}" dy="0em">{aspect_label} {aspect_date} {aspect_time}</tspan>')
        svg_content.append('  </text>')
        
        # Second line - Planet Retrograde heading (larger)
        heading_y = first_line_y + cazimi_line_height + first_spacing
        sign_text = f"{station_retro_sign}" + (f" &amp; {station_direct_sign}" if station_retro_sign != station_direct_sign else "")
        sign_scale_factor = 1.0
        if len(sign_text) > 20:
            sign_scale_factor = 0.9

        svg_content.append(f'  <text x="{center_x}" y="{heading_y}" fill="#FFFFFF" font-size="{heading_line_height}" font-weight="bold" text-anchor="middle" transform="scale({sign_scale_factor}, 1)">')
        svg_content.append(f'    <tspan x="{center_x / sign_scale_factor}" dy="0em">{planet.name.capitalize()} Retrograde in {sign_text}</tspan>')
        svg_content.append('  </text>')
        
        # Third line - Month-year subheading
        subheading_y = heading_y + heading_line_height + second_spacing
        svg_content.append(f'  <text x="{center_x}" y="{subheading_y}" fill="#FFFFFF" font-size="{subheading_line_height}" text-anchor="middle">')
        svg_content.append(f'    <tspan x="{center_x}" dy="0em">{month_range}</tspan>')
        svg_content.append('  </text>')
        
        # Fourth line - retrograde.observer (blue, like a hyperlink, fixed width font)
        url_y = subheading_y + subheading_line_height + third_spacing
        svg_content.append(f'  <text x="{center_x}" y="{url_y}" fill="#5599FF" font-size="{url_line_height}" font-family="monospace" font-weight="bold" text-anchor="middle" style="text-shadow: 1px 1px 2px #000000;">')
        svg_content.append(f'    <tspan x="{center_x}" dy="0em">retrograde.observer</tspan>')
        svg_content.append('  </text>')

        # Write the SVG file
        with open(output_path, 'w') as f:
            f.write(self._generate_svg_xml('\n'.join(svg_content)))
