# Move Ephemeris Formatting Helpers to Utility Module

## Current Task
Move the formatting helper functions from the CLI module to a dedicated utility module.

## Changes
[X] Created a new utility module `src/starloom/ephemeris/util.py`
[X] Implemented three formatting functions:
  - `get_zodiac_sign`: Converts ecliptic longitude to zodiac sign and degrees
  - `format_latitude`: Formats ecliptic latitude with N/S direction
  - `format_distance`: Formats distance in astronomical units
[X] Updated `__init__.py` to expose these functions
[X] Modified the ephemeris CLI module to use the new utility functions
[X] Updated the README.md with information about the new utility module

## Benefits
- **Code Reuse**: Formatting functions can now be used across multiple modules
- **Modularity**: Better separation of concerns between CLI logic and formatting
- **Documentation**: Added dedicated examples and documentation in README
- **Maintainability**: Easier to update formatting in one place

## Next Steps
- Add more utility functions as needed
- Consider adding customization options for formatting

# Improve Ephemeris CLI Output Formatting

## Current Task
Improve the output formatting of the ephemeris CLI command to display planetary positions in a more human-readable format.

## Changes
[X] Added zodiac sign calculation function to convert ecliptic longitude to zodiac sign and degrees
[X] Added latitude formatting with N/S direction
[X] Formatted distance in AU with 2 decimal places
[X] Displayed date in both human readable format and Julian date
[X] Implemented robust type checking to handle potential non-numeric values
[X] Fixed formatting issues with proper type checking

## Result
- Output now shows:
  - Line 1: Human readable date (and Julian date if available)
  - Line 2: Planet name, zodiac position, latitude, and distance
- Examples:
  - `2025-03-20 04:57:58 UTC`
  - `Venus 4° Aries, 8.5°N, 0.28 AU`

## Benefits
- More user-friendly output format
- Astrologically meaningful representation with zodiac signs
- Easier to read and understand at a glance
- Consistent formatting across all planets

# Simplify Ephemeris CLI Command

## Current Task
Simplify the ephemeris CLI command to allow `starloom ephemeris venus` instead of `starloom ephemeris position venus`.

## Changes
[X] Modified ephemeris.py to use a direct command instead of a command group with subcommands
[X] Changed from `@click.group()` + `@ephemeris.command()` to a single `@click.command()`
[X] Renamed the function from `position` to `ephemeris` to match the command name
[X] Updated the documentation examples to reflect the new usage pattern

## Notes
- This simplifies the user experience by reducing command complexity
- The command now follows a more intuitive pattern: `starloom ephemeris venus [options]`
- All functionality is preserved, only the command structure is changed

# Fix Ephemeris CLI QUANTITIES Parameter Issue

## Current Task
Fix an issue with the HorizonsEphemeris implementation where the QUANTITIES parameter was using incorrect values.

## Problem
The API was returning "Cannot read QUANTITIES" errors because the URL included EphemerisQuantity enum values ('.value') instead of the required HorizonsRequestObserverQuantities values.

## Solution
[X] Update the HorizonsEphemeris class to use HorizonsRequestObserverQuantities instead of EphemerisQuantity values
[X] Replace standard_quantities list in HorizonsEphemeris with correct enum values:
  - HorizonsRequestObserverQuantities.OBSERVER_ECLIPTIC_LONG_LAT.value (31)
  - HorizonsRequestObserverQuantities.TARGET_RANGE_RANGE_RATE.value (20)

## Notes
- The Horizons API expects numeric codes for the QUANTITIES parameter (e.g., 31,20)
- EphemerisQuantity contains the column names that appear in the response (e.g., "ObsEcLon")
- HorizonsRequestObserverQuantities contains the numeric codes needed for the request
- This is an important distinction between what we ask for and what we parse 

# Fixing Horizons CLI Test Failures

## Current Task
Fix the failing tests in the Horizons CLI module.

## Issue Analysis
We have three failing tests:
1. `test_parse_date_input` - The test expects `parse_date_input` to return a datetime object for ISO format dates, but it currently returns a Julian date float
2. `test_time_range_query` - The API cannot interpret the date format correctly
3. `test_elements_time_range_query` - Also fails due to date format issues

## Root Causes
1. `parse_date_input` function currently always returns Julian dates as floats, but the test expects datetime objects for ISO format dates
2. The TimeSpec.to_params() method is formatting datetime objects incorrectly for the Horizons API

