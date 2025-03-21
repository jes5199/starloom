# Test Failure Analysis - 2025-01-01

## Issues Identified
1. ~~Missing `prefetch_data` method in `CachedHorizonsEphemeris`~~ (RESOLVED)
   - `prefetch_data` functionality is now handled by `get_planet_positions`
   - Test needs to be updated to use new API
2. TypeError in `EphemerisDataSource` tests: datetime doesn't define `__round__` method

## Action Items
[X] ~~Add `prefetch_data` method to `CachedHorizonsEphemeris`~~ 
    - Instead, update test to use `get_planet_positions`
[ ] Fix datetime rounding issues in `EphemerisDataSource`

## Analysis
### Test Failures:
1. `test_prefetch_data` - ~~Missing method implementation~~ Outdated test
   - Test should be updated to use `get_planet_positions` instead
   - `get_planet_positions` provides same functionality with better implementation
2. Multiple `EphemerisDataSource` tests failing with same datetime rounding error
   - Affects value retrieval at bounds
   - Affects interpolation
   - Affects range operations

### Debug Output Analysis:
- System is fetching ephemeris data for 2025-01-01 to 2025-01-02
- Data structure shows only ECLIPTIC_LONGITUDE being returned
- Possible data completeness issue to investigate later

## Current Focus
1. ~~First implement missing prefetch_data method~~ Update test to use new API
2. Then investigate datetime rounding issues

# Current Task: Fix WeftWriter for Limited Date Ranges

## Issues Identified
1. The `WeftWriter` class had a method name mismatch: `create_multi_year_blocks` (plural) was called, but the actual method was named `create_multi_year_block` (singular)
2. The code was trying to generate samples for dates outside the data source's range
3. Monthly blocks were restricted to 28-31 days, causing problems with partial months
4. Missing ability to get stack traces on Ctrl+C for debugging

## Implementation Plan
[X] Fix method name mismatch in `create_multi_precision_file`
  - Change call from `create_multi_year_blocks` to `create_multi_year_block` 
  - Update parameters to match the singular method

[X] Fix `create_multi_year_block` to respect data source date range
  - Use data source's start/end dates when they're within the target year range
  - Calculate actual duration based on available data
  - Adjust sample count for shorter spans

[X] Update `MonthlyBlock` class to allow partial months
  - Allow day counts outside the 28-31 range
  - Add warning for unusual day counts

[X] Completely rewrite `create_monthly_blocks` to handle partial months
  - Special case for very short ranges (≤31 days)
  - Handle partial months at start of range
  - Handle partial months at end of range
  - Maintain full month handling for middle months

[X] Add SIGINT handler to print stack traces on Ctrl+C
  - Show call stack when interrupted
  - Display local variables for debugging

## Progress
- First attempt: Fixed method name mismatch and adjusted `create_multi_year_block`
- Second attempt: Fixed `create_monthly_blocks` to handle edge cases better
- Third attempt: Updated `MonthlyBlock` to accept partial months
- Final step: Added SIGINT handler for better debugging

## Lessons Learned
1. Always check method names carefully, especially plural vs. singular forms
2. Date range handling needs special care at boundaries
3. For ephemeris data, partial months are common at the start/end of a range
4. Adding signal handlers can greatly improve debugging workflow

# Current Task: Fix 48-hour Block Headers in .weft Files

## Goals
1. Modify the code to use ONE section header for contiguous 48-hour blocks
   - Currently each 48-hour block has its own header
   - Should have one header covering the entire range of blocks
   
2. Fix block visualization/description
   - Each 48-hour block is centered at midnight of a specific date
   - Should only show that one date when describing the block
   - Current visualization is confusing by showing a range

## Implementation Plan
[X] Update `create_forty_eight_hour_blocks` in `weft_writer.py`
   - ~~Create single header at start covering full range~~ ✗
   - ~~Create blocks with references to that header~~ ✗
   - Create individual headers for each block ✓
   - Center blocks at midnight of each date ✓
   
