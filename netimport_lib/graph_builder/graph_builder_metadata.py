"""Metadata helpers for dependency graph nodes."""

from pathlib import Path

import networkx as nx

from netimport_lib.graph_builder.resolver_shared import NodeTypes


class DisplayFolders:
    """Display folder labels used by the graph visualizers and summaries."""

    standard_library = "Standard library"
    external_dependencies = "External dependencies"
    unresolved_imports = "Unresolved imports"
    other_dependencies = "Other dependencies"


def populate_node_metadata(graph: nx.DiGraph, project_root: str) -> None:
    """Populate derived metadata that downstream renderers rely on."""
    for node_id in graph.nodes():
        node_data = graph.nodes[node_id]
        node_type = str(node_data.get("type", ""))
        display_folder, is_root_folder = build_folder_metadata(
            str(node_id),
            node_type,
            project_root,
        )
        node_data["folder"] = display_folder
        node_data["is_root_folder"] = is_root_folder
        node_data["in_degree"] = graph.in_degree(node_id)
        node_data["out_degree"] = graph.out_degree(node_id)
        node_data["total_degree"] = graph.degree(node_id)


def build_folder_metadata(
    node_id: str,
    node_type: str,
    project_root: str,
) -> tuple[str, bool]:
    """Return the folder bucket and root flag for a graph node."""
    if node_type == NodeTypes.project_file:
        display_folder = get_display_folder_name(node_id, project_root)
        return display_folder, display_folder == project_root
    if node_type == NodeTypes.standard_library:
        return DisplayFolders.standard_library, False
    if node_type == NodeTypes.external_library:
        return DisplayFolders.external_dependencies, False
    if node_type.startswith("unresolved"):
        return DisplayFolders.unresolved_imports, False
    return DisplayFolders.other_dependencies, False


def get_display_folder_name(full_path: str, project_root: str) -> str:
    """Build the display folder path for a project file node."""
    full_path_obj = Path(full_path).resolve()
    project_root_obj = Path(project_root).resolve()
    try:
        relative_parent = full_path_obj.relative_to(project_root_obj).parent
    except ValueError:
        return str(full_path_obj.parent)
    if str(relative_parent) == ".":
        return str(project_root_obj)
    return str(project_root_obj / relative_parent)
