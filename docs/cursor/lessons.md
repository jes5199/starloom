# Starloom Development Lessons

## Weft Test Fixes (2023-03-23)

When fixing the failing tests in the weft module, we discovered several important lessons:

1. The `unwrap_angles()` function was updated to require two additional parameters (`min_val` and `max_val`), which broke existing tests.

2. The `FortyEightHourBlock` constructor was updated to require a `center_date` parameter for better date handling.

3. The `FortyEightHourSectionHeader` constructor now requires `block_size` and `block_count` parameters for validation.

4. The evaluation logic was moved from `WeftFile` to `WeftReader` as part of a refactoring to improve modularity.

5. The serialized size of `FortyEightHourBlock` is 198 bytes, but tests were using a hardcoded value of 100. When serialization/deserialization validation was added, the tests failed.

6. When updating tests, we should carefully check expected values against actual behavior, especially if the code has improved since the tests were written.

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

## WeftEphemeris Implementation

1. When implementing a new data source class following an interface pattern:
   - Study the existing implementations to understand the interface contract
   - Implement all required methods with the same parameter signatures
   - Handle error cases gracefully, providing useful error messages

2. When working with archives (.tar.gz):
   - The `tarfile` module allows reading files directly without extracting to disk
   - Use `extractfile()` to get a file-like object for reading binary data
   - The WeftReader currently requires reading from a file, which required a temporary solution

3. Potential improvements for the WeftEphemeris class:
   - Find a way to initialize WeftReader directly from bytes without temporary files
   - Handle naming conventions more flexibly rather than assuming exact filenames
   - Normalize angle values (longitude) to ensure consistent ranges

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

## .weft File Format
1. Each FortyEightHourBlock must be immediately preceded by its header in the file
2. Each 48-hour block is centered at midnight of its date and extends 24 hours in each direction
3. The visualization should emphasize the center date of each block rather than its range
4. Block headers must have end_day after start_day
5. Blocks are ordered by decreasing precision (least precise first):
   - Multi-year blocks first (lowest precision, longest time span)
   - Monthly blocks second (medium precision, medium time span)
   - Forty-eight hour blocks last (highest precision, shortest time span)
   - This ordering allows truncating the file while maintaining progressively less precise but still useful data

## Block Types
1. Multi-year blocks: For long-term, low-precision data
2. Monthly blocks: For medium-term, medium-precision data
3. Forty-eight hour blocks: For short-term, high-precision data
   - Each block is centered at midnight UTC of its date
   - Extends 24 hours before and after midnight
   - Uses a quintic fit (degree 5 polynomial)
   - Typically uses 48 samples per day 

## WeftWriter and Ephemeris Data Handling

When working with ephemeris data and generating .weft files for planetary positions:

1. Date range handling:
   - Always check that the requested date range is valid for the data source
   - Handle partial periods (months, years) gracefully at the start and end of ranges
   - Be careful with method names, especially singular vs. plural forms (e.g., `create_multi_year_block` vs. `create_multi_year_blocks`)

2. Validation constraints:
   - Be careful with strict validation rules (like requiring months to have 28-31 days)
   - Consider using warnings instead of errors for unusual but valid cases
   - Implement flexible validation that accommodates edge cases like partial periods

3. Polynomial fitting:
   - Ensure the sample count is appropriate for the polynomial degree (at least degree+1 samples)
   - For short time spans, adjust the sample count to match the available data
   - Handle wrapping behaviors for quantities like longitude and right ascension

4. Debugging ephemeris generation:
   - Add SIGINT (Ctrl+C) handlers to get stack traces during long-running operations
   - Include local variable information in debug output for better context
   - Use proper exception handling to provide informative error messages

5. Working with multiple precision levels:
   - Different block types (multi-year, monthly, 48-hour) have different precision/efficiency tradeoffs
   - Ensure each block type respects the data source's date range
   - Configure sample points and polynomial degrees appropriately for each precision level
   
