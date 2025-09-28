#!/usr/bin/env python3

"""Enhanced summary table for Timewarrior reports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import sys
from typing import Dict, Iterable, List, Optional, Sequence

TIMEW_DATE_FORMAT = "%Y%m%dT%H%M%S%z"
MAX_ANNOTATION_WIDTH = 100
NOTES_DELIMITER = ";\n"

ANSI_RESET = "\033[0m"
ANSI_UNDERLINE = "\033[4m"
ANSI_ROW_ALT = "\033[48;2;26;26;26m"
ANSI_NO_ANNOTATION = "\033[38;2;238;162;87m"
ANSI_GAP = "\033[38;2;85;85;85m"


@dataclass
class TimewEntry:
    raw: Dict[str, object]
    start: datetime
    end: Optional[datetime]
    tags: str
    annotation_lines: List[str]

    @property
    def duration(self) -> timedelta:
        if self.end is None:
            now = datetime.now(tz=timezone.utc).replace(microsecond=0)
            return now - self.start
        return self.end - self.start

    @property
    def date(self) -> datetime:
        return self.start


def read_configuration(stream: Iterable[str]) -> Dict[str, str]:
    config: Dict[str, str] = {}
    for line in stream:
        if line == "\n":
            break
        key, _, remainder = line.partition(": ")
        value = remainder.rstrip("\n")
        config[key] = value
    return config


def read_entries(stream: Iterable[str]) -> List[Dict[str, object]]:
    payload = "".join(stream)
    return json.loads(payload) if payload else []


def join_tags(entry: Dict[str, object]) -> str:
    tags = entry.get("tags", [])
    return ", ".join(str(tag) for tag in tags)


def build_annotation_lines(entry: Dict[str, object]) -> List[str]:
    raw_annotation = entry.get("annotation", "")
    if raw_annotation:
        annotation_text = raw_annotation.replace("; ", "\n")
    else:
        annotation_text = "-"

    lines = annotation_text.split("\n")
    processed: List[str] = []
    for line in lines:
        if len(line) <= MAX_ANNOTATION_WIDTH:
            processed.append(line)
            continue

        chunks = [
            line[i : i + MAX_ANNOTATION_WIDTH]
            for i in range(0, len(line), MAX_ANNOTATION_WIDTH)
        ]
        processed.append(chunks[0])
        processed.extend(f"  {chunk}" for chunk in chunks[1:])

    return processed


def parse_timew_entries(entries: Sequence[Dict[str, object]]) -> List[TimewEntry]:
    parsed_entries: List[TimewEntry] = []
    for entry in entries:
        start = datetime.strptime(entry["start"], TIMEW_DATE_FORMAT)
        end_value = entry.get("end")
        end = datetime.strptime(end_value, TIMEW_DATE_FORMAT) if end_value else None
        parsed_entries.append(
            TimewEntry(
                raw=entry,
                start=start,
                end=end,
                tags=join_tags(entry),
                annotation_lines=build_annotation_lines(entry),
            )
        )
    return parsed_entries


def compute_column_widths(entries: Sequence[TimewEntry]) -> Dict[str, int]:
    max_tags_len = len("Tags")
    max_id_len = len("ID")
    max_annotation_len = len("Annotation")

    for entry in entries:
        tags_len = len(entry.tags)
        if tags_len > max_tags_len:
            max_tags_len = tags_len

        id_len = len(f"@{entry.raw['id']}")
        if id_len > max_id_len:
            max_id_len = id_len

        annotation_for_width = entry.raw.get("annotation", "")
        annotation_segments = (
            annotation_for_width.replace(";", "\n").split("\n")
            if annotation_for_width
            else [""]
        )
        for index, segment in enumerate(annotation_segments):
            segment_len = len(segment.strip())
            if index > 0:
                segment_len += 2
            if segment_len > MAX_ANNOTATION_WIDTH:
                segment_len = MAX_ANNOTATION_WIDTH
            if segment_len > max_annotation_len:
                max_annotation_len = segment_len

    return {
        "tags": max_tags_len,
        "id": max_id_len,
        "annotation": max_annotation_len,
    }


def build_layout(widths: Dict[str, int]) -> str:
    return (
        f"{{:<3}} {{:<10}} {{:<3}} {{:<{widths['id']}}} {{:<{widths['tags']}}} "
        f"{{:<{widths['annotation']}}} {{:>8}} {{:>8}} {{:>8}} {{:>8}}"
    )


def build_header(layout: str) -> str:
    parts = layout.split(" ")
    underlined_parts = [f"{ANSI_UNDERLINE}{part}{ANSI_RESET}" for part in parts]
    return " ".join(underlined_parts)


def local_time_string(moment: datetime) -> str:
    return moment.replace(tzinfo=timezone.utc).astimezone(tz=None).strftime("%H:%M:%S")


def should_reset_day(previous: Optional[TimewEntry], current: TimewEntry) -> bool:
    if previous is None:
        return True
    return previous.start.date() != current.start.date()


def should_print_total(current: TimewEntry, next_entry: Optional[TimewEntry]) -> bool:
    if next_entry is None:
        return True
    return next_entry.start.date() > current.start.date()


def next_day_gap(
    current: TimewEntry, next_entry: Optional[TimewEntry], layout: str
) -> Optional[str]:
    if next_entry is None or current.end is None:
        return None
    if next_entry.start.date() > current.start.date():
        return None
    if current.raw.get("end") == next_entry.raw.get("start"):
        return None

    gap_duration = next_entry.start - current.end
    start_local = local_time_string(current.end)
    next_local = local_time_string(next_entry.start)
    return layout.format(
        " ",
        " ",
        " ",
        "-",
        "-",
        "-",
        start_local,
        next_local,
        str(gap_duration),
        " ",
    )


def render_rows(entries: Sequence[TimewEntry], layout: str) -> timedelta:
    total_all = timedelta()
    total_day = timedelta()
    previous_entry: Optional[TimewEntry] = None

    for index, entry in enumerate(entries):
        next_entry = entries[index + 1] if index + 1 < len(entries) else None

        is_new_day = should_reset_day(previous_entry, entry)
        if is_new_day:
            total_day = timedelta()

        duration = entry.duration
        total_day += duration
        total_all += duration

        week_label = f"W{entry.start.isocalendar().week}" if is_new_day else ""
        date_label = entry.start.strftime("%Y-%m-%d") if is_new_day else ""
        day_label = entry.start.strftime("%a") if is_new_day else ""

        entry_id = f"@{entry.raw['id']}"
        start_local = local_time_string(entry.start)
        end_local = local_time_string(entry.end) if entry.end else "-"
        time_spent = str(duration)
        total_label = str(total_day) if should_print_total(entry, next_entry) else " "

        annotation_lines = entry.annotation_lines
        is_missing_annotation = annotation_lines and annotation_lines[0] == "-"
        row_color_prefix = ANSI_NO_ANNOTATION if is_missing_annotation else ""
        background_prefix = ANSI_ROW_ALT if index % 2 else ""
        color_prefix = f"{row_color_prefix}{background_prefix}"
        first_line = annotation_lines[0] if annotation_lines else "-"
        print(
            f"{color_prefix}{layout.format(week_label, date_label, day_label, entry_id, entry.tags, first_line, start_local, end_local, time_spent, total_label)}"
            f"{ANSI_RESET if (color_prefix or is_missing_annotation) else ''}"
        )

        for continuation in annotation_lines[1:]:
            prefix = ANSI_ROW_ALT if index % 2 else ""
            suffix = ANSI_RESET if prefix else ""
            print(
                f"{prefix}{layout.format(' ', ' ', ' ', ' ', ' ', continuation, ' ', ' ', ' ', ' ')}{suffix}"
            )

        gap_row = next_day_gap(entry, next_entry, layout)
        if gap_row:
            print(f"{ANSI_GAP}{gap_row}{ANSI_RESET}")

        previous_entry = entry

    return total_all


def format_total_line(total: timedelta, widths: Dict[str, int]) -> List[str]:
    spaces = (
        (3 + 1)
        + (10 + 1)
        + (3 + 1)
        + (widths["id"] + 1)
        + (widths["tags"] + 1)
        + (widths["annotation"] + 1)
        + (8 + 1)
        + (8 + 1)
        + (8 + 1)
        + 8
    )
    total_str = format_timedelta(total)
    underline = f"{{:>{spaces + len(ANSI_UNDERLINE)}}}".format(
        ANSI_UNDERLINE + (len(total_str) * " ")
    )
    underline_reset = underline + ANSI_RESET
    total_line = f"{{:>{spaces}}}".format(total_str)
    return [underline_reset, total_line]


def format_timedelta(value: timedelta) -> str:
    total_seconds = int(value.total_seconds())
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}"


if __name__ == "__main__":
    _ = read_configuration(sys.stdin)
    raw_entries = read_entries(sys.stdin)
    parsed_entries = parse_timew_entries(raw_entries)
    widths = compute_column_widths(parsed_entries)
    layout = build_layout(widths)

    header = build_header(layout)
    print(
        header.format(
            "Wk",
            "Date",
            "Day",
            "ID",
            "Tags",
            "Annotation",
            "Start",
            "End",
            "Time",
            "Total",
        )
    )

    total_duration = render_rows(parsed_entries, layout)

    for line in format_total_line(total_duration, widths):
        print(line)
