from pathlib import Path

from click.testing import CliRunner

import netimport_lib.cli as cli


def _write_pyproject_config(project_root: Path, config_body: str) -> None:
    (project_root / "pyproject.toml").write_text(
        "[project]\nname = 'sample-project'\nversion = '0.1.0'\n"
        f"{config_body}",
        encoding="utf-8",
    )


def test_cli_prints_console_summary(monkeypatch, tmp_path: Path) -> None:
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
    monkeypatch.setattr(
        cli,
        "load_config",
        lambda _project_root: {
            "ignored_nodes": set(),
            "ignored_dirs": set(),
            "ignored_files": set(),
            "ignore_stdlib": False,
            "ignore_external_lib": False,
        },
    )

    runner = CliRunner()
    result = runner.invoke(cli.main, [str(project_root), "--show-console-summary"])

    assert result.exit_code == 0
    assert "Dependency Graph Summary" in result.output
    assert "| Project files            | 2     |" in result.output
    assert "| Standard library modules | 1     |" in result.output
    assert "| External libraries       | 1     |" in result.output
    assert "| Unresolved imports       | 1     |" in result.output
    assert "| 1    | main.py   | 0        | 3        | 3     |" in result.output
    assert "| 1    | .missing.item | unresolved_relative |" in result.output


def test_cli_no_show_graph_disables_visualizer(monkeypatch, tmp_path: Path) -> None:
    project_root = tmp_path / "sample_project"
    project_root.mkdir()

    (project_root / "main.py").write_text(
        "import helper\n",
        encoding="utf-8",
    )
    (project_root / "helper.py").write_text(
        "",
        encoding="utf-8",
    )

    visualizer_calls: list[tuple[int, str]] = []

    def fake_visualizer(graph, layout) -> None:
        visualizer_calls.append((graph.number_of_nodes(), layout))

    monkeypatch.setattr(cli, "GRAPH_VISUALIZERS", {"bokeh": fake_visualizer})
    monkeypatch.setattr(
        cli,
        "load_config",
        lambda _project_root: {
            "ignored_nodes": set(),
            "ignored_dirs": set(),
            "ignored_files": set(),
            "ignore_stdlib": False,
            "ignore_external_lib": False,
        },
    )

    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        [str(project_root), "--show-console-summary", "--no-show-graph"],
    )

    assert result.exit_code == 0
    assert "Dependency Graph Summary" in result.output
    assert visualizer_calls == []


def test_cli_loads_config_from_target_project(monkeypatch, tmp_path: Path) -> None:
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

    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        [str(project_root), "--show-console-summary", "--no-show-graph"],
    )

    assert result.exit_code == 0
    assert "| Project files            | 1     |" in result.output


def test_cli_merges_file_and_cli_config(monkeypatch, tmp_path: Path) -> None:
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

    runner = CliRunner()
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


def test_cli_applies_ignored_files_from_config(monkeypatch, tmp_path: Path) -> None:
    project_root = tmp_path / "target_project"
    project_root.mkdir()
    _write_pyproject_config(project_root, "\n[tool.netimport]\nignored_files = ['skip.py']\n")

    (project_root / "main.py").write_text("", encoding="utf-8")
    (project_root / "skip.py").write_text("", encoding="utf-8")

    monkeypatch.setattr(cli, "GRAPH_VISUALIZERS", {})

    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        [str(project_root), "--show-console-summary", "--no-show-graph"],
    )

    assert result.exit_code == 0
    assert "| Project files            | 1     |" in result.output


def test_cli_works_without_tool_netimport_config(monkeypatch, tmp_path: Path) -> None:
    project_root = tmp_path / "target_project"
    project_root.mkdir()
    (project_root / "pyproject.toml").write_text(
        "[project]\nname = 'sample-project'\nversion = '0.1.0'\n",
        encoding="utf-8",
    )
    (project_root / "main.py").write_text("import os\n", encoding="utf-8")

    monkeypatch.setattr(cli, "GRAPH_VISUALIZERS", {})

    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        [str(project_root), "--show-console-summary", "--no-show-graph"],
    )

    assert result.exit_code == 0
    assert "| Project files            | 1     |" in result.output
