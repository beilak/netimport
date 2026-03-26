from pathlib import Path

from netimport_lib.config_loader import load_config


def test_load_config_returns_defaults_without_netimport_section(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "pyproject.toml").write_text(
        "[project]\nname = 'sample-project'\nversion = '0.1.0'\n",
        encoding="utf-8",
    )

    config = load_config(str(project_root))

    assert config == {
        "ignored_nodes": set(),
        "ignored_dirs": set(),
        "ignored_files": set(),
        "ignore_stdlib": False,
        "ignore_external_lib": False,
    }


def test_load_config_prefers_dot_netimport_toml_over_pyproject(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "pyproject.toml").write_text(
        "[project]\nname = 'sample-project'\nversion = '0.1.0'\n"
        "\n[tool.netimport]\nignored_dirs = ['from_pyproject']\nignore_stdlib = true\n",
        encoding="utf-8",
    )
    (project_root / ".netimport.toml").write_text(
        "ignored_dirs = ['from_netimport']\nignored_files = ['skip.py']\nignore_stdlib = false\n",
        encoding="utf-8",
    )

    config = load_config(str(project_root))

    assert config["ignored_dirs"] == {"from_netimport"}
    assert config["ignored_files"] == {"skip.py"}
    assert config["ignore_stdlib"] is False
