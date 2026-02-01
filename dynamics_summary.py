#!/usr/bin/env python3

"""Timewarrior report that outputs Dynamics data in a tabular view."""

from __future__ import annotations

from dataclasses import dataclass
import sys
from typing import List, Optional, Sequence, Tuple

from summary_table_layout import allocate_widths, terminal_width, wrap_text

from dynamics_common import (
    DynamicsRecord,
    build_dynamics_records,
    load_project_configuration,
    parse_timew_export,
    resolve_report_config,
    sanitize_description,
    split_report_input,
)

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


def build_table_rows(
    entries: Sequence[DynamicsRow],
) -> Tuple[List[List[str]], int, List[int]]:
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
            rows.append(
                [
                    row.date if index == 0 else "",
                    row.project if index == 0 else "",
                    row.project_task if index == 0 else "",
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
    rows: Sequence[Sequence[str]],
    headers: Sequence[str],
    terminal_columns: Optional[int],
) -> tuple[List[int], bool]:
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))
    total_width = sum(widths) + (len(widths) - 1)
    if terminal_columns and total_width > terminal_columns:
        min_widths = list(widths)
        for index in (1, 2, 5, 6):
            min_widths[index] = len(headers[index])
        return allocate_widths(widths, [1, 2, 5, 6], terminal_columns, min_widths), True
    return widths, False


def build_layout(widths: Sequence[int]) -> str:
    alignments = ["<", "<", "<", "<", "<", "<", "<", ">"]
    parts = [f"{{:{align}{width}}}" for align, width in zip(alignments, widths)]
    return " ".join(parts)


def print_header(layout: str, headers: Sequence[str]) -> None:
    formatted = layout.format(*headers)
    columns = formatted.split(" ")
    underlined = [f"{ANSI_UNDERLINE}{column}{ANSI_RESET}" for column in columns]
    print(" ".join(underlined))


def print_rows(
    layout: str,
    rows: Sequence[Sequence[str]],
    master_flags: Sequence[int],
    widths: Sequence[int],
    constrained: bool,
) -> None:
    master_index = -1
    for index, row in enumerate(rows):
        if master_flags[index]:
            master_index += 1
        if constrained:
            wrapped_columns = {
                column_index: wrap_text(row[column_index], widths[column_index])
                for column_index in (1, 2, 5, 6)
            }
            max_lines = max(
                (len(lines) for lines in wrapped_columns.values()), default=1
            )
        else:
            wrapped_columns = {}
            max_lines = 1
        color_prefix = ANSI_ROW_ALT if master_index % 2 else ""
        color_suffix = ANSI_RESET if color_prefix else ""
        description_is_empty = row[5] == ""
        primary_line = row[7] != ""
        highlight = ANSI_NO_DESCRIPTION if description_is_empty and primary_line else ""
        reset = ANSI_RESET if highlight else ""

        for line_index in range(max_lines):
            if line_index == 0:
                output_row = list(row)
            else:
                output_row = ["" for _ in row]
            if constrained:
                for column_index, lines in wrapped_columns.items():
                    output_row[column_index] = (
                        lines[line_index] if line_index < len(lines) else ""
                    )
            if highlight:
                print(f"{highlight}{layout.format(*output_row)}{reset}")
            else:
                print(f"{color_prefix}{layout.format(*output_row)}{color_suffix}")


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


def build_rows(records: Sequence[DynamicsRecord]) -> List[DynamicsRow]:
    rows: List[DynamicsRow] = []
    for record in records:
        rows.append(
            DynamicsRow(
                date=record.date,
                duration_minutes=record.duration_minutes,
                project=record.project_display,
                project_task=record.project_task_display,
                role=record.role,
                type=record.type,
                description=record.description,
                external_comment=record.external_comment,
                annotation_delimiter=record.annotation_delimiter,
                output_separator=record.output_separator,
            )
        )
    return rows


def main() -> None:
    report_config, payload = split_report_input(sys.stdin)
    timew_entries = parse_timew_export(payload)
    config = resolve_report_config(report_config)
    project_configs = load_project_configuration(config.config_file)

    dynamics_records = build_dynamics_records(
        timew_entries,
        project_configs,
        config,
        merge_on_display_values=True,
        include_format_in_merge=False,
    )
    dynamics_rows = build_rows(dynamics_records)

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
    terminal_columns = terminal_width(sys.stdout)
    widths, constrained = compute_column_widths(table_rows, headers, terminal_columns)
    layout = build_layout(widths)

    print_header(layout, headers)
    print_rows(layout, table_rows, master_flags, widths, constrained)
    print_total(widths, total_minutes)


if __name__ == "__main__":
    main()
