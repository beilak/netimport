from pathlib import Path
from typing import Final

import networkx as nx
from _pytest.monkeypatch import MonkeyPatch
from click.testing import CliRunner

from netimport_lib import cli
from netimport_lib.config_loader import NetImportConfigMap
from netimport_lib.visualizer import GraphVisualizer


def _default_loaded_config(_project_root: str) -> NetImportConfigMap:
    return {
        "ignored_nodes": set(),
        "ignored_dirs": set(),
        "ignored_files": set(),
        "ignore_stdlib": False,
        "ignore_external_lib": False,
    }


def _write_pyproject_config(project_root: Path, config_body: str) -> None:
    (project_root / "pyproject.toml").write_text(
        f"[project]\nname = 'sample-project'\nversion = '0.1.0'\n{config_body}",
        encoding="utf-8",
    )


def _build_recording_visualizer(
    name: str,
    supported_layouts: tuple[str, ...],
    default_layout: str,
    calls: list[tuple[str, str]],
) -> GraphVisualizer:
    def fake_visualizer(_graph: nx.DiGraph, layout: str) -> None:
        calls.append((name, layout))

    return GraphVisualizer(
        name=name,
        render=fake_visualizer,
        supported_layouts=supported_layouts,
        default_layout=default_layout,
    )


