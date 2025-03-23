# Implement WeftEphemeris Source for Starloom

## Task
Implement a new ephemeris source that reads data from weftball archives (tar.gz) without extracting them to disk.

## Goal
Enable running: `starloom ephemeris mercury --date now --source weft --data-dir mercury_weftball.tar.gz`

## TODOs
[X] Create new module structure for weft_ephemeris
[X] Create WeftEphemeris class implementing the ephemeris interface
[X] Add ability to read .tar.gz files without extraction
[X] Implement weft file parsing to extract positional data
[X] Register the new source in the CLI module
[X] Test with various planets and dates
[X] Handle error cases (missing files, invalid data)
[X] Create unit tests

## Implementation Notes
- Need to understand the weft file format for parsing
- Will use Python's tarfile module for accessing archives
- Must implement the same interface as other ephemeris sources (HorizonsEphemeris, etc.)
- Need to extract longitude, latitude, and distance data

## Completed Implementation
1. Created weft_ephemeris module with WeftEphemeris class 
2. Implemented interface to read from tar.gz files without full extraction
3. Added methods to read longitude, latitude, and distance data
4. Fixed TimeSpec handling with custom _get_julian_dates method
5. Added unit tests to verify functionality

## Potential Issues
1. Currently we write temporary files to disk during loading. This is not ideal - we should find a way to create WeftReader instances directly from bytes without temporary files.
2. Error handling could be improved with more specific error messages.
3. We may need to handle normalization of angles (longitude) to ensure values are in the expected range.
4. The implementation assumes specific filenames within the archive - we might need to make this more flexible.

## Future Improvements
1. Optimize the temporary file handling to avoid disk I/O
2. Add better error handling and logging
3. Consider supporting more quantities beyond the basic three
4. Improve the WeftReader to allow initialization directly from bytes

# Add Logging-Based Debugging to WeftFile Class

## Task
Modify the WeftFile's debugging to use the logging system instead of returning debug info from the evaluate method.

## Goal
Enable integration with the standard logging system for tracking the source of values.

## TODOs
[X] Import and use the logging module in WeftFile
[X] Create a logger instance in the WeftFile class initialization
[X] Modify evaluate() to log debug info instead of returning it
[X] Update _interpolate_forty_eight_hour_blocks() to use logging
[X] Create helper method for detailed interpolation debug logging
[X] Update return types to always return float instead of Union[float, Tuple]

## Implementation Notes
- Used the existing logging system through get_logger(__name__)
- Kept the debug parameter but changed its behavior to control logging
- Improved debug messages with detailed information like block IDs and date ranges
- Added dedicated helper method _log_interpolation_debug() for complex interpolation logging
- Detailed log format shows values, weights, and normalized weights for each block
