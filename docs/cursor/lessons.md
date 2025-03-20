# Starloom Development Lessons

## Julian Date Module

1. Be careful with importing modules that don't exist - in `julian.py`, there was a reference to an undefined `juliandate` module that was causing linting errors. When refactoring code, make sure to update all references.

2. The Julian date calculation is using the Meeus algorithm and is now implemented without special cases, making the code more maintainable and mathematically sound.

3. The code requires all datetime objects to be timezone-aware with UTC for proper Julian date calculations.

4. When implementing astronomical algorithms, precision is critical. The code uses `JD_PRECISION` constants for consistent rounding behavior.

5. Don't keep unused imports - they clutter the code and cause linting errors.

6. After making changes, always:
   - Run the linter: `python -m ruff check src/`
   - Run the type checker: `python -m mypy src/`
   - Run tests: `python -m pytest tests/`

# Lessons Learned

## Project Structure

- The package structure uses standard Python conventions with modules nested appropriately under src/starloom/.
- The directory structure with ephemeris as a subdirectory of starloom is correct and follows standard practices.

## Abstract Interfaces and Implementation

- Created an abstract Ephemeris interface in the ephemeris module with:
  - Abstract methods defined with @abstractmethod decorator
  - Type hints for all parameters and return values
  - Detailed docstrings explaining the expected behavior
  - Clear specification of the minimum required return values (longitude, latitude, distance)

- Implemented the interface in the horizons module with HorizonsEphemeris:
  - Proper inheritance from the abstract base class
  - Implementation of all required methods
  - Conversion between module-specific types (EphemerisQuantity) and standard types (Quantity)
  - Error handling for API responses and value conversions
  - Flexible input handling (multiple time formats, planet identifiers)

- Benefits of this approach:
  - Different ephemeris sources can be used interchangeably with the same interface
  - Code is more maintainable as implementations are consistent
  - Type checking ensures interface compliance
  - Clear separation of concerns between interface definition and implementation details

- Implementation challenges:
  - Need to carefully check for existing classes/constants before using them
  - When reusing existing modules, understand their design patterns and limitations
  - Mock appropriate external dependencies in tests to avoid network calls
  - Provide detailed error messages that help troubleshoot issues

## Enum Relationships

- `Quantity` (in ephemeris module) and `EphemerisQuantity` (in horizons module) are distinct but related enums:
  - `Quantity` is a comprehensive enum for all astronomical quantities, including both ephemeris columns and orbital elements.
  - `EphemerisQuantity` is a specialized enum specifically for quantities that can be parsed from Horizons API responses.
  - The horizons module imports and maps between these enums as needed.
  - Renaming `EphemerisQuantity` to `HorizonsQuantity` might better reflect its purpose.

- For robust enum mappings:
  - Create bidirectional mappings between related enums when needed
  - When one enum's values directly correspond to another's purpose, derive the mapping programmatically rather than hardcoding it
  - Group enum values into logical categories with comments for better organization
  - Include special handling for edge cases (like blank columns) with clear comments
  - For API-specific enums, use the exact string values expected by the API

## API Data Parsing

When parsing astronomical data from APIs like JPL Horizons:

1. Column name handling:
   - Use case-insensitive comparison for column names (e.g., "JDUT" vs "jdut")
   - Normalize column names to handle variations (spaces, underscores, formatting)
   - Include special handling for columns that might contain extra text (like "Date_________JDUT")

2. Pattern recognition:
   - Use substring matching for common patterns (e.g., "jdut" within longer headers)
   - Implement direct mapping for the most common column names
   - Provide fallback mechanisms to handle different API response formats

3. When working with multiple related enums:
   - Define the mapping between enums at the module level, not locally in functions
   - Ensure enums are defined in the correct order to avoid NameError issues
   - Use consistent bidirectional mapping between related enums

4. CSV parsing:
   - Be careful with blank columns that may have special meaning
   - Count blank columns to assign appropriate special quantity types
   - Handle both standard and custom-formatted CSV outputs

## Testing Abstract Interfaces

When testing abstract interfaces and their implementations:

