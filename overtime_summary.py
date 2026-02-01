#!/usr/bin/env python3

"""Timewarrior report for overtime summaries."""

from __future__ import annotations

import sys
from typing import List, Sequence, Tuple

from overtime_common import (
    DaySummary,
    build_overtime_summaries,
    format_minutes,
    load_config,
    parse_timew_export,
    read_report_header,
    resolve_report_range,
)

ANSI_RESET = "\033[0m"
ANSI_UNDERLINE = "\033[4m"
ANSI_RED = "\033[31m"
ANSI_GREEN = "\033[32m"
ALIGNMENTS = ["<", "<", "<", ">", ">", ">"]


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


def compute_column_widths(
    rows: Sequence[Sequence[str]], headers: Sequence[str]
) -> List[int]:
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))
    return widths


def format_row(
    row: Sequence[str],
    widths: Sequence[int],
    overtime_sign: int = 0,
) -> str:
    rendered: List[str] = []
    for index, (cell, width, align) in enumerate(zip(row, widths, ALIGNMENTS)):
        formatted = f"{cell:{align}{width}}"
        if index == 5 and overtime_sign:
            if overtime_sign < 0:
                formatted = f"{ANSI_RED}{formatted}{ANSI_RESET}"
            else:
                formatted = f"{ANSI_GREEN}{formatted}{ANSI_RESET}"
        rendered.append(formatted)
    return " ".join(rendered)


def print_header(widths: Sequence[int], headers: Sequence[str]) -> None:
    rendered: List[str] = []
    for header, width, align in zip(headers, widths, ALIGNMENTS):
        formatted = f"{header:{align}{width}}"
        rendered.append(f"{ANSI_UNDERLINE}{formatted}{ANSI_RESET}")
    print(" ".join(rendered))


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

    if not day_summaries:
        widths = compute_column_widths([], headers)
        print_header(widths, headers)
        return

    rows, overtime_values = build_rows(day_summaries)
    total_actual = sum(day.actual_minutes for day in day_summaries)
    total_expected = sum(day.expected_minutes for day in day_summaries)
    total_overtime = sum(day.overtime_minutes for day in day_summaries)
    total_row = build_total_row(total_expected, total_actual, total_overtime)
    widths = compute_column_widths(rows + [total_row], headers)
    print_header(widths, headers)
    for row, overtime_minutes in zip(rows, overtime_values):
        sign = 1 if overtime_minutes > 0 else -1 if overtime_minutes < 0 else 0
        print(format_row(row, widths, sign))

    print(format_total_overline(widths))
    total_sign = 1 if total_overtime > 0 else -1 if total_overtime < 0 else 0
    print(format_row(total_row, widths, total_sign))


if __name__ == "__main__":
    main()
