#!/usr/bin/env python3

"""Timewarrior report that outputs Dynamics data in a tabular view."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import math
import os
import sys
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

TIMEW_DATETIME_FORMAT = "%Y%m%dT%H%M%S%z"
DEFAULT_ANNOTATION_DELIMITER = "; "
DEFAULT_OUTPUT_SEPARATOR = ";\n"
CONFIG_ENV_VAR = "TIMEWARRIOR_EXT_DYNAMICS_CONFIG_JSON"
ANNOTATION_DELIMITER_ENV_VAR = "TIMEWARRIOR_EXT_DYNAMICS_ANNOTATION_DELIMITER"
OUTPUT_SEPARATOR_ENV_VAR = "TIMEWARRIOR_EXT_DYNAMICS_OUTPUT_SEPARATOR"
DEFAULT_CONFIG_FILENAME = ".dynamics_config.json"
DEFAULT_TYPE = "Work"
DEFAULT_MERGE_MAX_DESCRIPTION_LENGTH = 500

ANSI_RESET = "\033[0m"
ANSI_UNDERLINE = "\033[4m"
ANSI_ROW_ALT = "\033[48;2;26;26;26m"
ANSI_NO_DESCRIPTION = "\033[38;2;238;162;87m"


@dataclass
class DynamicsRow:
    date: str
    duration_minutes: int
    project: str
    project_task: str
    role: str
    type: str
    description: str
    external_comment: str
    annotation_delimiter: str
    output_separator: str

    def formatted_duration(self) -> str:
        hours, minutes = divmod(self.duration_minutes, 60)
        return f"{hours}:{minutes:02d}"


def skip_report_header(stream: Iterable[str]) -> None:
    for line in stream:
        if line == "\n":
            break


def parse_timew_export(stream: Iterable[str]) -> List[dict]:
    payload = "".join(stream)
    return json.loads(payload) if payload else []


def calculate_working_time(
    start: datetime, end: datetime, multiplier: float = 1.0
) -> int:
    total_seconds = (end - start).total_seconds()
    total_seconds *= multiplier
    total_minutes = round(total_seconds / 60)
    return math.ceil(total_minutes / 15) * 15


def join_unique(items: Sequence[str], delimiter: str) -> str:
    seen: List[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return delimiter.join(seen)


def merge_annotations(existing: str, new: str, delimiter: str) -> str:
    merged = delimiter.join([existing, new])
    return join_unique(merged.split(delimiter), delimiter)


def sanitize_description(text: str, delimiter: str, output_separator: str) -> str:
    parts = text.split(delimiter)
    visible = [
        part for part in parts if not (part.startswith("++") and part.endswith("++"))
    ]
    return output_separator.join(visible)


def load_project_configuration(config_filename: str) -> List[dict]:
    config_path = os.path.join(sys.path[0], config_filename)
    with open(config_path, encoding="utf-8") as config_file:
        return json.load(config_file)


def resolve_project_config(tags: Sequence[str], configs: Sequence[dict]) -> dict:
    tag_set = set(tags)
    matched: Optional[dict] = None

    for config in configs:
        config_tags = set(config.get("timew_tags", []))
        if config_tags == tag_set:
            return config
        if config_tags < tag_set:
            if matched is None:
                matched = config
                continue
            current = set(matched.get("timew_tags", []))
            if len(tag_set - config_tags) < len(tag_set - current):
                matched = config

    if matched:
        return matched

    if tag_set:
        project_note = f"NO PROJECT FOUND FOR THESE TAGS: {', '.join(tags)}"
    else:
        project_note = "NO TAGS DEFINED TO THIS TIME ENTRY"

    return {"project": project_note, "project_task": "-", "role": "-"}


def build_dynamics_row(
    entry: dict,
    project_config: dict,
    annotation_delimiter_override: Optional[str],
    output_separator_override: Optional[str],
) -> Tuple[Optional[DynamicsRow], bool]:
    if "end" not in entry:
        return None, False

    start_dt = datetime.strptime(entry["start"], TIMEW_DATETIME_FORMAT)
    end_dt = datetime.strptime(entry["end"], TIMEW_DATETIME_FORMAT)

    project_value = project_config.get("project", "")
    project_task_value = project_config.get("project_task", "")
    role_value = project_config.get("role", "")
    entry_type = project_config.get("type", DEFAULT_TYPE)

    annotation_delimiter = (
        annotation_delimiter_override
        if annotation_delimiter_override is not None
        else project_config.get("annotation_delimiter", DEFAULT_ANNOTATION_DELIMITER)
    )
    if not annotation_delimiter:
        annotation_delimiter = DEFAULT_ANNOTATION_DELIMITER

    output_separator = (
        output_separator_override
        if output_separator_override is not None
        else project_config.get("annotation_output_separator", DEFAULT_OUTPUT_SEPARATOR)
    )
    if not output_separator:
        output_separator = DEFAULT_OUTPUT_SEPARATOR

    annotation = entry.get("annotation", "")
    if "description_prefix" in project_config:
        description = project_config["description_prefix"] + annotation_delimiter + annotation
    else:
        description = annotation

    external_comment = project_config.get("external_comment", "")
    multiplier = float(project_config.get("multiplier", 1))
    merge_on_equal_tags = bool(project_config.get("merge_on_equal_tags", False))

    duration_minutes = calculate_working_time(start_dt, end_dt, multiplier)

    row = DynamicsRow(
        date=start_dt.astimezone().strftime("%Y-%m-%d"),
        duration_minutes=duration_minutes,
        project=project_value,
        project_task=project_task_value,
        role=role_value,
        type=entry_type,
        description=description,
        external_comment=external_comment,
        annotation_delimiter=annotation_delimiter,
        output_separator=output_separator,
    )

    return row, merge_on_equal_tags


def merge_entries(entries: List[DynamicsRow], new_entry: DynamicsRow, merge_on_equal_tags: bool) -> None:
    for index, existing in enumerate(entries):
        if (
            existing.date == new_entry.date
            and existing.project == new_entry.project
            and existing.project_task == new_entry.project_task
            and existing.role == new_entry.role
            and existing.type == new_entry.type
        ):
            if existing.description == new_entry.description:
                entries[index].duration_minutes += new_entry.duration_minutes
                return

            if (
                merge_on_equal_tags
                and len(existing.description) + len(new_entry.description)
                <= DEFAULT_MERGE_MAX_DESCRIPTION_LENGTH
            ):
                entries[index].duration_minutes += new_entry.duration_minutes
                entries[index].description = merge_annotations(
                    existing.description,
                    new_entry.description,
                    existing.annotation_delimiter,
                )
                return

            existing_title = existing.description.split(existing.annotation_delimiter)[0]
            new_title = new_entry.description.split(new_entry.annotation_delimiter)[0]
            if (
                existing_title == new_title
                and len(existing.description) + len(new_entry.description)
                <= DEFAULT_MERGE_MAX_DESCRIPTION_LENGTH
            ):
                entries[index].duration_minutes += new_entry.duration_minutes
                remainder = existing.annotation_delimiter.join(
                    new_entry.description.split(new_entry.annotation_delimiter)[1:]
                )
                entries[index].description = merge_annotations(
                    existing.description,
                    remainder,
                    existing.annotation_delimiter,
                )
                return

    entries.append(new_entry)


def build_table_rows(entries: Sequence[DynamicsRow]) -> Tuple[List[List[str]], int, List[int]]:
    rows: List[List[str]] = []
    master_flags: List[int] = []
    total_minutes = 0

    for row in entries:
        total_minutes += row.duration_minutes
        description_display = sanitize_description(
            row.description,
            row.annotation_delimiter,
            row.output_separator,
        )
        description_lines = description_display.split(row.output_separator)
        external_lines = (
            row.external_comment.split("\n") if row.external_comment else [""]
        )
        max_lines = max(len(description_lines), len(external_lines))

        description_lines.extend(
            ["" for _ in range(max_lines - len(description_lines))]
        )
        external_lines.extend(["" for _ in range(max_lines - len(external_lines))])

        for index, (desc, ext) in enumerate(zip(description_lines, external_lines)):
            project_display = truncate_for_table(row.project)
            task_display = truncate_for_table(row.project_task)
            rows.append(
                [
                    row.date if index == 0 else "",
                    project_display if index == 0 else "",
                    task_display if index == 0 else "",
                    row.role if index == 0 else "",
                    row.type if index == 0 else "",
                    desc,
                    ext,
                    row.formatted_duration() if index == 0 else "",
                ]
            )
            master_flags.append(1 if index == 0 else 0)

    return rows, total_minutes, master_flags


def compute_column_widths(
    rows: Sequence[Sequence[str]], headers: Sequence[str]
) -> List[int]:
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))
    max_widths = {1: 32, 2: 32}
    for index, max_width in max_widths.items():
        if widths[index] > max_width:
            widths[index] = max_width
    return widths


def truncate_for_table(value: str, max_length: int = 32) -> str:
    if len(value) <= max_length:
        return value
    ellipsis = "…"
    if max_length <= len(ellipsis):
        return value[:max_length]
    return value[: max_length - len(ellipsis)] + ellipsis


def build_layout(widths: Sequence[int]) -> str:
    alignments = ["<", "<", "<", "<", "<", "<", "<", ">"]
    parts = [f"{{:{align}{width}}}" for align, width in zip(alignments, widths)]
    return " ".join(parts)


def print_header(layout: str, headers: Sequence[str]) -> None:
    formatted = layout.format(*headers)
    columns = formatted.split(" ")
    underlined = [f"{ANSI_UNDERLINE}{column}{ANSI_RESET}" for column in columns]
    print(" ".join(underlined))


def print_rows(layout: str, rows: Sequence[Sequence[str]], master_flags: Sequence[int]) -> None:
    master_index = -1
    for index, row in enumerate(rows):
        if master_flags[index]:
            master_index += 1
        color_prefix = ANSI_ROW_ALT if master_index % 2 else ""
        color_suffix = ANSI_RESET if color_prefix else ""
        description_is_empty = row[5] == ""
        primary_line = row[7] != ""
        highlight = ANSI_NO_DESCRIPTION if description_is_empty and primary_line else ""
        reset = ANSI_RESET if highlight else ""
        if highlight:
            print(f"{highlight}{layout.format(*row)}{reset}")
        else:
            print(f"{color_prefix}{layout.format(*row)}{color_suffix}")


def print_total(widths: Sequence[int], total_minutes: int) -> None:
    total_str = format_total_duration(total_minutes)
    total_width = sum(widths) + (len(widths) - 1)
    underline = f"{{:>{total_width + len(ANSI_UNDERLINE)}}}".format(
        ANSI_UNDERLINE + (len(total_str) * " ")
    )
    print(f"{underline}{ANSI_RESET}")
    print(f"{{:>{total_width}}}".format(total_str))


def format_total_duration(total_minutes: int) -> str:
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours}:{minutes:02d}:00"


def main() -> None:
    skip_report_header(sys.stdin)
    timew_entries = parse_timew_export(sys.stdin)

    config_filename = os.getenv(CONFIG_ENV_VAR, DEFAULT_CONFIG_FILENAME)
    project_configs = load_project_configuration(config_filename)

    annotation_delimiter_override = os.getenv(ANNOTATION_DELIMITER_ENV_VAR)
    output_separator_override = os.getenv(OUTPUT_SEPARATOR_ENV_VAR)

    dynamics_rows: List[DynamicsRow] = []
    for entry in timew_entries:
        project_config = resolve_project_config(entry.get("tags", []), project_configs)
        row, merge_on_equal_tags = build_dynamics_row(
            entry,
            project_config,
            annotation_delimiter_override,
            output_separator_override,
        )
        if row is None:
            continue
        merge_entries(dynamics_rows, row, merge_on_equal_tags)

    headers = [
        "Date",
        "Project",
        "Project Task",
        "Role",
        "Type",
        "Description",
        "External Comments",
        "Duration",
    ]

    table_rows, total_minutes, master_flags = build_table_rows(dynamics_rows)
    widths = compute_column_widths(table_rows, headers)
    layout = build_layout(widths)

    print_header(layout, headers)
    print_rows(layout, table_rows, master_flags)
    print_total(widths, total_minutes)


if __name__ == "__main__":
    main()
