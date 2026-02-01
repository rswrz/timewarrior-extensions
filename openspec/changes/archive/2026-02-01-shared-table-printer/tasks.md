## 1. Shared Table Printer Module

- [x] 1.1 Define column config and table printer API (headers, rows, column config, stripe/highlight hooks)
- [x] 1.2 Implement terminal-aware width calculation with elastic and min-width support
- [x] 1.3 Implement row rendering with wrapping, explicit newline handling, and per-row striping
- [x] 1.4 Add highlight hook integration (row/cell styling layered with striping)

## 2. Update Summary Reports

- [x] 2.1 Refactor dynamics_summary to use the shared printer with its existing wrapping and highlight rules
- [x] 2.2 Refactor table_summary to use the shared printer with annotation/total behaviors preserved
- [x] 2.3 Refactor overtime_summary to use the shared printer and apply per-day row striping

## 3. Validation

- [x] 3.1 Verify output width behavior on constrained terminal widths
- [x] 3.2 Verify striping consistency and highlight layering across all three summaries
