## Why

The Dynamics reports currently round each individual Timewarrior interval to 15 minutes before merging, which overstates time when multiple intervals later consolidate into a single exported line item. This change aligns rounding with the organization policy (round per exported line item) and enables optionally absorbing small admin/timetracking entries into existing rounding slack.

## What Changes

- **BREAKING**: Change Dynamics report rounding behavior to merge intervals into exported line items first, then round the consolidated line item to 15-minute blocks (policy B).
- Compute raw durations from exact seconds (not rounded minutes) and only round once per exported line item.
- Add optional per-day absorption of a special tagged entry (configured via `reports.dynamics.absorb_tag`) into pre-rounding slack of other exported line items on the same day.
- When absorption is enabled, `dynamics_summary` prints an informational footer showing per-day slack, absorbed amount, and any leftover exported admin time.

## Capabilities

### New Capabilities

- `dynamics-lineitem-rounding`: Consolidate intervals into exported line items and apply 15-minute rounding once per exported line item.
- `dynamics-absorb-tag`: Optionally absorb admin/timetracking entries (by tag) into available per-day rounding slack.

### Modified Capabilities

- `dynamics-config`: Add support for the `reports.dynamics.absorb_tag` configuration key.

## Impact

- Affected code: `dynamics_common.py` (record building/merging/rounding), `dynamics_csv.py`, `dynamics_summary.py`.
- Behavior: totals and per-line durations may decrease compared to the current per-interval rounding approach.
- Documentation: update Dynamics report docs to describe line-item rounding and absorption behavior.
