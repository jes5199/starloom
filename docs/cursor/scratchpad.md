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