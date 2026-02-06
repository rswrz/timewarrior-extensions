## Purpose

Define how dynamics_* reports resolve configuration from defaults, Timewarrior header keys, and environment variables.
## Requirements
### Requirement: Configuration precedence
The dynamics_* reports MUST resolve configuration in this order: built-in defaults, then Timewarrior header keys, then environment variables.

#### Scenario: Header overrides defaults
- **WHEN** a configuration value is present in the Timewarrior report header
- **THEN** the resolved configuration uses the header value instead of the default

#### Scenario: Environment overrides header
- **WHEN** a configuration value is present in both the header and environment variables
- **THEN** the resolved configuration uses the environment variable value

#### Scenario: No overrides present
- **WHEN** a configuration value is absent from both the header and environment variables
- **THEN** the resolved configuration uses the built-in default

### Requirement: Supported header keys
The dynamics_* reports MUST read the following Timewarrior header keys when present: `reports.dynamics.config_file`, `reports.dynamics.annotation_delimiter`, `reports.dynamics.annotation_output_separator`, `reports.dynamics.exclude_tags`, `reports.dynamics.absorb_tag`, and `reports.dynamics.llm.*`.

#### Scenario: Header provides a supported key
- **WHEN** the Timewarrior report header contains any supported `reports.dynamics.*` key
- **THEN** the resolved configuration includes that value

#### Scenario: Header omits a supported key
- **WHEN** a supported `reports.dynamics.*` key is not present in the header
- **THEN** the resolved configuration falls back to defaults or environment overrides

### Requirement: Environment key mapping
The dynamics_* reports MUST map header keys to environment variables by uppercasing, replacing dots with underscores, and prefixing with `TIMEWARRIOR_`.

#### Scenario: Environment overrides a header key
- **WHEN** `reports.dynamics.annotation_output_separator` is set in the header and `TIMEWARRIOR_REPORTS_DYNAMICS_ANNOTATION_OUTPUT_SEPARATOR` is set in the environment
- **THEN** the resolved configuration uses the environment variable value

### Requirement: Config file selection
The dynamics_* reports MUST load per-project mappings from the resolved `reports.dynamics.config_file` path.

#### Scenario: Header sets config file
- **WHEN** `reports.dynamics.config_file` is set in the Timewarrior report header
- **THEN** the report loads the project config from that path

#### Scenario: Config file not overridden
- **WHEN** `reports.dynamics.config_file` is absent from header and environment
- **THEN** the report loads the project config from the built-in default path

### Requirement: LLM configuration source
The dynamics_* reports MUST resolve LLM settings from the effective `reports.dynamics.llm.*` configuration keys.

#### Scenario: LLM settings provided in environment
- **WHEN** `TIMEWARRIOR_REPORTS_DYNAMICS_LLM_MODEL` is set in the environment
- **THEN** the resolved configuration uses that model value

