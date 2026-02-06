# dynamics-lineitem-rounding Specification

## Purpose
TBD - created by archiving change dynamics-absorb-tag-lineitem-rounding. Update Purpose after archive.
## Requirements
### Requirement: Round durations per exported line item
The dynamics_* reports MUST compute billable duration by consolidating matching intervals into exported line items first, then rounding the consolidated duration to 15-minute blocks once per exported line item.

#### Scenario: Multiple intervals consolidate and round once
- **WHEN** multiple Timewarrior intervals map to the same exported line item (same date, project, project task, role, type, and merge rules)
- **THEN** the exported line item duration is calculated from the sum of their raw durations and rounded once to the next 15-minute block

#### Scenario: Fragmentation does not increase rounded time
- **WHEN** a user splits work for the same exported line item into multiple Timewarrior intervals
- **THEN** the exported rounded duration is the same as if the work had been tracked as one continuous interval with the same total duration

### Requirement: Use exact seconds for raw duration
The dynamics_* reports MUST derive raw durations from exact interval seconds and MUST NOT round to minutes before applying 15-minute rounding.

#### Scenario: Seconds are preserved through consolidation
- **WHEN** a Timewarrior interval duration includes non-zero seconds
- **THEN** the report includes those seconds when summing raw durations for a consolidated line item

### Requirement: Apply multiplier before 15-minute rounding
The dynamics_* reports MUST apply the configured per-project multiplier to the consolidated raw duration before rounding the exported duration to 15-minute blocks.

#### Scenario: Multiplier affects the rounded line item
- **WHEN** a consolidated line item has raw duration D and multiplier M
- **THEN** the report rounds (D × M) up to the next 15-minute block to produce the exported duration

