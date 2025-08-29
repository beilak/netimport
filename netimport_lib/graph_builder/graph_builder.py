import os
from pathlib import Path
from typing import TypedDict

import networkx as nx

from netimport_lib.graph_builder.resolver_imports import (
    NodeInfo,
    normalize_path,
    resolve_import_string,
)


class IgnoreConfigNode(TypedDict):
    nodes: set[str]
    stdlib: bool
    external_lib: bool


def is_node_allow_to_add(node: NodeInfo, ignore: IgnoreConfigNode) -> bool:
    if ignore["stdlib"] and node.type == "std_lib":
        return False
    if ignore["external_lib"] and node.type == "external_lib":
        return False
    if node.id in ignore["nodes"]:
        return False
    return True


def build_dependency_graph(
    file_imports_map: dict[str, list[str]],
    project_root: str,
    ignore: IgnoreConfigNode,
) -> nx.DiGraph:
    graph = nx.DiGraph()

    project_files_normalized: set[str] = set()
    for file_path_key in file_imports_map:
        project_files_normalized.add(normalize_path(file_path_key))

    for source_file_rel_path in project_files_normalized:
        label = Path(source_file_rel_path).name
        if label in ignore["nodes"]:
            continue
        graph.add_node(source_file_rel_path, type="project_file", label=label)

    for source_file_rel_path, import_strings in file_imports_map.items():
        source_node_id = source_file_rel_path

        if source_node_id not in graph:
            continue

        for import_str in import_strings:
            if not import_str:
                continue

            target_node = resolve_import_string(
                import_str,
                source_file_rel_path,
                project_root,
                project_files_normalized,
            )
            if target_node.id is None:
                continue

            if not is_node_allow_to_add(target_node, ignore):
                continue

            if target_node.id not in graph:
                label = (
                    Path(target_node.id).name
                    if target_node.type == "project_file"
                    else target_node.id
                )
                if label in ignore["nodes"]:
                    continue
                graph.add_node(target_node.id, type=target_node.type, label=label)

            if not graph.has_edge(source_node_id, target_node.id):
                graph.add_edge(
                    source_node_id, target_node.id, import_raw_string=import_str
                )

    for node_id in graph.nodes():
        display_folder = get_display_folder_name(node_id, project_root)
        graph.nodes[node_id]["folder"] = display_folder
        graph.nodes[node_id]["is_root_folder"] = display_folder == project_root

    return graph


def get_display_folder_name(full_path: str, project_root_name: str) -> str:
    try:
        full_path_obj = Path(full_path)
        path_parts = full_path_obj.parts
        if project_root_name in path_parts:
            root_index = path_parts.index(project_root_name)
            if root_index < len(path_parts) - 1:
                return str(Path(*path_parts[root_index:-1]))

        return str(full_path_obj.parent)

    except (ValueError, IndexError):
        return str(Path(full_path).parent)