6. Date-time handling in astronomical applications:
   - Always use timezone-aware datetime objects (preferably UTC)
   - Be consistent with time boundaries (e.g., midnight vs. noon for day boundaries)
   - Calculate time differences carefully, especially when crossing month or year boundaries 

## Block Selection Criteria for WEFT Files

When generating .weft files with different precision blocks (multi-year, monthly, 48-hour):

1. Coverage requirements:
   - Each block type has a minimum coverage requirement defined in `block_selection.py`
   - Monthly blocks require at least 66.6% coverage to be included
   - Multi-year blocks (century blocks) have similar coverage requirements
   - Daily blocks also have coverage thresholds

2. Integration between WeftWriter and block selection:
   - The `weft_writer.py` implementation must respect these coverage criteria
   - Block generation methods should use the appropriate `should_include_*_block` functions from `block_selection.py`
   - Return optional values (e.g., `Optional[MonthlyBlock]`) when blocks might not meet coverage criteria
   - Handle potential `None` returns when assembling the final .weft file

3. Handling partial periods:
   - When dealing with date ranges that don't align perfectly with month/year boundaries:
     - For partial months at the beginning or end of the requested range, check if they meet the coverage threshold
     - For multi-year blocks, similar coverage checks apply
     - Only include blocks that have sufficient data coverage

4. Best practices:
   - Integrate block selection criteria directly into block generation methods
   - Always check coverage before creating and fitting coefficients for a block
   - Handle edge cases gracefully, particularly at the boundaries of the requested date range
   - Return `None` for blocks that don't meet coverage criteria rather than raising exceptions
   - Check for `None` returns when processing lists of blocks

5. Testing considerations:
   - Test with date ranges that include partial periods at both start and end
   - Verify that blocks with insufficient coverage are excluded from the final file
   - Confirm that the .weft file contains the expected number of blocks based on coverage criteria 

# WEFT File Generation

## Block Selection and Coverage

1. When generating WEFT files with different block types (multi-year, monthly, 48-hour), coverage checks are important:
   - Each block type has a minimum coverage requirement (e.g., 66.6% for monthly blocks)
   - The `should_include_X_block` functions in `block_selection.py` determine if a block has sufficient coverage
   - When extending date ranges beyond available data, these checks prevent the inclusion of low-quality blocks

2. Implementation of partial month support:
   - Modified `MonthlyBlock` class to handle day counts outside the typical 28-31 day range
   - Added coverage checks in `create_monthly_blocks` to ensure partial months still meet coverage criteria
   - Used `TimeSpec.from_range` to calculate the actual coverage percentage within the data source range

3. Force inclusion flags:
   - Added `force_include` parameter to `should_include_daily_block` to bypass coverage checks when needed
   - Configured this flag through a special `force_include_daily` entry in the block configuration
   - This allows 48-hour blocks to be included even when they would normally be filtered out

4. Configuration structure:
   - The WEFT configuration dictionary uses a specific structure with block types as keys
   - Each block type has its own configuration with `enabled`, `sample_count`, and `polynomial_degree`
   - Special flags like `force_include_daily` need to be handled separately from block configurations

5. Debug logging:
   - Added debug statements to track which blocks are included or excluded
   - These statements provide visibility into the block selection process
   - Useful for troubleshooting issues with block coverage and selection

6. Attribute naming consistency:
   - Ensured consistent naming across similar classes (e.g., `coefficients` vs `coeffs`)
   - Inconsistent naming can lead to errors when accessing attributes
   - Tools like the `weft info` command depend on consistent attribute names across block types

7. Configuration auto-detection:
   - The `get_recommended_blocks` function analyzes the data source to determine appropriate block types
   - Block types are enabled based on data availability and time span
   - Default configuration can be overridden with explicit parameters 

When working with .weft file generation:

1. Data coverage calculation is critical:
   - Coverage should be calculated based on the span between the earliest and latest timestamps in the range
   - A good coverage threshold is 66.6% of the time period
   - For daily blocks, require at least 8 data points per day for adequate coverage