## Plan
[X] Fix `parse_date_input` to return datetime objects for ISO format inputs
[X] Fix TimeSpec.to_params() to format dates in a way the Horizons API understands
[X] Run tests to verify the fixes

## Details
- `parse_date_input` now returns the appropriate type based on input (datetime for ISO dates, float for Julian dates)
- TimeSpec.to_params() now uses the proper format for the Horizons API ('YYYY-MMM-DD HH:MM')
- The date format needs to be enclosed in single quotes as shown in the Horizons API documentation
- All tests are now passing

## Lessons Learned
- The JPL Horizons API expects dates in a very specific format, and it's important to read their documentation carefully
- The format needed was 'YYYY-MMM-DD HH:MM' with single quotes around it, not with braces
- Always check the API documentation for the exact format expected
- When tests fail, check the error messages carefully to understand what the API expects

# Horizons Request Module Refactoring

## Current Task
Refactor and improve the Horizons request module from the old project, making it more flexible and adding proper unit tests.

## Files to Address
1. src/starloom/horizons/request.py (main file to refactor)
2. src/starloom/horizons/location.py (new file)
3. tests/horizons/test_request.py (new file)

## Progress Tracking
[X] Review dependencies and request missing files
[X] Create Location class for observer coordinates
[X] Refactor HorizonsBasicRequest:
  - [X] Move solar-specific functionality into main class
  - [X] Add Location parameter support
  - [X] Improve error handling and retries
  - [X] Add type hints
[X] Create unit tests:
  - [X] Test basic request functionality
  - [X] Test location-based requests
  - [X] Test error handling
  - [X] Test URL generation
  - [X] Test POST request fallback
[X] Documentation updates
[X] Organize tests in proper subdirectory structure
[X] Fix test failures:
  - [X] Location formatting precision
  - [X] URL encoding behavior
  - [X] Date validation
  - [X] Mock response handling

## Notes
- All required files are present
- Imports have been updated to use the new package structure
- Solar request functionality is now optional through Location parameter
- Added comprehensive unit tests
- Improved error handling and retries
- Added type hints throughout
- Tests are now properly organized in tests/horizons/
- All tests are passing

## Next Steps
1. Consider adding more test cases for edge cases
2. Add integration tests with the actual Horizons API
3. Add more documentation or examples
4. Consider adding convenience methods for common use cases

# Current Task: Horizons API Improvements

## TODOs
[ ] Parameter Cleanup
  - Create TimeRange class to handle start/stop/step vs dates
  - Consider unified parameter for time specification
  - Clean up parameter handling in request.py

[ ] Type Checking
  - Add py.typed markers
  - Install type stubs for requests
  - Add type hints to all methods
  - Run mypy and fix any issues

[ ] API Improvements
  - Review API for confusing parts
  - Add better documentation
  - Consider adding convenience methods

[ ] Testing
  - Add test for quoted quantities in URL
  - Test comma handling in parameters
  - Add integration tests

[ ] CLI Implementation
  - Add CLI command for ecliptic coordinates
  - Support date, date list, and date range
  - Direct STDOUT printing
  - Add proper error handling

## Implementation Plan
1. Start with parameter cleanup as it affects other changes
2. Add type checking
3. Add missing tests
4. Implement CLI functionality

## Notes
- Need to check Horizons manual for exact parameter requirements
- Consider using dataclasses for parameter structures
- May need to add more error handling for edge cases

# Julian Date Module Linting and Type Checking

## Current Task
Fix linting and type checking issues in the Julian date module.

## Files to Address
1. src/starloom/space_time/julian.py
2. src/starloom/space_time/julian_calc.py

## Progress Tracking
[X] Run ruff linter on the source code
[X] Identify linting issues
  - [X] Undefined reference to `juliandate` module in `datetime_from_julian` function
  - [X] Unused `timezone` import
[X] Fix the linting issues:
  - [X] Replace `datetime_from_julian` implementation to use `_julian_to_datetime`
  - [X] Remove unused `timezone` import
[X] Run mypy type checker to verify the fixes
[X] Run tests to ensure functionality is preserved

## Notes
- Fixed reference to undefined `juliandate` module
- Removed unused imports
- All linting and type checking issues are resolved
- All tests pass after the changes

# Fixture Data Generation Task

## Task Overview
Create a script to generate fixture data using the starloom CLI for both ecliptic and elements commands.

