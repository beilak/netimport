"""CLI entrypoint for NetImport."""

import typing
from dataclasses import dataclass
from pathlib import Path

import click
import networkx as nx

from netimport_lib import (
    config_loader,
    imports_reader,
    project_file_reader,
    summary_builder,
    violations,
)
from netimport_lib.graph_builder import graph_builder
from netimport_lib.visualizer.registry import (
    DEFAULT_VISUALIZER,
    GRAPH_LAYOUT_CHOICES,
    GRAPH_VISUALIZER_NAMES,
    GRAPH_VISUALIZERS,
    GraphVisualizer,
)


NetImportConfigMap = config_loader.NetImportConfigMap
load_config = config_loader.load_config
load_explicit_config = config_loader.load_explicit_config
merge_config = config_loader.merge_config
AnalysisResult: typing.TypeAlias = tuple[nx.DiGraph, list[violations.Violation]]
IGNORED_NODES_KEY: typing.Final[config_loader.StringSetConfigKey] = config_loader.IGNORED_NODES_KEY
IGNORED_DIRS_KEY: typing.Final[config_loader.StringSetConfigKey] = config_loader.IGNORED_DIRS_KEY
IGNORED_FILES_KEY: typing.Final[config_loader.StringSetConfigKey] = config_loader.IGNORED_FILES_KEY
IGNORE_STDLIB_KEY: typing.Final[config_loader.BoolConfigKey] = config_loader.IGNORE_STDLIB_KEY
IGNORE_EXTERNAL_LIB_KEY: typing.Final[config_loader.BoolConfigKey] = (
    config_loader.IGNORE_EXTERNAL_LIB_KEY
)
FAIL_ON_UNRESOLVED_IMPORTS_KEY: typing.Final[config_loader.BoolConfigKey] = (
    config_loader.FAIL_ON_UNRESOLVED_IMPORTS_KEY
)
FORBIDDEN_EXTERNAL_LIBS_KEY: typing.Final[config_loader.StringSetConfigKey] = (
    config_loader.FORBIDDEN_EXTERNAL_LIBS_KEY
)


@dataclass(frozen=True, slots=True)
class _CliOverrides:
    ignored_dirs: tuple[str, ...]
    ignored_files: tuple[str, ...]
    ignored_nodes: tuple[str, ...]
    ignore_stdlib: bool | None
    ignore_external_lib: bool | None


@dataclass(frozen=True, slots=True)
class _CliCommand:
    project_root: str
    config_path: Path | None
    layout: str | None
    show_graph: str
    no_show_graph: bool
    show_console_summary: bool
    summary_format: str
    fail_on_violation: bool
    cli_overrides: _CliOverrides


