#!/usr/bin/env python3

"""Timewarrior extension to export Dynamics-compatible CSV data."""

from dataclasses import dataclass, field
from datetime import datetime
import json
import math
import os
import sys
import socket
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib import error as urlerror, request as urlrequest

TIMEW_DATETIME_FORMAT = "%Y%m%dT%H%M%S%z"
DEFAULT_ANNOTATION_DELIMITER = "; "
DEFAULT_OUTPUT_SEPARATOR = ";\n"
ANNOTATION_DELIMITER_ENV_VAR = "TIMEWARRIOR_EXT_DYNAMICS_ANNOTATION_DELIMITER"
OUTPUT_SEPARATOR_ENV_VAR = "TIMEWARRIOR_EXT_DYNAMICS_OUTPUT_SEPARATOR"
CSV_DELIMITER = ","
MAX_DESCRIPTION_LENGTH = 500
CONFIG_ENV_VAR = "TIMEWARRIOR_EXT_DYNAMICS_CONFIG_JSON"
DEFAULT_CONFIG_FILENAME = ".dynamics_config.json"
DEFAULT_TYPE = "Work"

LLM_ENABLED_ENV_VAR = "TIMEWARRIOR_EXT_DYNAMICS_LLM_ENABLED"
LLM_PROVIDER_ENV_VAR = "TIMEWARRIOR_EXT_DYNAMICS_LLM_PROVIDER"
LLM_ENDPOINT_ENV_VAR = "TIMEWARRIOR_EXT_DYNAMICS_LLM_ENDPOINT"
LLM_MODEL_ENV_VAR = "TIMEWARRIOR_EXT_DYNAMICS_LLM_MODEL"
LLM_TEMPERATURE_ENV_VAR = "TIMEWARRIOR_EXT_DYNAMICS_LLM_TEMPERATURE"
LLM_TIMEOUT_ENV_VAR = "TIMEWARRIOR_EXT_DYNAMICS_LLM_TIMEOUT"
OPENAI_API_KEY_ENV_VAR = "TIMEWARRIOR_EXT_DYNAMICS_OPENAI_API_KEY"

DEFAULT_LLM_ENDPOINT = "http://127.0.0.1:11434/api/generate"
DEFAULT_OPENAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"
DEFAULT_LLM_MODEL = "llama3"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_LLM_TEMPERATURE = 0.2
DEFAULT_LLM_TIMEOUT = 2.0


@dataclass
class DynamicsEntry:
    """Container for the final CSV payload."""

    date: str
    duration: int
    project: str
    project_task: str
    role: str
    type: str
    description: str
    external_comments: str
    annotation_delimiter: str
    output_separator: str
    llm_settings: Dict[str, Any] = field(default_factory=dict)

    def as_row(self) -> List[str]:
        return [
            self.date,
            str(self.duration),
            self.project,
            self.project_task,
            self.role,
            self.type,
            self.description,
            self.external_comments,
        ]


