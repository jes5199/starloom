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

# Improve FortyEightHourBlock and FortyEightHourSectionHeader Relationship

## Task
Redesign how FortyEightHourBlock and FortyEightHourSectionHeader relate when reading and writing .weft files.

## Goal
Ensure the last header seen is in effect for multiple FortyEightHourBlock records that follow it, and ensure the block size and count specified in the header are correctly respected.

## TODOs
[X] Understand the current implementation and its limitations
[X] Modify the `from_bytes` method to track the current active header
[X] Ensure block count from header is respected when reading blocks
[X] Validate block sizes match what's specified in the header
[X] Test the changes with sample weft files
[X] Update any related methods that might be affected

## Implementation Notes
- A FortyEightHourSectionHeader (0x00 02) should apply to all FortyEightHourBlock entries (0x00 01) that follow it
- Need to track how many blocks we've read for each header to ensure we match the expected count
- Block sizes should be consistent with what's specified in the header
- May need to adjust error handling for malformed files

## Current Implementation Analysis
- In `WeftFile.from_bytes`, the method creates a flat list of blocks
- When encountering a FortyEightHourBlock, it checks if the last block was a FortyEightHourSectionHeader
- If not, it raises an error (correct behavior)
- The method passes the last header to the FortyEightHourBlock constructor
- However, it doesn't track how many blocks have been read for each header
- It doesn't validate that the number of blocks matches the count in the header
- It doesn't check if the size of each block matches what's specified in the header

## Implemented Changes
1. Added tracking of the current FortyEightHourSectionHeader and the count of blocks read for it
2. Added validation that we read exactly the number of blocks specified in the header
3. Added validation of block sizes to ensure they match what's specified in the header
4. Improved error messages to provide more detail about what went wrong
5. Updated the `combine` method to properly handle multiple FortyEightHourBlocks per header
   - Changed from storing a single block per header to storing a list of blocks
   - Added sorting of blocks by center date for consistent ordering
   - Extended the final block list with all blocks for each header

## Summary
The implementation now correctly handles the relationship between FortyEightHourSectionHeader and FortyEightHourBlock:
- Multiple FortyEightHourBlocks can be associated with a single header
- Block count and size validation ensure the file format is followed correctly
- The combine method properly merges multiple blocks for the same header
- Error messages are more descriptive about what went wrong during parsing

# Current Task: Simplify WeftReader

## Task Description
Simplify the WeftReader class to:
1. Only handle a single file
2. Simplify interpolation logic to only interpolate between 48-hour blocks in the same section
3. Maintain block priority (48h -> monthly -> multi-year)
4. Remove unnecessary complexity

## Plan
[X] Remove multi-file support
[X] Simplify file loading to single file
[X] Clean up interpolation logic
[X] Remove unnecessary methods
[X] Update documentation
[X] Update CLI code
[X] Update tests
[ ] Test changes

## Progress
Completed major refactoring:
1. Removed multi-file support and simplified to single file handling
2. Updated interpolation logic to only interpolate between blocks in same section
3. Removed unnecessary methods and simplified the codebase
4. Updated documentation to reflect changes
5. Maintained block priority order
6. Improved error handling and logging
7. Updated CLI code to use new interface:
   - Fixed lookup command
   - Fixed combine command
8. Updated test suite:
   - Removed multi-file tests
   - Added new single-file tests
   - Improved test coverage for interpolation
   - Added error handling tests

Next steps:
1. Test the changes to ensure functionality is correct
2. Verify interpolation behavior with different block types
3. Check error handling for edge cases
