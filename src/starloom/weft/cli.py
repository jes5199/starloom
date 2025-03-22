"""
Command-line interface for the weft package.

This module provides functions for setting up command line arguments
and handling logging configuration.
"""

import argparse
import logging
from typing import Dict, Any

from .logging import set_log_level


def setup_arg_parser() -> argparse.ArgumentParser:
    """
    Set up the argument parser for weft command line tools.
    
    Returns:
        An ArgumentParser instance with common arguments configured
    """
    parser = argparse.ArgumentParser(description="Starloom Weft file utilities")
    
    # Add verbosity options
    parser.add_argument(
        "-v", "--verbose", 
        action="count", 
        default=0,
        help="Increase verbosity (can be used multiple times: -v, -vv, -vvv)"
    )
    parser.add_argument(
        "--debug", 
        action="store_true",
        help="Enable debug logging (equivalent to -vv)"
    )
    parser.add_argument(
        "--quiet", 
        action="store_true",
        help="Suppress all logging except errors"
    )
    
    return parser


def configure_logging(args: Dict[str, Any]) -> None:
    """
    Configure logging based on command line arguments.
    
    Args:
        args: Parsed command line arguments
    """
    # Determine log level based on verbosity flags
    if args.quiet:
        log_level = logging.ERROR
    elif args.debug:
        log_level = logging.DEBUG
    else:
        # Convert verbosity count to log level
        # 0 -> WARNING, 1 -> INFO, 2+ -> DEBUG
        verbosity = args.verbose
        if verbosity == 0:
            log_level = logging.WARNING
        elif verbosity == 1:
            log_level = logging.INFO
        else:
            log_level = logging.DEBUG
    
    # Apply log level to all weft loggers
    set_log_level(log_level) 