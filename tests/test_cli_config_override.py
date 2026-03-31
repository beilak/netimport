from pathlib import Path

from _pytest.monkeypatch import MonkeyPatch
from click.testing import CliRunner, Result

from netimport_lib import cli


def _write_text(file_path: Path, text: str) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(text, encoding="utf-8")


def _create_project(tmp_path: Path, project_name: str, files: dict[str, str]) -> Path:
    project_root = tmp_path / project_name
    project_root.mkdir()
    for relative_path, text in files.items():
        _write_text(project_root / relative_path, text)
    return project_root


def _invoke_cli(monkeypatch: MonkeyPatch, project_root: Path, *args: str) -> Result:
    monkeypatch.setattr(cli, "GRAPH_VISUALIZERS", {})
    return CliRunner().invoke(cli.main, [str(project_root), *args])


def test_cli_explicit_config_overrides_project(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = _create_project(
        tmp_path,
        "project_override",
        {"main.py": "import os\nimport helper\n", "helper.py": ""},
    )
    _write_text(
        project_root / "pyproject.toml",
        "[project]\nname = 'sample-project'\nversion = '0.1.0'\n"
        "\n[tool.netimport]\nignored_dirs = ['from_project']\nignore_stdlib = true\n",
    )

    explicit_config_path = tmp_path / "netimport.override.toml"
    _write_text(
        explicit_config_path,
        "ignored_dirs = ['explicit_zone']\nignore_stdlib = false\n",
    )

    (project_root / "from_project").mkdir()
    _write_text(project_root / "from_project" / "project_hidden.py", "")
    (project_root / "explicit_zone").mkdir()
    _write_text(project_root / "explicit_zone" / "explicit_hidden.py", "")

    cli_result = _invoke_cli(
        monkeypatch,
        project_root,
        "--config",
        str(explicit_config_path),
        "--show-console-summary",
        "--no-show-graph",
    )

    assert cli_result.exit_code == 0
    assert "| Project files            | 3     |" in cli_result.output
    assert "| Standard library modules | 1     |" in cli_result.output


def test_cli_flags_override_explicit_config(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = _create_project(
        tmp_path,
        "flag_override",
        {"main.py": "import os\nimport helper\n", "helper.py": ""},
    )
    explicit_config_path = tmp_path / "netimport.flags.toml"
    _write_text(
        explicit_config_path,
        "ignored_dirs = ['override_zone']\nignore_stdlib = true\n",
    )

    (project_root / "override_zone").mkdir()
    _write_text(project_root / "override_zone" / "explicit_hidden.py", "")
    (project_root / "from_cli").mkdir()
    _write_text(project_root / "from_cli" / "cli_hidden.py", "")

    cli_result = _invoke_cli(
        monkeypatch,
        project_root,
        "--config",
        str(explicit_config_path),
        "--ignored-dir",
        "from_cli",
        "--include-stdlib",
        "--show-console-summary",
        "--no-show-graph",
    )

    assert cli_result.exit_code == 0
    assert "| Project files            | 2     |" in cli_result.output
    assert "| Standard library modules | 1     |" in cli_result.output


def test_cli_rejects_explicit_config_without_keys(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = _create_project(tmp_path, "explicit_reject", {"main.py": ""})
    explicit_config_path = tmp_path / "custom.toml"
    _write_text(
        explicit_config_path,
        "[project]\nname = 'sample-project'\nversion = '0.1.0'\n",
    )

    cli_result = _invoke_cli(
        monkeypatch,
        project_root,
        "--config",
        str(explicit_config_path),
        "--no-show-graph",
    )

    assert cli_result.exit_code != 0
    assert "does not contain NetImport config" in cli_result.output