2. Block selection logic:
   - The minimum data density for 48-hour blocks should be 8 points per day (1 point every 3 hours)
   - Monthly blocks can work with lower data density (4 points per day)
   - Include a `force_forty_eight_hour_blocks` parameter to override normal coverage requirements
   - Make CLI flags match the underlying parameter names (e.g., `--force-48h-blocks`)

3. Testing weft file generation:
   - Test with various time steps (1h, 3h, 6h) to verify behavior at different data densities
   - Verify the content of generated files with `weft info` to confirm block inclusion
   - Compare file sizes between versions with different blocks (e.g., monthly-only vs. monthly+daily)

4. Coverage calculation approach:
   - Don't evaluate gaps between consecutive timestamps
   - Instead, check if the overall span between first and last timestamps covers a sufficient portion of the period
   - This better handles regular sampling patterns at different frequencies 

## Test Maintenance After Algorithm Changes

When making significant changes to core algorithms or data structures:

1. Always update related tests to reflect the new implementation:
   - If a calculation method changes, update test expectations to match
   - When attribute names change, update all references in tests
   - For renamed configuration keys, update all test assertions

2. Common test areas that require updating:
   - Coverage calculations - spans rather than gaps may change expected results
   - Expected data structure keys and attribute names
   - Numerical expectations (e.g., points per day)
   - Edge case behavior with new algorithms

3. Best practices for test updates:
   - Run tests immediately after algorithm changes
   - Keep test comments up-to-date with the current implementation logic
   - Document why expectations changed in the test code
   - Verify that the new behavior is correct, not just making tests pass

4. Naming consistency strategies:
   - Use the same attribute names across similar classes
   - When renaming, search the entire codebase for references
   - Document naming patterns in comments or docstrings
   - Use constants for feature flags and configuration keys to ensure consistency 

## SQLAlchemy Database Optimization

### Indexes for Optimizing Queries
- Added composite indexes to optimize query patterns:
  - Primary keys automatically create indexes, but custom indexes may be needed for specific query patterns
  - For tuple-based lookups with `.in_()`, create specific indexes on the tuple columns
  - Use `Index()` in SQLAlchemy model `__table_args__` to define indexes
  - Use `inspect()` to programmatically verify index existence and create them if missing
  
## .weft File Format

1. The .weft file preamble is critical and follows a specific format:
   ```
   #weft! v0.02 planet data_source timespan precision quantity value_behavior chebychevs generated@timestamp
   ```

2. When combining .weft files:
   - The preamble parts must be compared correctly, matching corresponding fields 
   - Essential fields (planet, data source, precision, quantity, behavior) must match
   - Timespan and generation timestamp can differ since they're updated for the combined file

3. Date format for timespan:
   - Use simple formats like "2000s" (for a decade) or "1900-1910" (for year ranges)
   - Avoid using full ISO timestamps which create parsing difficulties
   - Keep the timespan short and human-readable

4. When parsing preambles:
   - Always verify you have the minimum required parts
   - Compare parts by index only after confirming their meaning
   - Use comments to document the index-to-meaning mapping for clarity

5. When reporting errors:
   - Be specific about which field caused the incompatibility
   - Include the actual values being compared in the error message
   - Use descriptive variable names that match the field meanings 

6. Timespan customization:
   - When generating .weft files, offer customization options via CLI parameters
   - For timespans, provide a `--timespan` option to allow human-readable descriptors
   - Always propagate these custom options through all the relevant function calls
   - Ensure custom values have higher priority than automatically generated ones
   - Document the expected format clearly in help text 

## Logging Implementation

- **Date Added**: 2023-07-18
- **Problem**: Debug print statements were always displayed in the output, cluttering the terminal with diagnostic information that wasn't needed during normal operation.
- **Solution**: Implemented a standardized logging system with the following features:
  - Created a centralized `logging.py` module in the weft package
  - Used Python's built-in logging library with appropriate log levels
  - Made DEBUG level silent by default (set to WARNING)
  - Added environment variable control (`STARLOOM_LOG_LEVEL`)
  - Added command-line arguments for verbosity (`-v`, `--debug`, `--quiet`)
  - Documented the system in `docs/weft/logging.md`
