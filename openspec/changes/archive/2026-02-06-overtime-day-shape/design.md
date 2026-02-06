## Context

This repo provides Timewarrior report extensions. The overtime reports (`overtime_summary.py`, `overtime_csv.py`) currently:

- Compute daily `Actual`, `Expected`, and `Overtime` using whole minutes.
- Omit day-shape context needed for review (first start, last end, and pauses).

Timewarrior exports timestamps with second precision. The current implementation drops sub-minute precision by flooring `total_seconds` to minutes.

The change adds per-day `From`/`To`/`Pause` columns and moves overtime calculations to whole seconds.

Constraints and conventions:

- Input contract: header block + blank line + JSON array of entries.
- Active entries may omit `end` and MUST be ignored for this change.
- Local timezone boundaries define the day (splitting at local midnights).

## Goals / Non-Goals

**Goals:**

- Compute all overtime-related quantities (`Expected`, `Actual`, `Overtime`, weekly/grand totals) in whole seconds.
- Add `From`/`To` (clock times) and `Pause` (duration) per day to both reports.
- Keep day boundary behavior explicit: day clamping can produce `00:00:00`.
- Preserve existing environment variable configuration (`TIMEWARRIOR_EXT_OVERTIME_*`).
- Update docs to match the breaking output and header changes.

**Non-Goals:**

- Including active (no `end`) entries in any calculation.
- Adding configuration for pause thresholds, alternative day definitions, or output formats.
- Providing backwards-compatible CSV headers or dual-format modes.

## Decisions

### Decision: Use seconds as the internal unit

All overtime computations will use integer seconds.

Rationale:

- Timewarrior data is second-based; minute truncation is unnecessary and surprising.
- A single unit across `Expected`, `Actual`, `Overtime`, and totals simplifies correctness.

Alternatives considered:

- Keep minutes internally and compute new columns in seconds: rejected due to inconsistent precision.

### Decision: Derive day segments first, then compute all fields

Approach:

- Parse ended entries into local datetime intervals.
- Split each interval at local midnight boundaries into per-day segments.
- For each day, compute:
  - `Actual` as the sum of segment durations (seconds).
  - `From` as the earliest segment start time-of-day (clamped to `00:00:00`).
  - `To` as the latest segment end time-of-day (clamped to end-of-day).
  - `Pause` as the sum of gaps between merged segments.

Rationale:

- This keeps `Actual`, `From`/`To`, and `Pause` consistent because they originate from the same segment set.

Alternatives considered:

- Compute `Pause` as `(To-From) - Actual` without merging: rejected because overlaps can yield negative pause.

### Decision: Ignore active entries everywhere

Only entries containing `end` are included in segment generation.

Rationale:

- Keeps `From`/`To`/`Pause` consistent with `Actual` and the existing behavior.
- Avoids ambiguous reporting for an in-progress day.

### Decision: Output formatting

- Clock times: `From` and `To` use `HH:MM:SS`.
- Durations: `Expected`, `Actual`, `Overtime`, weekly `Total`, and `Pause` use `H:MM:SS`.
- Signed durations: `Overtime` and `Total` are prefixed with `+` or `-` when non-zero.

Rationale:

- Clock times should be fixed-width and scanable.
- Durations should avoid zero-padding hours to reduce noise.

### Decision: Column order

`overtime_summary` columns:

`Wk | Date | Day | From | To | Pause | Expected | Actual | Overtime | Total`

`overtime_csv` columns:

`Date,From,To,Pause,Expected,Actual,Overtime`

## Risks / Trade-offs

- Breaking output changes (headers and formats) → Mitigation: update docs; call out breaking changes in proposal/spec.
- Wider tables may wrap in narrow terminals → Mitigation: rely on existing dynamic width logic; keep time formats compact.
- Timezone boundary correctness depends on system tzinfo → Mitigation: keep current `.astimezone()` behavior and document that local time drives splitting.
- Overlapping/adjacent intervals could affect pause → Mitigation: merge intervals before gap calculation.

## Migration Plan

- Update both reports and docs together in one release.
- Users relying on the prior overtime CSV decimal-hour schema must update their downstream parsers.

## Open Questions

- None currently; behavior is fully specified in proposal/spec.
