"""Console summary formatting for dependency graphs."""

import json
import os
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean, median
from typing import Final, cast

import click
import networkx as nx

from netimport_lib.violations import Violation, build_violations_payload


TOP_ITEMS_LIMIT: Final[int] = 10
PROJECT_FILE_NODE_TYPE: Final[str] = "project_file"
EXTERNAL_LIB_NODE_TYPE: Final[str] = "external_lib"
UNRESOLVED_PREFIX: Final[str] = "unresolved"
SUMMARY_INTRO_LINES: Final[tuple[str, ...]] = (
    (
        "(This report summarizes the project's import graph so a reader or LLM "
        "can spot hotspots, risky dependencies, isolated files, and missing "
        "links.)"
    ),
    (
        "(Incoming degree shows how many project files depend on a file; "
        "outgoing degree shows how many dependencies a file pulls in. Higher "
        "values usually mean higher impact or complexity.)"
    ),
)


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


@dataclass(frozen=True, slots=True)
class _DegreeMetricSummary:
    avg: float
    median: float
    min: int
    max: int


@dataclass(frozen=True, slots=True)
class _OverviewSummary:
    nodes: int
    edges: int
    project_files: int
    standard_library_modules: int
    external_libraries: int
    unresolved_imports: int


@dataclass(frozen=True, slots=True)
class _ProjectMetricsSummary:
    project_files_analyzed: int
    incoming_degree: _DegreeMetricSummary
    outgoing_degree: _DegreeMetricSummary
    total_degree: _DegreeMetricSummary


@dataclass(frozen=True, slots=True)
class _RankedProjectFileSummary:
    rank: int
    file: str
    incoming: int
    outgoing: int
    total: int


@dataclass(frozen=True, slots=True)
class _UnresolvedImportSummary:
    rank: int
    import_name: str
    type: str


@dataclass(frozen=True, slots=True)
class _DependencySummaryPayload:
    schema_version: int
    overview: _OverviewSummary
    project_metrics: _ProjectMetricsSummary
    most_coupled_project_files: list[_RankedProjectFileSummary]
    least_coupled_project_files: list[_RankedProjectFileSummary]
    most_depended_on_project_files: list[_RankedProjectFileSummary]
    most_dependent_project_files: list[_RankedProjectFileSummary]
    external_dependencies: list[str]
    unresolved_imports: list[_UnresolvedImportSummary]
    violations: list[dict[str, str]]


def print_summary(graph: nx.DiGraph, violations: Sequence[Violation] = ()) -> None:
    """Print a formatted dependency summary for a graph."""
    for line in format_summary(graph, violations):
        click.echo(line)


def print_json_summary(graph: nx.DiGraph, violations: Sequence[Violation] = ()) -> None:
    """Print a machine-readable dependency summary for a graph."""
    click.echo(format_summary_json(graph, violations))


