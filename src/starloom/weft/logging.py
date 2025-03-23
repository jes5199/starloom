"""
Logging configuration for the starloom.weft package.

This module provides a standardized logging setup for all modules
within the weft package, ensuring consistent log formatting and control.
"""

import logging
import os
import sys

# Default logging level - Debug messages are suppressed by default
DEFAULT_LOG_LEVEL = logging.WARNING

# Create a custom formatter
FORMATTER = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger for the given name.

    Args:
        name: Name for the logger, typically __name__ of the calling module

    Returns:
        A configured logger instance
    """
    logger = logging.getLogger(name)

    # Only configure the logger if it hasn't been already
    if not logger.handlers:
        # Get the root starloom logger's level, or use default if not set
        root_logger = logging.getLogger("starloom")
        log_level = root_logger.getEffectiveLevel() if root_logger.getEffectiveLevel() != 0 else _get_log_level()
        logger.setLevel(log_level)

        # Create console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(FORMATTER)
        logger.addHandler(handler)

    return logger


def _get_log_level() -> int:
    """
    Get the logging level based on environment variables.

    Returns:
        The appropriate logging level as an int
    """
    # Check for environment variable override
    log_level_str = os.environ.get("STARLOOM_LOG_LEVEL", "").upper()

    if log_level_str == "DEBUG":
        return logging.DEBUG
    elif log_level_str == "INFO":
        return logging.INFO
    elif log_level_str == "WARNING":
        return logging.WARNING
    elif log_level_str == "ERROR":
        return logging.ERROR
    elif log_level_str == "CRITICAL":
        return logging.CRITICAL
    else:
        return DEFAULT_LOG_LEVEL


def set_log_level(level: int) -> None:
    """
    Set the logging level for all starloom loggers.

    Args:
        level: The logging level to set (e.g., logging.DEBUG)
    """
    # Update the root starloom logger
    logger = logging.getLogger("starloom")
    logger.setLevel(level)

    # Update all child loggers
    for handler in logger.handlers:
        handler.setLevel(level)

    # Also update the specific weft logger for backward compatibility
    weft_logger = logging.getLogger("starloom.weft")
    weft_logger.setLevel(level)

    for handler in weft_logger.handlers:
        handler.setLevel(level)
