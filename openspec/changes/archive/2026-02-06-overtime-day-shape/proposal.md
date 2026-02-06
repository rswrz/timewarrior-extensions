## Why

The overtime reports are currently missing key day-shape context (first start, last end, and pauses) and they silently drop sub-minute precision by truncating to whole minutes. Adding these columns and moving calculations to seconds makes the reports more accurate and more useful for reviewing work patterns.

## What Changes

- Add three per-day columns to both `overtime_csv` and `overtime_summary`: `From`, `To`, `Pause`.
- Compute `From`/`To` from ended intervals only (ignore active entries with no `end`).
- Define `From`/`To` as day-clamped clock times; cross-midnight segments can yield `00:00:00`.
- Define `Pause` as the sum of gaps between tracked intervals within the day (after sorting/merging overlaps), computed in seconds.
- **BREAKING** Change overtime calculations from minute-based to second-based for `Expected`, `Actual`, `Overtime`, and weekly/grand totals.
- **BREAKING** Change output formatting:
  - `From`/`To` render as `HH:MM:SS`.
  - Duration fields (`Expected`, `Actual`, `Overtime`, `Total`, `Pause`) render as signed/unsigned `H:MM:SS`.
- **BREAKING** Update `overtime_csv` headers and values from decimal hours to duration strings:
  - From: `Date,ExpectedHours,ActualHours,OvertimeHours`
  - To: `Date,From,To,Pause,Expected,Actual,Overtime`

## Capabilities

### New Capabilities

- `overtime-reports`: Define the output contract for `overtime_csv` and `overtime_summary`, including second-based calculations and the `From`/`To`/`Pause` columns.

### Modified Capabilities

- (none)

## Impact

- Affected code: `overtime_common.py`, `overtime_csv.py`, `overtime_summary.py`.
- Affected docs: `docs/overtime_csv.md`, `docs/overtime_summary.md`.
- Affected users: anyone parsing `overtime_csv` as numeric decimal hours; anyone expecting the prior column set/format in `overtime_summary`.
