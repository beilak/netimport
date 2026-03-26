"""Console summary formatting for dependency graphs."""

import os
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Final, cast

import click
import networkx as nx


TOP_ITEMS_LIMIT: Final[int] = 10
PROJECT_FILE_NODE_TYPE: Final[str] = "project_file"
EXTERNAL_LIB_NODE_TYPE: Final[str] = "external_lib"
UNRESOLVED_PREFIX: Final[str] = "unresolved"


@dataclass(frozen=True, slots=True)
class _ProjectNodeSummary:
    node_id: str
    display_name: str
    incoming: int
    outgoing: int
    total: int


@dataclass(frozen=True, slots=True)
class _SimpleNodeSummary:
    node_id: str
    display_name: str
    node_type: str


def print_summary(graph: nx.DiGraph) -> None:
    """Print a formatted dependency summary for a graph."""
    for line in format_summary(graph):
        click.echo(line)


def format_summary(graph: nx.DiGraph) -> list[str]:
    """Build a deterministic text summary for a dependency graph."""
    if not graph.nodes:
        return []

    project_entries = _build_project_entries(graph)
    sections = [
        _build_section("Dependency Graph Summary", _format_overview(graph)),
        _build_section("Project Coupling Metrics", _format_project_metrics(project_entries)),
        _build_section(
            "Most Coupled Project Files",
            _format_project_ranking(
                sorted(
                    project_entries,
                    key=lambda entry: (
                        -entry.total,
                        -entry.incoming,
                        -entry.outgoing,
                        entry.display_name,
                    ),
                ),
            ),
        ),
        _build_section(
            "Least Coupled Project Files",
            _format_project_ranking(
                sorted(
                    project_entries,
                    key=lambda entry: (
                        entry.total,
                        entry.incoming,
                        entry.outgoing,
                        entry.display_name,
                    ),
                ),
            ),
        ),
        _build_section(
            "Most Depended-On Project Files",
            _format_project_ranking(
                sorted(
                    project_entries,
                    key=lambda entry: (
                        -entry.incoming,
                        -entry.total,
                        -entry.outgoing,
                        entry.display_name,
                    ),
                ),
            ),
        ),
        _build_section(
            "Most Dependent Project Files",
            _format_project_ranking(
                sorted(
                    project_entries,
                    key=lambda entry: (
                        -entry.outgoing,
                        -entry.total,
                        -entry.incoming,
                        entry.display_name,
                    ),
                ),
            ),
        ),
        _build_section(
            "External Dependencies", _format_simple_node_list(_build_external_entries(graph))
        ),
        _build_section(
            "Unresolved Imports", _format_unresolved_entries(_build_unresolved_entries(graph))
        ),
    ]

    lines: list[str] = []
    for section_index, section in enumerate(sections):
        if section_index > 0:
            lines.append("")
        lines.extend(section)

    return lines


def _build_section(title: str, body_lines: Sequence[str]) -> list[str]:
    return [title, "=" * len(title), *body_lines]


def _format_overview(graph: nx.DiGraph) -> list[str]:
    return _format_table(
        ("Metric", "Value"),
        [
            ("Nodes", str(graph.number_of_nodes())),
            ("Edges", str(graph.number_of_edges())),
            ("Project files", str(_count_nodes_by_type(graph, PROJECT_FILE_NODE_TYPE))),
            ("Standard library modules", str(_count_nodes_by_type(graph, "std_lib"))),
            ("External libraries", str(_count_nodes_by_type(graph, EXTERNAL_LIB_NODE_TYPE))),
            ("Unresolved imports", str(_count_unresolved_nodes(graph))),
        ],
    )


def _format_project_metrics(project_entries: Sequence[_ProjectNodeSummary]) -> list[str]:
    if not project_entries:
        return _format_table(
            ("Metric", "Avg", "Median", "Min", "Max"),
            [("Project files analyzed", "0", "0", "0", "0")],
        )

    incoming_values = [entry.incoming for entry in project_entries]
    outgoing_values = [entry.outgoing for entry in project_entries]
    total_values = [entry.total for entry in project_entries]

    return _format_table(
        ("Metric", "Avg", "Median", "Min", "Max"),
        [
            ("Project files analyzed", str(len(project_entries)), "-", "-", "-"),
            _build_metric_row("Incoming degree", incoming_values),
            _build_metric_row("Outgoing degree", outgoing_values),
            _build_metric_row("Total degree", total_values),
        ],
    )


def _build_metric_row(metric_name: str, values: Sequence[int]) -> tuple[str, str, str, str, str]:
    return (
        metric_name,
        f"{mean(values):.2f}",
        f"{median(values):.2f}",
        str(min(values)),
        str(max(values)),
    )


def _iter_node_items(graph: nx.DiGraph) -> Iterable[tuple[str, Mapping[str, object]]]:
    for node_id, raw_data in graph.nodes(data=True):
        yield str(node_id), cast("Mapping[str, object]", raw_data)


def _get_str_attribute(data: Mapping[str, object], key: str, default: str = "") -> str:
    value = data.get(key, default)
    if isinstance(value, str):
        return value
    return default


