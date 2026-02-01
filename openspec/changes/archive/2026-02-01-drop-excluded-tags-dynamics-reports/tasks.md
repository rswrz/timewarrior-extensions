## 1. Config parsing

- [x] 1.1 Read Timewarrior report header in dynamics_csv.py to extract `reports.dynamics.exclude_tags`
- [x] 1.2 Replace header skip in dynamics_summary.py with header parsing for the same key
- [x] 1.3 Normalize exclusion list (split on commas, trim, ignore empties)

## 2. Entry filtering

- [x] 2.1 Skip any time entries in dynamics_csv.py whose tags intersect the exclusion list
- [x] 2.2 Skip any time entries in dynamics_summary.py whose tags intersect the exclusion list

## 3. Documentation

- [x] 3.1 Document `reports.dynamics.exclude_tags` in docs/dynamics_csv.md (behavior + example)
- [x] 3.2 Document `reports.dynamics.exclude_tags` in docs/dynamics_summary.md (behavior + note about report header)
