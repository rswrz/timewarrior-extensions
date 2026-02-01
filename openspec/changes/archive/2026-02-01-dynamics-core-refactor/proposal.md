## Why

The dynamics_csv and dynamics_summary reports duplicate core logic and diverge in how they resolve configuration (env vs header). Consolidating the core and formalizing config precedence improves consistency and makes future changes safer.

## What Changes

- Introduce a shared `dynamics_common.py` core that produces a canonical Dynamics record used by both reports.
- Move LLM refinement configuration into the shared core (summary can opt in later).
- Add Timewarrior header configuration keys for Dynamics report settings.
- **BREAKING** Rename Dynamics environment variables to mirror `reports.dynamics.*` header keys (env now uses `TIMEWARRIOR_REPORTS_DYNAMICS_*`).
- Define config precedence as defaults -> header -> env override.
- Update docs for the new configuration sources and env names.

## Capabilities

### New Capabilities
- `dynamics-config`: Resolve Dynamics report configuration from defaults, Timewarrior header keys, and env overrides with standardized key mapping.

### Modified Capabilities
- None

## Impact

- New shared core module: `dynamics_common.py`.
- Refactor `dynamics_csv.py` and `dynamics_summary.py` to consume the shared core.
- Documentation updates in `docs/dynamics_csv.md` and `docs/dynamics_summary.md`.
- Users must update environment variable names to the new `TIMEWARRIOR_REPORTS_DYNAMICS_*` scheme.