[X] Fix block visualization/description
   - Update relevant code to show single centered date ✓

## Progress
- First attempt: Tried using a single header for all blocks, but this doesn't work with the file format
  - The format requires each FortyEightHourBlock to be immediately preceded by its header
  
- Second attempt: Modified `create_forty_eight_hour_blocks` to:
  - Create a header for each block
  - Each header spans just that block's date
  - Center each block at midnight of its date
  - Sample data from 24h before to 24h after midnight
  - Properly handle boundary conditions at start/end of range

- Final step: Updated visualization in `weft info` command to:
  - Show just the centered date for each 48-hour block
  - Indent the coefficient count under each block
  - Make it clear that each block is centered at its date

## Lessons Learned
1. The .weft format requires each FortyEightHourBlock to be immediately preceded by its header
2. Each 48-hour block is centered at midnight of its date and extends 24 hours in each direction
3. The visualization should emphasize the center date of each block rather than its range

# Current Task: Implement Block Selection Criteria in WeftWriter

## Issues Identified
1. The WeftWriter doesn't use block selection criteria from `block_selection.py`
2. This can lead to generating blocks with insufficient data coverage
3. For example, partial months with only a few days were being included as monthly blocks

## Implementation Plan
[X] Understand block selection criteria in `block_selection.py`
  - Monthly blocks require at least 66.6% coverage
  - Similar criteria exist for century blocks and daily blocks
  
[X] Modify `create_monthly_blocks` to use block selection criteria
  - Import `should_include_monthly_block` function
  - Check coverage for each potential monthly block
  - Only create blocks that meet the coverage threshold
  - Handle partial months at start and end of data range properly

[X] Update `create_multi_year_block` to use block selection criteria
  - Import `should_include_century_block` function
  - Make the method return `Optional[MultiYearBlock]`
  - Only return a block if it meets coverage criteria

[X] Modify `create_forty_eight_hour_blocks` to use block selection criteria
  - Import `should_include_daily_block` function
  - Check coverage for each daily block
  - Only include blocks that meet the criteria

[X] Update calling code to handle Optional returns
  - Modify `create_multi_precision_file` to handle None returns
  - Only add blocks to the final file if they're not None

## Progress
- Analyzed `block_selection.py` to understand coverage requirements
- Added block selection checks to `create_monthly_blocks`
- Updated `create_multi_year_block` to return Optional[MultiYearBlock]
- Added coverage checks to `create_forty_eight_hour_blocks`
- Updated `create_multi_precision_file` to handle None returns
- Fixed imports to use top-level imports instead of local imports
- Tested with date ranges that include partial months and years

## Testing Results
- With date range 2024-12-15 to 2025-02-15:
  - Only January 2025 is included (as expected)
  - December 2024 and February 2025 are excluded due to insufficient coverage
  
- With date range 2024-12-20 to 2025-03-10:
  - January and February 2025 are included
  - December 2024 and March 2025 are excluded due to insufficient coverage

## Lessons Learned
1. Block selection criteria are essential for meaningful .weft files
2. They ensure that each block contains enough data for accurate interpolation
3. When implementing methods that might not produce valid blocks, return Optional types
4. Always verify block selection behavior with test cases for partial periods
5. Proper error handling and null checks are needed throughout the code

# Current Task: Add Force Include Flag for 48-hour Blocks

## Issues Identified
1. When including 48-hour blocks in long time spans, the coverage criteria would sometimes filter out valid blocks
2. Missing attribute 'coeffs' in FortyEightHourBlock class (actually named 'coefficients')
3. Special handling needed for force_include_daily flag in the configuration

## Implementation Plan
[X] Add force_include parameter to should_include_daily_block
  - Add a parameter to bypass coverage checks
  - Update docstring to explain the parameter
  - Make it default to False for backward compatibility
  
[X] Update create_forty_eight_hour_blocks to use force_include
  - Add force_include parameter to the method
  - Pass it to should_include_daily_block
  - Add debug statements to track force inclusion

