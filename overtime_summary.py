#!/usr/bin/env python3

"""Timewarrior report for overtime summaries."""

from __future__ import annotations

import sys
from typing import List, Sequence, Tuple

from summary_table_printer import (
    ANSI_FG_RESET,
    ANSI_RESET,
    ANSI_UNDERLINE,
    ColumnSpec,
    Style,
    compute_widths,
    render_header,
    render_rows,
)
from overtime_common import (
    DaySummary,
    build_overtime_summaries,
    format_minutes,
    load_config,
    parse_timew_export,
    read_report_header,
    resolve_report_range,
)

ANSI_RED = "\033[31m"
ANSI_GREEN = "\033[32m"


def format_overtime_minutes(minutes: int) -> str:
    if minutes < 0:
        sign = "-"
    elif minutes > 0:
        sign = "+"
    else:
        sign = ""
    total = abs(minutes)
    hours, remainder = divmod(total, 60)
    return f"{sign}{hours}:{remainder:02d}"


def build_rows(
    days: Sequence[DaySummary],
) -> Tuple[List[List[str]], List[int]]:
    rows: List[List[str]] = []
    overtime_values: List[int] = []
    last_week = None

    for day in days:
        week_cell = (
            day.week_label if last_week is None or day.week_label != last_week else ""
        )
        rows.append(
            [
                week_cell,
                day.moment.strftime("%Y-%m-%d"),
                day.weekday_label,
                format_minutes(day.expected_minutes),
                format_minutes(day.actual_minutes),
                format_overtime_minutes(day.overtime_minutes),
            ]
        )
        overtime_values.append(day.overtime_minutes)
        last_week = day.week_label

    return rows, overtime_values


def build_total_row(
    total_expected: int, total_actual: int, total_overtime: int
) -> List[str]:
    return [
        "",
        "",
        "",
        format_minutes(total_expected),
        format_minutes(total_actual),
        format_overtime_minutes(total_overtime),
    ]


def format_total_overline(widths: Sequence[int]) -> str:
    rendered: List[str] = []
    for index, width in enumerate(widths):
        spaces = " " * width
        if index >= 3:
            rendered.append(f"{ANSI_UNDERLINE}{spaces}{ANSI_RESET}")
        else:
            rendered.append(spaces)
    return " ".join(rendered)


def main() -> None:
    header = read_report_header(sys.stdin)
    entries = parse_timew_export(sys.stdin)

    try:
        config = load_config()
    except ValueError as exc:
        sys.stderr.write(f"{exc}\n")
        sys.exit(1)

    start_date, end_date = resolve_report_range(header)
    day_summaries = build_overtime_summaries(
        entries,
        config,
        start_date=start_date,
        end_date=end_date,
    )

    headers = ["Week", "Date", "Day", "Expected", "Actual", "Overtime"]
    columns = [
        ColumnSpec(align="<"),
        ColumnSpec(align="<"),
        ColumnSpec(align="<"),
        ColumnSpec(align=">"),
        ColumnSpec(align=">"),
        ColumnSpec(align=">"),
    ]

    if not day_summaries:
        widths, _ = compute_widths([], headers, columns, None)
        render_header(headers, widths, columns)
        return

    rows, overtime_values = build_rows(day_summaries)
    total_actual = sum(day.actual_minutes for day in day_summaries)
    total_expected = sum(day.expected_minutes for day in day_summaries)
    total_overtime = sum(day.overtime_minutes for day in day_summaries)
    total_row = build_total_row(total_expected, total_actual, total_overtime)
    widths, _ = compute_widths(rows + [total_row], headers, columns, None)
    render_header(headers, widths, columns)

    def overtime_cell_style(
        row_index: int,
        col_index: int,
        _value: str,
        _row: Sequence[str],
        line_index: int,
    ) -> Style | None:
        if col_index != 5 or line_index != 0:
            return None
        minutes = overtime_values[row_index]
        if minutes < 0:
            return Style(prefix=ANSI_RED, suffix=ANSI_FG_RESET)
        if minutes > 0:
            return Style(prefix=ANSI_GREEN, suffix=ANSI_FG_RESET)
        return None

    render_rows(rows, widths, columns, cell_style=overtime_cell_style)

    print(format_total_overline(widths))
    total_sign = 1 if total_overtime > 0 else -1 if total_overtime < 0 else 0
    total_style = None
    if total_sign < 0:
        total_style = Style(prefix=ANSI_RED, suffix=ANSI_FG_RESET)
    elif total_sign > 0:
        total_style = Style(prefix=ANSI_GREEN, suffix=ANSI_FG_RESET)

    def total_cell_style(
        _row_index: int,
        col_index: int,
        _value: str,
        _row: Sequence[str],
        line_index: int,
    ) -> Style | None:
        if col_index == 5 and line_index == 0:
            return total_style
        return None

    render_rows(
        [total_row],
        widths,
        columns,
        stripe=False,
        cell_style=total_cell_style,
    )


if __name__ == "__main__":
    main()