def test_cli_prints_console_summary(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    project_root = tmp_path / "sample_project"
    project_root.mkdir()

    (project_root / "main.py").write_text(
        "import helper\nimport os\nimport requests\n",
        encoding="utf-8",
    )
    (project_root / "helper.py").write_text(
        "from .missing import item\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(cli, "GRAPH_VISUALIZERS", {})
    monkeypatch.setattr(cli, "load_config", _default_loaded_config)

    runner: Final[CliRunner] = CliRunner()
    result = runner.invoke(
        cli.main,
        [str(project_root), "--show-console-summary", "--no-show-graph"],
    )

    assert result.exit_code == 0
    assert "Dependency Graph Summary" in result.output
    assert "| Project files            | 2     |" in result.output
    assert "| Standard library modules | 1     |" in result.output
    assert "| External libraries       | 1     |" in result.output
    assert "| Unresolved imports       | 1     |" in result.output
    assert "| 1    | main.py   | 0        | 3        | 3     |" in result.output
    assert "| 1    | .missing.item | unresolved_relative |" in result.output


def test_cli_no_show_graph_disables_visualizer(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    project_root = tmp_path / "sample_project"
    project_root.mkdir()

    (project_root / "main.py").write_text("import helper\n", encoding="utf-8")
    (project_root / "helper.py").write_text("", encoding="utf-8")

    visualizer_calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        cli,
        "GRAPH_VISUALIZERS",
        {
            "bokeh": _build_recording_visualizer(
                "bokeh",
                ("constrained",),
                "constrained",
                visualizer_calls,
            )
        },
    )
    monkeypatch.setattr(cli, "load_config", _default_loaded_config)

    runner: Final[CliRunner] = CliRunner()
    result = runner.invoke(
        cli.main,
        [str(project_root), "--show-console-summary", "--no-show-graph"],
    )

    assert result.exit_code == 0
    assert "Dependency Graph Summary" in result.output
    assert visualizer_calls == []


def test_cli_uses_bokeh_default_layout_when_layout_is_omitted(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "sample_project"
    project_root.mkdir()

    (project_root / "main.py").write_text("import helper\n", encoding="utf-8")
    (project_root / "helper.py").write_text("", encoding="utf-8")

    visualizer_calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        cli,
        "GRAPH_VISUALIZERS",
        {
            "bokeh": _build_recording_visualizer(
                "bokeh",
                ("constrained",),
                "constrained",
                visualizer_calls,
            ),
            "mpl": _build_recording_visualizer(
                "mpl",
                ("spring", "circular"),
                "spring",
                visualizer_calls,
            ),
        },
    )
    monkeypatch.setattr(cli, "load_config", _default_loaded_config)

    runner: Final[CliRunner] = CliRunner()
    result = runner.invoke(cli.main, [str(project_root)])

    assert result.exit_code == 0
    assert visualizer_calls == [("bokeh", "constrained")]


def test_cli_uses_mpl_default_layout_when_layout_is_omitted(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "sample_project"
    project_root.mkdir()

    (project_root / "main.py").write_text("import helper\n", encoding="utf-8")
    (project_root / "helper.py").write_text("", encoding="utf-8")

    visualizer_calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        cli,
        "GRAPH_VISUALIZERS",
        {
            "bokeh": _build_recording_visualizer(
                "bokeh",
                ("constrained",),
                "constrained",
                visualizer_calls,
            ),
            "mpl": _build_recording_visualizer(
                "mpl",
                ("spring", "circular"),
                "spring",
                visualizer_calls,
            ),
        },
    )
    monkeypatch.setattr(cli, "load_config", _default_loaded_config)

    runner: Final[CliRunner] = CliRunner()
    result = runner.invoke(cli.main, [str(project_root), "--show-graph", "mpl"])

    assert result.exit_code == 0
    assert visualizer_calls == [("mpl", "spring")]


def test_cli_accepts_supported_backend_and_layout_combination(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "sample_project"
    project_root.mkdir()

    (project_root / "main.py").write_text("import helper\n", encoding="utf-8")
    (project_root / "helper.py").write_text("", encoding="utf-8")

    visualizer_calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        cli,
        "GRAPH_VISUALIZERS",
        {
            "bokeh": _build_recording_visualizer(
                "bokeh",
                ("constrained",),
                "constrained",
                visualizer_calls,
            ),
            "mpl": _build_recording_visualizer(
                "mpl",
                ("spring", "circular"),
                "spring",
                visualizer_calls,
            ),
        },
    )
    monkeypatch.setattr(cli, "load_config", _default_loaded_config)

    runner: Final[CliRunner] = CliRunner()
    result = runner.invoke(
        cli.main,
        [str(project_root), "--show-graph", "mpl", "--layout", "circular"],
    )

    assert result.exit_code == 0
    assert visualizer_calls == [("mpl", "circular")]


def test_cli_rejects_unsupported_backend_and_layout_combination(tmp_path: Path) -> None:
    project_root = tmp_path / "sample_project"
    project_root.mkdir()

    runner: Final[CliRunner] = CliRunner()
    result = runner.invoke(
        cli.main,
        [str(project_root), "--show-graph", "bokeh", "--layout", "spring"],
    )

    assert result.exit_code != 0
    assert "Layout 'spring' is not supported by the 'bokeh' backend" in result.output
    assert "Supported layouts: constrained." in result.output


def test_cli_help_lists_only_supported_visualizers_and_layouts() -> None:
    runner: Final[CliRunner] = CliRunner()
    result = runner.invoke(cli.main, ["--help"])

    assert result.exit_code == 0
    assert "--show-graph [bokeh|mpl]" in result.output
    assert "--layout [constrained|spring|circular|shell|planar_layout]" in result.output
    assert "dot" not in result.output
    assert "neato" not in result.output
    assert "fdp" not in result.output
    assert "sfdp" not in result.output
    assert "kamada_kawai" not in result.output
    assert "spectral" not in result.output
    assert "plotly" not in result.output


def test_cli_loads_config_from_target_project(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    caller_root = tmp_path / "caller"
    caller_root.mkdir()
    _write_pyproject_config(caller_root, "\n[tool.netimport]\nignored_dirs = []\n")

    project_root = tmp_path / "target_project"
    project_root.mkdir()
    _write_pyproject_config(project_root, "\n[tool.netimport]\nignored_dirs = ['ignored']\n")

    (project_root / "main.py").write_text("", encoding="utf-8")
    ignored_dir = project_root / "ignored"
    ignored_dir.mkdir()
    (ignored_dir / "hidden.py").write_text("", encoding="utf-8")

    monkeypatch.chdir(caller_root)
    monkeypatch.setattr(cli, "GRAPH_VISUALIZERS", {})

    runner: Final[CliRunner] = CliRunner()
    result = runner.invoke(
        cli.main,
        [str(project_root), "--show-console-summary", "--no-show-graph"],
    )

    assert result.exit_code == 0
    assert "| Project files            | 1     |" in result.output


def test_cli_merges_file_and_cli_config(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    project_root = tmp_path / "target_project"
    project_root.mkdir()
    _write_pyproject_config(
        project_root,
        "\n[tool.netimport]\nignored_dirs = ['from_file']\nignore_stdlib = true\n",
    )

    (project_root / "main.py").write_text("import os\nimport helper\n", encoding="utf-8")
    (project_root / "helper.py").write_text("", encoding="utf-8")

    file_ignored_dir = project_root / "from_file"
    file_ignored_dir.mkdir()
    (file_ignored_dir / "skip_file.py").write_text("", encoding="utf-8")

    cli_ignored_dir = project_root / "from_cli"
    cli_ignored_dir.mkdir()
    (cli_ignored_dir / "skip_cli.py").write_text("", encoding="utf-8")

    monkeypatch.setattr(cli, "GRAPH_VISUALIZERS", {})

    runner: Final[CliRunner] = CliRunner()
    result = runner.invoke(
        cli.main,
        [
            str(project_root),
            "--show-console-summary",
            "--no-show-graph",
            "--ignored-dir",
            "from_cli",
            "--include-stdlib",
        ],
    )

    assert result.exit_code == 0
    assert "| Project files            | 2     |" in result.output
    assert "| Standard library modules | 1     |" in result.output


def test_cli_applies_ignored_files_from_config(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    project_root = tmp_path / "target_project"
    project_root.mkdir()
    _write_pyproject_config(project_root, "\n[tool.netimport]\nignored_files = ['skip.py']\n")

    (project_root / "main.py").write_text("", encoding="utf-8")
    (project_root / "skip.py").write_text("", encoding="utf-8")

    monkeypatch.setattr(cli, "GRAPH_VISUALIZERS", {})

    runner: Final[CliRunner] = CliRunner()
    result = runner.invoke(
        cli.main,
        [str(project_root), "--show-console-summary", "--no-show-graph"],
    )

    assert result.exit_code == 0
    assert "| Project files            | 1     |" in result.output


def test_cli_works_without_tool_netimport_config(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "target_project"
    project_root.mkdir()
    (project_root / "pyproject.toml").write_text(
        "[project]\nname = 'sample-project'\nversion = '0.1.0'\n",
        encoding="utf-8",
    )
    (project_root / "main.py").write_text("import os\n", encoding="utf-8")

    monkeypatch.setattr(cli, "GRAPH_VISUALIZERS", {})

    runner: Final[CliRunner] = CliRunner()
    result = runner.invoke(
        cli.main,
        [str(project_root), "--show-console-summary", "--no-show-graph"],
    )

    assert result.exit_code == 0
    assert "| Project files            | 1     |" in result.output
