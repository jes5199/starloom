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
  - Watch for interface extensions in concrete implementations that aren't part of the base interface
    - For example, HorizonsEphemeris.get_planet_position accepts a 'location' parameter that other implementations don't support
    - When using different implementations interchangeably, handle these differences gracefully
    - For CLI commands, include appropriate warnings when parameters will be ignored by certain implementations

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

4. Simplifying CLI command structure:
   - For simpler, more intuitive command interfaces, use direct commands instead of nested subcommands
   - When you want to enable syntax like `app command arg` instead of `app command subcommand arg`:
     * Use a simple `@click.command()` instead of the group + command pattern
     * Register this command directly with the main CLI
     * Make the command function name match the command name for clarity
   - This approach reduces command complexity while preserving functionality
   - Consider the command hierarchy carefully based on user experience goals

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

## User-Friendly CLI Output Formatting

1. When displaying astronomical data to users:
   - Convert technical values to human-readable formats (e.g., zodiac signs for ecliptic longitudes)
   - Use appropriate units with proper abbreviations (e.g., "AU" for astronomical units)
   - Include directional indicators where appropriate (e.g., "N" for north, "S" for south)
   - Format numerical values with appropriate precision (e.g., limit decimal places)
   - Group related information logically (e.g., date on one line, position on another)

2. When formatting output from API data:
   - Always validate and type-check values before formatting
   - Handle empty or null values gracefully with reasonable defaults
   - Provide appropriate error messages if data cannot be formatted
   - Use consistent formatting across similar data types
   - Consider both technical accuracy and user readability

3. CLI Interface Design:
   - When working with multiple implementations of a common interface, prefer the common subset of parameters
   - Drop implementation-specific parameters that aren't supported by all implementations
   - Consider separate commands for specialized functionality rather than conditional logic
   - Focus on consistency and simplicity for better user experience
   - Document clearly which parameters work with which data sources
   - Provide clear warning messages when certain parameters are ignored or not supported

4. Formatting zodiac positions:
   - Divide the ecliptic longitude (0-360°) into 12 equal segments of 30° each
   - Map each segment to the appropriate zodiac sign (Aries starting at 0°, Taurus at 30°, etc.)
   - Convert the longitude within each sign to degrees (0-29°)
   - Use proper symbols for degrees (°) and directional indicators (N/S)
   - Consider audience familiarity with terminology when choosing formats 

## Utility Module Organization

1. When developing a package with formatting or utility functions:
   - Create dedicated utility modules (e.g., `util.py`) for related helper functions
   - Group functions by their purpose (formatting, validation, conversion, etc.)
   - Export utility functions through the module's `__init__.py` for easy imports
   - Use consistent naming conventions (e.g., `format_*` for formatting functions)
   - Document each function with clear docstrings describing parameters and return values

2. Benefits of utility module organization:
   - Promotes code reuse across the codebase
   - Reduces duplication and ensures consistent formatting
   - Simplifies maintenance by centralizing related functionality
   - Makes the codebase more modular and testable
   - Provides clear documentation for utility functions

3. Best practices for utility functions:
   - Keep functions small and focused on a single task
   - Use type hints to clarify expected inputs and outputs
   - Add thorough documentation with examples
   - Consider future extensibility (e.g., formatting options)
   - Make functions pure (no side effects) when possible 

## Local Horizons and Cached Horizons Implementation

- Created a `LocalHorizonsStorage` class that provides both reading and writing operations for a local SQLite database containing ephemeris data.
- Implemented a lightweight `LocalHorizonsEphemeris` class that wraps the storage class to provide a standard Ephemeris interface for reading operations.
- Implemented a `CachedHorizonsEphemeris` class that combines the real Horizons API (`HorizonsEphemeris`) with local storage. It first checks if data is available locally, and if not, fetches it from the Horizons API and stores it for future use.
- Created example scripts showing how to use both the local-only and cached implementations.
- All implementations follow the `Ephemeris` abstract interface defined in `starloom.ephemeris.ephemeris`, ensuring consistent behavior across different data sources.

The key architectural approach is:
1. `LocalHorizonsStorage` - Centralized class for both reading and writing to the local database
2. `LocalHorizonsEphemeris` - Lightweight wrapper providing the standard Ephemeris interface by delegating to the storage class
3. `CachedHorizonsEphemeris` - Combines the real API with local cache for efficient data access

