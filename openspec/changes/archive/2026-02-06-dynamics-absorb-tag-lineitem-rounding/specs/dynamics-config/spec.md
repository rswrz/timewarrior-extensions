## MODIFIED Requirements

### Requirement: Supported header keys
The dynamics_* reports MUST read the following Timewarrior header keys when present: `reports.dynamics.config_file`, `reports.dynamics.annotation_delimiter`, `reports.dynamics.annotation_output_separator`, `reports.dynamics.exclude_tags`, `reports.dynamics.absorb_tag`, and `reports.dynamics.llm.*`.

#### Scenario: Header provides a supported key
- **WHEN** the Timewarrior report header contains any supported `reports.dynamics.*` key
- **THEN** the resolved configuration includes that value

#### Scenario: Header omits a supported key
- **WHEN** a supported `reports.dynamics.*` key is not present in the header
- **THEN** the resolved configuration falls back to defaults or environment overrides
