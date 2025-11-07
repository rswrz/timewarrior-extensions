# Timewarrior Extensions

A collection of personal [Timewarrior](https://timewarrior.net/) [extensions](https://timewarrior.net/docs/extensions/) to enhance my time tracking workflow.

## Extensions

- `dynamics_csv.py` — Export + merge entries to CSV (Dynamics‑ready), with tag→project mapping, rounding, and optional LLM description refinement. See [`docs/dynamics_csv.md`](docs/dynamics_csv.md)
- `dynamics_summary.py` — Table view using Dynamics logic (merging, rounding, config). See [`docs/dynamics_summary.md`](docs/dynamics_summary.md)
- `zoho.py` — Export entries to a Zoho-compatible CSV with tag-based project/task mapping and note merging. See [`docs/zoho.md`](docs/zoho.md)
- `csv.py` — Output raw `timew export` entries as a simple CSV. See [`docs/csv.md`](docs/csv.md)
- `table.py` — Colorized summary view with annotations, gaps, and totals. See [`docs/table.md`](docs/table.md)
- `debug.py` — Print the incoming Timewarrior payload to stdout unchanged (handy for troubleshooting pipelines).

## Configuration Files

The extensions use JSON configuration files for project and task mapping. The default configuration file is `.dynamics_config.json` (or specify a custom path via `TIMEWARRIOR_EXT_DYNAMICS_CONFIG_JSON`). These configuration files support both standard JSON and the enhanced JSON5 format.

### Configuration File Examples

See the JSON5 example for a complete set of parameters.

**Standard JSON format:**
```json
[
  {
    "project": "My Project",
    "project_task": "Development",
    "project_task_id": "",
    "timew_tags": ["project", "dev"],
    "role": "Developer",
    "type": "Work"
  }
]
```

**JSON5 format (when json5 is installed):**
```json5
[
  {
    // === REQUIRED FIELDS ===
    timew_tags: ["project", "dev"], // Tags to match from timewarrior entries
    
    // === PROJECT IDENTIFICATION ===
    project: "My Project", // Project name (fallback if no project_id)
    project_id: "", // Project ID for Dynamics (overrides project if set)
    project_task: "Development", // Task name (fallback if no project_task_id)
    project_task_id: "", // Task ID for Dynamics (overrides project_task if set)
    
    // === BASIC CONFIGURATION ===
    role: "Developer", // Role/position
    type: "Work", // Entry type (default: "Work")
    
    // === TIME CALCULATION ===
    multiplier: 1.0, // Time multiplier (default: 1.0)
    
    // === DESCRIPTION HANDLING ===
    description_prefix: "", // Prefix added to descriptions (optional)
    annotation_delimiter: "; ", // Delimiter for annotation parts (default: "; ")
    annotation_output_separator: ";\n", // Separator for output (default: ";\n")
    external_comment: "", // Additional comment field (optional)
    
    // === MERGING BEHAVIOR ===
    merge_on_equal_tags: false, // Merge entries with same tags (default: false)
    
    // === LLM DESCRIPTION REFINEMENT (dynamics_csv.py only) ===
    llm_enabled: false, // Enable LLM description refinement (default: false)
    llm_provider: "ollama", // Provider: "ollama" or "openai" (default: "ollama")
    llm_model: "llama3", // Model name (default: "llama3" for ollama, "gpt-4o-mini" for openai)
    llm_endpoint: "http://127.0.0.1:11434/api/generate", // LLM endpoint URL
    llm_temperature: 0.2, // LLM temperature (default: 0.2)
    llm_timeout: 2.0, // LLM request timeout in seconds (default: 2.0)
    llm_api_key: "your-api-key", // API key for OpenAI (required for openai provider)
  }, // Trailing comma is OK in JSON5
]
```

### JSON5 Support (Optional)

JSON5 is a superset of JSON that allows for more human-friendly configuration files with features like:

- **Comments**: Use `//` for line comments or `/* */` for block comments
- **Trailing commas**: Add commas after the last item in arrays/objects
- **Unquoted keys**: Write object keys without quotes when they're valid identifiers
- **Single quotes**: Use single quotes for strings
- **Multi-line strings**: Break long strings across multiple lines

### Installation

To enable JSON5 support, install the optional dependency:

```bash
pip3 install -r requirements.txt
```

Add `--user --break-system-packages` parameters if you are getting a warning about `externally-managed-environment`. The module is not available as homebrew formulae.

## Useful Aliases & Functions

For a set of helpful aliases and shell functions, visit the <https://github.com/rswrz/timewarrior>.
