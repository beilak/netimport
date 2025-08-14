from pathlib import Path
from typing import TypedDict

import toml


class NetImportConfigMap(TypedDict):
    ignored_nodes: set[str]
    ignored_dirs: set[str]
    ignored_files: set[str]
    ignore_stdlib: bool
    ignore_external_lib: bool


CONFIG_FILE_NAME = ".netimport.toml"
PYPROJECT_TOML_FILE = "pyproject.toml"
TOOL_SECTION_NAME = "tool"
APP_CONFIG_SECTION_NAME = "netimport"


def parse_config_object(app_config: dict) -> NetImportConfigMap:
    return NetImportConfigMap(
        ignored_nodes=set(app_config.get("ignored_nodes", [])),
        ignored_dirs=set(app_config.get("ignored_dirs", [])),
        ignored_files=set(app_config.get("ignored_files", [])),
        ignore_stdlib=app_config.get("ignore_stdlib", False),
        ignore_external_lib=app_config.get("ignore_external_lib", False),
    )


def load_config(
    project_root: str,
) -> NetImportConfigMap:
    pyproject_path = Path(project_root) / PYPROJECT_TOML_FILE

    if pyproject_path.exists():
        with pyproject_path.open(encoding="utf-8") as f:
            data = toml.load(f)

        if (
            TOOL_SECTION_NAME in data
            and isinstance(data[TOOL_SECTION_NAME], dict)
            and APP_CONFIG_SECTION_NAME in data[TOOL_SECTION_NAME]
            and isinstance(data[TOOL_SECTION_NAME][APP_CONFIG_SECTION_NAME], dict)
        ):
            app_config = data[TOOL_SECTION_NAME][APP_CONFIG_SECTION_NAME]
            return parse_config_object(app_config)

    return NetImportConfigMap(
        ignored_nodes=set(),
        ignored_dirs=set(),
        ignored_files=set(),
        ignore_stdlib=False,
        ignore_external_lib=False,
    )
