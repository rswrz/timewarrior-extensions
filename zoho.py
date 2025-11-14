#!/usr/bin/env python3

"""Timewarrior extension to export Zoho-compatible CSV data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
try:
    import json5 as json
except ImportError:
    import json
import math
import os
import sys
from typing import Dict, Iterable, List, Optional, Sequence

TIMEW_DATETIME_FORMAT = "%Y%m%dT%H%M%S%z"
DEFAULT_CONFIG_FILENAME = ".zoho_config.json"
CONFIG_ENV_VAR = "TIMEWARRIOR_EXT_ZOHO_CONFIG_JSON"
CSV_DELIMITER = ","
NOTES_DELIMITER = ";\n"


@dataclass
class ZohoEntry:
    """In-memory representation of a Zoho CSV row."""

    date: str
    duration: timedelta
    project_name: str
    task_name: str
    billable_status: str
    notes: str

    def as_row(self) -> List[str]:
        return [
            self.date,
            format_duration(self.duration),
            self.project_name,
            self.task_name,
            self.billable_status,
            self.notes,
        ]


def calculate_working_time(
    start: datetime, end: datetime, multiplier: float = 1.0
) -> timedelta:
    """Return a timedelta rounded up to 15-minute blocks after applying multiplier."""

    total_seconds = (end - start).total_seconds()
    total_seconds *= multiplier
    total_minutes = math.ceil(round(total_seconds / 60) / 15) * 15
    return timedelta(minutes=int(total_minutes))


def csv_escape_special_chars(text: str) -> str:
    """Escape characters that need quoting in CSV output."""

    return text.replace('"', '""').replace("\\", "\\\\")


def load_project_configuration() -> List[Dict[str, object]]:
    """Read project definitions from the configured JSON file."""

    config_filename = os.getenv(CONFIG_ENV_VAR, DEFAULT_CONFIG_FILENAME)
    config_path = os.path.join(sys.path[0], config_filename)
    with open(config_path, encoding="utf-8") as config_file:
        return json.load(config_file)


def parse_timew_export(stream: Iterable[str]) -> List[Dict[str, object]]:
    """Parse the JSON payload produced by `timew export`."""

    for line in stream:
        if line == "\n":
            break

    payload = "".join(stream)
    return json.loads(payload) if payload else []


def resolve_project_config(
    tags: Sequence[str], project_configs: Sequence[Dict[str, object]]
) -> Dict[str, object]:
    """Return the project configuration matching the provided tags."""

    tag_set = set(tags)
    matched_config: Optional[Dict[str, object]] = None

    for project_config in project_configs:
        config_tags = set(project_config.get("tag", []))
        if config_tags == tag_set:
            return project_config
        if config_tags < tag_set:
            if matched_config is None:
                matched_config = project_config
                continue
            current_tags = set(matched_config.get("tag", []))
            if len(tag_set - config_tags) < len(tag_set - current_tags):
                matched_config = project_config

    if matched_config:
        return matched_config

    return {
        "project_name": "NO PROJECT FOUND FOR THESE TAGS: {}".format(", ".join(tags)),
        "task_name": "",
    }


def merge_entries(entries: List[ZohoEntry], new_entry: ZohoEntry) -> None:
    """Insert or merge the new entry into the existing list."""

    for index, existing in enumerate(entries):
        if (
            existing.date == new_entry.date
            and existing.project_name == new_entry.project_name
            and existing.task_name == new_entry.task_name
        ):
            if existing.notes == new_entry.notes:
                entries[index].duration = existing.duration + new_entry.duration
                return

            existing_title = existing.notes.split(NOTES_DELIMITER)[0]
            new_title = new_entry.notes.split(NOTES_DELIMITER)[0]
            if existing_title == new_title:
                entries[index].duration = existing.duration + new_entry.duration
                merged_notes = merge_notes(existing.notes, new_entry.notes)
                entries[index].notes = merged_notes
                return

    entries.append(new_entry)


def merge_notes(existing_notes: str, new_notes: str) -> str:
    """Merge note items while preserving order and removing duplicates."""

    remainder = NOTES_DELIMITER.join(new_notes.split(NOTES_DELIMITER)[1:])
    merged = NOTES_DELIMITER.join([existing_notes, remainder])
    unique_segments: List[str] = []
    for segment in merged.split(NOTES_DELIMITER):
        if segment not in unique_segments:
            unique_segments.append(segment)
    return NOTES_DELIMITER.join(unique_segments)


def sanitize_notes(notes: str) -> str:
    """Remove hidden note markers before writing to the CSV."""

    visible = [
        segment
        for segment in notes.split(NOTES_DELIMITER)
        if not (segment.startswith("++") and segment.endswith("++"))
    ]
    return NOTES_DELIMITER.join(visible)


def format_duration(duration_value: timedelta) -> str:
    """Return the Zoho time format (HH:MM) by trimming seconds from timedelta."""

    duration_string = str(duration_value)
    return duration_string[:-3] if duration_string.endswith(":00") else duration_string


def format_csv_row(values: Sequence[str]) -> str:
    """Render a CSV row with the expected quoting."""

    escaped = [f'"{csv_escape_special_chars(value)}"' for value in values]
    return CSV_DELIMITER.join(escaped)


def write_output(entries: Sequence[ZohoEntry]) -> None:
    """Send the CSV header and rows to stdout."""

    header = (
        "Date",
        "Time Spent",
        "Project Name",
        "Task Name",
        "Billable Status",
        "Notes",
    )
    print(format_csv_row(header))

    for entry in entries:
        row = entry.as_row()
        row[5] = sanitize_notes(row[5])
        print(format_csv_row(row))


def build_entry(
    track: Dict[str, object], project_config: Dict[str, object]
) -> Optional[ZohoEntry]:
    """Create a ZohoEntry for the provided time track if it has ended."""

    if "end" not in track:
        return None

    tags = track.get("tags", [])
    annotation = track.get("annotation", "")
    notes = annotation.replace("; ", NOTES_DELIMITER)

    if "note_prefix" in project_config:
        prefix = project_config["note_prefix"]
        notes = prefix + "\n" + notes if notes else prefix + "\n"

    start = datetime.strptime(track["start"], TIMEW_DATETIME_FORMAT)
    end = datetime.strptime(track["end"], TIMEW_DATETIME_FORMAT)

    multiplier = (
        float(project_config["multiplier"]) if "multiplier" in project_config else 1.0
    )
    time_spent = calculate_working_time(start, end, multiplier)

    project_name = project_config.get("project_name", "")
    task_name = project_config.get("task_name", "")
    billable_status = (
        "Billable" if project_config.get("billable") is True else "Non Billable"
    )

    return ZohoEntry(
        date=start.astimezone().strftime("%Y-%m-%d"),
        duration=time_spent,
        project_name=project_name,
        task_name=task_name,
        billable_status=billable_status,
        notes=notes,
    )


def main() -> None:
    project_configs = load_project_configuration()
    timew_entries = parse_timew_export(sys.stdin)

    entries: List[ZohoEntry] = []
    for track in timew_entries:
        project_config = resolve_project_config(track.get("tags", []), project_configs)
        entry = build_entry(track, project_config)
        if entry is None:
            continue
        merge_entries(entries, entry)

    write_output(entries)


if __name__ == "__main__":
    main()
