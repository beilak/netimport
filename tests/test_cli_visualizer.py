from pathlib import Path
from unittest.mock import Mock

import pytest
from _pytest.monkeypatch import MonkeyPatch
from click.testing import CliRunner, Result

from netimport_lib import cli
from netimport_lib.visualizer import bokeh_plotter
from netimport_lib.visualizer.registry import GraphVisualizer


_CLI_DEFAULTS = ("bokeh", "constrained")


def _invoke_visualizer_cli(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    render: Mock,
    cli_args_suffix: list[str] | None = None,
) -> tuple[Result, Mock, GraphVisualizer]:
    visualizer_name, default_layout = _CLI_DEFAULTS
    project_root = tmp_path / "sample_project"
    project_root.mkdir()
    (project_root / "main.py").write_text("import helper\n", encoding="utf-8")
    (project_root / "helper.py").touch()
    visualizer = GraphVisualizer(
        name=visualizer_name,
        render=render,
        supported_layouts=(default_layout,),
        default_layout=default_layout,
    )
    monkeypatch.setattr(
        cli,
        "GRAPH_VISUALIZERS",
        {"bokeh": visualizer},
    )
    monkeypatch.setattr(
        cli,
        "load_config",
        lambda _project_root: {
            "ignored_nodes": set(),
            "ignored_dirs": set(),
            "ignored_files": set(),
            "ignore_stdlib": False,
            "ignore_external_lib": False,
            "fail_on_unresolved_imports": False,
            "forbidden_external_libs": set(),
        },
    )
    cli_args = [str(project_root)]
    if cli_args_suffix is not None:
        cli_args.extend(cli_args_suffix)
    return CliRunner().invoke(cli.main, cli_args), render, visualizer


def test_cli_no_show_graph_skips_visualizer(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    cli_result, render, _visualizer = _invoke_visualizer_cli(
        monkeypatch,
        tmp_path,
        Mock(return_value=None),
        ["--no-show-graph", "--show-console-summary"],
    )

    assert cli_result.exit_code == 0
    assert "Dependency Graph Summary" in cli_result.output
    render.assert_not_called()


@pytest.mark.parametrize(
    ("cli_args_suffix", "expected_result"),
    [
        (None, (0, _CLI_DEFAULTS[1], None)),
        (
            ["--show-graph", _CLI_DEFAULTS[0], "--layout", _CLI_DEFAULTS[1]],
            (0, _CLI_DEFAULTS[1], None),
        ),
        (
            ["--show-graph", _CLI_DEFAULTS[0], "--layout", "spring"],
            (2, None, "'spring' is not 'constrained'"),
        ),
    ],
)
def test_cli_validates_requested_layout(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    cli_args_suffix: list[str] | None,
    expected_result: tuple[int, str | None, str | None],
) -> None:
    cli_result, render, visualizer = _invoke_visualizer_cli(
        monkeypatch,
        tmp_path,
        Mock(return_value=None),
        cli_args_suffix,
    )

    assert cli_result.exit_code == expected_result[0]
    if expected_result[1] is not None:
        assert render.call_args.args[1] == expected_result[1]
        assert expected_result[1] in visualizer.supported_layouts
    if expected_result[2] is not None:
        assert "Invalid value for '--layout'" in cli_result.output
        assert expected_result[2] in cli_result.output


def test_cli_prints_visualizer_message(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    message = "Saved interactive graph to /tmp/netimport-graph.html"
    cli_result, _render, _visualizer = _invoke_visualizer_cli(
        monkeypatch,
        tmp_path,
        Mock(return_value=message),
    )

    assert cli_result.exit_code == 0
    assert message in cli_result.output


@pytest.mark.parametrize(
    ("cli_args_suffix", "expected_result"),
    [
        (None, (1, "output", "Failed to render graph with")),
        (
            ["--show-console-summary"],
            (0, "stderr", "Warning: Failed to render graph with"),
        ),
    ],
)
def test_cli_handles_visualizer_failure(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    cli_args_suffix: list[str] | None,
    expected_result: tuple[int, str, str],
) -> None:
    error_message = "automatic browser launch failed"
    cli_result, _render, visualizer = _invoke_visualizer_cli(
        monkeypatch,
        tmp_path,
        Mock(side_effect=RuntimeError(error_message)),
        cli_args_suffix,
    )

    assert cli_result.exit_code == expected_result[0]
    if expected_result[0] == 0:
        assert "Dependency Graph Summary" in cli_result.stdout

    expected_message = f"{expected_result[2]} '{visualizer.name}': {error_message}"
    if expected_result[1] == "stderr":
        assert expected_message in cli_result.stderr
    else:
        assert expected_message in cli_result.output


def test_cli_keeps_summary_if_browser_unavailable(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "sample_project"
    project_root.mkdir()
    (project_root / "main.py").write_text("import helper\n", encoding="utf-8")
    (project_root / "helper.py").touch()
    output_path = tmp_path / "netimport-graph.html"

    monkeypatch.setattr(
        cli,
        "load_config",
        lambda _project_root: {
            "ignored_nodes": set(),
            "ignored_dirs": set(),
            "ignored_files": set(),
            "ignore_stdlib": False,
            "ignore_external_lib": False,
            "fail_on_unresolved_imports": False,
            "forbidden_external_libs": set(),
        },
    )
    monkeypatch.setattr(bokeh_plotter, "_save_plot", lambda _plot: output_path)
    monkeypatch.setattr(bokeh_plotter, "_open_saved_plot", lambda _path: False)

    cli_result = CliRunner().invoke(
        cli.main,
        [str(project_root), "--show-console-summary"],
    )

    assert cli_result.exit_code == 0
    assert "Dependency Graph Summary" in cli_result.stdout
    assert "Interactive dependency graph saved to" in cli_result.stderr