def format_summary(graph: nx.DiGraph, violations: Sequence[Violation] = ()) -> list[str]:
    """Build a deterministic text summary for a dependency graph."""
    if not graph.nodes:
        return []

    project_entries = _build_project_entries(graph)
    sections = [
        _build_section(
            "Dependency Graph Summary",
            (
                "(High-level graph totals. Use this table to quickly size the "
                "project and see how much of the graph is project code, stdlib, "
                "external libraries, or unresolved imports.)"
            ),
            _format_overview(graph),
        ),
        _build_section(
            "Project Coupling Metrics",
            (
                "(Aggregate coupling across all project files. Avg and Median "
                "describe a typical file, while Min and Max highlight the "
                "spread and the biggest extremes.)"
            ),
            _format_project_metrics(project_entries),
        ),
        _build_section(
            "Most Coupled Project Files",
            (
                "(Files with the highest total degree. Higher totals mean a "
                "file is highly connected overall, so changes here are more "
                "likely to ripple across the project.)"
            ),
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
            (
                "(Files with the lowest total degree. Very low values can "
                "indicate isolated utilities, unfinished integration, or code "
                "paths that deserve a second look.)"
            ),
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
            (
                "(Files with the highest incoming degree. These are reuse hubs: "
                "the more incoming links a file has, the more carefully it "
                "should usually be changed.)"
            ),
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
            (
                "(Files with the highest outgoing degree. High outgoing values "
                "often point to orchestration code, complex workflows, or "
                "modules with many responsibilities.)"
            ),
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
            "External Dependencies",
            (
                "(Third-party libraries imported by the project. Review this "
                "list for dependency sprawl, standardization opportunities, and "
                "policy or supply-chain checks.)"
            ),
            _format_simple_node_list(_build_external_entries(graph)),
        ),
        _build_section(
            "Unresolved Imports",
            (
                "(Imports NetImport could not resolve. These often point to "
                "broken imports, missing files, excluded paths, or dynamic "
                "import patterns.)"
            ),
            _format_unresolved_entries(_build_unresolved_entries(graph)),
        ),
        _build_section(
            "Policy Violations",
            (
                "(Configured rule violations found during analysis. A non-empty "
                "table means the graph is valid to inspect, but not fully "
                "compliant with the active policy.)"
            ),
            _format_violations(violations),
        ),
    ]

    lines = [*SUMMARY_INTRO_LINES, ""]
    for section_index, section in enumerate(sections):
        if section_index > 0:
            lines.append("")
        lines.extend(section)

    return lines


def build_summary_payload(
    graph: nx.DiGraph,
    violations: Sequence[Violation] = (),
) -> dict[str, object]:
    """Build a deterministic structured summary for a dependency graph."""
    project_entries = _build_project_entries(graph)
    external_entries = _build_external_entries(graph)
    unresolved_entries = _build_unresolved_entries(graph)

    payload = _DependencySummaryPayload(
        schema_version=1,
        overview=_build_overview_summary(graph),
        project_metrics=_build_project_metrics_summary(project_entries),
        most_coupled_project_files=_build_ranked_project_files(
            sorted(
                project_entries,
                key=lambda entry: (
                    -entry.total,
                    -entry.incoming,
                    -entry.outgoing,
                    entry.display_name,
                ),
            )
        ),
        least_coupled_project_files=_build_ranked_project_files(
            sorted(
                project_entries,
                key=lambda entry: (
                    entry.total,
                    entry.incoming,
                    entry.outgoing,
                    entry.display_name,
                ),
            )
        ),
        most_depended_on_project_files=_build_ranked_project_files(
            sorted(
                project_entries,
                key=lambda entry: (
                    -entry.incoming,
                    -entry.total,
                    -entry.outgoing,
                    entry.display_name,
                ),
            )
        ),
        most_dependent_project_files=_build_ranked_project_files(
            sorted(
                project_entries,
                key=lambda entry: (
                    -entry.outgoing,
                    -entry.total,
                    -entry.incoming,
                    entry.display_name,
                ),
            )
        ),
        external_dependencies=[entry.display_name for entry in external_entries],
        unresolved_imports=[
            _UnresolvedImportSummary(
                rank=index,
                import_name=entry.display_name,
                type=entry.node_type,
            )
            for index, entry in enumerate(unresolved_entries, start=1)
        ],
        violations=build_violations_payload(list(violations)),
    )

    return cast("dict[str, object]", asdict(payload))


def format_summary_json(graph: nx.DiGraph, violations: Sequence[Violation] = ()) -> str:
    """Serialize a deterministic JSON dependency summary for a graph."""
    return json.dumps(build_summary_payload(graph, violations), indent=2)


def _build_section(title: str, description: str, body_lines: Sequence[str]) -> list[str]:
    return [title, "=" * len(title), description, *body_lines]