- **Files Modified**:
  - Created: `src/starloom/weft/logging.py`
  - Created: `src/starloom/weft/cli.py`
  - Updated: `src/starloom/weft/weft_writer.py`
  - Updated: `src/starloom/weft/block_selection.py`
  - Updated: `src/starloom/weft/ephemeris_data_source.py`
  - Updated: `scripts/make_weftball.py`
  - Created: `docs/weft/logging.md`
- **Benefits**: Debug output is now controlled and silent by default, while still available when needed for troubleshooting. 

## CLI Module Organization

1. Common CLI utilities should be centralized in a shared module:
   - The `starloom.cli.common` module is an appropriate place for shared CLI utilities
   - Avoid duplicating CLI utilities in different submodules (like `weft.cli`)
   - When a utility can be used by multiple CLI commands, move it to the common module

2. When moving utilities between modules:
   - Update all imports in dependent files to use the new location
   - Maintain backward compatibility in any shared components like logging
   - Keep method signatures consistent to minimize breakage

3. For logging configuration:
   - Use a hierarchical approach with a root logger (e.g., 'starloom')
   - Configure child loggers consistently (e.g., 'starloom.weft', 'starloom.cli')
   - When moving logger configuration, ensure all existing code still works

4. CLI argument parsing should follow consistent patterns:
   - Use the same verbosity flags across all commands (-v, --debug, --quiet)
   - The `configure_logging` function in `cli.common` provides standardized level setting 
   - Parser setup should be reusable across different commands and submodules

## Date Span Formatting

### Issue with _descriptive_timespan for Decade Spans and Single Year Cases
When formatting date spans in the `WeftWriter._descriptive_timespan` method, there were issues with:
1. Date ranges crossing decade boundaries like 1899-12-31 to 1910-01-02 not being correctly identified as "1900s"
2. Date ranges that span 3 years but really represent a single year (e.g., 1999-12-31 to 2001-01-02) returning "1999-2001" instead of just "2000"

The problem was that the algorithm wasn't flexible enough to recognize approximate spans, especially when the dates were close to but not exactly at year or decade boundaries.

### Solution
- Implemented special case handling for date ranges like 1899-1910 to map to "1900s"
- Added special handling for single-year spans with buffer days:
  - When a range spans from the end of one year to the beginning of another (e.g., 1999-12-31 to 2001-01-02)
  - Identified the single middle year (2000) and returned it instead of the range "1999-2001"
- Added more flexible detection of approximate decade spans:
  - Check if a start date is within 1 year of a decade start and end date is within 1 year of the decade end
  - Consider both the current and next decade as potential matches
- Kept the buffer day adjustment for dates near month boundaries
- Created comprehensive unit tests for various date span patterns, including edge cases

### Lesson Learned
When dealing with date range formatting, consider edge cases at boundaries like decade transitions and year transitions. A combination of specific case handling and general algorithms may be necessary for robust behavior. Always use unit tests to verify edge cases work as expected, especially with date ranges that could be interpreted in multiple ways (e.g., 1999-2001 could be either a multi-year range or a single year with buffer days).

## CLI Argument Handling

### Issue with configure_logging() and Dictionary Conversion
The `make_weftball.py` script failed with an `AttributeError: 'dict' object has no attribute 'quiet'` when trying to configure logging because it was improperly calling `configure_logging(vars(args))`. 

The `configure_logging` function in `src/starloom/cli/common.py` expects a dictionary with specific keys ('quiet', 'debug', 'verbose'), but the dictionary created by `vars(args)` didn't guarantee these keys would exist.

### Initial Solution Attempt
Explicitly provide the expected dictionary keys with defaults when calling `configure_logging`:

