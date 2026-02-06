## 1. Spec and doc alignment

- [x] 1.1 Re-read `openspec/changes/overtime-day-shape/proposal.md` and confirm breaking output changes are implemented as specified
- [x] 1.2 Re-read `openspec/changes/overtime-day-shape/specs/overtime-reports/spec.md` and confirm all requirements are covered by tasks below

## 2. Core computation (overtime_common)

- [x] 2.1 Convert day summary model and calculations from minutes to seconds in `overtime_common.py`
- [x] 2.2 Ensure `Expected` is computed as `round(DAILY_HOURS * 3600)` seconds for configured work days
- [x] 2.3 Ensure active entries (no `end`) are ignored for all calculations
- [x] 2.4 Implement local-midnight splitting into per-day segments for ended entries and aggregate `Actual` as sum of segment seconds
- [x] 2.5 Implement per-day `From` and `To` derived from segments (clock times, clamped so midnight splits can yield `00:00:00`)
- [x] 2.6 Implement per-day `Pause` as sum of gaps between merged segments (sort + merge overlaps/adjacent, then sum gaps)
- [x] 2.7 Add shared formatting helpers:
  - `HH:MM:SS` for clock times
  - `H:MM:SS` for durations and signed durations

## 3. overtime_summary output

- [x] 3.1 Add columns in order: `Wk`, `Date`, `Day`, `From`, `To`, `Pause`, `Expected`, `Actual`, `Overtime`, `Total` in `overtime_summary.py`
- [x] 3.2 Update all duration formatting to `H:MM:SS` (including weekly totals and the grand total row)
- [x] 3.3 Keep overtime/total coloring behavior, driven by signed seconds
- [x] 3.4 Verify table width computation still behaves reasonably with wider time strings

## 4. overtime_csv output

- [x] 4.1 Change header to `Date,From,To,Pause,Expected,Actual,Overtime` in `overtime_csv.py`
- [x] 4.2 Emit `From`/`To` as `HH:MM:SS` and duration columns as `H:MM:SS`
- [x] 4.3 Remove/replace decimal-hours formatting paths (no longer used)

## 5. Documentation updates

- [x] 5.1 Update `docs/overtime_csv.md` to reflect new headers and string-based duration formats
- [x] 5.2 Update `docs/overtime_summary.md` to mention new columns and `H:MM:SS` formatting for durations

## 6. Manual verification

- [x] 6.1 Run `timew report overtime_summary :week` and confirm column order, sign formatting, and colors
- [x] 6.2 Run `timew report overtime_csv :week` and confirm headers and time formats
- [x] 6.3 Spot-check a day with multiple intervals: confirm `Pause` equals the sum of gaps between intervals
- [x] 6.4 Spot-check a cross-midnight entry: confirm next day can show `From=00:00:00` and seconds match expectations
