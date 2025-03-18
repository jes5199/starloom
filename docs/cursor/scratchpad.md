# Space Time Module Import and Test Fixes

## Current Task
Fix imports and add missing unit tests for the space_time module that was imported from another project.

## Files to Address
1. src/starloom/space_time/rounding.py
2. src/starloom/space_time/sidereal.py
3. src/starloom/space_time/julian.py
4. src/starloom/space_time/pythonic_datetimes.py

## Progress Tracking
[X] Run existing unit tests to identify import issues
[X] Fix import paths in test files
[ ] Review each module to identify untested functions
[ ] Add missing unit tests for:
  - [ ] rounding.py (need tests for round_to_nearest_minute and round_to_nearest_second)
  - [ ] sidereal.py (need to review and add tests)
  - [ ] julian.py (all functions tested)
  - [ ] pythonic_datetimes.py (need tests for all functions)
[ ] Verify all tests pass

## Notes
- Current import path in tests is using 'lib.time' which needs to be updated to 'starloom.space_time'
- Need to check if all functions in each module have corresponding tests
- Functions needing tests:
  - rounding.py:
    - round_to_nearest_minute
    - round_to_nearest_second
  - pythonic_datetimes.py:
    - ensure_utc
    - _normalize_longitude
    - _get_longitude_offset
    - get_local_datetime
    - get_closest_local_midnight_before
    - get_local_date
  - sidereal.py: (need to review) 