```python
configure_logging({
    'quiet': args.quiet if hasattr(args, 'quiet') else False,
    'debug': args.debug if hasattr(args, 'debug') else False,
    'verbose': args.verbose if hasattr(args, 'verbose') else 0
})
```

### Complete Solution
Upon testing, the issue was more fundamental - the `configure_logging` function itself was not designed to handle dictionary input at all. It needed modification to accept both argparse.Namespace objects and dictionaries:

```python
def configure_logging(args: Dict[str, Any]) -> None:
    # Check if args is a dictionary or an object
    if isinstance(args, dict):
        quiet = args.get('quiet', False)
        debug = args.get('debug', False)
        verbosity = args.get('verbose', 0)
    else:
        # Handle as argparse.Namespace for backward compatibility
        quiet = args.quiet if hasattr(args, 'quiet') else False
        debug = args.debug if hasattr(args, 'debug') else False
        verbosity = args.verbose if hasattr(args, 'verbose') else 0
        
    # Rest of the function remains the same
    # ...
```

### Lesson Learned
When designing utility functions that handle command-line arguments:
1. Be explicit about what type of input the function expects (argparse.Namespace, dict, etc.)
2. Consider adding type checking and flexible input handling for greater robustness
3. Document clearly what format the function expects and provide examples
4. Use defensive programming techniques like dict.get() with defaults or hasattr() checks
5. When modifying shared utility functions, ensure backward compatibility with existing callers

## Function Implementation vs. Usage Pattern

### Issue with get_decade_range Function Not Matching Its Use
In the `make_weftball.py` script, the `get_decade_range` function was defined to return a single string (e.g., "1900s") based on a date. However, the code was trying to use it as if it returned an iterable of date pairs:

```python
for decade_start, decade_end in get_decade_range("1700-01-01 00:00"):
    # ...
```

This resulted in a `ValueError: not enough values to unpack (expected 2, got 1)` error because the function was returning a single string value, not a sequence of tuples.

### Solution
Align the implementation and usage by using the predefined `DECADES` constant for iteration, and using the `get_decade_range` function only to format date strings:

```python
for decade_start, decade_end in DECADES:
    decade_range = get_decade_range(decade_start)
    # Use decade_range in formatting
```

### Lesson Learned
1. Ensure function implementations match their usage patterns throughout the codebase
2. Pay careful attention to return value types, especially when refactoring code
3. When a function's name suggests it returns multiple values (e.g., "range"), but actually returns a single value, consider renaming it for clarity (e.g., "format_decade")
4. Always trace through the code execution path to ensure consistent expectations between callers and implementations

## CLI Module Structure and Naming

### Issue with CLI Module References in make_weftball.py
In the `make_weftball.py` script, there were references to non-existent CLI modules:
- `src.starloom.cli.generate_weft` (for generating weft files)
- `src.starloom.cli.combine_wefts` (for combining weft files)

After examining the codebase, it was discovered that these functions were actually implemented as subcommands of a single module `src.starloom.cli.weft` using the Click framework.

### Solution
Update all CLI command references to use the correct module and subcommand structure:

```python
# Before (incorrect)
cmd = [
    "python", "-m", "src.starloom.cli.generate_weft",
    "--planet", planet,
    # other arguments...
]

# After (correct)
cmd = [
    "python", "-m", "src.starloom.cli.weft",
    "generate",  # Subcommand name
    planet,      # Positional argument
    # other arguments...
]
```

Similarly for the combine command, using the correct subcommand syntax and parameter ordering:

```python
# Before (incorrect)
cmd = [
    "python", "-m", "src.starloom.cli.combine_wefts",
    "--output", output_file,
    *input_files,
]

# After (correct)
cmd = [
    "python", "-m", "src.starloom.cli.weft",
    "combine",
    file1, file2,  # The Click command requires exactly two input files
    output_file,   # Output file is a positional argument, not an option
    "--timespan", "some-timespan",  # Additional options
]
```

