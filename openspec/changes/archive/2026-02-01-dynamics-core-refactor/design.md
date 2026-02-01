## Context

The Dynamics CSV and summary reports currently duplicate parsing, merging, and configuration logic. Configuration is split between environment variables, per-project JSON, and (for exclude tags) the Timewarrior report header, which risks drift and inconsistent behavior. This change introduces a shared core module with a canonical record and standardized configuration resolution.

## Goals / Non-Goals

**Goals:**
- Provide a single shared core (`dynamics_common.py`) that produces canonical Dynamics records for both outputs.
- Standardize configuration precedence as defaults -> Timewarrior header -> environment variables.
- Align environment variable naming with header keys (`TIMEWARRIOR_REPORTS_DYNAMICS_*`).
- Keep existing mapping, rounding, merging, and LLM behavior stable.

**Non-Goals:**
- Changing the per-project JSON schema or mapping strategy.
- Altering CSV or summary output formats beyond config source changes.
- Enabling LLM refinement in the summary report in this change.

## Decisions

- **Canonical record in core.** The shared core returns a single Dynamics record shape consumed by both renderers, minimizing duplication and ensuring consistent merging behavior.
  - *Alternative:* separate CSV/Summary shapes from core. Rejected to avoid fragmentation.
- **Config resolution pipeline.** Config resolves in order: defaults -> header (`reports.dynamics.*`) -> env (`TIMEWARRIOR_REPORTS_DYNAMICS_*`).
  - *Alternative:* env-first or header-only. Rejected to support both report-embedded config and runtime overrides.
- **Header-aligned env naming.** Environment variables mirror header keys by uppercasing and replacing dots with underscores.
  - *Alternative:* keep legacy `TIMEWARRIOR_EXT_DYNAMICS_*`. Rejected due to early-stage willingness to break and desire for uniform mapping.
- **LLM config in core, summary opt-in later.** LLM settings are resolved in the shared config, but only CSV uses them initially.
  - *Alternative:* keep LLM confined to CSV. Rejected to centralize config and prepare for future summary usage.

## Risks / Trade-offs

- **Breaking env changes** -> Users must update env variables. Mitigation: update docs clearly and keep defaults usable.
- **Behavior drift during refactor** -> Shared core might subtly change merging or formatting. Mitigation: preserve existing logic and order of operations.
- **Header config parsing edge cases** -> Header may be absent when piping `timew export`. Mitigation: keep robust header detection and fall back to defaults/env.
- **LLM config placement** -> Risk of exposing API key in header. Mitigation: document that secrets should use env overrides.

## Migration Plan

- Implement shared core and refactor both reports to use it.
- Update documentation with new header keys, precedence, and env naming.
- Users update environment variable names to the new `TIMEWARRIOR_REPORTS_DYNAMICS_*` scheme.

## Open Questions

- Should the summary report ever enable LLM refinement, and if so under what flag?
