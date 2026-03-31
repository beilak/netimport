from pathlib import Path

from _pytest.monkeypatch import MonkeyPatch
from click.testing import CliRunner, Result

from netimport_lib import cli


def _create_project(tmp_path: Path, project_name: str, files: dict[str, str]) -> Path:
    project_root = tmp_path / project_name
    project_root.mkdir()
    for relative_path, text in files.items():
        file_path = project_root / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(text, encoding="utf8")
    return project_root


def _write_pyproject_config(project_root: Path, config_body: str) -> None:
    (project_root / "pyproject.toml").write_text(
        f"[project]\nname = 'sample-project'\nversion = '0.1.0'\n{config_body}",
        encoding="utf8",
    )


def _invoke_summary_cli(monkeypatch: MonkeyPatch, project_root: Path, *extra_args: str) -> Result:
    monkeypatch.setattr(cli, "GRAPH_VISUALIZERS", {})
    return CliRunner().invoke(
        cli.main,
        [str(project_root), "--show-console-summary", "--no-show-graph", *extra_args],
    )


def test_cli_loads_target_project_config(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    caller_root = _create_project(tmp_path, "caller", {})
    _write_pyproject_config(caller_root, "\n[tool.netimport]\nignored_dirs = []\n")

    project_root = _create_project(tmp_path, "target_project", {"app.py": ""})
    _write_pyproject_config(project_root, "\n[tool.netimport]\nignored_dirs = ['ignored']\n")
    ignored_dir = project_root / "ignored"
    ignored_dir.mkdir()
    (ignored_dir / "hidden.py").write_text("", encoding="utf-8")

    monkeypatch.chdir(caller_root)
    cli_result = _invoke_summary_cli(monkeypatch, project_root)

    assert cli_result.exit_code == 0
    assert "| Project files            | 1     |" in cli_result.output


def test_cli_merges_file_and_cli_config(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    project_root = _create_project(
        tmp_path,
        "analysis_target",
        {"entry.py": "import os\nimport helper\n", "helper.py": ""},
    )
    _write_pyproject_config(
        project_root,
        "\n[tool.netimport]\nignored_dirs = ['from_file']\nignore_stdlib = true\n",
    )

    file_ignored_dir = project_root / "from_file"
    file_ignored_dir.mkdir()
    (file_ignored_dir / "skip_file.py").write_text("", encoding="utf-8")

    cli_ignored_dir = project_root / "from_cli"
    cli_ignored_dir.mkdir()
    (cli_ignored_dir / "skip_cli.py").write_text("", encoding="utf-8")

    cli_result = _invoke_summary_cli(
        monkeypatch,
        project_root,
        "--ignored-dir",
        "from_cli",
        "--include-stdlib",
    )

    assert cli_result.exit_code == 0
    assert "| Project files            | 2     |" in cli_result.output
    assert "| Standard library modules | 1     |" in cli_result.output


def test_cli_applies_ignored_files(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    project_root = _create_project(
        tmp_path,
        "ignored_files_project",
        {"worker.py": "", "skip.py": ""},
    )
    _write_pyproject_config(project_root, "\n[tool.netimport]\nignored_files = ['skip.py']\n")

    cli_result = _invoke_summary_cli(monkeypatch, project_root)

    assert cli_result.exit_code == 0
    assert "| Project files            | 1     |" in cli_result.output


def test_cli_works_without_tool_config(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    project_root = _create_project(
        tmp_path,
        "plain_project",
        {"script.py": "import os\n"},
    )
    (project_root / "pyproject.toml").write_text(
        "[project]\nname = 'sample-project'\nversion = '0.1.0'\n",
        encoding="utf8",
    )

    cli_result = _invoke_summary_cli(monkeypatch, project_root)

    assert cli_result.exit_code == 0
    assert "| Project files            | 1     |" in cli_result.output
