"""Profiling wrapper for starloom CLI commands."""

import cProfile
import pstats
from starloom.cli import cli


def profile_command():
    """Run the CLI command with profiling enabled."""
    profiler = cProfile.Profile()
    try:
        profiler.enable()
        cli()
    finally:
        profiler.disable()
        stats = pstats.Stats(profiler)
        stats.sort_stats("cumulative")
        stats.print_stats()


if __name__ == "__main__":
    profile_command()
