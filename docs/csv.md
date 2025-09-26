# CSV Timewarrior Extension

`csv.py` is a minimal report extension that converts the raw `timew export` payload into a simple CSV file.

## Usage

- Report mode (recommended): `timew report csv :week > entries.csv`
- Direct pipe: `timew export :week | ./csv.py > entries.csv`

The extension reads from stdin (after Timewarrior’s header section) and writes CSV lines to stdout.

## Output Columns

1. `Start` – UTC timestamp from the entry’s `start`
2. `End` – UTC timestamp from `end` (empty if the entry is still active)
3. `Annotation` – Raw annotation text
4. `Tags` – Tags joined with a single space between each tag

All fields are double-quoted and any embedded quotes/backslashes are escaped to keep the CSV valid.

## Input Assumptions

- The script ignores the configuration header that Timewarrior prepends when invoking a report.
- The JSON payload is expected to be the same shape as `timew export` (entries may omit `end`, `annotation`, or `tags`).

## Example

```
timew start projectA
timew annotate "Investigate issue"
timew stop
timew report csv :today
```

Produces CSV like:

```
"Start","End","Annotation","Tags"
"20240918T081500Z","20240918T091000Z","Investigate issue","projectA"
```

