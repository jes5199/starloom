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