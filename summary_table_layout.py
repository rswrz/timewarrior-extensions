from __future__ import annotations

import sys
import os
from typing import Iterable, List, Optional, Sequence, TextIO


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
