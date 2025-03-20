# Project-wide TODO list

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

- [ ] Review API for confusing parts
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