class _CliSupport:
    """Private namespace for command execution helpers."""

    @classmethod
    def load_cli_config(cls, cli_command: _CliCommand) -> NetImportConfigMap:
        try:
            loaded_config = (
                load_config(cli_command.project_root)
                if cli_command.config_path is None
                else merge_config(
                    load_config(cli_command.project_root),
                    load_explicit_config(cli_command.config_path),
                )
            )
        except (OSError, TypeError, ValueError) as exc:
            raise click.ClickException(str(exc)) from exc
        return cls.merge_cli_config(loaded_config, cli_command.cli_overrides)

    @classmethod
    def merge_cli_config(
        cls,
        loaded_config: NetImportConfigMap,
        cli_overrides: _CliOverrides,
    ) -> NetImportConfigMap:
        merged_config = NetImportConfigMap(
            ignored_nodes=set(loaded_config[IGNORED_NODES_KEY]),
            ignored_dirs=set(loaded_config[IGNORED_DIRS_KEY]),
            ignored_files=set(loaded_config[IGNORED_FILES_KEY]),
            ignore_stdlib=loaded_config[IGNORE_STDLIB_KEY],
            ignore_external_lib=loaded_config[IGNORE_EXTERNAL_LIB_KEY],
            fail_on_unresolved_imports=loaded_config[FAIL_ON_UNRESOLVED_IMPORTS_KEY],
            forbidden_external_libs=set(loaded_config[FORBIDDEN_EXTERNAL_LIBS_KEY]),
        )

        merged_config[IGNORED_DIRS_KEY].update(cli_overrides.ignored_dirs)
        merged_config[IGNORED_FILES_KEY].update(cli_overrides.ignored_files)
        merged_config[IGNORED_NODES_KEY].update(cli_overrides.ignored_nodes)

        if cli_overrides.ignore_stdlib is not None:
            merged_config[IGNORE_STDLIB_KEY] = cli_overrides.ignore_stdlib
        if cli_overrides.ignore_external_lib is not None:
            merged_config[IGNORE_EXTERNAL_LIB_KEY] = cli_overrides.ignore_external_lib
        return merged_config

    @classmethod
    def get_visualizer_selection(
        cls,
        cli_command: _CliCommand,
    ) -> tuple[GraphVisualizer | None, str | None]:
        if cli_command.no_show_graph:
            return None, None
        selected_visualizer = cls.get_visualizer(cli_command.show_graph)
        return selected_visualizer, cls.resolve_visualizer_layout(
            selected_visualizer,
            cli_command.layout,
        )

    @classmethod
    def get_visualizer(cls, name: str) -> GraphVisualizer:
        try:
            return GRAPH_VISUALIZERS[name]
        except KeyError as exc:
            raise click.ClickException(f"Graph backend '{name}' is not available.") from exc

    @classmethod
    def resolve_visualizer_layout(
        cls,
        visualizer: GraphVisualizer,
        layout: str | None,
    ) -> str:
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

    @classmethod
    def run_analysis(
        cls,
        cli_command: _CliCommand,
    ) -> AnalysisResult:
        loaded_config = cls.load_cli_config(cli_command)
        dependency_graph = graph_builder.build_dependency_graph(
            {
                file_path: imports_reader.get_imported_modules_as_strings(file_path)
                for file_path in sorted(
                    project_file_reader.find_python_files(
                        cli_command.project_root,
                        ignored_dirs=loaded_config[IGNORED_DIRS_KEY],
                        ignored_files=loaded_config[IGNORED_FILES_KEY],
                    )
                )
            },
            cli_command.project_root,
            ignore=graph_builder.IgnoreConfigNode(
                nodes=loaded_config[IGNORED_NODES_KEY],
                stdlib=loaded_config[IGNORE_STDLIB_KEY],
                external_lib=loaded_config[IGNORE_EXTERNAL_LIB_KEY],
            ),
        )
        _remove_isolated_init_nodes(dependency_graph)
        return dependency_graph, violations.build_violations(
            dependency_graph,
            fail_on_unresolved_imports=loaded_config[FAIL_ON_UNRESOLVED_IMPORTS_KEY],
            forbidden_external_libs=loaded_config[FORBIDDEN_EXTERNAL_LIBS_KEY],
        )

    @classmethod
    def render_graph(
        cls,
        selected_visualizer: GraphVisualizer,
        dependency_graph: nx.DiGraph,
        selected_layout: str,
    ) -> None:
        try:
            render_message = selected_visualizer.render(dependency_graph, selected_layout)
        except Exception as exc:
            raise click.ClickException(
                f"Failed to render graph with '{selected_visualizer.name}': {exc}"
            ) from exc
        if render_message:
            click.echo(render_message)


