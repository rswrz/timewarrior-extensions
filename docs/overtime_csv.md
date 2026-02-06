# Overtime CSV Export Extension

Exports overtime calculations to a CSV format compatible with the overtime
report output. The CSV uses the same configuration and calculation logic.

## Usage

```bash
timew report overtime_csv :week > /tmp/overtime.csv
```

Or with exported JSON:

```bash
timew export :week | python3 overtime_csv.py > /tmp/overtime.csv
```

## CSV Columns

Columns are double-quoted with embedded quotes escaped by doubling.

1. `Date` — `YYYY-MM-DD`
2. `From` — `HH:MM:SS` (first tracked segment start, day-clamped)
3. `To` — `HH:MM:SS` (last tracked segment end, day-clamped; may be `24:00:00`)
4. `Pause` — `H:MM:SS` (sum of gaps between tracked intervals within the day)
5. `Expected` — `H:MM:SS`
6. `Actual` — `H:MM:SS`
7. `Overtime` — signed `H:MM:SS` (`+`/`-` when non-zero)

## Configuration

Uses the same environment variables as the overtime summary report. See
`docs/overtime_summary.md` for details.
