# Timewarrior Extensions

A collection of personal [Timewarrior](https://timewarrior.net/) [extensions](https://timewarrior.net/docs/extensions/) to enhance my time tracking workflow.

## Extensions

- `dynamics_csv.py` — Export + merge entries to CSV (Dynamics‑ready), with tag→project mapping, rounding, and optional LLM description refinement. See [`docs/dynamics_csv.md`](docs/dynamics_csv.md)
- `dynamics_summary.py` — Table view using Dynamics logic (merging, rounding, config). See [`docs/dynamics_summary.md`](docs/dynamics_summary.md)
- `zoho.py` — Export entries to a Zoho-compatible CSV with tag-based project/task mapping and note merging. See [`docs/zoho.md`](docs/zoho.md)
- `csv.py` — Output raw `timew export` entries as a simple CSV. See [`docs/csv.md`](docs/csv.md)
- `table.py` — Colorized summary view with annotations, gaps, and totals. See [`docs/table.md`](docs/table.md)
- `debug.py` — Print the incoming Timewarrior payload to stdout unchanged (handy for troubleshooting pipelines).

## JSON5 Support (Optional)

The extentsions optionally support to write the configuration in `JSON5` format allowing for more human-friendly features like Comments (`//` or `/* */`) or trailing commas.  
To enable JSON5 support, install the optional dependency:

```bash
pip3 install -r requirements.txt
```

## Useful Aliases & Functions

For a set of helpful aliases and shell functions, visit the <https://github.com/rswrz/timewarrior>.
