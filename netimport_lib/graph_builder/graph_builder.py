"""Dependency graph construction logic."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import networkx as nx

from netimport_lib.graph_builder.graph_builder_edges import (
    add_import_edges,
    normalize_file_imports_map,
)
from netimport_lib.graph_builder.graph_builder_metadata import populate_node_metadata
from netimport_lib.graph_builder.graph_builder_nodes import (
    ImportResolutionContext,
    _NodeFilterConfig,
    add_project_file_nodes,
)
from netimport_lib.graph_builder.resolver.paths import normalize_path


@dataclass(frozen=True, slots=True)
class IgnoreConfigNode:
    """Filters that control which nodes are excluded from the graph."""

    nodes: set[str]
    stdlib: bool
    external_lib: bool


def build_dependency_graph(
    file_imports_map: Mapping[str, Sequence[str]],
    project_root: str,
    ignore: IgnoreConfigNode,
) -> nx.DiGraph:
    """Build a dependency graph from source files and their imports."""
    graph = nx.DiGraph()
    normalized_project_root = normalize_path(project_root)
    normalized_file_imports_map = normalize_file_imports_map(file_imports_map)
    project_files_normalized = set(normalized_file_imports_map)

    add_project_file_nodes(graph, project_files_normalized, ignore.nodes)
    add_import_edges(
        graph,
        normalized_file_imports_map,
        ImportResolutionContext(normalized_project_root, project_files_normalized),
        _NodeFilterConfig(
            ignore_nodes=ignore.nodes,
            ignore_stdlib=ignore.stdlib,
            ignore_external=ignore.external_lib,
        ),
    )
    populate_node_metadata(graph, normalized_project_root)

    return graph
