# Table Timewarrior Extension

`table_summary.py` prints a colorized summary similar to `timew summary`, but with extra context (annotations split into bullet-style lines, gaps between entries, and grand totals).

## Usage

- As a Timewarrior report: `timew report table_summary :today`
- Pipe directly: `timew export :today | ./table_summary.py`

The extension reads stdin (after the header block) and writes a formatted table to stdout.

## Columns

- `Wk` – ISO week number (only on the first entry of a day)
- `Date` / `Day` – date and weekday (first entry per day)
- `ID` – record identifier (`@id`)
- `Tags` – comma-separated tag list
- `Annotation` – annotation split by `; ` into multi-line items (long lines wrapped at 100 chars)
- `Start` / `End` – local times; active entries show an empty End
- `Time` – interval duration
- `Total` – cumulative day total on the last row of each day

Entries are colored in alternating backgrounds; missing annotations show in a distinct color. Gaps between entries within the same day are highlighted with a “-” row indicating the idle period.

## Range Handling

The script honors the range supplied by Timewarrior’s report API (e.g. `Range: 20240921T000000Z - 20240922T000000Z`). Intervals are clipped to this span before rendering and split at midnight so work crossing days is shown once per day with appropriate durations.

## Totals

- Day totals reset whenever the date changes and appear on the final entry for that day.
- A grand total (HH:MM:SS) prints under the table.

## Formatting Notes

- Long annotation items wrap at 100 characters; continuation lines are indented.
- Hidden segments using `++secret++` remain part of the display (matching the default summary behavior).
- Color codes use ANSI escape sequences; when piping to plain text files, colors remain in the output.