This design ensures the storage logic lives in one place (the Storage class) while still providing the standardized Ephemeris interface through the wrapper class. The cached implementation provides a convenient way to automatically populate the local database when needed. 

## Unit Testing for Local and Cached Horizons

When implementing unit tests for local data storage and caching implementations:

1. **Test Environment Isolation**:
   - Use `tempfile.TemporaryDirectory()` to create isolated test environments
   - Clean up resources in `tearDown()` method to avoid test interference
   - Use separate test databases for each test case to ensure independence

2. **Mocking External Services**:
   - Use `unittest.mock.patch` to mock external API calls
   - Patch at the correct import point (where the class is imported, not where it's defined)
   - Provide appropriate return values or side effects for mocked methods

3. **Testing Caching Behavior**:
   - Verify cache miss correctly calls the underlying API
   - Verify cache hit avoids unnecessary API calls
   - Test proper data persistence between operations
   - Confirm error handling and fallback mechanisms work correctly

4. **Testing Database Operations**:
   - Test both read and write operations
   - Verify data integrity after storage and retrieval
   - Test edge cases like non-existent data
   - Use proper assertions for numerical values (e.g., `assertAlmostEqual` for floating-point values)

5. **Comprehensive Test Coverage**:
   - Test normal operations (happy path)
   - Test error handling (error path)
   - Test edge cases and boundary conditions
   - Test component interactions when applicable

Examples of effective test patterns:
- Pre-populating the database in setUp to test retrieval
- Using explicit assertions with clear failure messages
- Organizing related tests in separate test methods with descriptive names
- Using documentation strings to explain the purpose of each test 

## Comprehensive Database Testing

When working with database storage components, comprehensive testing should include:

1. **Database Structure Tests**:
   - Verify database files are created correctly
   - Check that tables exist with the correct structure
   - Verify primary keys and constraints are set up correctly
   - Test that database connections can be established

2. **CRUD Operation Tests**:
   - Create: Test inserting new data works correctly
   - Read: Test retrieving stored data returns expected values
   - Update: Test overwriting existing data works correctly
   - Delete: If applicable, test deletion functionality

3. **Edge Case Handling**:
   - Missing data fields
   - Different data types stored in the same database
   - Boundary conditions (e.g., dates at year boundaries, large values)
   - Concurrent access if relevant to the application

4. **Utility Method Testing**:
   - Test helper methods like date conversions independently
   - Verify precision and accuracy of mathematical operations
   - Test format conversions (e.g., datetime to Julian date)

5. **Data Isolation**:
   - Use temporary directories for test databases
   - Clean up after tests to avoid cross-test contamination
   - Use unique identifiers for test data to prevent collisions

## Example Code vs. Unit Tests

We've learned that example files (like `examples.py`) should be replaced by comprehensive unit tests for several reasons:

1. **Test Coverage**: Unit tests provide verifiable test coverage with assertions, while examples only demonstrate usage.

2. **Regression Detection**: Unit tests catch regressions when code changes, while examples won't alert you to broken functionality.

3. **Documentation**: Good unit tests serve as documentation of expected behavior, often more precisely than examples.

4. **CI/CD Integration**: Unit tests can be integrated into CI/CD pipelines, while examples cannot.

5. **Completeness**: Unit tests force you to consider edge cases and error paths, while examples typically cover only the happy path.

When transitioning from examples to tests:
- Convert example usage into proper test cases with assertions
- Add test cases for error conditions not covered in examples
- Structure tests to verify the entire API surface
- Consider keeping simple usage examples in docstrings for documentation 

## Database Update Operations

When implementing a database storage layer, it's crucial to properly handle update operations to prevent unique constraint violations:

1. **Check Before Insert**: Always check if a record with the same primary key exists before attempting an insert operation.

2. **Update vs Insert**: Use updates for existing records and inserts for new records. SQLAlchemy supports both patterns:
   ```python
   # Check if record exists
   existing = session.execute(select(Model).where(...)).scalar_one_or_none()
   
   if existing:
       # Update existing record
       for key, value in data.items():
           setattr(existing, key, value)
   else:
       # Insert new record
       new_record = Model(**data)
       session.add(new_record)
   ```

3. **Attribute Updates**: When updating an existing record, iterate through the attributes to avoid hardcoding field names, making the code more maintainable.

4. **Transaction Management**: Use session.commit() after all operations to ensure changes are saved within a single transaction.

5. **Error Handling**: Always handle potential database errors, especially IntegrityError for constraint violations.

6. **Primary Key Fields**: Be explicit about which fields constitute your primary key when checking for existing records.

These patterns help ensure data consistency while providing the ability to update existing records when needed. 

## Code Reuse and DRY Principle

When implementing astronomical calculations in a large codebase, follow these best practices:

1. **Reuse Existing Functionality**: The starloom project already has dedicated modules for calculations like Julian dates. Always use these existing functions rather than reimplementing them in other classes:
   - Instead of implementing `_datetime_to_julian` in each class, import and use `julian_from_datetime` from `space_time.julian`
   - Similarly for other common operations like splitting Julian dates into components
   - For type-flexible interfaces, use `get_julian_components` which accepts both datetime and Julian date inputs

2. **Benefits of Centralized Implementation**:
   - **Consistency**: All modules use the same calculation algorithm
   - **Maintenance**: Updates to the algorithm only need to be made in one place
   - **Testing**: The core implementation can be thoroughly tested once
   - **Precision**: Consistent handling of precision and rounding

3. **Import Strategy**:
   - Import specific functions rather than entire modules when possible
   - Use relative imports within the package (e.g., `from ..space_time.julian import julian_from_datetime`)
   - Make imports explicit in the module header rather than hiding them in function bodies

4. **Test Updates**:
   - When converting from a local implementation to using a shared module, update both the implementation and the tests
   - Tests may need to be modified to use the imported functions directly
   - Verify that the behavior is consistent by running the tests after changes

5. **Interface Design**:
   - Create flexible interfaces that accept multiple input types when appropriate
   - Use Union types to indicate multiple acceptable input formats
   - Add high-level utility functions that build on more specific functions
   - Document the expected types clearly in docstrings with examples

The astronomy calculations in starloom (like Julian date conversions) are mathematically complex and sensitive to precision issues. By centralizing these implementations, we ensure accuracy and consistency throughout the codebase. 

## Database Schema Alignment with Enums

When working with a system that maps between enums and database models (like SQLAlchemy models):

1. **Schema Consistency**: 
   - Ensure that your database schema (tables and columns) aligns with the enum definitions
   - If a field is defined in your enum (like `TARGET_EVENT_MARKER` in `Quantity` enum), it must have a corresponding column in the database model
   - Missing columns will cause runtime errors when attempting to store data (e.g., "target_event_marker is an invalid keyword argument")

2. **Schema Migration Strategy**:
   - When adding new fields to enums, also update the corresponding database models
   - Consider creating migration scripts to add new columns to existing database tables
   - Test database operations with all potential fields that may be written

3. **Error Handling**:
   - Implement error handling that can detect and report schema mismatches
   - Consider adding validation logic to check if all enum values have corresponding database columns
   - Handle unknown fields gracefully, perhaps by logging warnings and continuing without them

4. **Selective Field Mapping**:
   - When many fields exist, consider implementing selective mapping based on what's available in both source and destination
   - Filter out fields that don't have corresponding database columns before trying to write to the database
   - Provide clear documentation about which fields are supported in which storage implementations

5. **Testing**:
   - Test storage operations with the full range of potential fields
   - Include tests with edge case quantities that might not be commonly used
   - Verify both write and read operations for all supported fields 

# WEFT Binary Ephemeris Format Integration

- The WEFT format is a binary ephemeris format using Chebyshev polynomials for efficient storage and evaluation
- It supports multiple precision levels: multi-year blocks, monthly blocks, and daily blocks
- The implementation is now integrated with the CachedHorizonsEphemeris for data sourcing
- CLI commands added for generating and using WEFT files:
  - `starloom weft generate <planet> <quantity>` - Generate a WEFT file
  - `starloom weft info <file_path>` - Display info about a WEFT file
  - `starloom weft lookup <file_path> <date>` - Look up a value in a WEFT file

When adding CLI modules to starloom:
- Use type annotations for function parameters and return values
- Don't use the `name` parameter in `@click.group()` or `@group.command()`
- CLI main functions should return `None` 

## Type Checking
- When using evaluate_chebyshev, always pass List[float] - it does not accept numpy arrays
- NaN checking can be done in pure Python with `x != x` since NaN is the only value not equal to itself
- Numpy operations can often be replaced with simpler Python list operations:
  - List concatenation for padding: `list + [value] * count`
  - List slicing for trimming: `list[:-1]`
  - Length checks: `len(list)` or `not list` for empty check
  - Array comparison: `all(x == value for x in list)` instead of `np.all(array == value)`

## Dependencies
- Avoid unnecessary numpy dependencies when standard Python lists suffice
- When removing dependencies, check for hidden usages (e.g., type conversions, utility functions)
- Keep type hints consistent across the codebase (e.g., using List[float] consistently)
- When removing numpy from a module, also check and update the corresponding test files
- Remember to update test assertions that use numpy functions (e.g., replace np.all with Python's all()) 

## Weft Generate Command Issues

### Batch Fetching from Horizons API
- The Horizons API is much more efficient when fetching data in batches rather than individual timestamps
- Current implementation in CachedHorizonsEphemeris.prefetch_data makes individual requests for each timestamp
- Need to modify to use TimeSpec.from_range for batch requests
- This will significantly improve performance when generating .weft files

### Time Step Handling
- Timestamps being requested from Horizons need to be on even hour steps
- Current implementation may be requesting timestamps at arbitrary intervals
- Need to ensure step size is properly formatted for Horizons API (e.g., "1h", "30m")
- TimeSpec.from_range should be reviewed to ensure it handles step sizes correctly

### Type Checking with TypedDict
- Error "TypedDict does not support instance and class checks" indicates incorrect type checking
- TypedDict is a special type that doesn't support isinstance() checks
- Need to use proper type hints and avoid direct type checking of TypedDict instances
- Consider using Protocol classes or other type checking approaches for runtime type validation

### Best Practices
1. Always use batch requests when possible with external APIs
2. Validate and format time steps according to API requirements
3. Be careful with TypedDict type checking - use proper type hints instead of runtime checks
4. Add proper error handling and logging for debugging
5. Consider adding tests specifically for batch request handling and time step formatting 

## Julian Date Precision

When working with Julian dates in the codebase:
- Always use `JD_PRECISION` (9 decimal places) from `space_time/julian.py`
- Round Julian dates consistently when storing and querying from the database
- Be aware that Python's float precision can exceed our storage precision, causing cache misses
- Use `round(jd, JD_PRECISION)` when comparing Julian dates for equality

Example bug: Cache misses occurred when `2460754.3333333335` (query) didn't match `2460754.333333333` (stored). 

## API Changes
- The `prefetch_data` method in `CachedHorizonsEphemeris` has been removed in favor of using `get_planet_positions`
  - `get_planet_positions` provides the same functionality with a more robust implementation
  - It handles bulk data fetching, caching, and time range queries using `TimeSpec`
  - Tests should use `get_planet_positions` instead of the old `prefetch_data` method

## Known Issues
- DateTime rounding issues in `EphemerisDataSource` tests need to be addressed
  - Affects value retrieval at bounds
  - Affects interpolation
  - Affects range operations 

## Julian Date and DateTime Handling

1. When working with functions that convert between Julian dates and datetimes:
   - Always handle both float (Julian date) and datetime inputs
   - Use type hints with Union[float, datetime] to indicate multiple accepted types
   - Check input type before performing operations like rounding
   - Return consistent timezone-aware datetime objects

2. Common pitfalls:
   - Trying to round datetime objects (they don't support __round__)
   - Not handling negative Julian date fractions correctly
   - Assuming input is always a float when it could be a datetime

## Test Mocking Best Practices

1. When mocking API calls:
   - Mock the exact method being called, not a similar one
   - For example, mock `get_planet_positions` if that's what's used, not `get_planet_position`
   - Provide appropriate mock return values matching the actual method's format
   - Verify mock calls with correct parameters

2. Common mocking mistakes:
   - Mocking the wrong method name (singular vs plural)
   - Not matching the expected return value format
   - Not verifying mock calls with correct parameters
   - Not resetting mocks between test phases 