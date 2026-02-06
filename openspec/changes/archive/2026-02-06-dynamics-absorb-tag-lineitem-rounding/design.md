## Context

The `dynamics_csv` and `dynamics_summary` reports build `DynamicsRecord` entries from Timewarrior export data.

Current behavior rounds each individual Timewarrior interval to 15-minute blocks (after applying the per-project multiplier) and then merges records by day + project/task/role/type. This produces inflated totals when multiple intervals consolidate into a single exported line item, and it manufactures rounding slack at the interval level.

The organization policy for Dynamics export is:

- Round each exported timesheet line item to 15-minute blocks (not each raw interval).

Additionally, some admin work (e.g. end-of-day/week time tracking review) is difficult to allocate to a single customer. The goal is to optionally absorb that admin time into natural rounding slack of other exported line items on the same day.

## Goals / Non-Goals

**Goals:**

- Implement policy B permanently: merge intervals into exported line items first, then apply multiplier and 15-minute rounding once per exported line item.
- Compute raw durations using exact seconds (avoid rounding to minutes before applying 15-minute rounding).
- Add opt-in absorption behavior controlled by a single header/env config value: `reports.dynamics.absorb_tag`.
- Apply absorption per day and only using slack from entries that are actually exported (i.e. after exclude-tag filtering).
- Preserve mapping via tags: the absorb-tag entries can include normal mapping tags; classification is "contains absorb_tag".
- Add a human-readable note to `dynamics_summary` showing per-day slack/absorption effects when absorption is enabled.

**Non-Goals:**

- Supporting multiple absorb tags or multiple absorption buckets.
- Keeping backward-compatible interval-rounding semantics.
- Adding a `reports.dynamics.rounding_unit` toggle (avoid branching complexity).

## Decisions

1) Restructure the build pipeline into phases

- Phase 1: Parse and normalize Timewarrior intervals into internal "atoms" with exact `raw_seconds` and resolved mapping context (project/task/role/type, delimiter/separator, multiplier, etc.). No 15-minute rounding occurs in this phase.
- Phase 2: Merge atoms into draft line items using the existing merge key (date + project/task/role/type and current description merge rules).
- Phase 3: If absorption is enabled, run a per-day absorption pass over draft line items before any rounding is applied.
- Phase 4: Finalize draft line items into `DynamicsRecord` by applying multiplier and rounding to 15-minute blocks once per line item.

Rationale: This keeps rounding aligned with the line-item unit and prevents fragmentation of intervals from inflating billed time.

2) Use exact seconds for rounding math

- Raw duration is tracked in seconds: `raw_seconds = (end - start).total_seconds()`.
- Rounding uses 900-second (15-minute) blocks:
  - `rounded_seconds = ceil((raw_seconds * multiplier) / 900) * 900`
  - `duration_minutes = rounded_seconds / 60`

Rationale: exact seconds avoids error accumulation from intermediate minute rounding and matches the conceptual 15-minute block policy.

3) Absorption configuration and classification

- Add config key `reports.dynamics.absorb_tag`.
- Absorption is disabled when the resolved value is missing or empty.
- Any entry/line item whose tags contain `absorb_tag` is classified as absorbable admin time, even if it also contains normal mapping tags.

Rationale: keeps control in the user's tags/config mapping and avoids fragile "tag set equals" rules.

4) Absorption algorithm: adjust existing absorb-tag line items (no synthetic mapping)

For each day (based on the same date bucketing used for exported line items):

- Compute slack pool from non-absorb line items using pre-multiplier raw seconds:
  - `slack_seconds(line) = ceil(raw_seconds/900)*900 - raw_seconds`
- Compute total absorbable admin seconds from absorb-tag line items.
- Reduce absorb-tag line items by consuming slack seconds (deterministic order, e.g. stable by appearance) until slack is exhausted.
- Drop any absorb-tag line items that become zero.
- Any remaining admin seconds stay attached to their existing mapping and will be rounded as a normal exported line item.

Rationale: preserves the user's project/task/role/type mapping for leftovers via tags and avoids introducing a new special mapping layer.

5) `dynamics_summary` absorption note

When absorption is enabled and the input contains at least one absorb-tag entry, print a footer after totals:

- One line per day with: slack available, admin raw seconds, admin absorbed seconds, admin leftover seconds, and the exported rounded duration for leftover (if any).

Rationale: provides auditability without changing CSV schema or polluting the table rows.

## Risks / Trade-offs

- Behavior change: totals will likely decrease vs interval-rounding; this is intended but may surprise users. → Document clearly as a breaking change.
- Merge rules and rounding unit interaction: merging descriptions changes which line items exist, which affects rounding and slack. → This matches policy B (round per exported line item) but should be highlighted in docs.
- Deterministic ordering for absorption: different ordering could shift which admin line retains leftover time. → Use a stable, easy-to-explain ordering (e.g. stable by build order).
