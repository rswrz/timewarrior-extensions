## ADDED Requirements

### Requirement: Absorption is opt-in via absorb tag
The dynamics_* reports MUST only apply absorption behavior when the resolved configuration key `reports.dynamics.absorb_tag` is present and non-empty.

#### Scenario: Absorb tag missing disables absorption
- **WHEN** `reports.dynamics.absorb_tag` is missing or resolves to an empty value
- **THEN** the report output is computed without any absorption behavior

#### Scenario: Absorb tag set enables absorption
- **WHEN** `reports.dynamics.absorb_tag` resolves to a non-empty tag name
- **THEN** the report classifies entries containing that tag as absorbable admin time

### Requirement: Absorbable entries are classified by contains-tag
The dynamics_* reports MUST classify a Timewarrior entry as absorbable when its tag set contains the configured absorb tag, even if it also contains additional tags.

#### Scenario: Entry contains absorb tag and other tags
- **WHEN** a Timewarrior entry has tags that include the absorb tag and include other mapping tags
- **THEN** the entry is treated as absorbable for absorption calculations while still using all tags for project mapping

### Requirement: Absorption is applied per day using only exported slack
When absorption is enabled, the dynamics_* reports MUST apply absorption independently per day and MUST only use slack from entries that would otherwise be exported.

#### Scenario: Excluded-tag entries do not contribute slack
- **WHEN** an entry is excluded from the Dynamics output due to `reports.dynamics.exclude_tags`
- **THEN** that entry contributes no slack to absorption calculations

#### Scenario: Absorption does not cross day boundaries
- **WHEN** a report range includes multiple days
- **THEN** absorbable admin time on one day is only absorbed into slack from non-absorb entries on the same day

### Requirement: Slack is computed pre-multiplier on consolidated line items
When absorption is enabled, the report MUST compute available slack on each day from non-absorb consolidated line items using their pre-multiplier raw duration and 15-minute rounding blocks.

#### Scenario: Multiplier does not increase slack
- **WHEN** a non-absorb consolidated line item has multiplier greater than 1
- **THEN** its slack contribution is computed from the pre-multiplier raw duration only

### Requirement: Absorption reduces absorbable line items
When absorption is enabled, the report MUST reduce the raw duration of absorbable consolidated line items by consuming available slack on the same day, and MUST omit any absorbable line item whose resulting raw duration becomes zero.

#### Scenario: Absorbable time fully fits in slack
- **WHEN** total absorbable raw time on a day is less than or equal to total slack on that day
- **THEN** no absorbable line item is exported for that day

#### Scenario: Absorbable time exceeds slack
- **WHEN** total absorbable raw time on a day exceeds total slack on that day
- **THEN** the remaining absorbable time after slack consumption is exported and rounded like any other line item

### Requirement: Summary report shows absorption note
When absorption is enabled and the input contains at least one absorbable entry, `dynamics_summary` MUST display an informational footer describing per-day slack, absorbed time, and any leftover exported absorbable time.

#### Scenario: Footer is not shown when absorption is disabled
- **WHEN** absorption is disabled
- **THEN** `dynamics_summary` does not display the absorption footer
