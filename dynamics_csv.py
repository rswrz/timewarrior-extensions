#!/usr/bin/env python3

"""Timewarrior extension to export Dynamics-compatible CSV data."""

import sys
from typing import Optional, Sequence

from dynamics_common import (
    DEFAULT_OUTPUT_SEPARATOR,
    DynamicsRecord,
    LLMRefiner,
    build_dynamics_records,
    load_project_configuration,
    parse_timew_export,
    resolve_report_config,
    sanitize_description,
    split_report_input,
)

CSV_DELIMITER = ","


def csv_escape_special_chars(text: str) -> str:
    """Escape CSV-sensitive characters to keep manual formatting consistent."""

    return text.replace('"', '""').replace("\\", "\\\\")


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


def write_output(entries: Sequence[DynamicsRecord]) -> None:
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
        line = format_csv_row(
            entry.as_csv_row(), entry.annotation_delimiter, entry.output_separator
        )
        if index + 1 == len(entries):
            sys.stdout.write(line)
        else:
            sys.stdout.write(line + "\n")


def main() -> None:
    report_config, payload = split_report_input(sys.stdin)
    timew_entries = parse_timew_export(payload)
    config = resolve_report_config(report_config)
    project_configs = load_project_configuration(config.config_file)

    dynamics_entries = build_dynamics_records(
        timew_entries,
        project_configs,
        config,
        merge_on_display_values=False,
        include_format_in_merge=True,
    )

    refiner = LLMRefiner.from_config(config.llm)
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
