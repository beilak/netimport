import os
import click
import networkx as nx

from netimport_lib.graph_builder.graph_builder import build_dependency_graph
from netimport_lib.graph_draw import draw_graph
from netimport_lib.imports_reader import get_imported_modules_as_strings
from netimport_lib.project_file_reader import find_python_files

IGNORE_NODES: set = set()
# {
    #"typing",
    #"__init__.py",
    #"dataclasses",
    #"decimal",
# }




@click.command()
@click.argument(
    "project_path",
    type=str,
    # type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True)
)
@click.option(
    "--output-graph", "-o",
    type=click.Path(file_okay=True, dir_okay=False, writable=True, resolve_path=True),
    help="Save PNG file",
    default=None
)
@click.option(
    "--show-graph/--no-show-graph", "-s/-ns",
    default=False,
    help="Show(Matplotlib)"
)
@click.option(
    "--layout",
    type=click.Choice(['planar_layout', 'spring', 'kamada_kawai', 'circular', 'spectral', 'shell', 'dot', 'neato', 'fdp', 'sfdp'], case_sensitive=False),
    default='planar_layout',
    show_default=True,
)
@click.option(
    "--ignored-dirs",
    type=str,
    default=None,
    callback=lambda ctx, param, value: [d.strip() for d in value.split(',')] if value else None
)
@click.option(
    "--ignored-files",
    type=str,
    default=None,
    callback=lambda ctx, param, value: [f.strip() for f in value.split(',')] if value else None
)
@click.option(
    "--show-console-summary", "-cs",
    is_flag=True,
)
# @click.option(
#     "--export-dot",
#     type=click.Path(file_okay=True, dir_okay=False, writable=True, resolve_path=True),
#     help="Export DOT for Graphviz.",
#     default=None
# )
def main(
    project_path: str,
    output_graph: str | None,
    show_graph: bool,
    layout: str,
    config: str | None = None,
    ignored_dirs: list[str] | None = None,
    ignored_files: list[str] | None = None,
    show_console_summary: bool | None = False,
    export_dot: str | None = None,
    export_mermaid: str | None = None,
    include_type_checking: bool | None = False,
):

    # ToDo Not ready. Not all params used

    ignored_dirs_tmp = {".venv"}

    file_imports_map: dict[str, list[str]] = {}

    py_files = find_python_files(
        project_path, ignored_dirs=ignored_dirs_tmp, ignored_files=set()
    )
    for f_path in sorted(py_files):
        print(os.path.relpath(f_path, project_path))


    print("IMPORTS MAPS")

    for f_path in sorted(py_files):
        # k = f"{project_path}/{os.path.relpath(f_path, project_path)}"
        file_imports_map[f_path] = get_imported_modules_as_strings(f_path)

        print("----" * 10)
        print(f_path)
        print("Imports")
        print(get_imported_modules_as_strings(f_path))

    dependency_graph = build_dependency_graph(
        file_imports_map,
        project_path,
        IGNORE_NODES,
    )

    # Remove all isolated __init__.py
    isolated_nodes = list(nx.isolates(dependency_graph))
    print(f"No depends nodes {isolated_nodes}")
    nodes_to_remove = []
    for node_id in isolated_nodes:
        node_attributes = dependency_graph.nodes[node_id]
        if node_attributes.get("label") == "__init__.py":
            nodes_to_remove.append(node_id)
    if nodes_to_remove:
        dependency_graph.remove_nodes_from(nodes_to_remove)


    print(dependency_graph.nodes)
    draw_graph(dependency_graph)
