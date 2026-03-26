from pathlib import Path

from click.testing import CliRunner

import netimport_lib.cli as cli


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