## Plan
[X] Create a fixtures directory structure in tests/
[X] Create a script to generate fixture data
[X] Generate data for multiple planets
[X] Save data in appropriate format (JSON)
[X] Document the fixture data structure

## Required Data
1. Ecliptic positions for:
   - Venus (single time and time range)
   - Mars (single time and time range)
2. Orbital elements for:
   - Mars (single time and time range)
   - Jupiter (single time and time range)

## Time Ranges
- Single time: 2025-03-19T20:00:00
- Time range: 2025-03-19T20:00:00 to 2025-03-19T22:00:00 with 1h steps

## Results
- Successfully generated fixture data for all required planets and commands
- Data is stored in JSON format in tests/fixtures/
- Directory structure:
  - tests/fixtures/ecliptic/
    - venus_single.json
    - venus_range.json
    - mars_single.json
    - mars_range.json
  - tests/fixtures/elements/
    - mars_single.json
    - mars_range.json
    - jupiter_single.json
    - jupiter_range.json

# Horizons Parser Rework

## Current Code Analysis
- Parser for standard Horizons ephemeris responses
- Handles CSV-like data format with $$SOE/$$EOE markers
- Supports multiple quantities (EphemerisQuantity enum)
- Handles blank columns for special markers
- Uses Julian dates for time tracking

## Areas for Improvement
1. Code Organization
   - Move to src/starloom/horizons/parsers/
   - Split into multiple files for better organization
   - Create base parser class for common functionality

2. Type System
   - Add more comprehensive type hints
   - Consider using TypedDict for structured data
   - Add validation for input data

3. Error Handling
   - Add proper error handling for malformed data
   - Add validation for required fields
   - Add logging for debugging

4. Performance
   - Cache parsed data instead of re-parsing
   - Optimize CSV parsing
   - Consider using pandas for large datasets

## Implementation Plan
[ ] Create base parser class
[ ] Implement OBSERVER type parser
[ ] Add proper error handling
[ ] Add data validation
[ ] Add tests
[ ] Add documentation

## File Structure
```
src/starloom/horizons/
├── parsers/
│   ├── __init__.py
│   ├── base.py        # Base parser class
│   ├── observer.py    # OBSERVER type parser
│   └── elements.py    # ELEMENTS type parser
├── quantities.py      # EphemerisQuantity enum
└── types.py          # Type definitions
```

# Julian Date Test Fix

## Task
Fix test that expects incorrect Julian date value

## Progress
[X] Identified the failing test in test_request.py
[X] Investigated the Julian date calculation in julian_calc.py
[X] Verified that the implementation is correct - it handles dates after 1583 properly
[X] Updated the test to expect 2460310.5 instead of 2460309.5 for January 1, 2024
[X] Tests now pass
[X] Added lesson to lessons.md

## Notes
- The Julian date calculation in the codebase is correct
- The test was expecting the wrong value (2460309.5 instead of 2460310.5)
- For January 1, 2024 UTC, the correct Julian date is 2460310.5
- The implementation in julian_calc.py correctly implements the Meeus algorithm
- Always check expected values in tests when dealing with astronomical calculations 

# Linting Fixes for Horizons CLI Module

## Current Task
Fix linting issues identified by Ruff in the Horizons CLI module.

## Issues Identified
1. Undefined name `EphemerisQuantity` in the `ecliptic` function
2. Redefinition of `ecliptic` function (defined twice)

## Fixes Applied
[X] Added import for EphemerisQuantity from correct module
[X] Renamed first `ecliptic` function to `ecliptic_single`
[X] Used Click's `name` parameter to keep command name as "ecliptic"
[X] Verified all linting issues are resolved
[X] Verified all tests still pass

## Notes
- Using Click's `name` parameter is a clean way to resolve function name conflicts
- Always make sure to import all required classes and modules
- Running the linter regularly helps catch issues before they cause problems 

# ObserverParser Implementation

## Task
Improve the ObserverParser to be more general and handle different column types from JPL Horizons API responses.

## Implementation Decision
We identified that there are two ObserverParser implementations in the codebase:
1. A standalone one in `src/starloom/horizons/observer_parser.py`
2. One in the parsers module in `src/starloom/horizons/parsers/observer.py` that inherits from BaseHorizonsParser

Since the standalone parser is actually being used in the test code, and the parsers module doesn't appear to be imported or used anywhere in the codebase, we decided to update the standalone parser to handle the general case.

