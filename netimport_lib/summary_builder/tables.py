"""Shared section and table formatting helpers for summaries."""

from collections.abc import Sequence

from netimport_lib.summary_builder.constants import TableRow, _SummaryText


def _build_section(title: str, description: str, body_lines: Sequence[str]) -> list[str]:
    return [title, "=" * len(title), description, *body_lines]


def _normalize_table_rows(headers: TableRow, rows: Sequence[TableRow]) -> list[TableRow]:
    return list(rows) or [tuple(_SummaryText.none_text for _ in headers)]


def _build_column_widths(headers: TableRow, normalized_rows: Sequence[TableRow]) -> list[int]:
    columns = list(zip(headers, *normalized_rows, strict=False))
    return [max(len(cell) for cell in column) for column in columns]


def _build_table_border(widths: Sequence[int]) -> str:
    joined_segments = "+".join("-" * (width + 2) for width in widths)
    return f"+{joined_segments}+"


def _format_table(headers: TableRow, rows: Sequence[TableRow]) -> list[str]:
    normalized_rows = _normalize_table_rows(headers, rows)
    widths = _build_column_widths(headers, normalized_rows)
    border = _build_table_border(widths)
    table_lines = [border, _format_table_row(headers, widths), border]
    table_lines.extend(_format_table_row(row, widths) for row in normalized_rows)
    table_lines.append(border)
    return table_lines


def _format_table_row(row: TableRow, widths: Sequence[int]) -> str:
    cells: list[str] = []
    for cell, width in zip(row, widths, strict=True):
        cells.append(f" {cell.ljust(width)} ")
    return "|{}|".format("|".join(cells))
