import os
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median

import click
import networkx as nx


TOP_ITEMS_LIMIT = 10


@dataclass(frozen=True)
class ProjectNodeSummary:
    node_id: str
    display_name: str
    incoming: int
    outgoing: int
    total: int


@dataclass(frozen=True)
class SimpleNodeSummary:
    node_id: str
    display_name: str
    node_type: str


def print_summary(graph: nx.DiGraph) -> None:
    for line in format_summary(graph):
        click.echo(line)


def format_summary(graph: nx.DiGraph) -> list[str]:
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
                    key=lambda entry: (-entry.total, -entry.incoming, -entry.outgoing, entry.display_name),
                ),
            ),
        ),
        _build_section(
            "Least Coupled Project Files",
            _format_project_ranking(
                sorted(
                    project_entries,
                    key=lambda entry: (entry.total, entry.incoming, entry.outgoing, entry.display_name),
                ),
            ),
        ),
        _build_section(
            "Most Depended-On Project Files",
            _format_project_ranking(
                sorted(
                    project_entries,
                    key=lambda entry: (-entry.incoming, -entry.total, -entry.outgoing, entry.display_name),
                ),
            ),
        ),
        _build_section(
            "Most Dependent Project Files",
            _format_project_ranking(
                sorted(
                    project_entries,
                    key=lambda entry: (-entry.outgoing, -entry.total, -entry.incoming, entry.display_name),
                ),
            ),
        ),
        _build_section("External Dependencies", _format_simple_node_list(_build_external_entries(graph))),
        _build_section("Unresolved Imports", _format_unresolved_entries(_build_unresolved_entries(graph))),
    ]

    lines: list[str] = []
    for section_index, section in enumerate(sections):
        if section_index > 0:
            lines.append("")
        lines.extend(section)
    return lines


def _build_section(title: str, body_lines: list[str]) -> list[str]:
    return [title, "=" * len(title), *body_lines]


def _format_overview(graph: nx.DiGraph) -> list[str]:
    return _format_table(
        ("Metric", "Value"),
        [
            ("Nodes", str(graph.number_of_nodes())),
            ("Edges", str(graph.number_of_edges())),
            ("Project files", str(_count_nodes_by_type(graph, "project_file"))),
            ("Standard library modules", str(_count_nodes_by_type(graph, "std_lib"))),
            ("External libraries", str(_count_nodes_by_type(graph, "external_lib"))),
            ("Unresolved imports", str(_count_unresolved_nodes(graph))),
        ],
    )


def _format_project_metrics(project_entries: list[ProjectNodeSummary]) -> list[str]:
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


def _build_metric_row(metric_name: str, values: list[int]) -> tuple[str, str, str, str, str]:
    return (
        metric_name,
        f"{mean(values):.2f}",
        f"{median(values):.2f}",
        str(min(values)),
        str(max(values)),
    )


def _build_project_entries(graph: nx.DiGraph) -> list[ProjectNodeSummary]:
    project_root = _infer_project_root(graph)
    entries: list[ProjectNodeSummary] = []

    for node_id, data in graph.nodes(data=True):
        if data.get("type") != "project_file":
            continue

        entries.append(
            ProjectNodeSummary(
                node_id=str(node_id),
                display_name=_format_project_display_name(str(node_id), project_root),
                incoming=int(data.get("in_degree", 0)),
                outgoing=int(data.get("out_degree", 0)),
                total=int(data.get("total_degree", 0)),
            )
        )

    return entries


def _infer_project_root(graph: nx.DiGraph) -> str | None:
    project_dirs = [
        str(Path(str(node_id)).parent)
        for node_id, data in graph.nodes(data=True)
        if data.get("type") == "project_file"
    ]
    if not project_dirs:
        return None
    return os.path.commonpath(project_dirs)


def _format_project_display_name(node_id: str, project_root: str | None) -> str:
    if project_root:
        try:
            relative_path = os.path.relpath(node_id, project_root)
            if not relative_path.startswith(".."):
                return relative_path
        except ValueError:
            pass
    return str(Path(node_id).name)


def _format_project_ranking(
    project_entries: list[ProjectNodeSummary],
) -> list[str]:
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


def _build_external_entries(graph: nx.DiGraph) -> list[SimpleNodeSummary]:
    entries = [
        SimpleNodeSummary(
            node_id=str(node_id),
            display_name=str(data.get("label", node_id)),
            node_type=str(data.get("type", "")),
        )
        for node_id, data in graph.nodes(data=True)
        if data.get("type") == "external_lib"
    ]
    return sorted(entries, key=lambda entry: entry.display_name)


def _build_unresolved_entries(graph: nx.DiGraph) -> list[SimpleNodeSummary]:
    entries = [
        SimpleNodeSummary(
            node_id=str(node_id),
            display_name=str(data.get("label", node_id)),
            node_type=str(data.get("type", "")),
        )
        for node_id, data in graph.nodes(data=True)
        if str(data.get("type", "")).startswith("unresolved")
    ]
    return sorted(entries, key=lambda entry: (entry.display_name, entry.node_type))


def _format_simple_node_list(entries: list[SimpleNodeSummary]) -> list[str]:
    if not entries:
        return _format_table(("Dependency",), [("None",)])
    return _format_table(
        ("Rank", "Dependency"),
        [(str(index), entry.display_name) for index, entry in enumerate(entries, start=1)],
    )


def _format_unresolved_entries(entries: list[SimpleNodeSummary]) -> list[str]:
    if not entries:
        return _format_table(("Import", "Type"), [("None", "-")])
    return _format_table(
        ("Rank", "Import", "Type"),
        [(str(index), entry.display_name, entry.node_type) for index, entry in enumerate(entries, start=1)],
    )


def _format_table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> list[str]:
    normalized_rows = rows or [tuple("None" for _ in headers)]
    columns = list(zip(headers, *normalized_rows, strict=False))
    widths = [max(len(str(cell)) for cell in column) for column in columns]

    border = "+" + "+".join("-" * (width + 2) for width in widths) + "+"

    table_lines = [border, _format_table_row(headers, widths), border]
    table_lines.extend(_format_table_row(row, widths) for row in normalized_rows)
    table_lines.append(border)
    return table_lines


def _format_table_row(row: tuple[str, ...], widths: list[int]) -> str:
    cells = [f" {str(cell).ljust(width)} " for cell, width in zip(row, widths, strict=True)]
    return "|" + "|".join(cells) + "|"


def _count_nodes_by_type(graph: nx.DiGraph, node_type: str) -> int:
    return sum(1 for _, data in graph.nodes(data=True) if data.get("type") == node_type)


def _count_unresolved_nodes(graph: nx.DiGraph) -> int:
    return sum(1 for _, data in graph.nodes(data=True) if str(data.get("type", "")).startswith("unresolved"))