def _with_command_options(
    callback: typing.Callable[..., None],
) -> typing.Callable[..., None]:
    decorators = (
        click.argument("project_path", type=str),
        click.option(
            "--config",
            "config_path",
            type=click.Path(exists=True, dir_okay=False, path_type=Path),
            default=None,
            help="Load an explicit TOML config file and apply it after project config.",
        ),
        click.option(
            "--layout",
            type=click.Choice(GRAPH_LAYOUT_CHOICES, case_sensitive=False),
            default=None,
            help="Layout for the selected graph backend. If omitted, the backend default is used.",
        ),
        click.option(
            "--show-graph",
            type=click.Choice(GRAPH_VISUALIZER_NAMES, case_sensitive=False),
            default=DEFAULT_VISUALIZER,
            show_default=True,
        ),
        click.option(
            "--no-show-graph",
            is_flag=True,
            default=False,
            help="Disable graph visualization even if a graph backend is configured.",
        ),
        click.option(
            "--show-console-summary",
            is_flag=True,
            default=False,
            help="Show a summary of the project dependencies in the console.",
        ),
        click.option(
            "--summary-format",
            type=click.Choice(("text", "json"), case_sensitive=False),
            default="text",
            show_default=True,
            help="Output format for --show-console-summary.",
        ),
        click.option(
            "--fail-on-violation",
            is_flag=True,
            default=False,
            help="Exit with code 1 when configured policy violations are found.",
        ),
        click.option(
            "--ignored-dir",
            "ignored_dirs",
            multiple=True,
            help="Directory name to ignore. Can be passed multiple times.",
        ),
        click.option(
            "--ignored-file",
            "ignored_files",
            multiple=True,
            help="File name to ignore. Can be passed multiple times.",
        ),
        click.option(
            "--ignored-node",
            "ignored_nodes",
            multiple=True,
            help="Graph node label or id to ignore. Can be passed multiple times.",
        ),
        click.option(
            "--ignore-stdlib",
            "ignore_stdlib",
            flag_value=True,
            default=None,
            help="Exclude standard library modules from the graph.",
        ),
        click.option(
            "--include-stdlib",
            "ignore_stdlib",
            flag_value=False,
            help="Force standard library modules to be included in the graph.",
        ),
        click.option(
            "--ignore-external-lib",
            "ignore_external_lib",
            flag_value=True,
            default=None,
            help="Exclude external libraries from the graph.",
        ),
        click.option(
            "--include-external-lib",
            "ignore_external_lib",
            flag_value=False,
            help="Force external libraries to be included in the graph.",
        ),
    )
    decorated_callback = callback
    for decorator in reversed(decorators):
        decorated_callback = decorator(decorated_callback)
    return decorated_callback


def _build_cli_command(command_options: dict[str, object]) -> _CliCommand:
    return _CliCommand(
        project_root=str(Path(typing.cast("str", command_options["project_path"])).resolve()),
        config_path=typing.cast("Path | None", command_options["config_path"]),
        layout=typing.cast("str | None", command_options["layout"]),
        show_graph=typing.cast("str", command_options["show_graph"]),
        no_show_graph=typing.cast("bool", command_options["no_show_graph"]),
        show_console_summary=typing.cast("bool", command_options["show_console_summary"]),
        summary_format=typing.cast("str", command_options["summary_format"]),
        fail_on_violation=typing.cast("bool", command_options["fail_on_violation"]),
        cli_overrides=_CliOverrides(
            ignored_dirs=typing.cast("tuple[str, ...]", command_options["ignored_dirs"]),
            ignored_files=typing.cast("tuple[str, ...]", command_options["ignored_files"]),
            ignored_nodes=typing.cast("tuple[str, ...]", command_options["ignored_nodes"]),
            ignore_stdlib=typing.cast("bool | None", command_options["ignore_stdlib"]),
            ignore_external_lib=typing.cast(
                "bool | None",
                command_options["ignore_external_lib"],
            ),
        ),
    )


def _remove_isolated_init_nodes(dependency_graph: nx.DiGraph) -> None:
    isolated_nodes = list(nx.isolates(dependency_graph))
    nodes_to_remove = [
        node_id
        for node_id in isolated_nodes
        if str(dependency_graph.nodes[node_id].get("label")) == "__init__.py"
    ]
    if nodes_to_remove:
        dependency_graph.remove_nodes_from(nodes_to_remove)


@click.command()
@_with_command_options
def main(**command_options: object) -> None:
    """Analyze a Python project and optionally visualize its dependency graph."""
    cli_command = _build_cli_command(command_options)
    selected_visualizer, selected_layout = _CliSupport.get_visualizer_selection(cli_command)
    dependency_graph, violations = _CliSupport.run_analysis(cli_command)

    if selected_visualizer is not None and selected_layout is not None:
        _CliSupport.render_graph(selected_visualizer, dependency_graph, selected_layout)
    if cli_command.show_console_summary:
        if cli_command.summary_format == "json":
            summary_builder.print_json_summary(dependency_graph, violations)
        else:
            summary_builder.print_summary(dependency_graph, violations)
    if cli_command.fail_on_violation and violations:
        raise click.exceptions.Exit(1)


if __name__ == "__main__":
    main()
