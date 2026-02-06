## Purpose

Define the behavior and output contract for the overtime report extensions (`overtime_summary` and `overtime_csv`), including second-precision calculations and day-shape columns (`From`, `To`, `Pause`).

## Requirements

### Requirement: Compute daily overtime summaries with second precision
The overtime reports SHALL compute daily summaries using whole seconds (no truncation to minutes).

#### Scenario: Seconds are preserved
- **WHEN** ended time tracking entries include sub-minute durations
- **THEN** the computed daily `Actual` time includes those seconds

### Requirement: Ignore active entries
The overtime reports SHALL ignore any entry that does not include an `end` timestamp.

#### Scenario: Active entry is excluded
- **WHEN** the input includes an entry with `start` but no `end`
- **THEN** the entry does not affect `Actual`, `From`, `To`, or `Pause`

### Requirement: Split ended entries across local day boundaries
The overtime reports SHALL attribute ended entry time to the local calendar day(s) it spans by splitting entries at local midnight boundaries.

#### Scenario: Cross-midnight entry is split
- **WHEN** an ended entry spans two local dates
- **THEN** the portion before midnight contributes to the first day and the portion after midnight contributes to the next day

### Requirement: Provide day clock bounds (From/To)
For each reported day, the reports SHALL compute `From` and `To` from ended entry segments on that day.

- `From` SHALL be the earliest segment start time-of-day on that day, clamped to `00:00:00`.
- `To` SHALL be the latest segment end time-of-day on that day, clamped to `24:00:00`.

#### Scenario: Next-day segment yields 00:00:00
- **WHEN** an ended entry spans midnight into the next local date
- **THEN** the next day MAY have `From` equal to `00:00:00` due to clamping at midnight

#### Scenario: No work on a day
- **WHEN** a day has zero ended entry segments within the report date range
- **THEN** `From` and `To` are empty for that day

### Requirement: Compute Pause as sum of gaps between intervals
For each reported day, the reports SHALL compute `Pause` as the sum of gaps between ended entry segments on that day.

- Segments SHALL be sorted by start time and overlapping/adjacent segments SHALL be merged before gap calculation.
- A gap SHALL be the time between the end of one merged segment and the start of the next merged segment.

#### Scenario: Pause sums gaps between segments
- **WHEN** a day contains two non-overlapping segments separated by a gap
- **THEN** `Pause` equals the duration of that gap

#### Scenario: Overlapping segments do not create negative pause
- **WHEN** a day contains overlapping segments
- **THEN** the segments are merged and the resulting `Pause` does not become negative

### Requirement: Compute Expected time from configuration
For each reported day, the reports SHALL compute `Expected` as:

- `round(DAILY_HOURS * 3600)` seconds for days whose ISO weekday is included in `WORK_DAYS`
- `0` seconds for days not included in `WORK_DAYS`

#### Scenario: Work day produces expected time
- **WHEN** the date is a configured work day
- **THEN** `Expected` is non-zero and equals the configured daily hours in seconds

#### Scenario: Non-work day produces zero expected
- **WHEN** the date is not a configured work day
- **THEN** `Expected` is `0:00:00`

### Requirement: Compute Overtime as Actual minus Expected
For each reported day, the reports SHALL compute `Overtime` as `Actual - Expected` in seconds.

#### Scenario: Surplus time yields positive overtime
- **WHEN** `Actual` is greater than `Expected`
- **THEN** `Overtime` is positive

#### Scenario: Deficit time yields negative overtime
- **WHEN** `Actual` is less than `Expected`
- **THEN** `Overtime` is negative

### Requirement: Render overtime_summary columns and formats
The `overtime_summary` report SHALL render a daily table with weekly grouping and a weekly total.

#### Scenario: overtime_summary column order and formatting
- **WHEN** `overtime_summary` is rendered
- **THEN** it includes columns in this order: `Wk`, `Date`, `Day`, `From`, `To`, `Pause`, `Expected`, `Actual`, `Overtime`, `Total`
- **THEN** `From` and `To` are formatted as `HH:MM:SS`
- **THEN** duration fields (`Pause`, `Expected`, `Actual`, `Overtime`, `Total`) are formatted as `H:MM:SS`
- **THEN** `Overtime` and `Total` are signed with `+` or `-` when non-zero

### Requirement: Render overtime_csv columns and formats
The `overtime_csv` report SHALL render one row per reported day in a CSV format.

#### Scenario: overtime_csv column order and formatting
- **WHEN** `overtime_csv` is rendered
- **THEN** it includes columns in this order: `Date`, `From`, `To`, `Pause`, `Expected`, `Actual`, `Overtime`
- **THEN** `From` and `To` are formatted as `HH:MM:SS`
- **THEN** duration fields (`Pause`, `Expected`, `Actual`, `Overtime`) are formatted as `H:MM:SS`
