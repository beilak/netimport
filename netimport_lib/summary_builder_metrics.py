"""Metric builders for dependency summary overviews and coupling data."""

from collections.abc import Sequence
from statistics import mean, median

import networkx as nx

from netimport_lib.summary_builder_constants import _SummaryText
from netimport_lib.summary_builder_counts import (
    _count_nodes_by_type,
    _count_unresolved_nodes,
)
from netimport_lib.summary_builder_models import (
    _DegreeMetricSummary,
    _OverviewSummary,
    _ProjectMetricsSummary,
    _ProjectNodeSummary,
)
from netimport_lib.summary_builder_tables import _format_table


def _build_overview_summary(graph: nx.DiGraph) -> _OverviewSummary:
    return _OverviewSummary(
        nodes=graph.number_of_nodes(),
        edges=graph.number_of_edges(),
        project_files=_count_nodes_by_type(graph, _SummaryText.project_file_node_type),
        standard_library_modules=_count_nodes_by_type(graph, "std_lib"),
        external_libraries=_count_nodes_by_type(graph, _SummaryText.external_lib_node_type),
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
        zero_metrics = _build_zero_degree_metric_summary()
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
            [
                (
                    _SummaryText.project_files_analyzed_label,
                    _SummaryText.zero_text,
                    _SummaryText.zero_text,
                    _SummaryText.zero_text,
                    _SummaryText.zero_text,
                )
            ],
        )
    metrics = _build_project_metrics_summary(project_entries)
    return _format_table(
        ("Metric", "Avg", "Median", "Min", "Max"),
        [
            (
                _SummaryText.project_files_analyzed_label,
                str(metrics.project_files_analyzed),
                _SummaryText.not_available_text,
                _SummaryText.not_available_text,
                _SummaryText.not_available_text,
            ),
            _build_metric_row("Incoming degree", metrics.incoming_degree),
            _build_metric_row("Outgoing degree", metrics.outgoing_degree),
            _build_metric_row("Total degree", metrics.total_degree),
        ],
    )


def _build_degree_metric_summary(degree_values: Sequence[int]) -> _DegreeMetricSummary:
    return _DegreeMetricSummary(
        avg=mean(degree_values),
        median=median(degree_values),
        min=min(degree_values),
        max=max(degree_values),
    )


def _build_zero_degree_metric_summary() -> _DegreeMetricSummary:
    zero_float = float(0)
    return _DegreeMetricSummary(avg=zero_float, median=zero_float, min=0, max=0)


def _build_metric_row(
    metric_name: str,
    metric_values: _DegreeMetricSummary,
) -> tuple[str, str, str, str, str]:
    return (
        metric_name,
        f"{metric_values.avg:.2f}",
        f"{metric_values.median:.2f}",
        str(metric_values.min),
        str(metric_values.max),
    )
