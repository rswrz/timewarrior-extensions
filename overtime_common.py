#!/usr/bin/env python3

"""Shared helpers for overtime report extensions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

try:
    import json5 as json
except ImportError:
    import json
import os
import sys
import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

TIMEW_DATETIME_FORMAT = "%Y%m%dT%H%M%S%z"

ENV_PREFIX = "TIMEWARRIOR_EXT_OVERTIME_"
DAILY_HOURS_ENV_VAR = f"{ENV_PREFIX}DAILY_HOURS"
WORK_DAYS_ENV_VAR = f"{ENV_PREFIX}WORK_DAYS"
DEBUG_ENV_VAR = f"{ENV_PREFIX}DEBUG"

DEFAULT_DAILY_HOURS = 8.0
DEFAULT_WORK_DAYS = "1,2,3,4,5"


@dataclass
class OvertimeConfig:
    daily_hours: float
    work_days: List[int]


@dataclass
class DaySummary:
    moment: date
    week_label: str
    weekday_label: str
    from_second_of_day: Optional[int]
    to_second_of_day: Optional[int]
    pause_seconds: Optional[int]
    actual_seconds: int
    expected_seconds: int
    overtime_seconds: int


def read_report_header(stream: Iterable[str]) -> Dict[str, str]:
    config: Dict[str, str] = {}
    for line in stream:
        if line.strip() == "":
            break
        key, _, remainder = line.partition(": ")
        value = remainder.rstrip("\n")
        if key:
            config[key.strip()] = value
    return config


def parse_timew_export(stream: Iterable[str]) -> List[dict]:
    payload = "".join(stream)
    return json.loads(payload) if payload else []


def _debug_enabled() -> bool:
    value = os.getenv(DEBUG_ENV_VAR, "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _debug(message: str) -> None:
    if _debug_enabled():
        sys.stderr.write(message.rstrip() + "\n")


def _parse_header_datetime(value: str) -> Optional[datetime]:
    if not value:
        return None

    cleaned = value.strip()
    if cleaned.endswith("Z") and len(cleaned) > 1:
        cleaned = f"{cleaned[:-1]}+0000"

    formats = [
        TIMEW_DATETIME_FORMAT,
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            parsed = datetime.strptime(cleaned, fmt)
            if parsed.tzinfo is None:
                local_tz = datetime.now().astimezone().tzinfo
                parsed = parsed.replace(tzinfo=local_tz)
            return parsed
        except ValueError:
            continue
    return None


def _extract_range_dates(
    header: Dict[str, str],
) -> Tuple[Optional[date], Optional[date]]:
    normalized = {key.strip().lower(): value for key, value in header.items()}
    range_value = normalized.get("range", "")
    if range_value:
        matches = re.findall(r"(\d{4}-\d{2}-\d{2})", range_value)
        if len(matches) >= 2:
            start_dt = _parse_header_datetime(matches[0])
            end_dt = _parse_header_datetime(matches[1])
        else:
            start_dt = None
            end_dt = None
    else:
        start_dt = None
        end_dt = None

    if start_dt is None or end_dt is None:
        start_value = (
            normalized.get("start")
            or normalized.get("range_start")
            or normalized.get("temp.report.start")
        )
        end_value = (
            normalized.get("end")
            or normalized.get("range_end")
            or normalized.get("temp.report.end")
        )
        start_dt = _parse_header_datetime(start_value) if start_value else None
        end_dt = _parse_header_datetime(end_value) if end_value else None

    start_date = start_dt.astimezone().date() if start_dt else None
    end_date = end_dt.astimezone().date() if end_dt else None
    if start_date and end_dt and end_date:
        local_end = end_dt.astimezone()
        if local_end.time() == time.min and end_date > start_date:
            end_date = end_date - timedelta(days=1)

    _debug(f"[overtime] header range='{range_value}' start={start_date} end={end_date}")
    return start_date, end_date


def _warn(message: str) -> None:
    sys.stderr.write(message.rstrip() + "\n")


def _parse_float_env(
    name: str, default: float, allow_none: bool = False
) -> Optional[float]:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return None if allow_none else default

    try:
        value = float(raw)
    except ValueError:
        _warn(f"Invalid value for {name}. Using default {default}.")
        return default

    if value < 0:
        _warn(f"Negative value for {name}. Using default {default}.")
        return default

    return value


def _parse_work_days(value: Optional[str]) -> List[int]:
    raw = value if value is not None else DEFAULT_WORK_DAYS
    raw = raw.strip()
    if not raw:
        _warn("WORK_DAYS was empty. Using default work days.")
        raw = DEFAULT_WORK_DAYS

    parsed: List[int] = []
    for part in raw.split(","):
        item = part.strip()
        if not item:
            continue
        try:
            day = int(item)
        except ValueError:
            _warn(f"Invalid WORK_DAYS entry: {item}. Skipping.")
            continue
        if day < 1 or day > 7:
            _warn(f"WORK_DAYS entry out of range (1-7): {day}. Skipping.")
            continue
        if day not in parsed:
            parsed.append(day)

    if not parsed:
        _warn("WORK_DAYS did not include any valid entries. Using defaults.")
        return _parse_work_days(DEFAULT_WORK_DAYS)

    return parsed


def load_config() -> OvertimeConfig:
    daily_hours = _parse_float_env(DAILY_HOURS_ENV_VAR, DEFAULT_DAILY_HOURS)
    work_days = _parse_work_days(os.getenv(WORK_DAYS_ENV_VAR))
    return OvertimeConfig(
        daily_hours=daily_hours if daily_hours is not None else DEFAULT_DAILY_HOURS,
        work_days=work_days,
    )


def effective_daily_hours(config: OvertimeConfig) -> float:
    if not config.work_days:
        raise ValueError("WORK_DAYS must not be empty.")
    return config.daily_hours


def format_clock_hms(seconds_of_day: int) -> str:
    if seconds_of_day < 0:
        seconds_of_day = 0
    if seconds_of_day >= 24 * 3600:
        return "24:00:00"
    hours, remainder = divmod(seconds_of_day, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def format_duration_hms(seconds: int) -> str:
    total = abs(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}"


def format_signed_duration_hms(seconds: int) -> str:
    if seconds < 0:
        sign = "-"
    elif seconds > 0:
        sign = "+"
    else:
        sign = ""
    return f"{sign}{format_duration_hms(seconds)}"


def _seconds_since_midnight(moment: datetime) -> int:
    midnight = datetime.combine(moment.date(), time.min, tzinfo=moment.tzinfo)
    return int((moment - midnight).total_seconds())


def _to_second_of_day(day: date, moment: datetime) -> int:
    if moment.date() > day and moment.time() == time.min:
        return 24 * 3600
    return _seconds_since_midnight(moment)


def build_day_segments(entries: Sequence[dict]) -> Dict[date, List[Tuple[datetime, datetime]]]:
    """Split ended entries into local-day segments.

    Returns a mapping of day -> list of (start_local, end_local) segments, where
    end_local may be a local midnight on the following date for segments that end
    exactly at the day boundary.
    """

    segments: Dict[date, List[Tuple[datetime, datetime]]] = {}

    for entry in entries:
        if "end" not in entry:
            continue

        try:
            start_dt = datetime.strptime(entry["start"], TIMEW_DATETIME_FORMAT)
            end_dt = datetime.strptime(entry["end"], TIMEW_DATETIME_FORMAT)
        except (KeyError, ValueError):
            continue

        start_local = start_dt.astimezone()
        end_local = end_dt.astimezone()

        if end_local <= start_local:
            continue

        current = start_local
        while current.date() < end_local.date():
            midnight = datetime.combine(
                current.date() + timedelta(days=1), time.min, tzinfo=current.tzinfo
            )
            if midnight > current:
                segments.setdefault(current.date(), []).append((current, midnight))
            current = midnight

        if end_local > current:
            segments.setdefault(current.date(), []).append((current, end_local))

    return segments


def _merge_intervals(
    intervals: Sequence[Tuple[datetime, datetime]],
) -> List[Tuple[datetime, datetime]]:
    if not intervals:
        return []

    ordered = sorted(intervals, key=lambda pair: pair[0])
    merged: List[Tuple[datetime, datetime]] = []
    current_start, current_end = ordered[0]
    for start, end in ordered[1:]:
        if start <= current_end:
            if end > current_end:
                current_end = end
        else:
            merged.append((current_start, current_end))
            current_start, current_end = start, end
    merged.append((current_start, current_end))
    return merged


def _sum_interval_seconds(intervals: Sequence[Tuple[datetime, datetime]]) -> int:
    total = 0
    for start, end in intervals:
        delta = end - start
        seconds = int(delta.total_seconds())
        if seconds > 0:
            total += seconds
    return total


def _pause_seconds(merged: Sequence[Tuple[datetime, datetime]]) -> int:
    if len(merged) < 2:
        return 0
    pause = 0
    for index in range(len(merged) - 1):
        gap = merged[index + 1][0] - merged[index][1]
        seconds = int(gap.total_seconds())
        if seconds > 0:
            pause += seconds
    return pause


def build_overtime_summaries(
    entries: Sequence[dict],
    config: OvertimeConfig,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[DaySummary]:
    segments_by_date = build_day_segments(entries)
    actual_by_date = {
        day: _sum_interval_seconds(day_segments)
        for day, day_segments in segments_by_date.items()
    }
    dates_in_scope = set(actual_by_date.keys())

    if not dates_in_scope and (start_date is None or end_date is None):
        return []

    if dates_in_scope:
        if start_date is None:
            start_date = min(dates_in_scope)
        if end_date is None:
            end_date = max(dates_in_scope)
    if start_date is None or end_date is None:
        return []
    if end_date < start_date:
        return []

    date_range: List[date] = []
    cursor = start_date
    while cursor <= end_date:
        date_range.append(cursor)
        cursor += timedelta(days=1)

    daily_hours = effective_daily_hours(config)
    expected_seconds_per_day = int(round(daily_hours * 3600))

    day_summaries: List[DaySummary] = []

    for current in date_range:
        day_segments = segments_by_date.get(current, [])
        actual = actual_by_date.get(current, 0)
        is_work_day = current.isoweekday() in config.work_days
        expected = expected_seconds_per_day if is_work_day else 0
        overtime = actual - expected

        key = current.isocalendar().week
        if actual == 0 and expected == 0:
            continue

        from_second: Optional[int] = None
        to_second: Optional[int] = None
        pause_seconds: Optional[int] = None
        if day_segments:
            merged = _merge_intervals(day_segments)
            earliest_start = min(start for start, _end in merged)
            latest_end = max(end for _start, end in merged)
            from_second = _seconds_since_midnight(earliest_start)
            to_second = _to_second_of_day(current, latest_end)
            pause_seconds = _pause_seconds(merged)

        day_summaries.append(
            DaySummary(
                moment=current,
                week_label=f"W{key}",
                weekday_label=current.strftime("%a"),
                from_second_of_day=from_second,
                to_second_of_day=to_second,
                pause_seconds=pause_seconds,
                actual_seconds=actual,
                expected_seconds=expected,
                overtime_seconds=overtime,
            )
        )

    return day_summaries


def resolve_report_range(
    header: Dict[str, str],
) -> Tuple[Optional[date], Optional[date]]:
    if _debug_enabled():
        normalized = {key.strip().lower(): value for key, value in header.items()}
        keys = [
            "range",
            "start",
            "end",
            "range_start",
            "range_end",
            "temp.report.start",
            "temp.report.end",
        ]
        header_pairs = ", ".join(f"{key}={normalized.get(key, '')}" for key in keys)
        _debug(f"[overtime] header keys {{ {header_pairs} }}")
    return _extract_range_dates(header)
