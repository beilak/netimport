import click
import networkx as nx

from netimport_lib.config_loader import NetImportConfigMap, load_config
from netimport_lib.graph_builder.graph_builder import (
    IgnoreConfigNode,
    build_dependency_graph,
)
from netimport_lib.imports_reader import get_imported_modules_as_strings
from netimport_lib.project_file_reader import find_python_files
from netimport_lib.visualizer import GRAPH_VISUALIZERS


IGNORE_NODES: set = set()
# {
# "typing",
# "__init__.py",
# "dataclasses",
# "decimal",
# }


@click.command()
@click.argument(
    "project_path",
    type=str,
    # type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True)
)
# @click.option(
#     "--output-graph",
#     "-o",
#     type=click.Path(file_okay=True, dir_okay=False, writable=True, resolve_path=True),
#     help="Save PNG file",
#     default=None,
# )
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
    "--show-console-summary",
    "-cs",
    is_flag=True,
)
# @click.option(
#     "--export-dot",
#     type=click.Path(file_okay=True, dir_okay=False, writable=True, resolve_path=True),
#     help="Export DOT for Graphviz.",
#     default=None
# )

@click.option(
    "--show-graph",
    type=click.Choice(
        ["bokeh", "mpl"],
        case_sensitive=False,
    ),
    default="bokeh",
    show_default=True,
)
def main(
    project_path: str,
    # output_graph: str | None,
    layout: str,
    config: str | None = None,
    # ignored_dirs: set[str] | None = None,
    ignored_files: list[str] | None = None,
    show_console_summary: bool | None = False,
    export_dot: str | None = None,
    export_mermaid: str | None = None,
    include_type_checking: bool | None = False,
    show_graph: str | None = "bokeh",
) -> None:
    # TODO Not ready. Not all params used

    loaded_config: NetImportConfigMap = load_config(".")

    # ignore_stdlib: Final[bool] = loaded_config.get("ignore_stdlib", False)

    file_imports_map: dict[str, list[str]] = {}

    py_files = find_python_files(
        project_path,
        ignored_dirs=loaded_config["ignored_dirs"],
        ignored_files=set(),
    )
    # for f_path in sorted(py_files):
    #     print(os.path.relpath(f_path, project_path))

    # print("IMPORTS MAPS")

    for f_path in sorted(py_files):
        # k = f"{project_path}/{os.path.relpath(f_path, project_path)}"
        file_imports_map[f_path] = get_imported_modules_as_strings(f_path)

        # print("----" * 10)
        # print(f_path)
        # print("Imports")
        # print(get_imported_modules_as_strings(f_path))

    dependency_graph = build_dependency_graph(
        file_imports_map,
        project_path,
        ignore=IgnoreConfigNode(
            nodes=loaded_config["ignored_nodes"],
            stdlib=loaded_config["ignore_stdlib"],
            external_lib=loaded_config["ignore_external_lib"],
        ),
    )

    # Remove all isolated __init__.py
    isolated_nodes = list(nx.isolates(dependency_graph))
    # print(f"No depends nodes {isolated_nodes}")
    nodes_to_remove = []
    for node_id in isolated_nodes:
        node_attributes = dependency_graph.nodes[node_id]
        if node_attributes.get("label") == "__init__.py":
            nodes_to_remove.append(node_id)
    if nodes_to_remove:
        dependency_graph.remove_nodes_from(nodes_to_remove)

    # print(dependency_graph.nodes)
    # draw_plotly_graph(dependency_graph, layout)

    if show_graph and (visualizer := GRAPH_VISUALIZERS.get(show_graph)):
        visualizer(dependency_graph, layout)