## Changes Made
1. Enhanced ObserverParser to dynamically detect and map columns in the horizons response
2. Used csv parsing to correctly handle CSV formatting
3. Added support for mapping between Quantity and EphemerisQuantity enums
4. Added a normalize_column_name utility function to standardize column names
5. Updated the tests to work with the new implementation

## Future Work
1. Eventually we may want to consolidate the two implementations
2. Consider making the standalone parser inherit from BaseHorizonsParser for consistency 

# ElementsParser Implementation

## Task
Create an orbital elements parser for the JPL Horizons ELEMENTS format data.

## Implementation Details
- Created `ElementsParser` class in `src/starloom/horizons/elements_parser.py`
- Defined `ElementsQuantity` enum with all possible orbital element columns
- Implemented parsing logic based on the ObserverParser approach
- Key points:
  - Elements data has consistent column format (unlike Observer data that changes based on requested quantities)
  - Implemented mapping from column headers to ElementsQuantity enum values
  - Handles CSV parsing, header detection, and data extraction
  - Provides get_value, get_values, and get_all_values methods for accessing data
  - Added comprehensive unit tests

## Testing
- Created tests in `tests/horizons/test_elements_parser.py`
- Verified the parser correctly extracts data from Jupiter fixture
- Confirmed all orbital elements are correctly mapped and extracted
- All tests are passing

## Next Steps
- Consider creating a base parser class that both ObserverParser and ElementsParser can inherit from
- Could move common functionality (CSV extraction, data access methods) to the base class
- Expand to handle more edge cases and error conditions 

# File Renaming: elements_parser to observer_elements_parser

## Task
Renamed elements_parser.py to observer_elements_parser.py for naming consistency with observer_parser.py

## Changes
[X] Created a new file observer_elements_parser.py with identical content from elements_parser.py
[X] Updated import statements in:
  - src/starloom/horizons/__init__.py
  - tests/horizons/test_elements_parser.py
[X] Deleted the original elements_parser.py file
[X] Verified imports work correctly

## Notes
- The rename helps maintain consistency in the codebase
- Both parser files now follow the same naming convention with "observer_" prefix
- All tests continue to pass after the rename
- No change to test file names was necessary as they already reference the class name, not the file name 

# Class Renaming: ElementsQuantity to ObserverElementsQuantity

## Task
Renamed ElementsQuantity to ObserverElementsQuantity and TestElementsParser to TestObserverElementsParser for naming consistency

## Changes
[X] Renamed ElementsQuantity to ObserverElementsQuantity in observer_elements_parser.py
[X] Updated import statements in __init__.py
[X] Renamed TestElementsParser to TestObserverElementsParser in test_elements_parser.py
[X] Updated all references to ElementsQuantity in test_elements_parser.py

## Notes
- The rename helps maintain consistency in the codebase
- Both parser files and classes now follow the same naming convention with "Observer" prefix
- These changes complete the naming standardization started with renaming the file
- Consistent naming makes the codebase more maintainable and easier to understand 

# Update HorizonsRequest for Quantities Parameter Logic

## Current Task
Modify the `HorizonsRequest` class to only include the quantities parameter when using the `OBSERVER` ephem_type, since it gets ignored for other ephem types.

## Plan
[X] Examine the get_url and _get_base_params methods in HorizonsRequest class
[X] Update the logic to only include quantities when ephem_type is OBSERVER
  - Updated `get_url` method to only add quantities for OBSERVER ephem type
  - Updated `_format_post_data` method to do the same for POST requests
[X] Test the changes to ensure they work correctly
  - All tests in tests/horizons/test_request.py pass
  - All tests in the horizons module continue to pass

## Notes
- The modification was simple and straightforward
- The tests continue to pass, confirming that our changes don't break existing functionality
- This implementation is more efficient as it avoids sending unnecessary parameters to the API 

# Directory Structure and Duplication Review

## Current Task
Enhance `EphemerisQuantity` mapping and fix the observer parser integration.

## Analysis
1. We have two separate but related enums:
   - `Quantity` in `src/starloom/ephemeris/quantities.py`: A comprehensive enum for all astronomical quantities
   - `EphemerisQuantity` in `src/starloom/horizons/quantities.py`: A specific enum for quantities that can be parsed from Horizons API responses

2. The observer parser was using a local mapping instead of the new global `EphemerisQuantityToQuantity` mapping.

