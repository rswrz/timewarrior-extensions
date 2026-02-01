## Context

`table_summary.py` and `dynamics_summary.py` render ASCII tables with fixed or capped column widths, which leads to wasted space on wide terminals and awkward wrapping on narrow terminals. The change should stay within the standard library and avoid new configuration knobs. When output is non-TTY (piped/redirected), widths should expand to content without artificial limits.

## Goals / Non-Goals

**Goals:**
- Compute column widths based on detected terminal width when stdout is a TTY.
- Treat non-TTY output as unlimited width so tables expand to content.
- Keep layout readable by distributing remaining width across elastic columns.
- Avoid new dependencies and new configuration options.

**Non-Goals:**
- Perfectly preventing all line wrapping on very narrow terminals.
- Changing the table structure or adding new output columns.
- Introducing configurable width limits or user-tunable layout settings.

## Decisions

- **Use standard library terminal sizing**: Use `os.get_terminal_size()` for width detection. This avoids extra dependencies and works across platforms.
  - Alternative: external libraries like `rich`/`tabulate`. Rejected due to dependency and behavior changes.
- **TTY vs non-TTY behavior**: When stdout is not a TTY, attempt to size based on stderr if stderr is a TTY; otherwise treat width as effectively unlimited so column widths derive purely from content and headers.
  - Alternative: fall back to default 80 columns. Rejected because it artificially constrains redirected output.
- **Elastic column allocation**: Identify fixed columns (dates, ids, times, durations) and elastic columns (tags/annotation for table_summary; project/task/description/external for dynamics_summary). Allocate remaining width proportionally across elastic columns.
  - Alternative: hard caps per column. Rejected by requirement; ultra-wide terminals can use full width.
- **Narrow terminal behavior**: If calculated widths are smaller than some cell content, allow natural wrapping rather than truncating aggressively. This keeps behavior simple and matches user preference.

## Risks / Trade-offs

- **Very narrow terminals** → Rows may wrap across lines, reducing scanability. Mitigation: keep fixed columns minimal and let elastic columns absorb the squeeze.
- **Assumed terminal width** → Some environments provide inaccurate TTY width. Mitigation: non-TTY path avoids small defaults; TTY path relies on actual terminal size.
- **Formatting assumptions** → Python string formatting does not truncate, so long content can still overflow allocated widths. Mitigation: accept wrapping as acceptable in narrow terminals.
