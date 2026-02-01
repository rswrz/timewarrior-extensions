## 1. Shared Layout Utilities

- [x] 1.1 Add terminal width detection helper that treats non-TTY as unlimited
- [x] 1.2 Define elastic width allocation logic with fixed vs elastic columns

## 2. Table Summary Layout

- [x] 2.1 Update `table_summary.py` column width computation to use terminal width
- [x] 2.2 Allocate remaining width across Tags and Annotation columns
- [x] 2.3 Verify narrow terminals wrap without errors

## 3. Dynamics Summary Layout

- [x] 3.1 Update `dynamics_summary.py` column width computation to use terminal width
- [x] 3.2 Allocate remaining width across Project, Project Task, Description, and External Comments columns
- [x] 3.3 Confirm non-TTY output uses content-based widths