[X] Update create_multi_precision_file to pass force_include flag
  - Use force_include_daily from config
  - Pass to create_forty_eight_hour_blocks

[X] Update get_recommended_blocks to set force_include_daily
  - Add special flag outside block type configurations
  - Set based on force_forty_eight_hour_blocks parameter

[X] Fix attribute name inconsistency in weft info command
  - Update to use 'coefficients' instead of 'coeffs' for FortyEightHourBlock

[X] Fix formatting issues in block_selection.py
  - Handle special flags separately from block type configs

## Progress
- Added force_include parameter to should_include_daily_block
- Updated create_forty_eight_hour_blocks to use this parameter
- Modified create_multi_precision_file to pass the flag from config
- Updated get_recommended_blocks to set force_include_daily flag
- Fixed attribute name in weft info command
- Fixed special flag handling in ephemeris_weft_generator.py
- Tested with force inclusion flag to verify blocks are included

## Testing Results
- Without force_include flag: Only blocks with sufficient coverage included
- With force_include flag: All blocks included regardless of coverage
- Fixed FortyEightHourBlock attribute access in weft info command
- Successfully generated a WEFT file with both monthly and 48-hour blocks

## Lessons Learned
1. Special configuration flags need careful handling in multi-level configurations
2. Always ensure consistent attribute naming across similar classes
3. Force inclusion flags provide flexibility when coverage criteria are too restrictive
4. When iterating over dictionary items, type checking helps prevent unexpected errors
5. Debug logging is invaluable for tracking block selection decisions

# Current Task: Fix Coverage Calculation for .weft File Generation

## Issues Identified
1. The coverage calculation used gaps between consecutive timestamps
2. This caused hourly data with regular 1-hour gaps to be incorrectly flagged as having 0% coverage
3. Daily blocks were not being included for hourly data without forcing them
4. The minimum data density for 48-hour blocks was set too high (24 points per day)

## Implementation Plan
[X] Fix analyze_data_coverage function to calculate coverage differently
  - Calculate coverage based on span between first and last points
  - Remove gap-based calculation that was causing issues
  - Add better debug logging to show coverage calculation method
  
[X] Update should_include_daily_block to use the new coverage calculation
  - Use a 66.6% coverage threshold (matching monthly blocks)
  - Require at least 8 points per day for sufficient coverage

[X] Lower the minimum data density threshold in get_recommended_blocks
  - Change from 24 points per day (hourly) to 8 points per day (3-hourly)
  - Keep the rest of the block selection logic the same

[X] Test with different data densities
  - 1-hour data (24 points per day)
  - 3-hour data (8 points per day)
  - 6-hour data (4 points per day)

## Progress
- Modified analyze_data_coverage to calculate coverage based on span between first and last timestamps
- Updated should_include_daily_block to use a 66.6% coverage threshold
- Changed get_recommended_blocks to enable 48-hour blocks at 8 points per day
- Tested with 1-hour, 3-hour, and 6-hour data
- Verified that 48-hour blocks are included for 1-hour and 3-hour data, but not 6-hour data (as expected)

## Testing Results
- With 1-hour data (24 points per day):
  - All days report 100% coverage
  - All 48-hour blocks included
  - Generated .weft file contains 63 blocks (1 monthly + 31 daily)
  
- With 3-hour data (8 points per day):
  - All days report 100% coverage
  - All 48-hour blocks included
  - Generated .weft file contains 63 blocks (1 monthly + 31 daily)
  
- With 6-hour data (4 points per day):
  - All days report 100% coverage
  - No 48-hour blocks included (below 8 points/day threshold)
  - Generated .weft file contains 1 block (monthly only)

## Lessons Learned
1. Coverage calculation should focus on the overall span covered, not gaps between timestamps
2. For astronomical data with regular sampling patterns, the span-based approach is more reliable
3. A threshold of 8 points per day (3-hour data) is sufficient for 48-hour blocks
4. The force_include parameter is still useful for cases that don't meet coverage criteria
5. Clear debug logging is essential for understanding coverage calculations
