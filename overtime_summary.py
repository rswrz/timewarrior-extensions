#!/usr/bin/env python3

"""Timewarrior report for overtime summaries."""

from __future__ import annotations

import sys
from typing import List, Optional, Sequence, Tuple

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
    format_clock_hms,
    format_duration_hms,
    format_signed_duration_hms,
    load_config,
    parse_timew_export,
    read_report_header,
    resolve_report_range,
)

ANSI_RED = "\033[31m"
ANSI_GREEN = "\033[32m"


def build_rows(
    days: Sequence[DaySummary],
) -> Tuple[List[List[str]], List[int], List[Optional[int]]]:
    rows: List[List[str]] = []
    overtime_values: List[int] = []
    weekly_total_values: List[Optional[int]] = []
    last_week = None
    week_total = 0

    for index, day in enumerate(days):
        week_cell = (
            day.week_label if last_week is None or day.week_label != last_week else ""
        )
        if last_week is None or day.week_label != last_week:
            week_total = 0
        week_total += day.overtime_seconds
        next_day = days[index + 1] if index + 1 < len(days) else None
        is_week_end = next_day is None or next_day.week_label != day.week_label
        weekly_total = week_total if is_week_end else None
        from_value = (
            format_clock_hms(day.from_second_of_day)
            if day.from_second_of_day is not None
            else ""
        )
        to_value = (
            format_clock_hms(day.to_second_of_day)
            if day.to_second_of_day is not None
            else ""
        )
        pause_value = (
            format_duration_hms(day.pause_seconds)
            if day.pause_seconds is not None
            else ""
        )

        rows.append(
            [
                week_cell,
                day.moment.strftime("%Y-%m-%d"),
                day.weekday_label,
                from_value,
                to_value,
                pause_value,
                format_duration_hms(day.expected_seconds),
                format_duration_hms(day.actual_seconds),
                format_signed_duration_hms(day.overtime_seconds),
                (
                    format_signed_duration_hms(weekly_total)
                    if weekly_total is not None
                    else ""
                ),
            ]
        )
        overtime_values.append(day.overtime_seconds)
        weekly_total_values.append(weekly_total)
        last_week = day.week_label

    return rows, overtime_values, weekly_total_values


def build_total_row(
    total_expected: int, total_actual: int, total_overtime: int
) -> List[str]:
    return [
        "",
        "",
        "",
        "",
        "",
        "",
        format_duration_hms(total_expected),
        format_duration_hms(total_actual),
        "",
        format_signed_duration_hms(total_overtime),
    ]


def format_total_overline(widths: Sequence[int], total_row: Sequence[str]) -> str:
    rendered: List[str] = []
    for index, width in enumerate(widths):
        spaces = " " * width
        if total_row[index]:
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

    headers = [
        "Wk",
        "Date",
        "Day",
        "From",
        "To",
        "Pause",
        "Expected",
        "Actual",
        "Overtime",
        "Total",
    ]
    columns = [
        ColumnSpec(align="<"),
        ColumnSpec(align="<"),
        ColumnSpec(align="<"),
        ColumnSpec(align=">"),
        ColumnSpec(align=">"),
        ColumnSpec(align=">"),
        ColumnSpec(align=">"),
        ColumnSpec(align=">"),
        ColumnSpec(align=">"),
        ColumnSpec(align=">"),
    ]

    if not day_summaries:
        widths, _ = compute_widths([], headers, columns, None)
        render_header(headers, widths, columns)
        return

    rows, overtime_values, weekly_total_values = build_rows(day_summaries)
    total_actual = sum(day.actual_seconds for day in day_summaries)
    total_expected = sum(day.expected_seconds for day in day_summaries)
    total_overtime = sum(day.overtime_seconds for day in day_summaries)
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
        if line_index != 0:
            return None
        seconds: Optional[int] = None
        if col_index == 8:
            seconds = overtime_values[row_index]
        elif col_index == 9:
            seconds = weekly_total_values[row_index]
        if seconds is None:
            return None
        if seconds < 0:
            return Style(prefix=ANSI_RED, suffix=ANSI_FG_RESET)
        if seconds > 0:
            return Style(prefix=ANSI_GREEN, suffix=ANSI_FG_RESET)
        return None

    render_rows(rows, widths, columns, cell_style=overtime_cell_style)

    print(format_total_overline(widths, total_row))
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
        if col_index == 9 and line_index == 0:
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
