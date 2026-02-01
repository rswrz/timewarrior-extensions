#!/usr/bin/env python3

"""Enhanced summary table for Timewarrior reports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
import json
import sys
from typing import Dict, Iterable, List, Optional, Sequence

from summary_table_layout import allocate_widths, terminal_width, wrap_text

TIMEW_DATE_FORMAT = "%Y%m%dT%H%M%S%z"
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
            now = datetime.now(tz=self.start.tzinfo or timezone.utc).replace(
                microsecond=0
            )
            return now - self.start
        return self.end - self.start

    @property
    def date(self) -> datetime:
        return self.start


def read_configuration(stream: Iterable[str]) -> Dict[str, str]:
    config: Dict[str, str] = {}
    for line in stream:
        if line.strip() == "":
            break
        key, _, remainder = line.partition(": ")
        value = remainder.rstrip("\n")
        config[key] = value
    return config


def parse_header_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None

    cleaned = value.strip()
    if cleaned.endswith("Z") and len(cleaned) > 1:
        cleaned = f"{cleaned[:-1]}+0000"

    formats = [TIMEW_DATE_FORMAT, "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"]
    for fmt in formats:
        try:
            parsed = datetime.strptime(cleaned, fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=datetime.now().astimezone().tzinfo)
            return parsed
        except ValueError:
            continue
    return None


def resolve_report_range(
    config: Dict[str, str],
) -> tuple[Optional[datetime], Optional[datetime]]:
    start_value = config.get("temp.report.start")
    end_value = config.get("temp.report.end")
    if not end_value:
        return None, None
    start_dt = parse_header_datetime(start_value)
    end_dt = parse_header_datetime(end_value)
    if start_dt and end_dt:
        local_end = end_dt.astimezone()
        if (
            local_end.time() == time.min
            and local_end.date() > start_dt.astimezone().date()
        ):
            end_dt = end_dt - timedelta(days=1)
    return start_dt, end_dt


def read_entries(stream: Iterable[str]) -> List[Dict[str, object]]:
    payload = "".join(stream)
    return json.loads(payload) if payload else []


def join_tags(entry: Dict[str, object]) -> str:
    raw_tags = entry.get("tags", [])
    if not isinstance(raw_tags, list):
        return ""
    return ", ".join(str(tag) for tag in raw_tags)


def build_annotation_lines(entry: Dict[str, object]) -> List[str]:
    raw_annotation = entry.get("annotation", "")
    if raw_annotation:
        annotation_text = str(raw_annotation).replace("; ", "\n")
    else:
        annotation_text = "-"

    return annotation_text.split("\n")


def parse_timew_entries(entries: Sequence[Dict[str, object]]) -> List[TimewEntry]:
    parsed_entries: List[TimewEntry] = []
    for entry in entries:
        start_raw = entry.get("start")
        if not start_raw:
            continue
        start = datetime.strptime(str(start_raw), TIMEW_DATE_FORMAT)
        end_value = entry.get("end")
        end = (
            datetime.strptime(str(end_value), TIMEW_DATE_FORMAT) if end_value else None
        )
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


def format_timew_timestamp(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime(TIMEW_DATE_FORMAT)


def split_entries_by_day(
    entries: Sequence[TimewEntry],
    range_start: Optional[datetime],
    range_end: Optional[datetime],
) -> List[TimewEntry]:
    split_entries: List[TimewEntry] = []

    start_date = range_start.astimezone().date() if range_start else None
    end_date = range_end.astimezone().date() if range_end else None

    for entry in entries:
        start_local = entry.start.astimezone()
        end_value = entry.end
        if end_value is None:
            end_value = datetime.now(tz=timezone.utc).replace(microsecond=0)
        end_local = end_value.astimezone()

        if end_local <= start_local:
            continue

        current_day = start_local.date()
        last_day = end_local.date()
        tzinfo = start_local.tzinfo

        while current_day <= last_day:
            if start_date and current_day < start_date:
                current_day += timedelta(days=1)
                continue
            if end_date and current_day > end_date:
                break

            day_start = datetime.combine(current_day, time.min, tzinfo=tzinfo)
            day_end = day_start + timedelta(days=1)
            segment_start = max(start_local, day_start)
            segment_end = min(end_local, day_end)
            if segment_end <= segment_start:
                current_day += timedelta(days=1)
                continue

            segment_end_value: Optional[datetime] = segment_end
            if (
                entry.end is None
                and current_day == end_local.date()
                and segment_end == end_local
            ):
                segment_end_value = None

            raw = dict(entry.raw)
            raw["start"] = format_timew_timestamp(segment_start)
            if segment_end_value is None:
                raw.pop("end", None)
            else:
                raw["end"] = format_timew_timestamp(segment_end)

            split_entries.append(
                TimewEntry(
                    raw=raw,
                    start=segment_start,
                    end=segment_end_value,
                    tags=entry.tags,
                    annotation_lines=entry.annotation_lines,
                )
            )

            current_day += timedelta(days=1)

    return split_entries


def compute_column_widths(
    entries: Sequence[TimewEntry], terminal_columns: Optional[int]
) -> tuple[List[int], bool]:
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
            str(annotation_for_width).replace(";", "\n").split("\n")
            if annotation_for_width
            else [""]
        )
        for segment in annotation_segments:
            segment_len = len(segment.strip())
            if segment_len > max_annotation_len:
                max_annotation_len = segment_len

    widths = [3, 10, 3, max_id_len, max_tags_len, max_annotation_len, 8, 8, 8, 8]
    total_width = sum(widths) + (len(widths) - 1)
    if terminal_columns and total_width > terminal_columns:
        min_widths = list(widths)
        tags_limit = max(len("Tags"), terminal_columns // 4)
        min_widths[4] = min(widths[4], tags_limit)
        min_widths[5] = len("Annotation")
        return (
            allocate_widths(
                widths,
                [4, 5],
                terminal_columns,
                min_widths,
                shrink_order=[5, 4],
            ),
            True,
        )
    return widths, False


def build_layout(widths: Sequence[int]) -> str:
    alignments = ["<", "<", "<", "<", "<", "<", ">", ">", ">", ">"]
    parts = [f"{{:{align}{width}}}" for align, width in zip(alignments, widths)]
    return " ".join(parts)


def build_header(layout: str) -> str:
    parts = layout.split(" ")
    underlined_parts = [f"{ANSI_UNDERLINE}{part}{ANSI_RESET}" for part in parts]
    return " ".join(underlined_parts)


def local_time_string(moment: datetime) -> str:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(tz=None).strftime("%H:%M:%S")


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


def render_rows(
    entries: Sequence[TimewEntry],
    layout: str,
    widths: Sequence[int],
    constrained: bool,
) -> timedelta:
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

        if constrained:
            annotation_lines = wrap_annotation_lines(entry.annotation_lines, widths[5])
            tag_lines = wrap_text(entry.tags, widths[4])
        else:
            annotation_lines = entry.annotation_lines
            tag_lines = [entry.tags]
        max_lines = max(len(annotation_lines), len(tag_lines))
        if max_lines == 0:
            annotation_lines = ["-"]
            tag_lines = [""]
            max_lines = 1

        is_missing_annotation = annotation_lines and annotation_lines[0] == "-"
        row_color_prefix = ANSI_NO_ANNOTATION if is_missing_annotation else ""
        background_prefix = ANSI_ROW_ALT if index % 2 else ""
        color_prefix = f"{row_color_prefix}{background_prefix}"

        for line_index in range(max_lines):
            tags_line = tag_lines[line_index] if line_index < len(tag_lines) else ""
            annotation_line = (
                annotation_lines[line_index]
                if line_index < len(annotation_lines)
                else ""
            )
            if line_index == 0:
                print(
                    f"{color_prefix}{layout.format(week_label, date_label, day_label, entry_id, tags_line, annotation_line, start_local, end_local, time_spent, total_label)}"
                    f"{ANSI_RESET if (color_prefix or is_missing_annotation) else ''}"
                )
            else:
                prefix = ANSI_ROW_ALT if index % 2 else ""
                suffix = ANSI_RESET if prefix else ""
                print(
                    f"{prefix}{layout.format(' ', ' ', ' ', ' ', tags_line, annotation_line, ' ', ' ', ' ', ' ')}{suffix}"
                )

        gap_row = next_day_gap(entry, next_entry, layout)
        if gap_row:
            print(f"{ANSI_GAP}{gap_row}{ANSI_RESET}")

        previous_entry = entry

    return total_all


def format_total_line(total: timedelta, widths: Sequence[int]) -> List[str]:
    spaces = sum(widths) + (len(widths) - 1)
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


def wrap_annotation_lines(lines: Sequence[str], width: int) -> List[str]:
    if width <= 0:
        return list(lines)
    wrapped: List[str] = []
    for line in lines:
        chunks = wrap_text(line, width)
        if not chunks:
            wrapped.append("")
            continue
        wrapped.append(chunks[0])
        if width <= 1:
            wrapped.extend(chunk[:width] for chunk in chunks[1:])
        else:
            wrapped.extend(f"…{chunk[: width - 1]}" for chunk in chunks[1:])
    return wrapped


if __name__ == "__main__":
    config = read_configuration(sys.stdin)
    raw_entries = read_entries(sys.stdin)
    parsed_entries = parse_timew_entries(raw_entries)
    range_start, range_end = resolve_report_range(config)
    parsed_entries = split_entries_by_day(parsed_entries, range_start, range_end)
    terminal_columns = terminal_width(sys.stdout)
    widths, constrained = compute_column_widths(parsed_entries, terminal_columns)
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

    total_duration = render_rows(parsed_entries, layout, widths, constrained)

    for line in format_total_line(total_duration, widths):
        print(line)
