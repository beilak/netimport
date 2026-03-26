"""CLI entrypoint for NetImport."""

from dataclasses import dataclass
from pathlib import Path

import click
import networkx as nx

from netimport_lib.config_loader import (
    NetImportConfigMap,
    load_config,
    load_explicit_config,
    merge_config,
)
from netimport_lib.graph_builder.graph_builder import IgnoreConfigNode, build_dependency_graph
from netimport_lib.imports_reader import get_imported_modules_as_strings
from netimport_lib.project_file_reader import find_python_files
from netimport_lib.summary_builder import print_json_summary, print_summary
from netimport_lib.visualizer import (
    DEFAULT_VISUALIZER,
    GRAPH_LAYOUT_CHOICES,
    GRAPH_VISUALIZER_NAMES,
    GRAPH_VISUALIZERS,
    GraphVisualizer,
)


@dataclass(frozen=True, slots=True)
class _CliOverrides:
    ignored_dirs: tuple[str, ...]
    ignored_files: tuple[str, ...]
    ignored_nodes: tuple[str, ...]
    ignore_stdlib: bool | None
    ignore_external_lib: bool | None


@click.command()
@click.argument("project_path", type=str)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Load an explicit TOML config file and apply it after project config.",
)
@click.option(
    "--layout",
    type=click.Choice(GRAPH_LAYOUT_CHOICES, case_sensitive=False),
    default=None,
    help="Layout for the selected graph backend. If omitted, the backend default is used.",
)
@click.option(
    "--show-graph",
    type=click.Choice(GRAPH_VISUALIZER_NAMES, case_sensitive=False),
    default=DEFAULT_VISUALIZER,
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
    "--summary-format",
    type=click.Choice(("text", "json"), case_sensitive=False),
    default="text",
    show_default=True,
    help="Output format for --show-console-summary.",
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
def main(  # noqa: PLR0913
    project_path: str,
    config_path: Path | None = None,
    layout: str | None = None,
    show_graph: str = DEFAULT_VISUALIZER,
    no_show_graph: bool = False,
    show_console_summary: bool = False,
    summary_format: str = "text",
    ignored_dirs: tuple[str, ...] = (),
    ignored_files: tuple[str, ...] = (),
    ignored_nodes: tuple[str, ...] = (),
    ignore_stdlib: bool | None = None,
    ignore_external_lib: bool | None = None,
) -> None:
    """Analyze a Python project and optionally visualize its dependency graph."""
    project_root = str(Path(project_path).resolve())
    loaded_config = _load_cli_config(
        project_root=project_root,
        config_path=config_path,
        cli_overrides=_CliOverrides(
            ignored_dirs=ignored_dirs,
            ignored_files=ignored_files,
            ignored_nodes=ignored_nodes,
            ignore_stdlib=ignore_stdlib,
            ignore_external_lib=ignore_external_lib,
        ),
    )

    selected_visualizer: GraphVisualizer | None = None
    selected_layout: str | None = None
    if not no_show_graph:
        selected_visualizer = _get_visualizer(show_graph)
        selected_layout = _resolve_visualizer_layout(selected_visualizer, layout)

    py_files = find_python_files(
        project_root,
        ignored_dirs=loaded_config["ignored_dirs"],
        ignored_files=loaded_config["ignored_files"],
    )
    file_imports_map = {
        file_path: get_imported_modules_as_strings(file_path) for file_path in sorted(py_files)
    }

    dependency_graph = build_dependency_graph(
        file_imports_map,
        project_root,
        ignore=IgnoreConfigNode(
            nodes=loaded_config["ignored_nodes"],
            stdlib=loaded_config["ignore_stdlib"],
            external_lib=loaded_config["ignore_external_lib"],
        ),
    )
    _remove_isolated_init_nodes(dependency_graph)

    if selected_visualizer is not None and selected_layout is not None:
        selected_visualizer.render(dependency_graph, selected_layout)

    if show_console_summary:
        if summary_format == "json":
            print_json_summary(dependency_graph)
        else:
            print_summary(dependency_graph)


def _remove_isolated_init_nodes(dependency_graph: nx.DiGraph) -> None:
    isolated_nodes = list(nx.isolates(dependency_graph))
    nodes_to_remove = [
        node_id
        for node_id in isolated_nodes
        if str(dependency_graph.nodes[node_id].get("label")) == "__init__.py"
    ]
    if nodes_to_remove:
        dependency_graph.remove_nodes_from(nodes_to_remove)


def _load_cli_config(
    project_root: str,
    config_path: Path | None,
    cli_overrides: _CliOverrides,
) -> NetImportConfigMap:
    try:
        loaded_config = load_config(project_root)
        if config_path is not None:
            loaded_config = merge_config(loaded_config, load_explicit_config(config_path))
    except (OSError, TypeError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc

    return _merge_cli_config(loaded_config, cli_overrides)


def _merge_cli_config(
    loaded_config: NetImportConfigMap,
    cli_overrides: _CliOverrides,
) -> NetImportConfigMap:
    merged_config: NetImportConfigMap = {
        "ignored_nodes": set(loaded_config["ignored_nodes"]),
        "ignored_dirs": set(loaded_config["ignored_dirs"]),
        "ignored_files": set(loaded_config["ignored_files"]),
        "ignore_stdlib": loaded_config["ignore_stdlib"],
        "ignore_external_lib": loaded_config["ignore_external_lib"],
    }

    merged_config["ignored_dirs"].update(cli_overrides.ignored_dirs)
    merged_config["ignored_files"].update(cli_overrides.ignored_files)
    merged_config["ignored_nodes"].update(cli_overrides.ignored_nodes)

    if cli_overrides.ignore_stdlib is not None:
        merged_config["ignore_stdlib"] = cli_overrides.ignore_stdlib
    if cli_overrides.ignore_external_lib is not None:
        merged_config["ignore_external_lib"] = cli_overrides.ignore_external_lib

    return merged_config


def _get_visualizer(name: str) -> GraphVisualizer:
    try:
        return GRAPH_VISUALIZERS[name]
    except KeyError as exc:
        raise click.ClickException(f"Graph backend '{name}' is not available.") from exc


def _resolve_visualizer_layout(visualizer: GraphVisualizer, layout: str | None) -> str:
    if layout is None:
        return visualizer.default_layout

    if layout in visualizer.supported_layouts:
        return layout

    supported_layouts = ", ".join(visualizer.supported_layouts)
    raise click.BadParameter(
        (
            f"Layout '{layout}' is not supported by the '{visualizer.name}' backend. "
            f"Supported layouts: {supported_layouts}."
        ),
        param_hint="--layout",
    )


if __name__ == "__main__":
    main()