## Improvements Made
[X] Expanded `EphemerisQuantity` to include all quantities found in `QuantityForColumnName`
[X] Added a new mapping `EphemerisQuantityToQuantity` for direct mapping between enums
[X] Simplified `QuantityForColumnName` to use the new mapping, making it more maintainable
[X] Fixed the order of definitions to avoid NameError (moved EphemerisQuantityToQuantity before its usage)
[X] Enhanced the parser's column mapping with:
   - [X] Case-insensitive matching
   - [X] Special handling for Julian date columns with extra text
   - [X] Direct mapping for common column names
   - [X] Better fallback mechanism

## Benefits
1. `EphemerisQuantity` is now comprehensive, matching all the column names in Horizons API responses
2. The bidirectional mapping between enums is clear and maintainable
3. Code duplication is reduced by deriving `QuantityForColumnName` from `EphemerisQuantityToQuantity`
4. The parser is more robust to variations in API response formats
5. All tests are now passing (52 tests in total)

## Next Steps
[ ] If needed, rename `EphemerisQuantity` to `HorizonsQuantity` (as noted in TODO.md)
[ ] Add more documentation about the enums and their relationships
[ ] Consider enhancing test cases with more variations of API response formats 

# Starloom Tasks

## Current Task: Rename Observer Elements to Orbital Elements

Need to rename "observer_elements" to "orbital_elements" in all occurrences since it was a typo.

### Plan:
[X] Create a new file `orbital_elements_parser.py` with updated content
[X] Update imports in other files
[X] Update test files
[X] Update class/enum names from ObserverElementsQuantity to OrbitalElementsQuantity
[X] Delete the old file once changes are complete

✅ All tasks completed!

# Scratchpad for Current Task

## Task: Implement Abstract Ephemeris Interface and Horizons Implementation

### Goal
Create an abstract interface for ephemeris data sources and implement it for the JPL Horizons API.

### Requirements
- Create an abstract Ephemeris class in starloom.ephemeris module
- Implement a HorizonsEphemeris class in starloom.horizons module
- The interface should have a method to get a planet's position (ecliptic longitude, ecliptic latitude, distance)
- Support different time formats (None for current time, Julian date float, or datetime)
- Add unit tests for the implementation

### Plan
[X] Create an abstract Ephemeris class in src/starloom/ephemeris/ephemeris.py
[X] Update the ephemeris module's __init__.py to export the Ephemeris class
[X] Implement HorizonsEphemeris class in src/starloom/horizons/ephemeris.py
[X] Update the horizons module's __init__.py to export the HorizonsEphemeris class
[X] Document lessons learned in lessons.md
[X] Create unit tests for the HorizonsEphemeris implementation
[X] Fix implementation issues and make tests pass

### Implementation Issues and Fixes

1. TimePoint non-existent class:
   - Original implementation tried to use a non-existent TimePoint class
   - Solution: Updated to use TimeSpec.from_dates() directly with datetime objects or Julian dates

2. Location.GEOCENTRIC missing:
   - Original implementation tried to use a non-existent GEOCENTRIC constant
   - Solution: Created a geocentric_location class attribute with "@399" which is the Horizons syntax for geocentric coordinates

3. Error handling expectations:
   - Test expected KeyError for invalid planet names, but implementation raised ValueError
   - Solution: Updated test to expect ValueError with the correct error message

### Unit Test Details
Created comprehensive tests that verify:
1. Different planet identifier formats:
   - String ID (e.g., "499" for Mars)
   - Planet enum (e.g., Planet.MARS)
   - String enum name (e.g., "MARS")

2. Different time formats:
   - Default (current time)
   - Julian date
   - Datetime object with timezone

3. Error handling:
   - Empty response from API
   - Invalid planet name

4. Result validation:
   - Verifies presence of required quantities (longitude, latitude, distance)
   - Checks actual values against expected results from fixtures

### Implementation Details

The implementation:
1. Uses the HorizonsRequest to query the JPL Horizons API
2. Converts between the module-specific EphemerisQuantity enum and the standard Quantity enum
3. Handles different planet identifier formats (enum, name, ID)
4. Supports multiple time formats (current time, Julian date, datetime)
5. Provides proper error handling

### Next Steps
- Add more methods to the interface as needed (ephemeris ranges, other coordinate systems)
- Consider implementing caching to reduce API calls for repeated requests
- Add integration tests to verify actual API responses 

## Current Task: Update HorizonsEphemeris to default to geocentric coordinates

### Task Description
The goal is to modify the `get_planet_position` method in the `HorizonsEphemeris` implementation to default to geocentric coordinates when no specific location is provided.