1. Mock external services:
   - Use unittest.mock to avoid actual API calls
   - Mock at the point where the external call happens (e.g., make_request method)
   - Provide realistic mock responses from fixture files

2. Test across dimensions:
   - Test with different input formats (enum, string name, ID, etc.)
   - Test with different time formats (current, julian date, datetime)
   - Test error conditions (empty responses, invalid inputs)
   - Test exact output values against expected results

3. Organize fixture data:
   - Keep fixture files in a logical directory structure (e.g., by response type)
   - Use real API responses as fixtures when possible
   - Document the source and purpose of each fixture file

4. Be consistent with error expectations:
   - Ensure expected exceptions match what the implementation throws
   - Include specific error messages in the exception match pattern
   - Use proper assertions to validate results

## Julian Date Calculations

When working with Julian dates in astronomical calculations:

1. The correct value for January 1, 2024 UTC is 2460310.5, not 2460309.5
2. Julian date calculations need to handle both Julian and Gregorian calendars correctly
3. The implementation in `src/starloom/space_time/julian_calc.py` correctly handles dates after 1583 (Gregorian calendar adoption)
4. When tests fail due to date calculation mismatches, verify the expected values rather than assuming the implementation is wrong

## Date Handling

- Always use timezone-aware datetime objects (UTC preferred) for astronomical calculations
- For dates across calendar reforms, be sure to use the correct algorithm for the corresponding calendar system

## JPL Horizons API

When working with the JPL Horizons API:

1. The API requires dates in a very specific format:
   - Format: 'YYYY-MMM-DD HH:MM' (e.g., '2035-Jul-12 10:17:19.373')
   - Month should be a three-letter abbreviation with the first letter capitalized (e.g., Jan, Feb, Mar)
   - The entire date string should be enclosed in single quotes
   - Don't use curly braces for optional parts as suggested in some error messages

2. When using API parameters that expect dates:
   - START_TIME, STOP_TIME: Use quoted date format, e.g. START_TIME='2025-Mar-19 20:00'
   - TLIST: For numeric Julian dates, just use the value directly
   - Be careful with URL encoding when submitting requests
   
3. The API responses include error messages that can help identify formatting issues:
   - Watch for messages like "Cannot interpret date" or "Too many constants"
   - Error messages may suggest using a format like "YYYY-MMM-DD {HH:MN}", but the braces are not literal
   
4. Use Julian dates as a reliable alternative when date formatting is problematic 

5. Special location syntax:
   - "@399" is the special syntax for geocentric coordinates (center of Earth)
   - For ground-based locations, use the Location class with proper latitude/longitude 

6. Parameters relevant to specific ephemeris types:
   - The QUANTITIES parameter is only relevant for OBSERVER ephem_type
   - When using other ephemeris types (VECTORS, ELEMENTS, SPK, APPROACH), the QUANTITIES parameter is ignored by the API
   - Be sure to only include parameters that are relevant to the specific ephemeris type being requested

## Click CLI Development

When developing command-line interfaces with Click:

1. Use the `name` parameter in `@click.command()` decorators to specify a different name for the CLI command than the function name:
   ```python
   @app.command(name="custom-name")
   def function_name():
       # This command will be called as "custom-name"
       pass
   ```

2. When you need to have multiple implementations of a command (e.g., different parameter signatures):
   - Use different function names for each implementation
   - Use the `name` parameter to make them all appear as the same command name
   - This avoids Python function redefinition errors while maintaining the desired CLI interface

3. Be careful when using nested command groups:
   - Commands in different groups can have the same name without conflict
   - Commands within the same group must have unique names (or set with the `name` parameter)
   - Always validate your command structure with `--help` flags 

## Implementation Notes
- When parsing CSV data, it's better to use the standard csv library than manually splitting by commas
- Some fixtures in the tests/fixtures directory may contain error messages rather than valid data
- When working with column-based data, it's good to dynamically map column indices to quantity enums
- There are two different ObserverParser implementations in the codebase that should eventually be consolidated 

# JPL Horizons Parser Development

