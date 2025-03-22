# Weft Logging System

The Starloom Weft package includes a standardized logging system that makes debug prints silent by default while allowing users to enable detailed logging when needed.

## Log Levels

The logging system uses standard Python logging levels:

- **DEBUG**: Detailed information, typically only useful for diagnosing problems
- **INFO**: Confirmation that things are working as expected
- **WARNING**: Indication that something unexpected happened, but the process can continue
- **ERROR**: Due to a more serious problem, the software couldn't perform some function
- **CRITICAL**: A serious error indicating the program may be unable to continue running

By default, the logging level is set to **WARNING**, meaning DEBUG and INFO messages will not be displayed.

## Controlling Logging in Scripts

When using Weft command-line tools, you can control the verbosity level using command-line arguments:

```bash
# Run with default logging (warnings and errors only)
python -m scripts.make_weftball mars

# Enable info-level logging (includes basic progress messages)
python -m scripts.make_weftball mars -v

# Enable debug-level logging (includes all diagnostic output)
python -m scripts.make_weftball mars --debug
# or
python -m scripts.make_weftball mars -vv

# Suppress all but error messages
python -m scripts.make_weftball mars --quiet
```

## Controlling Logging in Your Code

### Setting Log Level with Environment Variable

You can set the `STARLOOM_LOG_LEVEL` environment variable to control logging for all Weft modules:

```bash
# Enable debug logging
export STARLOOM_LOG_LEVEL=DEBUG
python -m scripts.make_weftball mars

# Enable info logging
export STARLOOM_LOG_LEVEL=INFO
python -m scripts.make_weftball mars
```

### Programmatically Controlling Logging

In your own code that uses the Weft package, you can configure logging as follows:

```python
from src.starloom.weft.logging import get_logger, set_log_level
import logging

# Get a logger for your module
logger = get_logger(__name__)

# Set log level for all weft loggers
set_log_level(logging.DEBUG)  # Show all messages
# or
set_log_level(logging.INFO)   # Show info, warning, error, critical
# or
set_log_level(logging.WARNING)  # Default - show warnings, errors, and critical only
```

## Adding Logging to Your Code

When developing new modules that integrate with the Weft package, use the logging system as follows:

```python
from src.starloom.weft.logging import get_logger

# Create a logger for this module
logger = get_logger(__name__)

def my_function():
    # Use different log levels appropriately
    logger.debug("Detailed technical information")
    logger.info("Normal operational messages")
    logger.warning("Something unexpected but not serious")
    logger.error("A more serious problem")
    logger.critical("A critical error")
```

## Benefits

1. **Consistent Output Format** - All log messages follow the same format with timestamps and module names
2. **Centralized Control** - Change the verbosity level in one place
3. **Silent by Default** - Debug information doesn't clutter the output unless requested
4. **Selective Debugging** - Enable detailed logging only when needed 