### Lesson Learned
1. When using CLI modules in scripts:
   - Check the actual module structure by examining the source code
   - Pay attention to how commands are structured (e.g., subcommands vs. separate modules)
   - Note the order and nature of arguments (positional vs. options)
   - Verify parameter names (e.g., `--stop` vs. `--end`)

2. With Click-based CLIs specifically:
   - Subcommands follow the main module name (e.g., `weft generate`)
   - Positional arguments come before options (those with -- prefix)
   - Some commands have specific requirements (e.g., combine takes exactly two input files)

3. When writing automation scripts:
   - Add robust error handling for subprocess calls
   - Use debug logging to show the exact commands being executed
   - Consider implementing special cases (e.g., combining more than two files iteratively)

## CLI Command Usage in Scripts

### Issue with Subprocess Command Structure in make_weftball.py
The `make_weftball.py` script initially used Python module imports (`python -m src.starloom.cli.weft`) to access CLI functionality, but in typical usage, users interact with the package through the installed command-line interface (`starloom weft`).

### Solution
Update all subprocess calls to use the installed CLI command instead of direct module imports:

```python
# Before (using Python module imports)
cmd = [
    "python", "-m", "src.starloom.cli.weft",
    "generate",
    # parameters...
]

# After (using installed CLI command)
cmd = [
    "starloom",
    "weft",
    "generate",
    # parameters...
]
```

### Lesson Learned
1. When developing scripts that interact with CLI tools:
   - Prefer using the installed command-line interface that users typically interact with
   - This creates a more consistent user experience and simplifies commands
   - Using installed commands makes scripts less dependent on internal module structures
   - Scripts become more robust to internal refactoring if they use the public interface

2. Benefits of using installed commands:
   - Better alignment with typical user workflows
   - More resilience to internal package changes
   - Shorter, more readable commands
   - Using the same code path that users interact with directly, ensuring consistent behavior

3. When to use direct module imports:
   - During development before the CLI is fully established
   - When needing access to functionality not exposed in the CLI
   - In test scripts that need to bypass the CLI layer

## Python Package Imports

When working with Python packages that use the `src` layout:
1. Never import from the `src` directory directly (e.g., `from src.starloom.weft import WeftFile`)
2. Always use the package name as it would be when installed (e.g., `from starloom.weft import WeftFile`)
3. The `src` directory is just a development-time convention to help with import isolation and testing
4. Importing from `src` can cause issues with exception comparison and other runtime behaviors

Example of incorrect import:
```python
from src.starloom.weft import WeftFile  # Wrong
```

Example of correct import:
```python
from starloom.weft import WeftFile  # Correct
```

# Development Lessons

## Weft File Format

### Block Types
1. The weft format supports three types of blocks:
   - MultiYearBlock: For long-term, low-precision data
   - MonthlyBlock: For medium-term, medium-precision data
   - FortyEightHourBlock: For short-term, high-precision data

2. Block Priority:
   - FortyEightHourBlock (highest)
   - MonthlyBlock
   - MultiYearBlock (lowest)

### Value Behavior
1. Three types of value behavior:
   - Wrapping: For angles that wrap around (e.g., longitude [0, 360])
   - Bounded: For values with min/max limits (e.g., latitude [-90, 90])
   - Unbounded: For raw values with no limits

2. Value behavior is specified in the file preamble

### File Structure
1. Preamble format:
   ```
   #weft! v0.02 <id> jpl:horizons <date-range> <precision> <value-type> <behavior> chebychevs generated@<timestamp>
   ```

2. Each block has a 2-byte marker:
   - MultiYearBlock: b"\x00\x03"
   - MonthlyBlock: b"\x00\x02"
   - FortyEightHourBlock: b"\x00\x01"

## Common Issues

### Position Discrepancies
1. When positions differ significantly:
   - Check coordinate systems (ecliptic vs equatorial)
   - Verify value behavior settings
   - Check for sign errors in coefficients
   - Verify block selection logic

2. When using multi-year blocks:
   - Expect lower precision
   - Consider generating higher precision blocks
   - Verify Chebyshev coefficient accuracy

