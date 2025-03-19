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