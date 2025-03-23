"""
Command-line interface utilities for starloom.

This module provides functions for setting up command line arguments
and handling logging configuration.
"""

import argparse
import logging
from typing import Dict, Any, Union
from argparse import Namespace

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


def configure_logging(args: Union[Dict[str, Any], Namespace]) -> None:
    """
    Configure logging based on command line arguments.

    Args:
        args: Parsed command line arguments (as a dictionary or Namespace)
    """
    # Determine log level based on verbosity flags
    if isinstance(args, dict):
        quiet = args.get("quiet", False)
        debug = args.get("debug", False)
        verbosity = args.get("verbose", 0)
    else:
        # Handle as argparse.Namespace
        quiet = getattr(args, "quiet", False)
        debug = getattr(args, "debug", False)
        verbosity = getattr(args, "verbose", 0)

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

    # Configure the root logger first
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove any existing handlers
    root_logger.handlers = []

    # Create a console handler
    handler = logging.StreamHandler()
    handler.setLevel(log_level)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Also explicitly configure the starloom and weft loggers
    starloom_logger = logging.getLogger("starloom")
    starloom_logger.setLevel(log_level)
    starloom_logger.propagate = True  # Ensure messages propagate to root

    # Explicitly set the weft module loggers
    weft_logger = logging.getLogger("starloom.weft")
    weft_logger.setLevel(log_level)
    weft_logger.propagate = True

    cli_logger = logging.getLogger("starloom.cli")
    cli_logger.setLevel(log_level)
    cli_logger.propagate = True

    # Apply log level to all starloom loggers
    set_log_level(log_level)

    # Log the configuration
    root_logger.debug(
        f"Logging configured with level {logging.getLevelName(log_level)}"
    )