### Development Tips
1. Always check the preamble for:
   - Value behavior settings
   - Date range
   - Value type
   - Generation timestamp

2. Use logging to track:
   - Block selection
   - Value calculation
   - Interpolation behavior

3. Use the debug mode in WeftFile.evaluate():
   ```python
   # Enable debug logging first
   from starloom.weft.logging import set_log_level
   import logging
   set_log_level(logging.DEBUG)
   
   # Then use the debug parameter
   value = weft_file.evaluate(datetime.now(), debug=True)
   ```
   - Logs detailed information about which block was used to calculate the value
   - For interpolated values, logs weights and individual block contributions
   - All debug information goes to the configured logger, not the return value
   - Helpful for diagnosing unexpected values or block selection issues

## Weft Format Implementation

1. When implementing binary file formats with hierarchical sections, proper tracking of section headers and their associated blocks is crucial for maintaining data integrity.

2. The FortyEightHourSectionHeader (0x00 02) defines parameters (block size, block count) that must be strictly enforced for all FortyEightHourBlocks (0x00 01) that follow it.

3. When reading binary data, validate not just the semantic correctness but also the structural requirements like block sizes and counts to ensure proper parsing.

4. Error messages should be specific about what went wrong during parsing, including details like expected vs. actual block counts or sizes.

5. When combining files with hierarchical structures, ensure that the relationship between parent sections (headers) and their child blocks is preserved throughout the process.

## Time Handling

When working with the WEFT file generation system:

1. FortyEightHourSectionHeader class requires block_size and block_count parameters:
   - These parameters must be provided when instantiating the class
   - The correct approach is to create the header first with dummy values, then update them after creating the blocks
   - The block_size should be calculated from an actual serialized block to ensure consistency

2. Block size calculation must match exactly what's expected by the reader:
   - When calculating block sizes, include the full serialized size including any markers
   - Consistency between writer and reader block size expectations is critical
   - Test by reading the file after writing to validate format correctness

3. Be careful with module name collisions:
   - A bug occurred due to importing both `time` module and `time` class from datetime
   - Fix by importing the module with an alias: `import time as time_module`
   - Then use the alias throughout the code: `time_module.time()`

4. When organizing blocks in the file:
   - Group related blocks together (e.g., a header followed by its data blocks)
   - Update the header with the correct count and size before writing
   - Ensure the blocks appear in the expected order

5. Use a consistent approach to create and manage header/block relationships:
   - When a block refers to its header, make sure the header exists first
   - When a header specifies a block count, ensure that exact number of blocks follows
   - When updating a header's properties, do so before serializing the file
```

## Type Checking with mypy

Run `mypy src` to perform type checking on the entire codebase.

Key facts about the project's type checking setup:
- mypy is configured in `pyproject.toml` with `strict = true` enabled
- The project uses Python 3.8+ type annotations
- Common typing issues encountered:
  1. Missing Optional[str] for parameters with None defaults
  2. Missing type parameters for generics like Tuple (must be e.g., Tuple[str, ...])
  3. Improper None checking before accessing attributes of potentially None objects
  4. Method calls to non-existent methods (WeftReader.get_value_with_linear_interpolation)
  5. Tuple type mismatches when used as dictionary keys
  6. Missing __all__ for re-exported module attributes
  7. Complex union types that need more specific type narrowing

Fixed issues in March 2025:
- Fixed WeftEphemeris to use proper method calls (get_value instead of get_value_with_linear_interpolation)
- Fixed improper None handling in with statements
- Fixed Optional type annotations for parameters with None defaults
- Fixed missing type parameters for generic types
- Added __all__ declaration to julian.py to properly re-export datetime_to_julian
- Added explicit float cast for numpy return types
- Fixed tuple type annotations to use proper date type instead of str
- Added None checks before accessing attributes on potentially None objects

Remaining type issues:
- Complex union type handling in weft_writer.py
- Missing type stubs for third-party libraries (ruff)
- Unreachable code detection edge cases