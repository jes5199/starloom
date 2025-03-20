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