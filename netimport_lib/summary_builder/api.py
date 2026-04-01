"""Console summary formatting for dependency graphs."""

import json
from collections.abc import Sequence
from dataclasses import asdict

import click
import networkx as nx

from netimport_lib.policy.violations import Violation, build_violations_payload
from netimport_lib.summary_builder.constants import _SummaryText
from netimport_lib.summary_builder.lists import (
    _build_external_entries,
    _build_unresolved_entries,
    _build_unresolved_import_payload,
    _format_simple_node_list,
    _format_unresolved_entries,
    _format_violations,
)
from netimport_lib.summary_builder.metrics import (
    _build_overview_summary,
    _build_project_metrics_summary,
    _format_overview,
    _format_project_metrics,
)
from netimport_lib.summary_builder.project_nodes import _build_project_entries
from netimport_lib.summary_builder.rankings import (
    _build_ranked_project_files,
    _format_project_ranking,
)
from netimport_lib.summary_builder.tables import _build_section


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

    lines = [*_SummaryText.summary_intro_lines, ""]
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
    return {
        "schema_version": 1,
        "overview": asdict(_build_overview_summary(graph)),
        "project_metrics": asdict(_build_project_metrics_summary(project_entries)),
        "most_coupled_project_files": _build_ranked_project_files(
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
        "least_coupled_project_files": _build_ranked_project_files(
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
        "most_depended_on_project_files": _build_ranked_project_files(
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
        "most_dependent_project_files": _build_ranked_project_files(
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
        "external_dependencies": [entry.display_name for entry in external_entries],
        "unresolved_imports": _build_unresolved_import_payload(unresolved_entries),
        "violations": build_violations_payload(list(violations)),
    }


def format_summary_json(graph: nx.DiGraph, violations: Sequence[Violation] = ()) -> str:
    """Serialize a deterministic JSON dependency summary for a graph."""
    return json.dumps(build_summary_payload(graph, violations), indent=2)
