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
2. `ExpectedHours` — decimal hours
3. `ActualHours` — decimal hours
4. `OvertimeHours` — decimal hours

## Configuration

Uses the same environment variables as the overtime summary report. See
`docs/overtime_summary.md` for details.
