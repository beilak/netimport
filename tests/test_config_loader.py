from pathlib import Path

import pytest

from netimport_lib.config_loader import load_config, load_explicit_config


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
        "fail_on_unresolved_imports": False,
        "forbidden_external_libs": set(),
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


def test_load_explicit_config_reads_top_level_netimport_file(tmp_path: Path) -> None:
    config_path = tmp_path / "custom.toml"
    config_path.write_text(
        "ignored_dirs = ['tmp']\nignored_files = ['skip.py']\nignore_stdlib = true\n",
        encoding="utf-8",
    )

    config = load_explicit_config(config_path)

    assert config == {
        "ignored_dirs": {"tmp"},
        "ignored_files": {"skip.py"},
        "ignore_stdlib": True,
    }


def test_load_explicit_config_reads_pyproject_style_file(tmp_path: Path) -> None:
    config_path = tmp_path / "custom-pyproject.toml"
    config_path.write_text(
        "[project]\nname = 'sample-project'\nversion = '0.1.0'\n"
        "\n[tool.netimport]\nignored_nodes = ['requests']\nignore_external_lib = true\n",
        encoding="utf-8",
    )

    config = load_explicit_config(config_path)

    assert config == {
        "ignored_nodes": {"requests"},
        "ignore_external_lib": True,
    }


def test_load_explicit_config_rejects_toml_without_netimport_keys(tmp_path: Path) -> None:
    config_path = tmp_path / "custom.toml"
    config_path.write_text(
        "[project]\nname = 'sample-project'\nversion = '0.1.0'\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="does not contain NetImport config"):
        load_explicit_config(config_path)
