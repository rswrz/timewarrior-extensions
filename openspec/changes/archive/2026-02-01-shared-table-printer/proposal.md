## Why

The summary reports each implement their own terminal table rendering, which leads to duplicated logic and inconsistent row striping. Consolidating table printing into a shared library improves readability, consistency, and maintainability across overtime, dynamics, and table summaries.

## What Changes

- Introduce a shared table printer module for summary reports, providing terminal-aware column sizing, per-row striping, and wrapping.
- Update overtime_summary, dynamics_summary, and table_summary to use the shared table printer for consistent rendering and striping.
- Standardize odd-row background striping across summary reports while preserving report-specific highlights (e.g., missing annotation, overtime sign).

## Capabilities

### New Capabilities
- `summary-table-printer`: Shared table printer for terminal summaries, including column sizing, wrapping, and row striping.

### Modified Capabilities
- None.

## Impact

- New shared table printer module added near summary utilities.
- Summary report scripts (overtime_summary.py, dynamics_summary.py, table_summary.py) updated to use the shared rendering path.
- Terminal width handling and wrapping rules centralized.
