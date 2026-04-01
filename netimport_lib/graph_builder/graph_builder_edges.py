"""Edge helpers for dependency graph construction."""

from collections.abc import Mapping, Sequence

import networkx as nx

from netimport_lib.graph_builder.graph_builder_nodes import (
    ImportResolutionContext,
    _NodeFilterConfig,
    add_target_node_and_edge,
)
from netimport_lib.graph_builder.resolver.imports import resolve_import_string
from netimport_lib.graph_builder.resolver.paths import normalize_path


def normalize_file_imports_map(
    file_imports_map: Mapping[str, Sequence[str]],
) -> dict[str, tuple[str, ...]]:
    """Return a normalized mapping of source files to deterministic imports."""
    return {
        normalize_path(file_path): tuple(sorted(import_strings))
        for file_path, import_strings in sorted(file_imports_map.items())
    }


def add_import_edges(
    graph: nx.DiGraph,
    file_imports_map: Mapping[str, Sequence[str]],
    resolution_context: ImportResolutionContext,
    node_filter: _NodeFilterConfig,
) -> None:
    """Resolve imports for each project file and add matching graph edges."""
    for source_node_id, import_strings in sorted(file_imports_map.items()):
        if source_node_id not in graph:
            continue
        _add_import_edges_for_source(
            graph,
            source_node_id,
            import_strings,
            resolution_context,
            node_filter,
        )


def _add_import_edges_for_source(
    graph: nx.DiGraph,
    source_node_id: str,
    import_strings: Sequence[str],
    resolution_context: ImportResolutionContext,
    node_filter: _NodeFilterConfig,
) -> None:
    for import_str in sorted(import_strings):
        if not import_str:
            continue
        target_node = resolve_import_string(
            import_str,
            source_node_id,
            resolution_context.project_root,
            resolution_context.project_files_normalized,
        )
        add_target_node_and_edge(
            graph,
            source_node_id,
            target_node,
            import_str,
            node_filter,
        )
