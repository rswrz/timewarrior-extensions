#!/usr/bin/env python3

"""Simple Timewarrior CSV exporter."""

from __future__ import annotations

import json
import sys
from typing import Iterable, List, Dict

CSV_DELIMITER = ","


def skip_configuration(stream: Iterable[str]) -> None:
    for line in stream:
        if line == "\n":
            break


def read_export(stream: Iterable[str]) -> List[Dict[str, object]]:
    payload = "".join(stream)
    return json.loads(payload) if payload else []


def csv_escape(value: str) -> str:
    return value.replace('"', '""')


def format_row(columns: List[str]) -> str:
    escaped = [f'"{csv_escape(column)}"' for column in columns]
    return CSV_DELIMITER.join(escaped)


def main() -> None:
    skip_configuration(sys.stdin)
    entries = read_export(sys.stdin)

    print(format_row(["Start", "End", "Annotation", "Tags"]))

    for entry in entries:
        start = entry.get("start", "")
        end = entry.get("end", "")
        annotation = entry.get("annotation", "")
        tags = " ".join(entry.get("tags", []))

        print(format_row([start, end, annotation, tags]))


if __name__ == "__main__":
    main()
