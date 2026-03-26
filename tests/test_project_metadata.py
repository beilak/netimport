from pathlib import Path
from typing import cast

import toml


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_project_dependencies_do_not_include_hidden_plotly_backend() -> None:
    with (PROJECT_ROOT / "pyproject.toml").open(encoding="utf-8") as pyproject_file:
        pyproject = toml.load(pyproject_file)

    project_section = cast("dict[str, list[str]]", pyproject["project"])
    dependencies = project_section["dependencies"]

    assert all(not str(dependency).startswith("plotly") for dependency in dependencies)
