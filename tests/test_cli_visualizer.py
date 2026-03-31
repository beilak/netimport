from pathlib import Path
from unittest.mock import Mock

from _pytest.monkeypatch import MonkeyPatch
from click.testing import CliRunner, Result

from netimport_lib import cli
from netimport_lib.visualizer.registry import GraphVisualizer


def _invoke_visualizer_cli(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    render: Mock,
    *,
    no_show_graph: bool = False,
    requested_layout: str | None = None,
) -> tuple[Result, Mock, GraphVisualizer]:
    project_root = tmp_path / "sample_project"
    project_root.mkdir()
    (project_root / "main.py").write_text("import helper\n", encoding="utf-8")
    (project_root / "helper.py").write_text("", encoding="utf-8")
    visualizer = GraphVisualizer(
        name="bokeh",
        render=render,
        supported_layouts=("constrained",),
        default_layout="constrained",
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
    if no_show_graph:
        cli_args.extend(["--show-console-summary", "--no-show-graph"])
    elif requested_layout is None:
        cli_args.extend([])
    else:
        cli_args.extend(["--show-graph", "bokeh", "--layout", requested_layout])
    return CliRunner().invoke(cli.main, cli_args), render, visualizer


def test_cli_no_show_graph_skips_visualizer(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    cli_result, render, _visualizer = _invoke_visualizer_cli(
        monkeypatch,
        tmp_path,
        Mock(return_value=None),
        no_show_graph=True,
    )

    assert cli_result.exit_code == 0
    assert "Dependency Graph Summary" in cli_result.output
    render.assert_not_called()


def test_cli_uses_default_bokeh_layout(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    cli_result, render, visualizer = _invoke_visualizer_cli(
        monkeypatch,
        tmp_path,
        Mock(return_value=None),
    )

    assert cli_result.exit_code == 0
    assert render.call_args.args[1] == visualizer.default_layout


def test_cli_accepts_supported_backend_layout(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    cli_result, render, visualizer = _invoke_visualizer_cli(
        monkeypatch,
        tmp_path,
        Mock(return_value=None),
        requested_layout="constrained",
    )

    assert cli_result.exit_code == 0
    assert render.call_args.args[1] in visualizer.supported_layouts


def test_cli_prints_visualizer_message(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    message = "Saved interactive graph to /tmp/netimport-graph.html"
    cli_result, _render, _visualizer = _invoke_visualizer_cli(
        monkeypatch,
        tmp_path,
        Mock(return_value=message),
    )

    assert cli_result.exit_code == 0
    assert message in cli_result.output


def test_cli_wraps_visualizer_error(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    error_message = "automatic browser launch failed"
    cli_result, _render, visualizer = _invoke_visualizer_cli(
        monkeypatch,
        tmp_path,
        Mock(side_effect=RuntimeError(error_message)),
    )

    assert cli_result.exit_code != 0
    assert f"Failed to render graph with '{visualizer.name}': {error_message}" in cli_result.output


def test_cli_rejects_unsupported_backend_layout(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    cli_result, _render, _visualizer = _invoke_visualizer_cli(
        monkeypatch,
        tmp_path,
        Mock(return_value=None),
        requested_layout="spring",
    )

    assert cli_result.exit_code != 0
    assert "Invalid value for '--layout'" in cli_result.output
    assert "'spring' is not 'constrained'" in cli_result.output
