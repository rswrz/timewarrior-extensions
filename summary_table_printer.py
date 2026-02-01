from __future__ import annotations

from dataclasses import dataclass
import os
import sys
from typing import Callable, List, Optional, Sequence, TextIO, Tuple

ANSI_RESET = "\033[0m"
ANSI_UNDERLINE = "\033[4m"
ANSI_ROW_ALT = "\033[48;2;26;26;26m"
ANSI_FG_RESET = "\033[39m"


def terminal_width(stream: Optional[TextIO] = None) -> Optional[int]:
    target = stream or sys.stdout
    if target.isatty():
        try:
            columns = os.get_terminal_size(target.fileno()).columns
        except OSError:
            columns = 0
        return columns if columns > 0 else None

    # timew report may pipe stdout internally while stderr still points
    # at the user's terminal; fall back to stderr for terminal sizing.
    if sys.stderr.isatty():
        try:
            columns = os.get_terminal_size(sys.stderr.fileno()).columns
        except OSError:
            columns = 0
        return columns if columns > 0 else None

    return None


def allocate_widths(
    widths: Sequence[int],
    elastic_indices: Sequence[int],
    total_width: Optional[int],
    min_widths: Optional[Sequence[int]] = None,
    shrink_order: Optional[Sequence[int]] = None,
) -> List[int]:
    adjusted = list(widths)
    if total_width is None or not elastic_indices:
        return adjusted

    min_widths = list(min_widths) if min_widths is not None else [1] * len(adjusted)
    separator_count = len(adjusted) - 1
    current_total = sum(adjusted) + separator_count

    if current_total == total_width:
        return adjusted

    if current_total < total_width:
        extra = total_width - current_total
        index = 0
        while extra > 0:
            target = elastic_indices[index % len(elastic_indices)]
            adjusted[target] += 1
            extra -= 1
            index += 1
        return adjusted

    overflow = current_total - total_width
    capacities = {i: max(0, adjusted[i] - min_widths[i]) for i in elastic_indices}
    shrink_order = (
        list(shrink_order) if shrink_order is not None else list(elastic_indices)
    )

    while overflow > 0 and any(capacities[i] > 0 for i in elastic_indices):
        for i in shrink_order:
            if overflow <= 0:
                break
            if capacities[i] <= 0:
                continue
            adjusted[i] -= 1
            capacities[i] -= 1
            overflow -= 1
    current_total = sum(adjusted) + separator_count
    if current_total < total_width:
        extra = total_width - current_total
        index = 0
        while extra > 0:
            target = elastic_indices[index % len(elastic_indices)]
            adjusted[target] += 1
            extra -= 1
            index += 1

    return adjusted


def wrap_text(value: str, width: int) -> List[str]:
    if width <= 0 or len(value) <= width:
        return [value]
    words = value.split()
    if not words:
        return [value]
    lines: List[str] = []
    current = words[0]
    for word in words[1:]:
        if len(current) + 1 + len(word) <= width:
            current = f"{current} {word}"
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


@dataclass(frozen=True)
class ColumnSpec:
    align: str = "<"
    wrap: bool = False
    elastic: bool = False
    min_width: Optional[int] = None
    wrap_fn: Optional[Callable[[str, int], List[str]]] = None


@dataclass(frozen=True)
class Style:
    prefix: str = ""
    suffix: str = ""


RowStyleFn = Callable[[int, Sequence[str], int], Optional[Style]]
CellStyleFn = Callable[[int, int, str, Sequence[str], int], Optional[Style]]


def compute_widths(
    rows: Sequence[Sequence[str]],
    headers: Sequence[str],
    columns: Sequence[ColumnSpec],
    terminal_columns: Optional[int],
    shrink_order: Optional[Sequence[int]] = None,
) -> Tuple[List[int], bool]:
    if len(headers) != len(columns):
        raise ValueError("Headers and columns must be the same length")

    widths = [len(header) for header in headers]
    max_word_lengths = [len(header) for header in headers]

    for row in rows:
        for index, cell in enumerate(row):
            cell_value = "" if cell is None else str(cell)
            for segment in cell_value.split("\n"):
                segment_len = len(segment)
                if segment_len > widths[index]:
                    widths[index] = segment_len
                if columns[index].wrap and segment:
                    for word in segment.split():
                        word_len = len(word)
                        if word_len > max_word_lengths[index]:
                            max_word_lengths[index] = word_len

    for index, column in enumerate(columns):
        if column.min_width is not None:
            widths[index] = max(widths[index], column.min_width)

    total_width = sum(widths) + (len(widths) - 1)
    if terminal_columns and total_width > terminal_columns:
        min_widths = list(widths)
        for index, column in enumerate(columns):
            base = len(headers[index])
            if column.min_width is not None:
                base = max(base, column.min_width)
            if column.wrap:
                base = max(base, max_word_lengths[index])
            min_widths[index] = base
        elastic_indices = [
            index for index, column in enumerate(columns) if column.elastic
        ]
        if not elastic_indices:
            return widths, False
        if shrink_order is not None:
            shrink_order = [index for index in shrink_order if index in elastic_indices]
        return (
            allocate_widths(
                widths,
                elastic_indices,
                terminal_columns,
                min_widths,
                shrink_order=shrink_order,
            ),
            True,
        )

    return widths, False


