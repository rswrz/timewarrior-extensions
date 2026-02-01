# AI Agent Guide

This repo contains Timewarrior report extensions implemented as standalone Python scripts.
The goal of this guide is to make AI-assisted work safe, consistent, and low friction.

## Repo layout

- Extension scripts live at the repo root (e.g. `dynamics_csv.py`, `table_summary.py`).
- Per-extension documentation lives in `docs/`.
- Example config files use `*_config_example.json` and should never contain real secrets.

## Timewarrior extension contract

- Timewarrior passes a header block, then a blank line, then a JSON array of entries.
- The header block is the full Timewarrior configuration and may include
  extension-specific keys, plus `temp.*` metadata.
- Extensions must read from stdin and write to stdout.
- Active entries may omit `end`.
- Timestamps use `YYYYMMDDTHHMMSSZ` or `YYYYMMDDTHHMMSS+0000` formats.

See `docs/extension_primer.md` for a short overview of the input/output flow.

## Conventions in this repo

- CSV exporters: `*_csv.py`
- Console summaries: `*_summary.py`
- Configs are JSON (JSON5 optional via `requirements.txt`).
- Environment variable prefixes:
  - `TIMEWARRIOR_EXT_<NAME>_...`
  - `TIMEWARRIOR_EXT_DYNAMICS_...`
  - `TIMEWARRIOR_EXT_ZOHO_...`
  - `TIMEWARRIOR_EXT_OVERTIME_...`

## Safety and secrets

- Do not commit real config files. Use `*_config_example.json` only.
- Never add API keys or tokens to source control.
- If a change needs a new config key, document it in the matching `docs/*.md` file.

## How to run extensions

- Report mode (preferred): `timew report <ext> :week`
- Direct pipe: `timew export :week | ./<ext>.py` (missing header)
- Use `debug.py` report extension to inspect raw input for troubleshooting: `timew report debug :week`

## Working with AI agents

- Keep edits focused and minimal.
- Preserve existing behavior unless a change is explicitly requested.
- Update or add docs whenever behavior or config changes.
- Avoid introducing new dependencies unless clearly needed.