def _build_overview_summary(graph: nx.DiGraph) -> _OverviewSummary:
    return _OverviewSummary(
        nodes=graph.number_of_nodes(),
        edges=graph.number_of_edges(),
        project_files=_count_nodes_by_type(graph, PROJECT_FILE_NODE_TYPE),
        standard_library_modules=_count_nodes_by_type(graph, "std_lib"),
        external_libraries=_count_nodes_by_type(graph, EXTERNAL_LIB_NODE_TYPE),
        unresolved_imports=_count_unresolved_nodes(graph),
    )


def _format_overview(graph: nx.DiGraph) -> list[str]:
    overview = _build_overview_summary(graph)
    return _format_table(
        ("Metric", "Value"),
        [
            ("Nodes", str(overview.nodes)),
            ("Edges", str(overview.edges)),
            ("Project files", str(overview.project_files)),
            ("Standard library modules", str(overview.standard_library_modules)),
            ("External libraries", str(overview.external_libraries)),
            ("Unresolved imports", str(overview.unresolved_imports)),
        ],
    )


def _build_project_metrics_summary(
    project_entries: Sequence[_ProjectNodeSummary],
) -> _ProjectMetricsSummary:
    if not project_entries:
        zero_metrics = _DegreeMetricSummary(avg=0.0, median=0.0, min=0, max=0)
        return _ProjectMetricsSummary(
            project_files_analyzed=0,
            incoming_degree=zero_metrics,
            outgoing_degree=zero_metrics,
            total_degree=zero_metrics,
        )

    incoming_values = [entry.incoming for entry in project_entries]
    outgoing_values = [entry.outgoing for entry in project_entries]
    total_values = [entry.total for entry in project_entries]

    return _ProjectMetricsSummary(
        project_files_analyzed=len(project_entries),
        incoming_degree=_build_degree_metric_summary(incoming_values),
        outgoing_degree=_build_degree_metric_summary(outgoing_values),
        total_degree=_build_degree_metric_summary(total_values),
    )


def _format_project_metrics(project_entries: Sequence[_ProjectNodeSummary]) -> list[str]:
    if not project_entries:
        return _format_table(
            ("Metric", "Avg", "Median", "Min", "Max"),
            [("Project files analyzed", "0", "0", "0", "0")],
        )

    metrics = _build_project_metrics_summary(project_entries)

    return _format_table(
        ("Metric", "Avg", "Median", "Min", "Max"),
        [
            ("Project files analyzed", str(metrics.project_files_analyzed), "-", "-", "-"),
            _build_metric_row("Incoming degree", metrics.incoming_degree),
            _build_metric_row("Outgoing degree", metrics.outgoing_degree),
            _build_metric_row("Total degree", metrics.total_degree),
        ],
    )


def _build_degree_metric_summary(values: Sequence[int]) -> _DegreeMetricSummary:
    return _DegreeMetricSummary(
        avg=mean(values),
        median=median(values),
        min=min(values),
        max=max(values),
    )


def _build_metric_row(
    metric_name: str,
    values: _DegreeMetricSummary,
) -> tuple[str, str, str, str, str]:
    return (
        metric_name,
        f"{values.avg:.2f}",
        f"{values.median:.2f}",
        str(values.min),
        str(values.max),
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


def _build_ranked_project_files(
    project_entries: Sequence[_ProjectNodeSummary],
) -> list[_RankedProjectFileSummary]:
    return [
        _RankedProjectFileSummary(
            rank=index,
            file=entry.display_name,
            incoming=entry.incoming,
            outgoing=entry.outgoing,
            total=entry.total,
        )
        for index, entry in enumerate(project_entries[:TOP_ITEMS_LIMIT], start=1)
    ]


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


def _format_violations(violations: Sequence[Violation]) -> list[str]:
    if not violations:
        return _format_table(("Rule", "Message"), [("None", "-")])

    return _format_table(
        ("Rank", "Rule", "Target", "Type", "Message"),
        [
            (
                str(index),
                violation.rule,
                violation.label,
                violation.node_type,
                violation.message,
            )
            for index, violation in enumerate(violations, start=1)
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