def _get_int_attribute(data: Mapping[str, object], key: str, default: int = 0) -> int:
    value = data.get(key, default)
    if isinstance(value, int):
        return value
    return default


def _build_project_entries(graph: nx.DiGraph) -> list[_ProjectNodeSummary]:
    project_root = _infer_project_root(graph)
    entries: list[_ProjectNodeSummary] = []

    for node_id, data in _iter_node_items(graph):
        if _get_str_attribute(data, "type") != PROJECT_FILE_NODE_TYPE:
            continue

        entries.append(
            _ProjectNodeSummary(
                node_id=node_id,
                display_name=_format_project_display_name(node_id, project_root),
                incoming=_get_int_attribute(data, "in_degree"),
                outgoing=_get_int_attribute(data, "out_degree"),
                total=_get_int_attribute(data, "total_degree"),
            )
        )

    return entries


def _infer_project_root(graph: nx.DiGraph) -> str | None:
    project_dirs = [
        str(Path(node_id).parent)
        for node_id, data in _iter_node_items(graph)
        if _get_str_attribute(data, "type") == PROJECT_FILE_NODE_TYPE
    ]
    if not project_dirs:
        return None

    return os.path.commonpath(project_dirs)


def _format_project_display_name(node_id: str, project_root: str | None) -> str:
    if project_root is not None:
        try:
            relative_path = os.path.relpath(node_id, project_root)
        except ValueError:
            return Path(node_id).name

        if not relative_path.startswith(".."):
            return relative_path

    return Path(node_id).name


def _format_project_ranking(project_entries: Sequence[_ProjectNodeSummary]) -> list[str]:
    return _format_table(
        ("Rank", "File", "Incoming", "Outgoing", "Total"),
        [
            (
                str(index),
                entry.display_name,
                str(entry.incoming),
                str(entry.outgoing),
                str(entry.total),
            )
            for index, entry in enumerate(project_entries[:TOP_ITEMS_LIMIT], start=1)
        ],
    )


def _build_external_entries(graph: nx.DiGraph) -> list[_SimpleNodeSummary]:
    entries = [
        _SimpleNodeSummary(
            node_id=node_id,
            display_name=_get_str_attribute(data, "label", node_id),
            node_type=_get_str_attribute(data, "type"),
        )
        for node_id, data in _iter_node_items(graph)
        if _get_str_attribute(data, "type") == EXTERNAL_LIB_NODE_TYPE
    ]

    return sorted(entries, key=lambda entry: entry.display_name)


def _build_unresolved_entries(graph: nx.DiGraph) -> list[_SimpleNodeSummary]:
    entries = [
        _SimpleNodeSummary(
            node_id=node_id,
            display_name=_get_str_attribute(data, "label", node_id),
            node_type=_get_str_attribute(data, "type"),
        )
        for node_id, data in _iter_node_items(graph)
        if _get_str_attribute(data, "type").startswith(UNRESOLVED_PREFIX)
    ]

    return sorted(entries, key=lambda entry: (entry.display_name, entry.node_type))


def _format_simple_node_list(entries: Sequence[_SimpleNodeSummary]) -> list[str]:
    if not entries:
        return _format_table(("Dependency",), [("None",)])

    return _format_table(
        ("Rank", "Dependency"),
        [(str(index), entry.display_name) for index, entry in enumerate(entries, start=1)],
    )


def _format_unresolved_entries(entries: Sequence[_SimpleNodeSummary]) -> list[str]:
    if not entries:
        return _format_table(("Import", "Type"), [("None", "-")])

    return _format_table(
        ("Rank", "Import", "Type"),
        [
            (str(index), entry.display_name, entry.node_type)
            for index, entry in enumerate(entries, start=1)
        ],
    )


def _format_table(headers: tuple[str, ...], rows: Sequence[tuple[str, ...]]) -> list[str]:
    normalized_rows = list(rows) or [tuple("None" for _ in headers)]
    columns = list(zip(headers, *normalized_rows, strict=False))
    widths = [max(len(cell) for cell in column) for column in columns]

    border = "+" + "+".join("-" * (width + 2) for width in widths) + "+"
    table_lines = [border, _format_table_row(headers, widths), border]
    table_lines.extend(_format_table_row(row, widths) for row in normalized_rows)
    table_lines.append(border)

    return table_lines


def _format_table_row(row: tuple[str, ...], widths: Sequence[int]) -> str:
    cells = [f" {cell.ljust(width)} " for cell, width in zip(row, widths, strict=True)]
    return "|" + "|".join(cells) + "|"


def _count_nodes_by_type(graph: nx.DiGraph, node_type: str) -> int:
    return sum(
        1 for _, data in _iter_node_items(graph) if _get_str_attribute(data, "type") == node_type
    )


def _count_unresolved_nodes(graph: nx.DiGraph) -> int:
    return sum(
        1
        for _, data in _iter_node_items(graph)
        if _get_str_attribute(data, "type").startswith(UNRESOLVED_PREFIX)
    )
