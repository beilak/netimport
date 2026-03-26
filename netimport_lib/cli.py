from pathlib import Path

import click
import networkx as nx

from netimport_lib.config_loader import NetImportConfigMap, load_config
from netimport_lib.graph_builder.graph_builder import (
    IgnoreConfigNode,
    build_dependency_graph,
)
from netimport_lib.imports_reader import get_imported_modules_as_strings
from netimport_lib.project_file_reader import find_python_files
from netimport_lib.summary_builder import print_summary
from netimport_lib.visualizer import GRAPH_VISUALIZERS


IGNORE_NODES: set = set()


@click.command()
@click.argument("project_path", type=str)
@click.option(
    "--layout",
    type=click.Choice(
        [
            "planar_layout",
            "spring",
            "kamada_kawai",
            "circular",
            "spectral",
            "shell",
            "dot",
            "neato",
            "fdp",
            "sfdp",
        ],
        case_sensitive=False,
    ),
    default="planar_layout",
    show_default=True,
)
@click.option(
    "--show-graph",
    type=click.Choice(
        ["bokeh", "mpl"],
        case_sensitive=False,
    ),
    default="bokeh",
    show_default=True,
)
@click.option(
    "--no-show-graph",
    is_flag=True,
    default=False,
    help="Disable graph visualization even if a graph backend is configured.",
)
@click.option(
    "--show-console-summary",
    is_flag=True,
    default=False,
    help="Show a summary of the project dependencies in the console.",
)
@click.option(
    "--ignored-dir",
    "ignored_dirs",
    multiple=True,
    help="Directory name to ignore. Can be passed multiple times.",
)
@click.option(
    "--ignored-file",
    "ignored_files",
    multiple=True,
    help="File name to ignore. Can be passed multiple times.",
)
@click.option(
    "--ignored-node",
    "ignored_nodes",
    multiple=True,
    help="Graph node label or id to ignore. Can be passed multiple times.",
)
@click.option(
    "--ignore-stdlib",
    "ignore_stdlib",
    flag_value=True,
    default=None,
    help="Exclude standard library modules from the graph.",
)
@click.option(
    "--include-stdlib",
    "ignore_stdlib",
    flag_value=False,
    help="Force standard library modules to be included in the graph.",
)
@click.option(
    "--ignore-external-lib",
    "ignore_external_lib",
    flag_value=True,
    default=None,
    help="Exclude external libraries from the graph.",
)
@click.option(
    "--include-external-lib",
    "ignore_external_lib",
    flag_value=False,
    help="Force external libraries to be included in the graph.",
)
def main(
    project_path: str,
    layout: str,
    show_graph: str | None = "bokeh",
    no_show_graph: bool = False,
    show_console_summary: bool = False,
    ignored_dirs: tuple[str, ...] = (),
    ignored_files: tuple[str, ...] = (),
    ignored_nodes: tuple[str, ...] = (),
    ignore_stdlib: bool | None = None,
    ignore_external_lib: bool | None = None,
) -> None:
    project_root = str(Path(project_path).resolve())
    loaded_config = _merge_cli_config(
        load_config(project_root),
        ignored_dirs=ignored_dirs,
        ignored_files=ignored_files,
        ignored_nodes=ignored_nodes,
        ignore_stdlib=ignore_stdlib,
        ignore_external_lib=ignore_external_lib,
    )

    file_imports_map: dict[str, list[str]] = {}

    py_files = find_python_files(
        project_root,
        ignored_dirs=loaded_config["ignored_dirs"],
        ignored_files=loaded_config["ignored_files"],
    )

    for f_path in sorted(py_files):
        file_imports_map[f_path] = get_imported_modules_as_strings(f_path)

    dependency_graph = build_dependency_graph(
        file_imports_map,
        project_root,
        ignore=IgnoreConfigNode(
            nodes=loaded_config["ignored_nodes"],
            stdlib=loaded_config["ignore_stdlib"],
            external_lib=loaded_config["ignore_external_lib"],
        ),
    )

    # Remove all isolated __init__.py
    isolated_nodes = list(nx.isolates(dependency_graph))
    nodes_to_remove = []
    for node_id in isolated_nodes:
        node_attributes = dependency_graph.nodes[node_id]
        if node_attributes.get("label") == "__init__.py":
            nodes_to_remove.append(node_id)
    if nodes_to_remove:
        dependency_graph.remove_nodes_from(nodes_to_remove)

    if not no_show_graph and show_graph and (visualizer := GRAPH_VISUALIZERS.get(show_graph)):
        visualizer(dependency_graph, layout)

    if show_console_summary:
        print_summary(dependency_graph)


def _merge_cli_config(
    loaded_config: NetImportConfigMap,
    *,
    ignored_dirs: tuple[str, ...],
    ignored_files: tuple[str, ...],
    ignored_nodes: tuple[str, ...],
    ignore_stdlib: bool | None,
    ignore_external_lib: bool | None,
) -> NetImportConfigMap:
    merged_config: NetImportConfigMap = {
        "ignored_nodes": set(loaded_config["ignored_nodes"]),
        "ignored_dirs": set(loaded_config["ignored_dirs"]),
        "ignored_files": set(loaded_config["ignored_files"]),
        "ignore_stdlib": loaded_config["ignore_stdlib"],
        "ignore_external_lib": loaded_config["ignore_external_lib"],
    }

    merged_config["ignored_dirs"].update(ignored_dirs)
    merged_config["ignored_files"].update(ignored_files)
    merged_config["ignored_nodes"].update(ignored_nodes)

    if ignore_stdlib is not None:
        merged_config["ignore_stdlib"] = ignore_stdlib
    if ignore_external_lib is not None:
        merged_config["ignore_external_lib"] = ignore_external_lib

    return merged_config
