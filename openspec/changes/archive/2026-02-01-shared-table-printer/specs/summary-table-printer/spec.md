## ADDED Requirements

### Requirement: Render terminal table with headers and rows
The table printer SHALL accept a list of column headers and a row matrix of string cells and render a table with a single header line followed by row output.

#### Scenario: Header and rows are printed
- **WHEN** the printer is called with headers and at least one row
- **THEN** it prints an underlined header line followed by the rendered rows in order

### Requirement: Terminal-aware column sizing
The table printer SHALL compute column widths based on headers, cell content, and available terminal width, and SHALL allocate extra or reduced width only among columns marked as elastic.

#### Scenario: Constrained terminal width
- **WHEN** the terminal width is smaller than the total natural width
- **THEN** only elastic columns are reduced down to their minimum widths and the table fits the terminal width

### Requirement: Configurable wrapping and explicit line breaks
The table printer SHALL wrap long text only in columns marked as wrap-enabled and SHALL also respect explicit newline characters within any cell as hard line breaks.

#### Scenario: Wrapped and newline-split cells
- **WHEN** a row contains a wrap-enabled column with long text and a cell containing newline characters
- **THEN** the printer splits the cell by newline, wraps any long segments to the column width, and renders the row across multiple printed lines

### Requirement: Stripe rows by logical row index
The table printer SHALL apply alternating row striping based on the logical row index, and SHALL apply the same stripe background to all printed lines produced by that row.

#### Scenario: Multi-line row keeps one stripe
- **WHEN** a row expands into multiple printed lines due to wrapping or newline splits
- **THEN** all printed lines from that row use the same stripe background

### Requirement: Optional highlight hooks
The table printer SHALL support optional hooks to apply additional styling to specific rows or cells without changing the base stripe behavior.

#### Scenario: Row highlight applied
- **WHEN** a row highlight hook returns a style for a row
- **THEN** the row is rendered with the highlight in addition to the stripe background
