#!/usr/bin/env python3

"""Timewarrior report that exports overtime summaries to CSV."""

from __future__ import annotations

import sys
from typing import List, Sequence

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

CSV_DELIMITER = ","


def csv_escape(value: str) -> str:
    return value.replace('"', '""').replace("\\", "\\\\")


def format_row(values: Sequence[str]) -> str:
    escaped = [f'"{csv_escape(value)}"' for value in values]
    return CSV_DELIMITER.join(escaped)


def build_rows(days: Sequence[DaySummary]) -> List[List[str]]:
    rows: List[List[str]] = []
    for day in days:
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
                day.moment.strftime("%Y-%m-%d"),
                from_value,
                to_value,
                pause_value,
                format_duration_hms(day.expected_seconds),
                format_duration_hms(day.actual_seconds),
                format_signed_duration_hms(day.overtime_seconds),
            ]
        )
    return rows


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
    rows = build_rows(day_summaries)

    header = [
        "Date",
        "From",
        "To",
        "Pause",
        "Expected",
        "Actual",
        "Overtime",
    ]
    sys.stdout.write(format_row(header) + "\n")

    for index, row in enumerate(rows):
        line = format_row(row)
        if index + 1 == len(rows):
            sys.stdout.write(line)
        else:
            sys.stdout.write(line + "\n")


if __name__ == "__main__":
    main()
