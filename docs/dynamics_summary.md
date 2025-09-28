# Dynamics Summary Report

`dynamics_summary.py` combines the Dynamics report logic (tag-based project mapping, rounding, merging) with the console table presentation of `table.py`. The result is a readable table view that still honours the Dynamics configuration.

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
- `Duration` – rounded to the next 15 minutes (HH:MM)

Descriptions and comments are rendered as multi-line cells; hidden segments (`++secret++`) are removed from display.

## Configuration

The report honours the same sources as the Dynamics CSV report, but only through `.dynamics_config.json` and environment variables:

1. Per-project overrides from `.dynamics_config.json`
2. Environment variables (`TIMEWARRIOR_EXT_DYNAMICS_…`)
3. Built-in defaults

Supported environment variables mirror the CSV exporter:

- `TIMEWARRIOR_EXT_DYNAMICS_CONFIG_JSON`
- `TIMEWARRIOR_EXT_DYNAMICS_ANNOTATION_DELIMITER`
- `TIMEWARRIOR_EXT_DYNAMICS_OUTPUT_SEPARATOR`

## Merging & Rounding

Entries are rounded to 15-minute blocks (configurable per project with `multiplier`). Records on the same day with matching project/task/role/type are merged using the same logic as the Dynamics CSV report, preventing duplicates in the table.

## Totals

The table ends with a grand total of all displayed durations, formatted as `HH:MM:SS`.

## Colours

Like `table.py`, the output uses simple ANSI highlighting (alternating row shading and a distinct colour for missing descriptions). When piping to files that don’t support colour, the escape codes remain visible.
