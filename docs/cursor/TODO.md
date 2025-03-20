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
- [X] Implement `LocalHorizonsEphemeris` for reading from local SQLite database
- [X] Implement `LocalHorizonsStorage` for writing to local database
- [X] Implement `CachedHorizonsEphemeris` that combines API and local storage
- [X] Add comprehensive test suite for caching functionality
- [X] Add dedicated test coverage for storage operations
- [X] Replace example files with proper unit tests
- [ ] Enhance querying to find closest time point when exact match not found
- [ ] Create CLI command for prefetching and caching large amounts of data