### Progress
[X] Modified `get_planet_position` method to default to geocentric coordinates if location is null
[X] Fixed test issue with patching the wrong class paths
[X] Enhanced testing strategy with proper mock objects
[X] Ensured all tests pass, including the full test suite

### Implementation Details
1. The `get_planet_position` method in `HorizonsEphemeris` was updated to default to a geocentric location when no specific location is provided
2. We had to fix the test file which had issues with patching
3. Key points:
   - We discovered that we needed to patch `starloom.horizons.ephemeris.HorizonsRequest` instead of `starloom.horizons.request.HorizonsRequest` because we need to patch the class at the point where it's imported, not where it's defined
   - We also needed to properly patch `ObserverParser.parse` to return mock data
   - We implemented proper checks in the tests to verify that the location parameter is correctly passed

### Next Steps
- Consider if there are any other API improvements to make
- Document the geocentric default behavior in the docstring of relevant methods

### Lessons Learned
- When patching classes with unittest.mock, it's important to patch where they are imported, not where they're defined
- Mock objects need to be set up properly for each test case
- Testing location handling required careful mock setup for both the HorizonsRequest and ObserverParser classes 

# Create New CLI Module for Ephemeris

## Current Task
Create a new CLI module for ephemeris in the starloom package.

## Plan
[X] Examine the existing CLI structure
[X] Create a new ephemeris.py file in the CLI module
[X] Implement the basic CLI command structure
[X] Connect the new module to the main CLI
[X] Test the new CLI module

## Current Progress
- Created ephemeris.py with a basic CLI command structure
- Added a `position` command that fetches planet positions
- Connected the ephemeris module to the main CLI
- Used HorizonsEphemeris implementation as the data source
- Added proper error handling for API failures
- All tasks completed successfully

## Key Features
- Reused the parse_date_input functionality from the horizons CLI
- Added support for location-based observation
- Improved error handling with user-friendly messages
- Properly integrated with the main CLI 

# Current Task: Refactor Local Horizons Implementation

## Task Overview
Refactor the implementation to make `LocalHorizonsStorage` handle both read and write operations, with `LocalHorizonsEphemeris` as a lightweight wrapper providing the Ephemeris interface.

## Progress
[X] Move database reading functionality from `LocalHorizonsEphemeris` to `LocalHorizonsStorage`
[X] Simplify `LocalHorizonsEphemeris` to delegate to the storage class
[X] Update the example script to demonstrate both interfaces
[X] Ensure `CachedHorizonsEphemeris` works with the updated architecture
[X] Update documentation in lessons.md

## Design Approach
- `LocalHorizonsStorage` provides both reading and writing operations for the local SQLite database
- `LocalHorizonsEphemeris` is a thin wrapper that delegates to the storage class while implementing the Ephemeris interface
- `CachedHorizonsEphemeris` checks local storage first and falls back to the Horizons API when needed

## Benefits
- Centralizes database access logic in one place
- Simplifies the architecture by clearly separating concerns
- Ensures consistent handling of database operations
- Still provides the standard Ephemeris interface for compatibility with other code

## Next Steps
- Implement more efficient querying to find the closest time point when an exact match is not found
- Add more error handling and logging for production use
- Consider adding a command-line interface for prefetching large amounts of data 

# Current Task: Add Unit Tests for Local and Cached Horizons

## Task Overview
Create comprehensive unit tests for the LocalHorizonsStorage, LocalHorizonsEphemeris, and CachedHorizonsEphemeris classes.

## Progress
[X] Create unit tests for CachedHorizonsEphemeris
  - [X] Test cache miss triggering API call
  - [X] Test cache hit avoiding API call
  - [X] Test prefetch_data functionality
  - [X] Test fallback to API on cache failure
[X] Create unit tests for LocalHorizonsStorage
  - [X] Test storing and retrieving a single data point
  - [X] Test storing and retrieving multiple data points
  - [X] Test error handling for non-existent data
[X] Create unit tests for LocalHorizonsEphemeris
  - [X] Test delegating to storage layer
  - [X] Test error handling for non-existent planet/time
[X] Create proper test directory structure
  - [X] tests/cached_horizons
  - [X] tests/local_horizons

## Testing Approach
- Used unittest framework with setUp/tearDown for test setup/cleanup
- Created temporary directories for test databases
- Employed mocking to isolate test units and avoid real API calls
- Tested both positive cases (success paths) and negative cases (error handling)
- Used tempfile module to create isolated test environments

