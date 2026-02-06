## 1. Config And Data Model

- [x] 1.1 Add `reports.dynamics.absorb_tag` to resolved configuration (header + env)
- [x] 1.2 Introduce an internal draft/atom representation that carries exact `raw_seconds`, tags, mapping, and formatting through merging

## 2. Line-Item Rounding (Policy B)

- [x] 2.1 Refactor Dynamics record building to merge intervals into draft line items before any 15-minute rounding
- [x] 2.2 Apply multiplier and 15-minute rounding once per consolidated line item using 900-second blocks
- [x] 2.3 Ensure description merging behavior and merge keys remain consistent with current Dynamics reports
- [x] 2.4 Ensure LLM refinement (if enabled) still runs after merging and uses the final description string

## 3. Absorption By Tag

- [x] 3.1 Classify absorbable admin entries by "contains absorb tag" while still resolving project mapping from all tags
- [x] 3.2 Compute per-day slack from non-absorb consolidated line items using pre-multiplier raw seconds
- [x] 3.3 Reduce absorb-tag consolidated line items by consuming available slack; drop admin line items reduced to zero
- [x] 3.4 Confirm excluded-tag entries do not contribute slack and do not participate in absorption

## 4. Summary Footer

- [x] 4.1 Add `dynamics_summary` footer that prints per-day slack/absorbed/leftover when absorption is enabled and absorb-tag entries exist
- [x] 4.2 Ensure footer does not affect table totals and is omitted when absorption is disabled

## 5. Documentation And Validation

- [x] 5.1 Update `docs/dynamics_csv.md` to describe line-item rounding and the new absorb-tag behavior
- [x] 5.2 Update `docs/dynamics_summary.md` to describe the absorption footer
- [x] 5.3 Manually validate with representative examples (fragmented intervals, multiplier > 1, absorption fits vs leftover)
