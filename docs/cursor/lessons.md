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

## Julian Date Calculations

When working with Julian dates in astronomical calculations:

1. The correct value for January 1, 2024 UTC is 2460310.5, not 2460309.5
2. Julian date calculations need to handle both Julian and Gregorian calendars correctly
3. The implementation in `src/starloom/space_time/julian_calc.py` correctly handles dates after 1583 (Gregorian calendar adoption)
4. When tests fail due to date calculation mismatches, verify the expected values rather than assuming the implementation is wrong

## Date Handling

- Always use timezone-aware datetime objects (UTC preferred) for astronomical calculations
- For dates across calendar reforms, be sure to use the correct algorithm for the corresponding calendar system 