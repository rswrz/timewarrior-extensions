# Zoho Timewarrior Extension

`zoho.py` exports Timewarrior entries as CSV rows ready to import into Zoho, handling project/task lookups, quarter-hour rounding, and note merging.

## Usage

- As a report extension: `timew report zoho :week > zoho.csv`
- Or via pipe: `timew export :week | ./zoho.py > zoho.csv`

The script reads the JSON export from stdin (after Timewarrior’s header block) and writes CSV to stdout.

## CSV Columns

1. Date (YYYY-MM-DD from the entry start time in local timezone)
2. Time Spent (`HH:MM`, rounded up to the next 15 minutes after multiplier)
3. Project Name
4. Task Name
5. Billable Status (`Billable` or `Non Billable`)
6. Notes (multiline; hidden markers removed)

## Tag→Project Mapping

- Config file is `.zoho_config.json` alongside the script; override with env var `TIMEWARRIOR_EXT_ZOHO_CONFIG_JSON`.
- Each mapping has a `tag` list plus metadata (`project_name`, `task_name`, etc.).
- Matching priorities:
  - Exact tag set match wins immediately.
  - Otherwise choose the mapping whose tags are a strict subset of the entry tags with the smallest remainder (most specific subset).
  - If nothing matches, fallback project name is `NO PROJECT FOUND FOR THESE TAGS: …` and task name is empty.

## Supported Config Keys per Mapping

- `tag` (array, required)
- `project_name` (string)
- `task_name` (string)
- `billable` (boolean → `Billable` vs `Non Billable`)
- `multiplier` (number, default 1)
- `note_prefix` (string prepended to Notes with a newline)

Example (`.zoho_config.json`):

```json
[
  {
    "tag": ["customer", "project"],
    "project_name": "Example Project",
    "task_name": "Research",
    "billable": true,
    "multiplier": 1.0,
    "note_prefix": "Customer Project"
  },
  {
    "tag": ["internal", "meeting"],
    "project_name": "Internal",
    "task_name": "Meetings",
    "billable": false
  }
]
```

## Notes Handling

- Timewarrior annotations are converted to multiline notes by replacing `; ` with `;\n`.
- `note_prefix` adds a line above the annotation content (always ending with `\n`).
- When multiple entries merge (same date/project/task/notes title), note items are deduplicated while preserving order.
- Segments wrapped in `++hidden++` are removed from the final CSV output.

## Merging Rules

Within a single day, entries are merged when:

1. Date, Project, Task, and Notes are identical → durations added.
2. Same Date/Project/Task and notes share the same first line → durations added and note items combined (unique entries, maintain order).

## Environment Variables

- `TIMEWARRIOR_EXT_ZOHO_CONFIG_JSON`: path to the JSON config file (default `.zoho_config.json`).

## Gotchas

- Active (non-ended) entries are skipped.
- Duration rounding always rounds *up* to the next quarter hour after applying `multiplier`.
- Time spent string trims trailing `:00` seconds (Zoho format expectation).

## Troubleshooting

- “No project found” rows mean the tag combination didn’t match any config entry.
- Double-check `note_prefix` usage if merged notes look duplicated: unique filtering happens per note segment.
- Inspect the CSV in a text editor if spreadsheet import appears misaligned; all fields are quoted for safety.

