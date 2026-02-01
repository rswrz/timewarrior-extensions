## Why

Time entries tagged for vacation, sick, or holiday are required for overtime tracking but should not flow into Dynamics exports. A configurable exclusion list prevents unwanted entries while keeping overtime_* behavior intact and future-proof.

## What Changes

- Read a new Timewarrior config key `reports.dynamics.exclude_tags` (comma-separated).
- Drop any dynamics_* report entries that contain at least one excluded tag.
- Document the new configuration in the Dynamics report docs.

## Capabilities

### New Capabilities
- `dynamics-exclude-tags`: Allow dynamics_* reports to drop entries matching a configured tag exclusion list.

### Modified Capabilities

## Impact

- `dynamics_csv.py` and `dynamics_summary.py` filter entries based on report header config.
- `docs/dynamics_csv.md` and `docs/dynamics_summary.md` gain the new config key description.
