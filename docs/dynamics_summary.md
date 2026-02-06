# Dynamics Summary Report

`dynamics_summary.py` combines the Dynamics report logic (tag-based project mapping, rounding, merging) with the console table presentation of `table_summary.py`. The result is a readable table view that still honours the Dynamics configuration.

## Usage

Run it like any other Timewarrior report:

```shell
timew report dynamics_summary :week
```

It skips the standard report header, reads the JSON payload from stdin, and writes an ANSI-coloured table to stdout.

## Columns

- `Date` – local date of the entry
- `Project` – project name from the Dynamics mapping
- `Project Task` – task name from the Dynamics mapping
- `Role`
- `Type`
- `Description` – annotation, split by the Dynamics delimiter and merged according to the Dynamics rules
- `External Comments`
- `Duration` – rounded to the next 15 minutes per exported line item (HH:MM)

Descriptions and comments are rendered as multi-line cells; hidden segments (`++secret++`) are removed from display.

## Configuration

Configuration is resolved in this order (later overrides earlier):

1. Built-in defaults
2. Timewarrior report header (`reports.dynamics.*`)
3. Environment variables (`TIMEWARRIOR_REPORTS_DYNAMICS_*`)

### Timewarrior report configuration

Example:

```
reports.dynamics.config_file = ~/.config/timew/dynamics.json
reports.dynamics.annotation_delimiter = ; 
reports.dynamics.annotation_output_separator = \n
reports.dynamics.exclude_tags = vacation, sick, holiday
```

Supported keys:

- `reports.dynamics.config_file`
- `reports.dynamics.annotation_delimiter`
- `reports.dynamics.annotation_output_separator`
- `reports.dynamics.exclude_tags`
- `reports.dynamics.absorb_tag` (optional)

Any entry containing one of the excluded tags is skipped entirely. This setting is read from the Timewarrior report header, so it applies when using `timew report dynamics_summary`.

### Environment Variables

- `TIMEWARRIOR_REPORTS_DYNAMICS_CONFIG_FILE`
- `TIMEWARRIOR_REPORTS_DYNAMICS_ANNOTATION_DELIMITER`
- `TIMEWARRIOR_REPORTS_DYNAMICS_ANNOTATION_OUTPUT_SEPARATOR`
- `TIMEWARRIOR_REPORTS_DYNAMICS_EXCLUDE_TAGS`

## Merging & Rounding

Entries are merged into exported line items first and then rounded to 15-minute
blocks once per exported line item (configurable per project with
`multiplier`). Records on the same day with matching project/task/role/type are
merged using the same logic as the Dynamics CSV report, preventing duplicates in
the table.

## Absorption footer (optional)

When `reports.dynamics.absorb_tag` is configured and the input contains at least
one entry with that tag, the summary prints an informational footer after the
total.

- It shows (per day): available slack, total absorb-tag raw time, how much was
  absorbed, leftover raw time, and (when leftover exists) the rounded exported
  time.
- The footer is informational only; it does not change the table rows or total.

## Totals

The table ends with a grand total of all displayed durations, formatted as `HH:MM:SS`.

## Colours

Like `table_summary.py`, the output uses simple ANSI highlighting (alternating row shading and a distinct colour for missing descriptions). When piping to files that don’t support colour, the escape codes remain visible.
