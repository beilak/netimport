"""Node helpers for dependency graph construction."""

from dataclasses import dataclass
from pathlib import Path

import networkx as nx

from netimport_lib.graph_builder.resolver_shared import NodeInfo, NodeTypes


@dataclass(frozen=True, slots=True)
class ImportResolutionContext:
    """Context needed to resolve imports against the current project."""

    project_root: str
    project_files_normalized: set[str]


@dataclass(frozen=True, slots=True)
class _NodeFilterConfig:
    ignore_nodes: set[str]
    ignore_stdlib: bool
    ignore_external: bool


def _is_node_allowed(node: NodeInfo, node_filter: _NodeFilterConfig) -> bool:
    if node_filter.ignore_stdlib and node.type == NodeTypes.standard_library:
        return False
    if node_filter.ignore_external and node.type == NodeTypes.external_library:
        return False
    return node.id not in node_filter.ignore_nodes


def add_project_file_nodes(
    graph: nx.DiGraph,
    project_files_normalized: set[str],
    ignore_nodes: set[str],
) -> None:
    """Add the project's own files as the initial graph nodes."""
    for source_file_path in sorted(project_files_normalized):
        label = Path(source_file_path).name
        if label in ignore_nodes:
            continue
        graph.add_node(source_file_path, type=NodeTypes.project_file, label=label)


def build_node_label(target_node: NodeInfo) -> str:
    """Build the user-facing node label for a resolved dependency."""
    if target_node.type == NodeTypes.project_file:
        return Path(target_node.id).name
    return target_node.id


def add_target_node_and_edge(
    graph: nx.DiGraph,
    source_node_id: str,
    target_node: NodeInfo,
    import_str: str,
    node_filter: _NodeFilterConfig,
) -> None:
    """Add a resolved target node and connect it to the source file."""
    if not _is_node_allowed(target_node, node_filter):
        return
    if target_node.id not in graph:
        label = build_node_label(target_node)
        if label in node_filter.ignore_nodes:
            return
        graph.add_node(target_node.id, type=target_node.type, label=label)
    if not graph.has_edge(source_node_id, target_node.id):
        graph.add_edge(source_node_id, target_node.id, import_raw_string=import_str)