def render_header(
    headers: Sequence[str],
    widths: Sequence[int],
    columns: Sequence[ColumnSpec],
    stream: TextIO = sys.stdout,
) -> None:
    parts = [
        f"{header:{column.align}{width}}"
        for header, column, width in zip(headers, columns, widths)
    ]
    underlined = [f"{ANSI_UNDERLINE}{part}{ANSI_RESET}" for part in parts]
    print(" ".join(underlined), file=stream)


def render_rows(
    rows: Sequence[Sequence[str]],
    widths: Sequence[int],
    columns: Sequence[ColumnSpec],
    stripe: bool = True,
    stripe_color: str = ANSI_ROW_ALT,
    row_style: Optional[RowStyleFn] = None,
    cell_style: Optional[CellStyleFn] = None,
    start_index: int = 0,
    stream: TextIO = sys.stdout,
) -> None:
    if len(widths) != len(columns):
        raise ValueError("Widths and columns must be the same length")

    layout_parts = [
        f"{{:{column.align}{width}}}" for column, width in zip(columns, widths)
    ]

    for row_offset, row in enumerate(rows):
        row_index = start_index + row_offset
        row_cells: List[List[str]] = []
        for index, (cell, column, width) in enumerate(zip(row, columns, widths)):
            cell_value = "" if cell is None else str(cell)
            lines: List[str] = []
            for segment in cell_value.split("\n"):
                if column.wrap:
                    wrap_fn = column.wrap_fn or wrap_text
                    wrapped = wrap_fn(segment, width)
                    if not wrapped:
                        wrapped = [""]
                    lines.extend(wrapped)
                else:
                    lines.append(segment)
            if not lines:
                lines = [""]
            row_cells.append(lines)

        max_lines = max((len(lines) for lines in row_cells), default=1)
        for line_index in range(max_lines):
            formatted_cells: List[str] = []
            for col_index, (lines, layout) in enumerate(zip(row_cells, layout_parts)):
                line_value = lines[line_index] if line_index < len(lines) else ""
                formatted = layout.format(line_value)
                if cell_style:
                    style = cell_style(
                        row_index,
                        col_index,
                        line_value,
                        row,
                        line_index,
                    )
                    if style:
                        formatted = f"{style.prefix}{formatted}{style.suffix}"
                formatted_cells.append(formatted)

            line = " ".join(formatted_cells)
            prefix = ""
            suffix = ""
            if stripe and row_index % 2:
                prefix += stripe_color
            if row_style:
                style = row_style(row_index, row, line_index)
                if style:
                    prefix += style.prefix
                    suffix = style.suffix
            reset = ANSI_RESET if (prefix or suffix) else ""
            print(f"{prefix}{line}{suffix}{reset}", file=stream)


def render_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    columns: Sequence[ColumnSpec],
    terminal_columns: Optional[int] = None,
    stripe: bool = True,
    stripe_color: str = ANSI_ROW_ALT,
    row_style: Optional[RowStyleFn] = None,
    cell_style: Optional[CellStyleFn] = None,
    shrink_order: Optional[Sequence[int]] = None,
    stream: TextIO = sys.stdout,
) -> Tuple[List[int], bool]:
    if terminal_columns is None:
        terminal_columns = terminal_width(stream)

    widths, constrained = compute_widths(
        rows,
        headers,
        columns,
        terminal_columns,
        shrink_order=shrink_order,
    )
    render_header(headers, widths, columns, stream=stream)
    render_rows(
        rows,
        widths,
        columns,
        stripe=stripe,
        stripe_color=stripe_color,
        row_style=row_style,
        cell_style=cell_style,
        stream=stream,
    )
    return widths, constrained
