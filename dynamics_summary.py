#!/usr/bin/env python3

"""Timewarrior report that outputs Dynamics data in a tabular view."""

from __future__ import annotations

from dataclasses import dataclass
import sys
from typing import List, Sequence, Tuple

from summary_table_printer import (
    ANSI_FG_RESET,
    ANSI_RESET,
    ANSI_UNDERLINE,
    ColumnSpec,
    Style,
    render_table,
    terminal_width,
)

from dynamics_common import (
    DynamicsRecord,
    build_dynamics_records,
    load_project_configuration,
    parse_timew_export,
    resolve_report_config,
    sanitize_description,
    split_report_input,
)

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
) -> Tuple[List[List[str]], int]:
    rows: List[List[str]] = []
    total_minutes = 0

    for row in entries:
        total_minutes += row.duration_minutes
        description_display = sanitize_description(
            row.description,
            row.annotation_delimiter,
            row.output_separator,
        )
        if row.output_separator:
            description_lines = description_display.split(row.output_separator)
        else:
            description_lines = [description_display]
        external_lines = (
            row.external_comment.split("\n") if row.external_comment else [""]
        )
        rows.append(
            [
                row.date,
                row.project,
                row.project_task,
                row.role,
                row.type,
                "\n".join(description_lines),
                "\n".join(external_lines),
                row.formatted_duration(),
            ]
        )

    return rows, total_minutes


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

    table_rows, total_minutes = build_table_rows(dynamics_rows)
    columns = [
        ColumnSpec(align="<"),
        ColumnSpec(align="<", wrap=True, elastic=True),
        ColumnSpec(align="<", wrap=True, elastic=True),
        ColumnSpec(align="<"),
        ColumnSpec(align="<"),
        ColumnSpec(align="<", wrap=True, elastic=True),
        ColumnSpec(align="<", wrap=True, elastic=True),
        ColumnSpec(align=">"),
    ]

    def row_highlight(
        _row_index: int, row: Sequence[str], line_index: int
    ) -> Style | None:
        if line_index != 0:
            return None
        description_is_empty = row[5] == ""
        primary_line = row[7] != ""
        if description_is_empty and primary_line:
            return Style(prefix=ANSI_NO_DESCRIPTION, suffix=ANSI_FG_RESET)
        return None

    terminal_columns = terminal_width(sys.stdout)
    widths, _ = render_table(
        headers,
        table_rows,
        columns,
        terminal_columns=terminal_columns,
        shrink_order=[5, 6, 1, 2],
        row_style=row_highlight,
    )
    print_total(widths, total_minutes)


if __name__ == "__main__":
    main()
