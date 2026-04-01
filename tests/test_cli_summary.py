import json
from collections.abc import Callable
from pathlib import Path
from unittest.mock import Mock

from _pytest.monkeypatch import MonkeyPatch
from click.testing import CliRunner, Result

from netimport_lib import cli
from netimport_lib.config_loader import NetImportConfigMap


def _invoke_summary_cli(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    files: dict[str, str],
    *extra_args: str,
    load_config: Callable[[str], NetImportConfigMap] | None = None,
) -> Result:
    project_root = tmp_path / "sample_project"
    project_root.mkdir()
    for relative_path, text in files.items():
        file_path = project_root / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(text, encoding="utf-8")
    monkeypatch.setattr(cli, "GRAPH_VISUALIZERS", {})
    loader = load_config
    if loader is None:
        loader = Mock(
            return_value={
                "ignored_nodes": set(),
                "ignored_dirs": set(),
                "ignored_files": set(),
                "ignore_stdlib": False,
                "ignore_external_lib": False,
                "fail_on_unresolved_imports": False,
                "forbidden_external_libs": set(),
            },
        )
    monkeypatch.setattr(cli, "load_config", loader)
    return CliRunner().invoke(
        cli.main,
        [str(project_root), "--show-console-summary", *extra_args, "--no-show-graph"],
    )


def _assert_output(
    output: str,
    *,
    expected: tuple[str, ...] = (),
    unexpected: tuple[str, ...] = (),
) -> None:
    for expected_line in expected:
        assert expected_line in output
    for unexpected_line in unexpected:
        assert unexpected_line not in output


def test_cli_prints_console_summary(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    cli_result = _invoke_summary_cli(
        monkeypatch,
        tmp_path,
        {
            "app.py": "import helper\nimport os\nimport requests\n",
            "helper.py": "from .missing import item\n",
        },
    )

    assert cli_result.exit_code == 0
    _assert_output(
        cli_result.output,
        expected=(
            "Dependency Graph Summary",
            "This report summarizes the project's import graph",
            "High-level graph totals.",
            "| Project files            | 2     |",
            "| Standard library modules | 1     |",
            "| External libraries       | 1     |",
            "| Unresolved imports       | 1     |",
            "| 1    | app.py    | 0        | 3        | 3     |",
            "| 1    | .missing.item | unresolved_relative |",
        ),
    )


def test_cli_prints_json_summary(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    cli_result = _invoke_summary_cli(
        monkeypatch,
        tmp_path,
        {
            "main.py": "import helper\nimport os\nimport requests\n",
            "helper.py": "from .missing import item\n",
        },
        "--summary-format",
        "json",
    )

    payload = json.loads(cli_result.output)
    assert (cli_result.exit_code, payload["schema_version"]) == (0, 1)
    assert payload["overview"] == {
        "nodes": 5,
        "edges": 4,
        "project_files": 2,
        "standard_library_modules": 1,
        "external_libraries": 1,
        "unresolved_imports": 1,
    }
    assert payload["most_coupled_project_files"][0] == {
        "rank": 1,
        "file": "main.py",
        "incoming": 0,
        "outgoing": 3,
        "total": 3,
    }
    assert payload["external_dependencies"] == ["requests"]
    assert (
        payload["unresolved_imports"],
        payload["violations"],
    ) == (
        [
            {
                "rank": 1,
                "import_name": ".missing.item",
                "type": "unresolved_relative",
            }
        ],
        [],
    )


def test_cli_exits_on_policy_violations(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    cli_result = _invoke_summary_cli(
        monkeypatch,
        tmp_path,
        {"entry.py": "import requests\nfrom .missing import item\n"},
        "--summary-format",
        "json",
        "--fail-on-violation",
        load_config=lambda _project_root: {
            "ignored_nodes": set(),
            "ignored_dirs": set(),
            "ignored_files": set(),
            "ignore_stdlib": False,
            "ignore_external_lib": False,
            "fail_on_unresolved_imports": True,
            "forbidden_external_libs": {"requests"},
        },
    )

    assert cli_result.exit_code == 1
    payload = json.loads(cli_result.output)
    assert [violation["rule"] for violation in payload["violations"]] == [
        "forbidden_external_lib",
        "unresolved_import",
    ]


def test_cli_reports_policy_violations(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    cli_result = _invoke_summary_cli(
        monkeypatch,
        tmp_path,
        {"module.py": "from .missing import item\n"},
        load_config=lambda _project_root: {
            "ignored_nodes": set(),
            "ignored_dirs": set(),
            "ignored_files": set(),
            "ignore_stdlib": False,
            "ignore_external_lib": False,
            "fail_on_unresolved_imports": True,
            "forbidden_external_libs": set(),
        },
    )

    assert cli_result.exit_code == 0
    _assert_output(
        cli_result.output,
        expected=("Policy Violations", "unresolved_import"),
    )


def test_cli_help_lists_supported_options() -> None:
    cli_result = CliRunner().invoke(cli.main, ["--help"])

    assert cli_result.exit_code == 0
    _assert_output(
        cli_result.output,
        expected=(
            "--config FILE",
            "--show-graph [bokeh]",
            "--layout [constrained]",
            "--summary-format [text|json]",
        ),
        unexpected=("dot", "neato", "fdp", "sfdp", "kamada_kawai", "spectral", "plotly"),
    )
