# Timewarrior Extension Primer

This repo contains Timewarrior **report extensions**. Each script reads the
Timewarrior report payload from stdin and writes its output to stdout.

Reference: <https://timewarrior.net/docs/api/>

## Input shape (from Timewarrior)

Timewarrior sends:

1. A header block (key/value lines)
2. A blank line
3. A JSON array of entries (same shape as `timew export`)

Example (conceptual):

```
color: on
confirmation: on
debug: off
journal.size: -1
temp.db: ~/.timewarrior
temp.extensions: ~/.timewarrior/extensions
temp.report.end: 20380119T000000Z
temp.report.start: 20380119T000000Z
temp.report.tags: example,example2
temp.version: 1.9.1
verbose: on

[{"id":1,"start":"20380119T031206Z","end":"20380119T031407Z","tags":["example","example2"],"annotation":"This is an example"}]
```

Notes:

- The header block is a copy of the full Timewarrior configuration. Extensions
  can read configuration values from it, including custom extension-specific
  settings. Temporary values are prefixed with `temp.` (for example, report
  range and version metadata).
- Active entries may omit `end`.
- Timestamp format is usually `YYYYMMDDTHHMMSSZ` or `YYYYMMDDTHHMMSS+0000`.
- Extensions should skip or handle active entries gracefully.

## Output contract

- Read from stdin, write to stdout.
- Do not write normal output to stderr (stderr is reserved for warnings/errors).
- Keep output deterministic for easy testing.

## How to run

Report mode:

```shell
timew report <ext> :week
```

Troubleshooting input, using the `debug.py` report:

```shell
timew report debug :week
```

## Configs and environment variables

- Config files live next to scripts and use `*_config_example.json` for examples.
- JSON5 is optional via `requirements.txt`.
- Environment variables follow the `TIMEWARRIOR_EXT_<NAME>_...` pattern.
- Timewarrior configuration entries can be read from the header, e.g.
  `report.<ext_name>.<key>: value`.

## Docs

- Each extension has a dedicated doc in `docs/` describing config, output, and usage details.
- Update those docs whenever behavior or config changes.
