"""Dependency graph construction logic."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import networkx as nx

from netimport_lib.graph_builder.resolver_imports import (
    NodeInfo,
    normalize_path,
    resolve_import_string,
)


PROJECT_FILE_NODE_TYPE: Final[str] = "project_file"


@dataclass(frozen=True, slots=True)
class IgnoreConfigNode:
    """Filters that control which nodes are excluded from the graph."""

    nodes: set[str]
    stdlib: bool
    external_lib: bool


def _is_node_allowed(node: NodeInfo, ignore: IgnoreConfigNode) -> bool:
    if ignore.stdlib and node.type == "std_lib":
        return False
    if ignore.external_lib and node.type == "external_lib":
        return False
    return node.id not in ignore.nodes


def build_dependency_graph(
    file_imports_map: Mapping[str, Sequence[str]],
    project_root: str,
    ignore: IgnoreConfigNode,
) -> nx.DiGraph:
    """Build a dependency graph from source files and their imports."""
    graph = nx.DiGraph()
    normalized_project_root = normalize_path(project_root)
    normalized_file_imports_map = _normalize_file_imports_map(file_imports_map)
    project_files_normalized = set(normalized_file_imports_map)

    _add_project_file_nodes(graph, project_files_normalized, ignore)
    _add_import_edges(
        graph,
        normalized_file_imports_map,
        normalized_project_root,
        project_files_normalized,
        ignore,
    )
    _populate_node_metadata(graph, normalized_project_root)

    return graph


def _normalize_file_imports_map(
    file_imports_map: Mapping[str, Sequence[str]],
) -> dict[str, tuple[str, ...]]:
    return {
        normalize_path(file_path): tuple(import_strings)
        for file_path, import_strings in file_imports_map.items()
    }


def _add_project_file_nodes(
    graph: nx.DiGraph,
    project_files_normalized: set[str],
    ignore: IgnoreConfigNode,
) -> None:
    for source_file_path in project_files_normalized:
        label = Path(source_file_path).name
        if label in ignore.nodes:
            continue

        graph.add_node(source_file_path, type=PROJECT_FILE_NODE_TYPE, label=label)


def _add_import_edges(
    graph: nx.DiGraph,
    file_imports_map: Mapping[str, Sequence[str]],
    project_root: str,
    project_files_normalized: set[str],
    ignore: IgnoreConfigNode,
) -> None:
    for source_node_id, import_strings in file_imports_map.items():
        if source_node_id not in graph:
            continue

        for import_str in import_strings:
            if not import_str:
                continue

            target_node = resolve_import_string(
                import_str,
                source_node_id,
                project_root,
                project_files_normalized,
            )
            _add_target_node_and_edge(graph, source_node_id, target_node, import_str, ignore)


def _build_node_label(target_node: NodeInfo) -> str:
    if target_node.type == PROJECT_FILE_NODE_TYPE:
        return Path(target_node.id).name

    return target_node.id


def _add_target_node_and_edge(
    graph: nx.DiGraph,
    source_node_id: str,
    target_node: NodeInfo,
    import_str: str,
    ignore: IgnoreConfigNode,
) -> None:
    if not _is_node_allowed(target_node, ignore):
        return

    if target_node.id not in graph:
        label = _build_node_label(target_node)
        if label in ignore.nodes:
            return

        graph.add_node(target_node.id, type=target_node.type, label=label)

    if not graph.has_edge(source_node_id, target_node.id):
        graph.add_edge(source_node_id, target_node.id, import_raw_string=import_str)


def _populate_node_metadata(graph: nx.DiGraph, project_root: str) -> None:
    for node_id in graph.nodes():
        display_folder = _get_display_folder_name(str(node_id), project_root)
        graph.nodes[node_id]["folder"] = display_folder
        graph.nodes[node_id]["is_root_folder"] = display_folder == project_root
        graph.nodes[node_id]["in_degree"] = graph.in_degree(node_id)
        graph.nodes[node_id]["out_degree"] = graph.out_degree(node_id)
        graph.nodes[node_id]["total_degree"] = graph.degree(node_id)


def _get_display_folder_name(full_path: str, project_root: str) -> str:
    full_path_obj = Path(full_path).resolve()
    project_root_obj = Path(project_root).resolve()

    try:
        relative_parent = full_path_obj.relative_to(project_root_obj).parent
    except ValueError:
        return str(full_path_obj.parent)

    if str(relative_parent) == ".":
        return str(project_root_obj)

    return str(project_root_obj / relative_parent)
