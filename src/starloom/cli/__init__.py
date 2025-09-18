"""CLI entry point for starloom."""

import click


from .horizons import horizons
from .ephemeris import ephemeris
from .weft import weft
from .graphics import graphics
from .retrograde import retrograde
from .inanna import inanna
from .transits import transits
from .decans import decans
from . import common as common
from ..weft.logging import get_logger


# Create a logger for this module
logger = get_logger(__name__)


@click.group()
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Increase verbosity (can be used multiple times: -v, -vv, -vvv)",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug logging (equivalent to -vv)",
)
@click.option(
    "--quiet",
    is_flag=True,
    help="Suppress all logging except errors",
)
def cli(verbose: int, debug: bool, quiet: bool) -> None:
    """Starloom CLI."""
    # Configure logging based on command line arguments
    common.configure_logging(
        {
            "quiet": quiet,
            "debug": debug,
            "verbose": verbose,
        }
    )
    logger.debug("Debug logging enabled")


cli.add_command(horizons)
cli.add_command(ephemeris)
cli.add_command(weft)
cli.add_command(graphics)
cli.add_command(retrograde)
cli.add_command(inanna)
cli.add_command(decans)
cli.add_command(transits)
if __name__ == "__main__":
    cli()
