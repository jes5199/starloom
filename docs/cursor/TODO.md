# Project-wide TODO list

## Ephemeris Interface

- [X] Add unit tests for the Ephemeris interface
  - Test different planet identifiers (enum, name, ID)
  - Test different time formats (current time, Julian date, datetime)
  - Test error handling for API responses

- [ ] Enhance the Ephemeris interface
  - Add method for getting ephemeris ranges (multiple points)
  - Add support for other coordinate systems
  - Consider adding caching to reduce API calls

- [ ] Additional implementations
  - Add implementation for binary ephemeris files
  - Add implementation for local stored ephemeris data

## Weft Binary Files

- [X] Create weftball generation script
  - Script to generate decade-by-decade weft files for a planet
  - Combines files into one per quantity type
  - Creates a tar.gz archive containing the combined files
  - Example planets: Mars, Venus, Jupiter

## Enum Naming and Documentation

- [ ] Rename `EphemerisQuantity` to `HorizonsQuantity` to better reflect its purpose
  - Update all imports and references across the codebase
  - Update tests to use the new name
  - Ensure backward compatibility or document breaking changes

- [ ] Continue improving documentation for enum relationships
  - Add cross-references between related enums
  - Document mapping strategies between enums
  - Add examples of when to use each enum

## API Improvements

- [X] Review API for confusing parts
  - Update default location handling in `get_planet_position` to use geocentric coordinates
  - Add better documentation
  - Consider adding convenience methods

- [ ] Parameter Cleanup
  - Create TimeRange class to handle start/stop/step vs dates
  - Consider unified parameter for time specification
  - Clean up parameter handling in request.py

## Testing

- [ ] Add test for quoted quantities in URL
- [ ] Test comma handling in parameters
- [ ] Add integration tests

## Cache Implementation

- [X] Add database caching for ephemeris queries
- [X] Add dedicated test coverage for storage operations 
- [X] Replace example files with proper unit tests
- [X] Fix test issues related to Julian date conversion and data updates
- [X] Refactor Julian date conversion to use space_time.julian module
- [ ] Add error handling for cache misses
- [ ] Add cache invalidation strategy
- [ ] Implement prefetching for frequently accessed data
- [ ] Add migration strategy for schema changes

## CLI Improvements

- [X] Move CLI utilities from weft module to cli module
  - Create common.py in cli module
  - Update set_log_level to handle all starloom loggers
  - Update imports in dependent files
  - Delete the original cli.py file from weft

- [ ] Standardize CLI command patterns across modules
  - Ensure all commands follow similar structure
  - Use consistent parameter naming
  - Improve help text quality

- [ ] Add progress indicators for long-running operations
  - Add spinner or progress bar for API requests
  - Add progress tracking for file generation
  - Show intermediate results for multi-step operations

- [ ] Improve error handling in CLI
  - Add better error messages for common errors
  - Add suggestions for fixing common issues
  - Add verbose logging options
