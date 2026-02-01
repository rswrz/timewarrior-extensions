## Purpose

Define how summary table layouts adapt to terminal size and allocate widths across elastic columns.

## Requirements

### Requirement: Table width adapts to terminal size
When stdout is a TTY, summary tables MUST size their columns to fit within the detected terminal width and distribute any remaining space to elastic columns.

#### Scenario: TTY width drives allocation
- **WHEN** a summary report is rendered to a TTY with a detected width
- **THEN** the computed table layout fits within that width by allocating remaining space to elastic columns

### Requirement: Non-TTY output uses content width unless stderr is a TTY
When stdout is not a TTY, summary tables MUST use stderr terminal width if stderr is a TTY; otherwise they MUST compute column widths from headers and content without applying a terminal width limit.

#### Scenario: Output redirected with stderr TTY
- **WHEN** a summary report is rendered with stdout not attached to a TTY and stderr attached to a TTY
- **THEN** column widths are based on the stderr terminal width

#### Scenario: Output redirected without stderr TTY
- **WHEN** a summary report is rendered with stdout not attached to a TTY and stderr not attached to a TTY
- **THEN** column widths are based on header and content lengths without an 80-column fallback limit

### Requirement: Elastic columns by report
Each summary report MUST treat specific columns as elastic for width allocation.

#### Scenario: Table summary elastic columns
- **WHEN** `table_summary.py` computes a layout
- **THEN** the Tags and Annotation columns receive remaining width allocation after fixed columns are sized

#### Scenario: Dynamics summary elastic columns
- **WHEN** `dynamics_summary.py` computes a layout
- **THEN** the Project, Project Task, Description, and External Comments columns receive remaining width allocation after fixed columns are sized