- Different ephemeris types (OBSERVER vs ELEMENTS) have different column formats and data
- OBSERVER format has columns that change based on the requested quantities
- ELEMENTS format has a consistent set of columns with orbital parameters
- Creating separate parsers for each format improves maintainability
- Using Enum classes for the different quantity types helps with type checking and code readability
- The CSV module handles comma-separated parsing better than manual string splitting, especially for complex data
- When working with astronomical data, it's important to handle scientific notation properly (e.g., 4.829493868247705E-02)
- Parsing astronomical data requires careful error handling for missing or malformed values 

## Naming Conventions

- Correctly named the module related to orbital elements as `orbital_elements_parser.py` (previously incorrectly named as `observer_elements_parser.py`)
- The corresponding enum class is `OrbitalElementsQuantity` (previously incorrectly named as `ObserverElementsQuantity`)
- When renaming modules, need to check for:
  - File imports in __init__.py
  - References in test files 
  - Class/enum names and usages throughout the codebase 

## Python Testing

- Mocking in Python tests requires patching at the point where a class or function is imported, not where it's defined
- When patching classes with unittest.mock, use the import path from the module being tested
- For example, if `moduleA.py` imports `ClassB` from `moduleB.py`, and we want to test code in `moduleA.py` that uses `ClassB`, we should patch `moduleA.ClassB` rather than `moduleB.ClassB`
- This is because the code being tested uses the name bound at import time

## API Data Handling

- When testing classes that handle API data, it's important to mock both the request and response parsing stages
- For Horizons API, the HorizonsRequest.make_request() and ObserverParser.parse() methods both need to be mocked for proper unit testing
- Constructing test data that matches the expected format is crucial for meaningful tests

## Error Handling

- Error handling can be tested with pytest.raises() to verify the correct exceptions are raised under specific conditions
- It's important to test for appropriate exceptions like ValueError rather than letting default exceptions like AttributeError propagate
- Good error messages help both developers and users understand what went wrong

## Time Handling

- When working with astronomical calculations, it's important to use timezone-aware datetime objects
- If using datetime.now(), add timezone information using datetime.timezone.utc or another appropriate timezone
- Julian dates are a common format in astronomy and can be used as an alternative to datetime objects 

## CLI Module Development

1. When creating a new CLI module in a Click-based application:
   - Create a new Python file in the CLI module directory
   - Define a Click group function with the module name
   - Add commands to the group with appropriate decorators
   - Import and register the new module in the main CLI's `__init__.py`

2. When implementing CLI commands that use existing functionality:
   - Follow the patterns established in existing CLI modules
   - Reuse common utilities (like date parsing functions)
   - Provide helpful documentation and examples
   - Include proper error handling with user-friendly messages

3. For CLIs that interact with APIs:
   - Convert user-friendly inputs to the format required by the API
   - Provide sane defaults where appropriate
   - Format the output of API responses for readability
   - Consider adding flags to control output format 

## Horizons API Quantity Handling

When working with the JPL Horizons API, it's important to understand the distinction between request quantity codes and response column names:

1. Request quantity codes:
   - For OBSERVER ephemeris type, you must use numeric codes defined in HorizonsRequestObserverQuantities enum
   - Example: HorizonsRequestObserverQuantities.OBSERVER_ECLIPTIC_LONG_LAT.value (31)
   - These codes must be sent as numbers in the QUANTITIES parameter (e.g., "31,20")
   - The Horizons API will reject string-based quantity values with "Cannot read QUANTITIES" error

2. Response column names:
   - The EphemerisQuantity enum contains the actual column names that appear in the response
   - Example: EphemerisQuantity.ECLIPTIC_LONGITUDE.value ("ObsEcLon")
   - These are used for parsing the response, not for making the request
   - There's a mapping between request quantity codes and response column names

3. Common mistake:
   - Using EphemerisQuantity values (column names) in the QUANTITIES parameter of the request
   - This results in a malformed URL with strings instead of numeric codes
   - The API will respond with "Cannot read QUANTITIES" error

4. Best practice:
   - Use HorizonsRequestObserverQuantities for making requests
   - Use EphemerisQuantity for parsing responses
   - Maintain a clear mapping between the two for consistency 