## Benefits
- Verified correctness of all three components independently
- Validated the caching behavior functions as intended
- Ensured proper error handling throughout the system
- Created reusable test infrastructure for future additions

## Next Steps
- Add integration tests to verify components work together correctly
- Implement more complex test scenarios (e.g., near-match time queries)
- Add test coverage for edge cases (Julian date conversions, leap seconds, etc.) 

# Current Task: Improve Test Coverage and Remove Example Files

## Task Overview
Create dedicated storage tests for LocalHorizonsStorage class and remove example files in favor of comprehensive unit tests.

## Progress
[X] Create dedicated test file for LocalHorizonsStorage
  - [X] Test database creation and structure
  - [X] Test storing and retrieving data
  - [X] Test Julian date conversion functions
  - [X] Test overwriting existing data
  - [X] Test handling different planets
  - [X] Test handling missing quantities
[X] Remove example files
  - [X] Delete src/starloom/local_horizons/examples.py
  - [X] Delete src/starloom/cached_horizons/example.py

## Test Improvements
- Added dedicated test_storage.py file with comprehensive tests for the LocalHorizonsStorage class
- Added tests for database creation to verify table structure
- Added tests for Julian date conversion functionality
- Added tests for overwriting existing data
- Added tests for storing data for different planets
- Added tests for handling missing quantities
- Removed example files in favor of proper unit tests

## Benefits
- More comprehensive test coverage of storage functionality
- Cleaner codebase without redundant example files
- Better isolation of test cases
- Clear verification of all storage operations
- Proper testing of Julian date conversion functions

## Next Steps
- Add integration tests to verify all components work together
- Enhance query functionality to find closest time points
- Add CLI commands for data prefetching 

# Current Task

## Task Overview
Refactoring the LocalHorizonsStorage class to use the existing Julian date functions from space_time.julian instead of reimplementing them.

## Progress

- [X] Identified duplicated Julian date functionality in LocalHorizonsStorage
- [X] Replaced custom _datetime_to_julian with julian_from_datetime from space_time.julian
- [X] Replaced custom Julian date component splitting with julian_to_julian_parts
- [X] Updated affected tests to use the imported functions
- [X] Document lessons learned about code reuse in lessons.md

## Implementation Changes

1. Removed the following methods from LocalHorizonsStorage:
   - _datetime_to_julian: Replaced with julian_from_datetime
   - Integrated the functionality of _get_julian_components with julian_to_julian_parts

2. Updated imports in both the storage class and test file:
   ```python
   from ..space_time.julian import julian_from_datetime, datetime_from_julian, julian_to_julian_parts
   ```

3. Modified test methods to use the imported functions instead of the class methods that were removed.

## Benefits

- **Reduced Duplication**: Eliminated redundant Julian date calculation code
- **Improved Maintainability**: Future changes to Julian date calculations only need to be made in one place
- **Consistency**: All modules use the same calculation algorithm with the same precision
- **Better Testability**: The core Julian date implementation is extensively tested separately

## Next Steps

- [ ] Consider adding timezone awareness validation to ensure all datetime objects are timezone-aware
- [ ] Look for other areas where common functionality might be duplicated
- [ ] Add additional utility functions to space_time.julian if needed for other astronomical calculations 

# Current Task

## Task Overview
Adding a versatile utility function to space_time.julian for handling both datetime objects and Julian dates.

## Progress

- [X] Identified need for a flexible Julian date component handling function
- [X] Added `get_julian_components` function to space_time.julian module that:
  - Accepts both datetime objects and Julian date floats
  - Returns a tuple of (julian_date_integer, julian_date_fraction)
- [X] Updated LocalHorizonsStorage to use the new function
- [X] Updated tests to verify the new function works correctly
- [X] All tests passing

## Implementation Details

1. Added a new function to space_time.julian:
   ```python
   def get_julian_components(time: Union[float, datetime]) -> Tuple[int, float]:
       """Convert a time to Julian date integer and fraction components."""
       if isinstance(time, datetime):
           # Convert datetime to Julian date
           jd = julian_from_datetime(time)
       else:
           # Assume time is already a Julian date
           jd = time
       
       # Split into integer and fractional parts
       return julian_to_julian_parts(jd)
   ```

2. Updated storage.py to use this function instead of its own method:
   ```python
   jd, jd_fraction = get_julian_components(time)
   ```

