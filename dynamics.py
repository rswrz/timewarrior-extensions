#!/usr/bin/env python3

"""Timewarrior extension to export Dynamics-compatible CSV data."""

from dataclasses import dataclass
from datetime import datetime
import json
import math
import os
import sys
from typing import Iterable, List, Optional, Sequence, Tuple

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

    write_output(dynamics_entries)


if __name__ == "__main__":
    main()
