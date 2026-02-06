# Overtime Summary Report Extension

Outputs a daily/weekly overtime table (actual minus expected hours) with
configurable work hours and work days.

## Usage

```bash
timew report overtime_summary :week
```

Or with exported JSON:

```bash
timew export :week | python3 overtime_summary.py
```

## Output Notes

- The `Overtime` column is signed (`+` for surplus, `-` for deficit).
- Negative overtime is red and positive overtime is green when ANSI colors are supported.
- `From` and `To` are clock times formatted as `HH:MM:SS`.
- Duration fields (`Pause`, `Expected`, `Actual`, `Overtime`, `Total`) are formatted as `H:MM:SS`.
- `Pause` is computed as the sum of gaps between tracked intervals within the day (active entries are ignored).

## Configuration

All configuration is via environment variables. Defaults are used when values
are unset or invalid.

- `TIMEWARRIOR_EXT_OVERTIME_DAILY_HOURS` (default: `8`)
- `TIMEWARRIOR_EXT_OVERTIME_WORK_DAYS` (default: `1,2,3,4,5` for Mon-Fri)

Example:

```bash
export TIMEWARRIOR_EXT_OVERTIME_WORK_DAYS=1,2,3,4,5
```
