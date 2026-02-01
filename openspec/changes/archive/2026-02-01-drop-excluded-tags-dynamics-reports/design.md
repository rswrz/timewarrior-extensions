## Context

The Dynamics reports currently emit every completed Timewarrior entry that matches a project mapping. Users rely on special tags like vacation, sick, and holiday for overtime_* calculations, but those entries should not appear in Dynamics exports. The new behavior must rely on Timewarrior report configuration so it can be adjusted without code changes, and it should not alter overtime_* behavior.

## Goals / Non-Goals

**Goals:**
- Read `reports.dynamics.exclude_tags` from the Timewarrior report header and treat it as a comma-separated tag list.
- Drop any dynamics_* report entry whose tags intersect the excluded set.
- Apply the same filtering behavior to both `dynamics_csv.py` and `dynamics_summary.py`.

**Non-Goals:**
- Modify overtime_* logic or other report extensions.
- Add new environment variables or config files for exclusions.
- Implement partial tag matching (only exact tag names are compared).

## Decisions

- **Drop entries vs. remove tags:** Drop entries entirely when any excluded tag is present, because the downstream Dynamics tools should not receive those entries at all. Alternative considered: remove excluded tags before matching, which could still allow unwanted entries to appear.
- **Configuration source:** Read the exclusion list from the Timewarrior report header key `reports.dynamics.exclude_tags` to align with Timewarrior config conventions. Alternative considered: add a new JSON config entry or environment variable, which would require more setup and diverge from Timewarrior report configuration.
- **Parsing strategy:** Split on commas, trim whitespace, and ignore empty tokens to tolerate `a, b, , c`. Alternative considered: strict parsing with error output, which adds friction without clear benefit.
- **Header handling:** When the report header is missing (e.g., direct `timew export` piping), treat the exclusion list as empty to preserve current behavior. Alternative considered: erroring on missing header, which would be a breaking change for direct usage.

## Risks / Trade-offs

- [Unexpected missing entries] → Users may forget they configured exclusions and think entries are lost; mitigate by documenting the key in both Dynamics docs.
- [Direct pipe behavior] → `timew export | dynamics_*` will not apply exclusions because it lacks the header; mitigate by documenting that exclusions are read from report config and suggesting `timew report` usage.
