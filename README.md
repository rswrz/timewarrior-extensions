# Timewarrior Extensions

A collection of personal [Timewarrior](https://timewarrior.net/) [extensions](https://timewarrior.net/docs/extensions/) to enhance my time tracking workflow.

## Extensions

- `dynamics_csv.py` — Export + merge entries to CSV (Dynamics‑ready), with tag→project mapping, rounding, and optional LLM description refinement. See [`docs/dynamics_csv.md`](docs/dynamics_csv.md)
- `dynamics_summary.py` — Table view using Dynamics logic (merging, rounding, config). See [`docs/dynamics_summary.md`](docs/dynamics_summary.md)
- `zoho.py` — Export entries to a Zoho-compatible CSV with tag-based project/task mapping and note merging. See [`docs/zoho.md`](docs/zoho.md)
- `csv.py` — Output raw `timew export` entries as a simple CSV. See [`docs/csv.md`](docs/csv.md)
- `table.py` — Colorized summary view with annotations, gaps, and totals. See [`docs/table.md`](docs/table.md)
- `debug.py` — Print the incoming Timewarrior payload to stdout unchanged (handy for troubleshooting pipelines).

## Useful Aliases & Functions

For a set of helpful aliases and shell functions, visit the <https://github.com/rswrz/timewarrior>.

## 🧪 Experimentation

### Use `jq` for data manipulation

Source: <https://beko.famkos.net/2021/09/10/exporting-timewarrior-summary-with-duration-and-quarter-hours/>

```shell
timew export :week |
jq -r '["id", "start", "end", "duration", "quarter_hours", "description"],
(.[] |
    # make sure .end is set (may be empty for currently active tracked time)
    .end = (.end // (now | strftime("%Y%m%dT%H%M%SZ"))) |
    .duration = ( (.end | strptime("%Y%m%dT%H%M%SZ") | mktime) - (.start | strptime("%Y%m%dT%H%M%SZ") | mktime) ) |
    # round duration to quarter hours
    .quarter_hours = (.duration / 3600 / 0.25 | ceil*0.25) |
    [
        .id,
        # urks, localtimes are a mess in jq, ymmv - as long as it is consistent off I do not care tho
        (.start | strptime("%Y%m%dT%H%M%SZ") | mktime | todateiso8601),
        (.end | strptime("%Y%m%dT%H%M%SZ") | mktime | todateiso8601),
        (.duration | strftime("%T")),
        .quarter_hours,
        (.tags | join(", "))
    ]
) |
@csv'
```

```shell
timew export :month |
jq -r '["id", "start", "end", "duration", "quarter_hours", "tags", "description"],
(.[] |
    # make sure .end is set (may be empty for currently active tracked time)
    .end = (.end // (now | strflocaltime("%Y%m%dT%H%M%SZ"))) |
    .duration = ( (.end | strptime("%Y%m%dT%H%M%SZ") | mktime) - (.start | strptime("%Y%m%dT%H%M%SZ") | mktime) ) |
    # round duration to quarter hours
    .quarter_hours = (.duration / 3600 / 0.25 | ceil*0.25) |
    [
        .id,
        # urks, localtimes are a mess in jq, ymmv - as long as it is consistent off I do not care tho
        (.start | strptime("%Y%m%dT%H%M%SZ") | mktime | todateiso8601),
        (.end | strptime("%Y%m%dT%H%M%SZ") | mktime | todateiso8601),
        (.duration | strflocaltime("%T")),
        .quarter_hours,
        (.tags | join(", ")),
        .annotation
    ]
) |
@csv'
```
