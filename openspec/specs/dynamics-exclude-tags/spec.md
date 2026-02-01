## Purpose

Define how dynamics_* reports drop entries based on excluded tags.

## Requirements

### Requirement: Excluded tags drop entries
The dynamics_* reports MUST drop any time entry that contains at least one tag listed in the Timewarrior configuration key `reports.dynamics.exclude_tags`.

#### Scenario: Entry includes excluded tag
- **WHEN** a time entry includes any tag from `reports.dynamics.exclude_tags`
- **THEN** the entry is excluded from the Dynamics report output

#### Scenario: Entry has no excluded tags
- **WHEN** a time entry contains none of the tags from `reports.dynamics.exclude_tags`
- **THEN** the entry is processed normally by dynamics_* reports

#### Scenario: Exclusion list is missing or empty
- **WHEN** `reports.dynamics.exclude_tags` is not provided or resolves to an empty list
- **THEN** no entries are excluded based on tags