class LLMRefiner:
    """Refine descriptions using an optional LLM backend (local or remote)."""

    SYSTEM_PROMPT = (
        "You rewrite time tracking descriptions for clarity while keeping the original meaning. "
        "You must respond with JSON only."
    )

    def __init__(
        self,
        enabled: bool,
        endpoint: str = DEFAULT_LLM_ENDPOINT,
        model: str = DEFAULT_LLM_MODEL,
        temperature: float = DEFAULT_LLM_TEMPERATURE,
        timeout: float = DEFAULT_LLM_TIMEOUT,
        provider: str = "ollama",
        api_key: Optional[str] = None,
    ) -> None:
        self.enabled = enabled
        self.endpoint = endpoint
        self.model = model
        self.temperature = temperature
        self.timeout = timeout
        self.provider = provider
        self.api_key = api_key
        self._cache: Dict[Tuple[Any, ...], str] = {}

    @staticmethod
    def _parse_bool(value: Optional[str]) -> Optional[bool]:
        if value is None:
            return None
        lower = value.strip().lower()
        if lower in {"1", "true", "yes", "on"}:
            return True
        if lower in {"0", "false", "no", "off"}:
            return False
        return None

    @classmethod
    def from_env(cls) -> "LLMRefiner":
        enabled = cls._parse_bool(os.getenv(LLM_ENABLED_ENV_VAR))
        if not enabled:
            return cls(False)

        provider = os.getenv(LLM_PROVIDER_ENV_VAR, "ollama").strip().lower()
        if provider == "openai":
            endpoint = os.getenv(LLM_ENDPOINT_ENV_VAR, DEFAULT_OPENAI_ENDPOINT)
            default_model = DEFAULT_OPENAI_MODEL
        else:
            provider = "ollama"
            endpoint = os.getenv(LLM_ENDPOINT_ENV_VAR, DEFAULT_LLM_ENDPOINT)
            default_model = DEFAULT_LLM_MODEL

        model = os.getenv(LLM_MODEL_ENV_VAR, default_model)
        temperature_value = os.getenv(LLM_TEMPERATURE_ENV_VAR)
        timeout_value = os.getenv(LLM_TIMEOUT_ENV_VAR)
        api_key = os.getenv(OPENAI_API_KEY_ENV_VAR)

        try:
            temperature = float(temperature_value) if temperature_value is not None else DEFAULT_LLM_TEMPERATURE
        except ValueError:
            temperature = DEFAULT_LLM_TEMPERATURE

        try:
            timeout = float(timeout_value) if timeout_value is not None else DEFAULT_LLM_TIMEOUT
        except ValueError:
            timeout = DEFAULT_LLM_TIMEOUT

        return cls(
            True,
            endpoint=endpoint,
            model=model,
            temperature=temperature,
            timeout=timeout,
            provider=provider,
            api_key=api_key,
        )

    def refine(
        self,
        description: str,
        delimiter: Optional[str],
        output_separator: str,
        context: Dict[str, str],
        overrides: Optional[Dict[str, Any]] = None,
    ) -> str:
        if not self.enabled:
            return description

        overrides = overrides or {}
        override_enabled = overrides.get("enabled")
        if override_enabled is False:
            return description

        effective_model = overrides.get("model", self.model)
        effective_temperature = overrides.get("temperature", self.temperature)
        effective_endpoint = overrides.get("endpoint", self.endpoint)
        effective_timeout = overrides.get("timeout", self.timeout)
        effective_provider = str(overrides.get("provider", self.provider)).strip().lower()
        if effective_provider not in {"ollama", "openai"}:
            effective_provider = self.provider
        effective_api_key = overrides.get("api_key", self.api_key)

        try:
            effective_temperature = float(effective_temperature)
        except (TypeError, ValueError):
            effective_temperature = self.temperature

        try:
            effective_timeout = float(effective_timeout)
        except (TypeError, ValueError):
            effective_timeout = self.timeout

        if not effective_model or not effective_endpoint:
            return description
        if effective_provider == "openai" and not effective_api_key:
            return description

        delimiter = delimiter or ""
        segments = [description] if not delimiter else description.split(delimiter)
        if not segments:
            return description

        hidden_mask = []
        visible_segments: List[str] = []
        for segment in segments:
            is_hidden = segment.startswith("++") and segment.endswith("++")
            hidden_mask.append(is_hidden)
            if not is_hidden:
                visible_segments.append(segment.strip())

        if not visible_segments:
            return description

        cache_key = (
            description,
            delimiter,
            output_separator,
            effective_model,
            round(float(effective_temperature), 3),
            effective_provider,
            effective_endpoint,
            tuple(sorted((k, v) for k, v in context.items() if v)),
            tuple(visible_segments),
        )

        if cache_key in self._cache:
            return self._cache[cache_key]

        prompt = self._build_prompt(description, visible_segments, delimiter, output_separator, context)
        if effective_provider == "openai":
            payload: Dict[str, Any] = {
                "model": effective_model,
                "messages": [
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": float(effective_temperature),
            }
        else:
            payload = {
                "model": effective_model,
                "prompt": prompt,
                "system": self.SYSTEM_PROMPT,
                "stream": False,
                "options": {"temperature": float(effective_temperature)},
            }

        try:
            refined_segments = self._call_model(
                payload,
                effective_endpoint,
                effective_timeout,
                effective_provider,
                effective_api_key,
            )
        except Exception:
            return description

        if refined_segments is None or len(refined_segments) != len(visible_segments):
            return description

        visible_iter = iter(refined_segments)
        reconstructed: List[str] = []
        for is_hidden, original in zip(hidden_mask, segments):
            if is_hidden:
                reconstructed.append(original)
                continue

            candidate = next(visible_iter)
            if not isinstance(candidate, str):
                return description
            cleaned = candidate.strip()
            if not cleaned:
                cleaned = original.strip()
            reconstructed.append(cleaned)

        if delimiter:
            refined_description = delimiter.join(reconstructed)
        else:
            refined_description = reconstructed[0] if reconstructed else description

        self._cache[cache_key] = refined_description
        return refined_description

    @staticmethod
    def _build_prompt(
        description: str,
        segments: Sequence[str],
        delimiter: str,
        output_separator: str,
        context: Dict[str, str],
    ) -> str:
        context_lines = [f"{key.title()}: {value}" for key, value in context.items() if value]
        context_block = "\n".join(context_lines) if context_lines else "None"
        segments_json = json.dumps(list(segments), ensure_ascii=False)

        instructions = (
            "Rewrite each segment for clarity while keeping the original meaning. "
            "Return a JSON array with exactly {count} strings in the same order. "
            "Do not add, remove, or reorder segments. Keep numbers, IDs, and names unchanged. "
            "Each string must stay concise and professional. Respond with JSON only."
        ).format(count=len(segments))

        prompt = (
            f"{instructions}\n\n"
            f"Delimiter: {delimiter or '[none]'}\n"
            f"Output separator: {output_separator}\n"
            f"Context:\n{context_block}\n\n"
            f"Original description string:\n{description}\n\n"
            f"Segments JSON:\n{segments_json}\n"
        )
        return prompt

    def _call_model(
        self,
        payload: Dict[str, Any],
        endpoint: str,
        timeout: float,
        provider: str,
        api_key: Optional[str],
    ) -> Optional[List[str]]:
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if provider == "openai" and api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        request_obj = urlrequest.Request(endpoint, data=data, headers=headers)

        try:
            with urlrequest.urlopen(request_obj, timeout=float(timeout)) as response:
                raw = response.read().decode("utf-8")
        except (urlerror.URLError, socket.timeout):
            raise

        try:
            response_json = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Invalid JSON from LLM endpoint") from exc

        if provider == "openai":
            choices = response_json.get("choices")
            if not isinstance(choices, list) or not choices:
                return None
            first_choice = choices[0]
            if not isinstance(first_choice, dict):
                return None
            message = first_choice.get("message")
            if not isinstance(message, dict):
                return None
            output = message.get("content", "")
        else:
            output = response_json.get("response")
        if not isinstance(output, str):
            return None

        output = output.strip()
        try:
            parsed = json.loads(output)
        except json.JSONDecodeError:
            return None

        if not isinstance(parsed, list):
            return None

        return [str(item) for item in parsed]


def calculate_working_time(datetime_start: datetime, datetime_end: datetime, multiplier: float = 1) -> int:
    """Return minutes rounded up to 15-minute blocks after applying multiplier."""

    datetime_delta = datetime_end - datetime_start
    total_seconds = datetime_delta.total_seconds()
    total_seconds_multiplied = total_seconds * multiplier

    total_minutes = round(total_seconds_multiplied / 60)
    total_minutes_rounded_15m = math.ceil(total_minutes / 15) * 15

    return total_minutes_rounded_15m


def csv_escape_special_chars(text: str) -> str:
    """Escape CSV-sensitive characters to keep manual formatting consistent."""

    return text.replace('"', '""').replace("\\", "\\\\")


def sanitize_description(
    text: str,
    input_delimiter: Optional[str],
    output_separator: str,
) -> str:
    """Remove hidden markers and join list items with the configured separator."""

    if not input_delimiter:
        return text

    parts = text.split(input_delimiter)
    visible_parts = [element for element in parts if not (element.startswith("++") and element.endswith("++"))]
    return output_separator.join(visible_parts)


def join_unique(items: Sequence[str], delimiter: str) -> str:
    """Deduplicate list items while keeping their first-seen order."""

    unique: List[str] = []
    for item in items:
        if item not in unique:
            unique.append(item)
    return delimiter.join(unique)


def merge_annotations(existing: str, addition: str, delimiter: str) -> str:
    """Merge two delimiter-separated strings while preserving uniqueness."""

    merged = delimiter.join([existing, addition])
    return join_unique(merged.split(delimiter), delimiter)


def load_project_configuration() -> List[dict]:
    """Load project definitions from the configured JSON file."""

    config_filename = os.getenv(CONFIG_ENV_VAR, DEFAULT_CONFIG_FILENAME)
    config_path = os.path.join(sys.path[0], config_filename)
    with open(config_path, encoding="utf-8") as config_file:
        return json.load(config_file)


def parse_timew_export(stream: Iterable[str]) -> List[dict]:
    """Parse the JSON payload produced by `timew export`."""

    for line in stream:
        if line == "\n":
            break

    payload = "".join(stream)
    return json.loads(payload) if payload else []


def resolve_project_config(tags: Sequence[str], project_configs: Sequence[dict]) -> dict:
    """Return the project configuration matching the provided tags."""

    tag_set = set(tags)
    chosen_config: Optional[dict] = None

    for project_config in project_configs:
        config_tags = set(project_config.get("timew_tags", []))
        if config_tags == tag_set:
            return project_config
        if config_tags < tag_set:
            if chosen_config is None:
                chosen_config = project_config
                continue
            current_tags = set(chosen_config.get("timew_tags", []))
            if len(tag_set - config_tags) < len(tag_set - current_tags):
                chosen_config = project_config

    if chosen_config:
        return chosen_config

    if tag_set:
        project_note = f"NO PROJECT FOUND FOR THESE TAGS: {', '.join(tags)}"
    else:
        project_note = "NO TAGS DEFINED TO THIS TIME ENTRY"

    return {"project": project_note, "project_task": "-", "role": "-"}


def build_dynamics_entry(
    timew_entry: dict,
    project_config: dict,
    annotation_delimiter_override: Optional[str] = None,
    output_separator_override: Optional[str] = None,
) -> Tuple[DynamicsEntry, bool]:
    """Construct a DynamicsEntry from a timew record and config mapping."""

    timew_start = timew_entry["start"]
    timew_end = timew_entry["end"]

    start_dt = datetime.strptime(timew_start, TIMEW_DATETIME_FORMAT)
    end_dt = datetime.strptime(timew_end, TIMEW_DATETIME_FORMAT)

    multiplier = float(project_config["multiplier"]) if "multiplier" in project_config else 1
    duration_minutes = calculate_working_time(start_dt, end_dt, multiplier)

    project_value = (
        project_config["project_id"] if "project_id" in project_config else project_config.get("project", "")
    )
    project_task_value = (
        project_config["project_task_id"]
        if "project_task_id" in project_config
        else project_config.get("project_task", "")
    )
    role_value = project_config.get("role", "")

    annotation = timew_entry.get("annotation", "")
    if annotation_delimiter_override is not None:
        annotation_delimiter = annotation_delimiter_override
    else:
        annotation_delimiter = project_config.get("annotation_delimiter", DEFAULT_ANNOTATION_DELIMITER)
    if not annotation_delimiter:
        annotation_delimiter = DEFAULT_ANNOTATION_DELIMITER

    if output_separator_override is not None:
        output_separator = output_separator_override
    else:
        output_separator = project_config.get("annotation_output_separator", DEFAULT_OUTPUT_SEPARATOR)
    if output_separator is None or output_separator == "":
        output_separator = DEFAULT_OUTPUT_SEPARATOR

    if "description_prefix" in project_config:
        description = project_config["description_prefix"] + annotation_delimiter + annotation
    else:
        description = annotation

    external_comment = project_config.get("external_comment", "")
    merge_on_equal_tags = (
        bool(project_config["merge_on_equal_tags"]) if "merge_on_equal_tags" in project_config else False
    )

    entry_type = project_config.get("type", DEFAULT_TYPE)

    llm_settings: Dict[str, Any] = {}
    if "llm_enabled" in project_config:
        llm_settings["enabled"] = bool(project_config["llm_enabled"])
    if "llm_model" in project_config:
        llm_settings["model"] = project_config["llm_model"]
    if "llm_temperature" in project_config:
        try:
            llm_settings["temperature"] = float(project_config["llm_temperature"])
        except (TypeError, ValueError):
            pass
    if "llm_timeout" in project_config:
        try:
            llm_settings["timeout"] = float(project_config["llm_timeout"])
        except (TypeError, ValueError):
            pass
    if "llm_endpoint" in project_config:
        llm_settings["endpoint"] = project_config["llm_endpoint"]
    if "llm_provider" in project_config:
        llm_settings["provider"] = str(project_config["llm_provider"]).strip().lower()
    if "llm_api_key" in project_config:
        llm_settings["api_key"] = project_config["llm_api_key"]

    entry = DynamicsEntry(
        date=start_dt.astimezone().strftime("%Y-%m-%d"),
        duration=duration_minutes,
        project=project_value,
        project_task=project_task_value,
        role=role_value,
        type=entry_type,
        description=description,
        external_comments=external_comment,
        annotation_delimiter=annotation_delimiter,
        output_separator=output_separator,
        llm_settings=llm_settings,
    )

    return entry, merge_on_equal_tags


def should_merge_base(existing: DynamicsEntry, new_entry: DynamicsEntry) -> bool:
    """Check if two entries share the attributes required for merging."""

    return (
        existing.date == new_entry.date
        and existing.project == new_entry.project
        and existing.project_task == new_entry.project_task
        and existing.role == new_entry.role
        and existing.type == new_entry.type
        and existing.annotation_delimiter == new_entry.annotation_delimiter
        and existing.output_separator == new_entry.output_separator
    )


def merge_entries(
    entries: List[DynamicsEntry],
    new_entry: DynamicsEntry,
    merge_on_equal_tags: bool,
) -> None:
    """Merge the new entry into the list when a matching slot exists."""

    for existing in entries:
        if not should_merge_base(existing, new_entry):
            continue

        delimiter = existing.annotation_delimiter

        if existing.description == new_entry.description:
            existing.duration += new_entry.duration
            return

        if merge_on_equal_tags and len(existing.description) + len(new_entry.description) <= MAX_DESCRIPTION_LENGTH:
            existing.duration += new_entry.duration
            existing.description = merge_annotations(existing.description, new_entry.description, delimiter)
            return

        existing_title = existing.description.split(delimiter)[0]
        new_title = new_entry.description.split(delimiter)[0]

        if (
            existing_title == new_title
            and len(existing.description) + len(new_entry.description) <= MAX_DESCRIPTION_LENGTH
        ):
            existing.duration += new_entry.duration
            note_items_without_title = delimiter.join(new_entry.description.split(delimiter)[1:])
            existing.description = merge_annotations(existing.description, note_items_without_title, delimiter)
            return

    entries.append(new_entry)


def format_csv_row(
    values: Sequence[str],
    annotation_delimiter: Optional[str],
    output_separator: Optional[str],
) -> str:
    """Render the CSV row with manual quoting identical to original script."""

    row = list(values)
    if annotation_delimiter:
        separator = output_separator or DEFAULT_OUTPUT_SEPARATOR
        row[6] = sanitize_description(row[6], annotation_delimiter, separator)

    escaped = [f'"{csv_escape_special_chars(value)}"' for value in row]
    return CSV_DELIMITER.join(escaped)


def write_output(entries: Sequence[DynamicsEntry]) -> None:
    """Send the CSV header and rows to stdout."""

    header = (
        "Date",
        "Duration",
        "Project",
        "Project Task",
        "Role",
        "Type",
        "Description",
        "External Comments",
    )
    sys.stdout.write(format_csv_row(header, None, None) + "\n")

    for index, entry in enumerate(entries):
        line = format_csv_row(entry.as_row(), entry.annotation_delimiter, entry.output_separator)
        if index + 1 == len(entries):
            sys.stdout.write(line)
        else:
            sys.stdout.write(line + "\n")


def main() -> None:
    project_configs = load_project_configuration()
    timew_entries = parse_timew_export(sys.stdin)
    annotation_delimiter_override = os.getenv(ANNOTATION_DELIMITER_ENV_VAR)
    output_separator_override = os.getenv(OUTPUT_SEPARATOR_ENV_VAR)

    dynamics_entries: List[DynamicsEntry] = []
    for timew_entry in timew_entries:
        if "end" not in timew_entry:
            continue

        tags = timew_entry.get("tags", [])
        project_config = resolve_project_config(tags, project_configs)
        entry, merge_on_equal_tags = build_dynamics_entry(
            timew_entry,
            project_config,
            annotation_delimiter_override,
            output_separator_override,
        )
        merge_entries(
            dynamics_entries,
            entry,
            merge_on_equal_tags,
        )

    refiner = LLMRefiner.from_env()
    if refiner.enabled:
        for idx, dynamics_entry in enumerate(dynamics_entries):
            dynamics_entries[idx].description = refiner.refine(
                description=dynamics_entry.description,
                delimiter=dynamics_entry.annotation_delimiter,
                output_separator=dynamics_entry.output_separator,
                context={
                    "date": dynamics_entry.date,
                    "project": dynamics_entry.project,
                    "project_task": dynamics_entry.project_task,
                    "role": dynamics_entry.role,
                    "type": dynamics_entry.type,
                },
                overrides=dynamics_entry.llm_settings,
            )

    write_output(dynamics_entries)


if __name__ == "__main__":
    main()
