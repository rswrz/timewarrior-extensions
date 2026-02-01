## Why

Fixed-width table layouts in `table_summary.py` and `dynamics_summary.py` often waste space on wide terminals and wrap awkwardly on narrow terminals. A dynamic-width layout aligned to terminal size improves readability without adding configuration overhead.

## What Changes

- Compute table column widths based on detected terminal width, distributing remaining space across elastic columns.
- When output is non-TTY, treat width as unlimited so columns expand to content without forced truncation.
- Allow narrow terminals to wrap lines as needed rather than forcing a fixed width.

## Capabilities

### New Capabilities
- `summary-dynamic-table-widths`: Summary tables adapt column widths to terminal size with elastic columns and sensible fallback behavior for non-TTY output.

### Modified Capabilities
- (none)

## Impact

- Affects `table_summary.py` and `dynamics_summary.py` table layout logic.
- No new dependencies; uses standard library terminal sizing.
