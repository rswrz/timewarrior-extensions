# Dynamics Timewarrior Extension

Export and consolidate Timewarrior entries into a CSV ready for external systems (e.g., Dynamics), with smart tag→project mapping, merging, rounding, and optional LLM-powered description refinement.

## Usage

- As a Timewarrior report (recommended):
  - `timew report dynamics :week > times.csv`
- Or by piping JSON from `timew export`:
  - `timew export :week | ./dynamics.py > times.csv`

The script reads the Timewarrior report input from stdin per the Timewarrior extensions API and writes a CSV to stdout.

## CSV Columns

- Date
- Duration (minutes; rounded up to 15-minute blocks after multiplier)
- Project (id or name)
- Project Task (id or name)
- Role
- Type (defaults to "Work", overridable via config)
- Description (multiline cell; see Formatting)
- External Comments

## Tag Matching → Project Mapping

- Reads mappings from a JSON config (see Configuration).
- Matching strategy per time entry tags:
  - Exact set match wins immediately.
  - Otherwise choose the mapping whose `timew_tags` is a strict subset of the entry’s tags and has the smallest difference (most specific subset).
  - Fallbacks if nothing matches:
    - No tags → project: "NO TAGS DEFINED TO THIS TIME ENTRY".
    - Some tags but no match → project: "NO PROJECT FOUND FOR THESE TAGS: …".

## Merging Logic (same day + same project/task/role/type)

- Same description → durations are added.
- Same title (first segment before the annotation delimiter) → append unique list items, preserve order and cap total length.
- If `merge_on_equal_tags=true` in the matched config → merge regardless of description/title, deduplicate items.
- Combined description length is capped (default 500 chars); if exceeded, items are not merged further.

## Rounding and Multipliers

- Duration = ceil(round((end - start) × multiplier in minutes) / 15) × 15
- `multiplier` default is 1.0; can be configured per mapping.

## Description Formatting

- Input structure uses an annotation delimiter (default `; `). The description is typically `Title; item1; item2; …`.
- Any segment wrapped as `++hidden++` is excluded from the CSV output.
- Output formatting for the Description column joins segments with an output separator (default `;\n`) so list items render on separate lines inside a single CSV cell.

You can change both the input delimiter and the output separator globally via env vars or per mapping via config.

## Configuration

- Default location: `.dynamics_config.json` (alongside the script)
- Override via env var: `TIMEWARRIOR_EXT_DYNAMICS_CONFIG_JSON`

Each mapping object may include:

- `timew_tags` (array, required): tag set to match.
- `project` or `project_id` (string): exported Project value (prefers id).
- `project_task` or `project_task_id` (string): exported Project Task (prefers id).
- `role` (string)
- `type` (string, default "Work")
- `multiplier` (number, default 1)
- `merge_on_equal_tags` (boolean)
- `description_prefix` (string): prepended to the description (e.g., to enforce a title)
- `external_comment` (string)
- `annotation_delimiter` (string, default `; `)
- `annotation_output_separator` (string, default `;\n`)
- Optional LLM overrides (see below):
  - `llm_enabled` (boolean), `llm_model` (string), `llm_temperature` (number), `llm_timeout` (seconds), `llm_endpoint` (URL), `llm_provider` (string), `llm_api_key` (string)

Example:

```json
[
  {
    "project": "Example Project",
    "project_id": "11111111-1111-1111-1111-111111111111",
    "project_task": "Example Project Task",
    "project_task_id": "11111111-2222-2222-2222-111111111111",
    "timew_tags": ["example", "project", "one"],
    "role": "Cloud Engineer",
    "type": "Work",
    "multiplier": 1.0,
    "annotation_delimiter": "; ",
    "annotation_output_separator": ";\n"
  },
  {
    "project": "Example Project 2",
    "project_id": "22222222-2222-2222-2222-222222222222",
    "project_task": "Example Project 2 Task",
    "project_task_id": "22222222-1111-1111-1111-222222222222",
    "timew_tags": ["example", "project", "two"],
    "role": "Cloud Engineer",
    "type": "Work",
    "multiplier": 1.2,
    "merge_on_equal_tags": true,
    "description_prefix": "Project 2",
    "external_comment": "Billable"
  }
]
```

## Environment Variables

- Config path
  - `TIMEWARRIOR_EXT_DYNAMICS_CONFIG_JSON`: path to config JSON
- Formatting
  - `TIMEWARRIOR_EXT_DYNAMICS_ANNOTATION_DELIMITER`: override input delimiter
  - `TIMEWARRIOR_EXT_DYNAMICS_OUTPUT_SEPARATOR`: override output joiner
- Optional LLM refinement
  - `TIMEWARRIOR_EXT_DYNAMICS_LLM_ENABLED` (true/false; default off)
  - `TIMEWARRIOR_EXT_DYNAMICS_LLM_PROVIDER` (`ollama` default, or `openai`)
  - `TIMEWARRIOR_EXT_DYNAMICS_LLM_ENDPOINT` (default `http://127.0.0.1:11434/api/generate` for Ollama, `https://api.openai.com/v1/chat/completions` for OpenAI)
  - `TIMEWARRIOR_EXT_DYNAMICS_LLM_MODEL` (default `llama3` for Ollama; set e.g. `gpt-4o-mini` for OpenAI)
  - `TIMEWARRIOR_EXT_DYNAMICS_LLM_TEMPERATURE` (default `0.2`)
  - `TIMEWARRIOR_EXT_DYNAMICS_LLM_TIMEOUT` seconds (default `2.0`)
  - `TIMEWARRIOR_EXT_DYNAMICS_OPENAI_API_KEY` (required when provider is `openai`)

## LLM Refinement (Optional)

- When enabled, each merged row’s Description is rewritten for clarity by a local LLM.
- Structure safety:
  - Refinement happens after merging, not before.
  - The delimiter-separated structure is preserved (same number/order of segments).
  - Hidden `++…++` segments are not sent to the LLM and are preserved as-is.
  - On timeout/parse error, the original description is used.
- Per-project overrides: `llm_enabled`, `llm_model`, `llm_temperature`, `llm_timeout`, `llm_endpoint`, `llm_provider`, `llm_api_key`.
- Provider notes:
  - `ollama` (default): communicates with a local Ollama server.
  - `openai`: uses OpenAI Chat Completions; requires the API key either via env var or `llm_api_key`.

## Troubleshooting

- No output rows? Timewarrior omits `end` for active entries; these are skipped.
- Unmatched tags? Check your config `timew_tags` and the subset/priority rules.
- Unexpected merging? Verify `description_prefix`, `annotation_delimiter`, and `merge_on_equal_tags`.
- CSV breaks in spreadsheets? All values are quoted; Description is multiline by design.
- LLM issues? Confirm the endpoint is reachable, temperature/timeout are reasonable, or disable refinement.

## Tips

- Use `description_prefix` to create a stable title that encourages merging of related items.
- Keep list items short and focused; the output separator makes them readable in CSV.
- Prefer IDs for `project`/`project_task` if your downstream system expects them.
