"""
Command-line interface utilities for starloom.

This module provides functions for setting up command line arguments
and handling logging configuration.
"""

import argparse
import logging
from typing import Dict, Any

from ..weft.logging import set_log_level


def setup_arg_parser() -> argparse.ArgumentParser:
    """
    Set up the argument parser for starloom command line tools.

    Returns:
        An ArgumentParser instance with common arguments configured
    """
    parser = argparse.ArgumentParser(description="Starloom utilities")

    # Add verbosity options
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (can be used multiple times: -v, -vv, -vvv)",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug logging (equivalent to -vv)"
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Suppress all logging except errors"
    )

    return parser


def configure_logging(args: Dict[str, Any]) -> None:
    """
    Configure logging based on command line arguments.

    Args:
        args: Parsed command line arguments (as a dictionary or argparse.Namespace)
    """
    # Determine log level based on verbosity flags
    if isinstance(args, dict):
        quiet = args.get("quiet", False)
        debug = args.get("debug", False)
        verbosity = args.get("verbose", 0)
    else:
        # Handle as argparse.Namespace for backward compatibility
        quiet = args.quiet if hasattr(args, "quiet") else False
        debug = args.debug if hasattr(args, "debug") else False
        verbosity = args.verbose if hasattr(args, "verbose") else 0

    if quiet:
        log_level = logging.ERROR
    elif debug:
        log_level = logging.DEBUG
    else:
        # Convert verbosity count to log level
        # 0 -> WARNING, 1 -> INFO, 2+ -> DEBUG
        if verbosity == 0:
            log_level = logging.WARNING
        elif verbosity == 1:
            log_level = logging.INFO
        else:
            log_level = logging.DEBUG

    # Apply log level to all starloom loggers
    set_log_level(log_level)

    # Also configure the root logger to ensure all loggers work
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Create a console handler if none exists
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(log_level)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
    else:
        # Update existing handlers
        for handler in root_logger.handlers:
            handler.setLevel(log_level)
