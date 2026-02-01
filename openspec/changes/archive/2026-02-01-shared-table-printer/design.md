## Context

The summary report scripts (overtime_summary, dynamics_summary, table_summary) each implement their own terminal table rendering, with overlapping concerns such as column sizing, wrapping, header underlining, and row striping. Two scripts already share helper functions for terminal width and wrapping, but row rendering, striping logic, and highlight rules are duplicated and inconsistent.

## Goals / Non-Goals

**Goals:**
- Provide a shared table printer module for terminal summaries with terminal-aware column sizing, per-row striping, and optional wrapping.
- Make row striping consistent across summaries: stripe per logical row (entry/day) and apply to all printed lines from that row.
- Preserve report-specific highlights (e.g., missing annotation/description, overtime positive/negative) via explicit hooks.

**Non-Goals:**
- Redesign report data models or change report semantics beyond rendering.
- Introduce new external dependencies or formatting libraries.
- Change existing report configuration or input parsing behavior.

## Decisions

- **Introduce a shared table printer module** that accepts headers, row matrix, column config (alignment, wrap, elastic), and per-row styling hooks. This consolidates layout and rendering while keeping report-specific data preparation in each script.
  - *Alternative considered:* keep per-report renderers and only share width calculations. Rejected due to continued duplication of striping/highlight behavior.

- **Terminal-aware width calculation lives in the shared module**, reusing the existing allocation/wrapping logic and accepting per-column elastic + min-width settings.
  - *Alternative considered:* each report calculates widths and passes fixed widths to a dumb renderer. Rejected because it keeps width logic duplicated across reports.

- **Stripe per logical row, not per printed line.** A row with wrapped or newline-split cells uses the same background stripe for all its lines. This matches the readability goal and aligns with dynamics/table expectations and overtime day rows.
  - *Alternative considered:* stripe per printed line. Rejected as it breaks the visual grouping of multi-line rows.

- **Row/Cell highlight layering via hooks.** The renderer accepts optional callbacks to decorate rows/cells (e.g., overtime sign color on a specific column, missing annotation color for a row). The base stripe color is applied first; highlights can override or add foreground colors as needed.
  - *Alternative considered:* hard-code highlight rules in the shared module. Rejected to keep it generic and reusable.

## Risks / Trade-offs

- **Risk:** Existing reports rely on subtle formatting quirks (e.g., padding in total rows). → **Mitigation:** Keep report-specific total row formatting in each script and only use shared printer for main row rendering.
- **Risk:** Highlight + stripe color interactions could reduce readability. → **Mitigation:** Define a consistent layering order (stripe background first, highlight foreground second) and test on sample output.
- **Trade-off:** A more configurable renderer increases API surface. → **Mitigation:** Keep the column config minimal (alignment, wrap, elastic, min width) and default sensible behaviors.