3. Added specific tests for the function with both types of input.

## Benefits

- **Further Reduced Duplication**: Removed need for individual classes to implement this common logic
- **Improved API**: Added a more flexible public function to the julian module
- **Better Type Support**: Explicit handling of Union[float, datetime] makes the API easier to use
- **Compatibility**: Works with existing code expecting (int, float) tuple for Julian date components

## Next Steps

- [ ] Consider adding more utility functions for common operations
- [ ] Add support for other date/time types (like numpy.datetime64, pandas.Timestamp)
- [ ] Expand documentation to highlight the new function 

# Current Task

## Task Overview
Removing redundant methods in LocalHorizonsStorage after adding the versatile get_julian_components function to space_time.julian.

## Progress

- [X] Added the flexible `get_julian_components` function to space_time.julian
- [X] Updated LocalHorizonsStorage to use the new function
- [X] Completely removed the redundant `_get_julian_components` method from LocalHorizonsStorage
- [X] Verified all tests still pass

## Implementation Details

1. The original `_get_julian_components` method in LocalHorizonsStorage:
   ```python
   def _get_julian_components(self, time: Union[float, datetime]) -> Tuple[int, float]:
       if isinstance(time, datetime):
           jd = julian_from_datetime(time)
       else:
           jd = time
       return julian_to_julian_parts(jd)
   ```

2. Was completely replaced by direct calls to the new utility function:
   ```python
   jd, jd_fraction = get_julian_components(time)
   ```

## Benefits

- **Code Simplification**: Removed unnecessary method, making the code cleaner
- **Reduced Maintenance**: One less piece of code to maintain
- **Better Organization**: Julian date handling logic now fully centralizes in space_time.julian module
- **Better API Usage**: Using the proper abstraction level for this functionality

## Next Steps

- [ ] Look for similar opportunities for improvement in other classes
- [ ] Consider adding utility functions for other common astronomical calculations
- [ ] Add documentation about the julian module's functions in the project documentation 

# Add Multiple Ephemeris Sources to CLI

## Current Task
Implement support for selecting different ephemeris sources in the CLI command.

## Requirements
- Allow users to choose between horizons, sqlite (local_horizons), and cached_horizons
- Add a `--source` option to the CLI command
- Handle parameter differences between implementations (e.g., location support)
- Add `--data-dir` option for sources that need a data directory

## Progress
[X] Add imports for all ephemeris classes
[X] Create a mapping of friendly names to ephemeris classes
[X] Add `--source` option to the CLI command with choices from the mapping
[X] Add `--data-dir` option for SQLite and cached sources
[X] Handle parameter differences between implementations:
  - Only pass location to HorizonsEphemeris
  - Show appropriate warnings when location is ignored
[X] Update documentation and examples
[X] Show the source in the CLI output

## Implementation Notes
- Added a EPHEMERIS_SOURCES dictionary to map friendly names to classes
- Set "horizons" as the default source
- Added logic to handle different class initializations:
  - SQLite and cached implementations need a data_dir parameter
  - Other implementations use default constructor
- Added conditional logic to handle different get_planet_position signatures:
  - HorizonsEphemeris accepts a location parameter
  - Other implementations don't support location
- Added warning messages when location parameter is ignored
- Updated example documentation

## Lessons Learned
- When implementing a common interface, watch for extensions in concrete implementations
- Handle parameter differences gracefully with clear user feedback
- Document implementation-specific behavior in lessons.md 

# Remove Location Parameter from Ephemeris CLI

## Current Task
Remove the location parameter from the ephemeris CLI command.

## Rationale
- Location parameter was only fully supported by HorizonsEphemeris
- Other ephemeris implementations don't support location
- Removing it simplifies the CLI interface and eliminates conditional logic

## Changes Made
[X] Removed the `--location` option from the CLI command
[X] Removed the Location import
[X] Removed location parameter parsing logic
[X] Removed conditional logic for handling different location support across implementations
[X] Simplified the code to always call `get_planet_position` with only planet and time parameters
[X] Updated the documentation examples

## Result
- Cleaner, more consistent CLI interface
- All ephemeris sources now use the same parameter set
- Simplified implementation without conditional logic for different source types
- More maintainable codebase with fewer special cases

## Next Steps
- Consider implementing a separate command if location-specific ephemeris is needed in the future
- Could potentially add a geocentric-only implementation of location functionality to all ephemeris sources 